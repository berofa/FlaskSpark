"""Leadership of a service with several instances: the instance holding the key KEY of a NATS key-value bucket does the
work, further instances wait to take over.

    leadership = Leadership(nc, "calendar_leader", instance, on_lead=start_work, on_resign=stop_work)
    task = asyncio.create_task(leadership.run(stopped))
    ...
    await leadership.release()   # on a clean stop: the next instance takes over at once

The key is renewed every `refresh` seconds and lives `ttl` seconds (the bucket's TTL): an instance that dies or loses
NATS gives up the lead after at most `ttl` (on_resign when it notices), a renewal that finds another instance's key
resigns at once. An AsyncService reports its role in its heartbeat with {"leader": leadership.leader} in details().
Needs NATS with JetStream; without, nobody leads and run() keeps trying (logged).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from . import bus

log = logging.getLogger(__name__)

TTL = 15.0
REFRESH = 5.0
KEY = "leader"


async def _nothing() -> None:
    pass


class Leadership:
    def __init__(self, nc, bucket: str, instance: str, on_lead: Callable[[], Awaitable[None]] = _nothing,
                 on_resign: Callable[[], Awaitable[None]] = _nothing, ttl: float = TTL, refresh: float = REFRESH):
        if refresh >= ttl:
            raise ValueError("refresh must be shorter than ttl")
        self.nc, self.bucket, self.instance = nc, bucket, instance
        self.on_lead, self.on_resign = on_lead, on_resign
        self.ttl, self.refresh = ttl, refresh
        self.leader = False
        self.kv = None
        self.revision: int | None = None
        self.renewed = 0.0
        self.warned = False

    async def _kv(self):
        if self.kv is None:
            from nats.js.errors import BucketNotFoundError

            js = self.nc.jetstream(timeout=3)
            try:
                self.kv = await js.key_value(self.bucket)
            except BucketNotFoundError:
                self.kv = await js.create_key_value(bucket=self.bucket, ttl=self.ttl, history=1, replicas=bus.replicas())
        return self.kv

    async def step(self) -> bool:
        """One round: take the lead when it is free, renew it when held. Returns whether this instance leads."""
        from nats.js.errors import KeyWrongLastSequenceError

        try:
            kv = await asyncio.wait_for(self._kv(), self.refresh)
            if not self.leader:
                try:
                    self.revision = await kv.create(KEY, self.instance.encode())
                except KeyWrongLastSequenceError:
                    return False  # another instance leads
                log.info("%s leads (%s)", self.instance, self.bucket)
                self.leader, self.renewed = True, time.monotonic()
                await self.on_lead()
            else:
                self.revision = await kv.update(KEY, self.instance.encode(), last=self.revision)
                self.renewed = time.monotonic()
            self.warned = False
        except KeyWrongLastSequenceError:
            log.warning("%s lost the leadership (%s)", self.instance, self.bucket)
            await self.resign()
        except Exception as exc:  # noqa: BLE001 - NATS away: keep trying (the key runs out after ttl)
            (log.debug if self.warned else log.warning)("leader election %s: %s", self.bucket, exc or type(exc).__name__)
            self.warned = True
            self.kv = None
            if self.leader and time.monotonic() - self.renewed >= self.ttl:
                log.warning("%s could not renew the leadership for %.0f s: resigns (%s)", self.instance, self.ttl,
                            self.bucket)
                await self.resign()
        return self.leader

    async def run(self, stopped: asyncio.Event) -> None:
        while not stopped.is_set():
            await self.step()
            try:
                await asyncio.wait_for(stopped.wait(), self.refresh)
            except TimeoutError:
                pass

    async def resign(self) -> None:
        if self.leader:
            self.leader = False
            self.revision = None
            await self.on_resign()

    async def release(self) -> None:
        """Clean stop: resign and delete the key, so another instance takes over at once."""
        was = self.leader
        await self.resign()
        if was and self.kv is not None:
            try:
                await self.kv.delete(KEY)
            except Exception:  # noqa: BLE001 - it runs out after ttl anyway
                pass
