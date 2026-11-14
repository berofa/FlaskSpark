"""The guardian as a service: every guardian.interval seconds one run of all checks (in a thread: the checks are
synchronous); after each run the status tiles reload (ev.all.services). In between it watches the service directory
and the NATS servers (watch.StatusWatch) and tells the status tiles of a change at once; a change also brings the next
run forward (at most one per watch.RUN_GAP seconds). Its notifications go straight to the channels (Notifier
queue=False): it reports on the system the queue runs on.

NATS user "guardian" (NATS_GUARDIAN_USER / NATS_GUARDIAN_PASSWORD): reads the service directory (and subscribes to
$KV.services.> to watch it) and the work queue's stream, publishes ev.all.services and its heartbeat.
"""

from __future__ import annotations

import asyncio
import logging
import time

from flaskspark.core import bus, events, status
from flaskspark.core.notify import Notifier
from flaskspark.core.service import AsyncService

from . import watch
from .guard import Guard

log = logging.getLogger(__name__)


class GuardianService(AsyncService):
    NAME, NATS_USER = "guardian", "guardian"

    def __init__(self, nc, guard: Guard, status_watch: watch.StatusWatch | None = None):
        self.nc = nc
        self.guard = guard
        self.task: asyncio.Task | None = None
        self.sub = None
        self.rerun = asyncio.Event()  # the watch saw a change: run the checks again soon
        self._loop: asyncio.AbstractEventLoop | None = None
        if status_watch is None:
            monitors = bus.monitors()
            status_watch = watch.StatusWatch(self.changed, probe=(lambda: watch.nodes_up(monitors)) if monitors
                                             else None)
        self.watch = status_watch

    @classmethod
    async def create(cls, nc) -> GuardianService:
        from flaskspark.core import config

        cfg = config.load()
        return cls(nc, Guard(cfg, Notifier(cfg, queue=False)))

    def details(self) -> dict:
        return self.guard.summary()

    async def check(self) -> None:
        for n in await asyncio.to_thread(self.guard.run_once):
            log.warning("%s: %s - %s", n["level"], n["title"], n["message"])
        try:
            await asyncio.to_thread(self.guard.notifier.flush)  # what could not be sent before
        except Exception:  # noqa: BLE001 - next run again
            log.exception("notification outbox not flushed")
        await self._tell_tiles()
        self.watch.sent()

    async def _tell_tiles(self) -> None:
        try:
            await self.nc.publish(events.subject(status.TOPIC), bus.dumps({}))
        except Exception:  # noqa: BLE001 - NATS away: the tiles reload on their own
            pass

    def changed(self) -> None:
        """The watch saw a change (from the thread of its tick): the tiles reload now, the checks run again soon."""
        loop = self._loop
        if loop is None or loop.is_closed():
            return

        def due():
            self.rerun.set()
            asyncio.ensure_future(self._tell_tiles())
        loop.call_soon_threadsafe(due)

    async def wait(self, started: float) -> None:
        """Until the next run: every watch.TICK seconds a look at what changed; a change brings the run forward."""
        interval = float(self.guard.opt["interval"])
        while time.time() - started < interval:
            await asyncio.to_thread(self.watch.tick)
            if self.rerun.is_set() and time.time() - started >= watch.RUN_GAP:
                return
            await asyncio.sleep(min(watch.TICK, max(0.0, interval - (time.time() - started))))

    async def _run(self) -> None:
        while True:
            started = time.time()
            self.rerun.clear()
            try:
                await self.check()
            except Exception:  # noqa: BLE001 - next run again
                log.exception("guardian run failed")
            await self.wait(started)

    async def watch_directory(self) -> None:
        """The directory's messages into the watch. Without the right to subscribe NATS refuses it (its error
        callback): then only the servers are watched."""
        async def heard(msg):
            self.watch.beat(*watch.message(msg.subject, msg.headers, msg.data))
        try:
            self.sub = await self.nc.subscribe(watch.SUBJECT, cb=heard)
        except Exception as exc:  # noqa: BLE001 - the checks still run
            log.warning("service directory not watched: %s", exc)

    async def start(self) -> None:
        log.info("guardian started (every %ss, %d checks)", self.guard.opt["interval"], len(self.guard.checks))
        self._loop = asyncio.get_running_loop()
        await self.watch_directory()
        self.task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self.task is not None:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        if self.sub is not None:
            try:
                await self.sub.unsubscribe()
            except Exception:  # noqa: BLE001 - the connection is drained afterwards anyway
                pass


main = GuardianService.main
