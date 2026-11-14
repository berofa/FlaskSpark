"""Service directory: every instance of every service tells over NATS who it is, where it runs and how it is, so the
status tiles and the guardian see the services wherever they run (other hosts, containers; no systemd needed).

- Heartbeat: on ms.<service>.heartbeat every EVERY seconds, the same in the key-value bucket BUCKET under
  <service>.<instance> (TTL: an instance that dies drops out by itself; a clean stop deletes its key at once):

      {service, instance, host, pid, version, role, ok, details, started, memory, ts}

  service: the name of the service (ServiceInfo.name, e.g. "push"); role: "leader" | "standby" for services with a
  leadership (flaskspark.core.leader), else None; ok: the instance says it works; details: what the service adds
  (counts, its last step, ...).
- Writers: AsyncService (flaskspark.core.service) on its own connection through Registry; synchronous processes (the
  web app) through Beacon over the process's events connection (flaskspark.core.events).
- Readers: read() over a short connection of its own (stream info and the last message of each key: no consumer, so
  the rights stay small); the status tiles and the guardian group the instances by service.

Without NATS, or with a NATS without JetStream, nothing here raises or blocks a service: the heartbeat still goes out
on its subject when it can, the bucket is tried again after KV_RETRY seconds, and the readers report the directory as
not usable.

NATS rights of a service user: publish on ms.<service>.> and the bucket's API ($KV.services.>, $JS.API.STREAM.INFO.
KV_services, ...); readers need $JS.API.STREAM.INFO.KV_services and $JS.API.DIRECT.GET.KV_services / STREAM.MSG.GET.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import socket
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from . import bus

log = logging.getLogger(__name__)

BUCKET = "services"
STREAM = f"KV_{BUCKET}"
TTL = 60.0  # seconds an instance stays in the directory after its last heartbeat
EVERY = 10.0  # seconds between heartbeats
STALE = 35.0  # a heartbeat older than this: the instance is gone (or hangs)
KV_RETRY = 60.0  # seconds without writes to the bucket after a failure (no rights yet, no JetStream)
LEADER, STANDBY = "leader", "standby"

PROCESS_STARTED = time.time()  # about when this process started (the directory is imported early)
_version: str | None = None
_KEY_CHARS = re.compile(r"[^-_=a-zA-Z0-9]")


def host() -> str:
    """Where this instance runs (APP_HOST overrides, e.g. the host of a container)."""
    return os.environ.get("APP_HOST") or socket.gethostname()


def new_instance() -> str:
    """A name for this process's instance: host and a short random part (a restart is a new instance)."""
    return f"{host()}-{uuid.uuid4().hex[:6]}"


def version() -> str:
    """The code this process runs: APP_VERSION, else the version of the application's distribution (its name:
    APP_NAME), else ""."""
    global _version
    if _version is None:
        _version = os.environ.get("APP_VERSION", "")
        if not _version:
            from importlib.metadata import PackageNotFoundError, version as dist_version

            from . import paths

            try:
                _version = dist_version(paths.APP_NAME)
            except (PackageNotFoundError, ValueError):
                _version = ""
    return _version


def _memory() -> int | None:
    """Resident memory of this process in bytes (Linux), else None."""
    try:
        pages = int(Path("/proc/self/statm").read_text().split()[1])
        return pages * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError):
        return None


def subject(service: str) -> str:
    return f"ms.{service}.heartbeat"


def key(service: str, instance: str) -> str:
    """The instance's key in the bucket (only the characters NATS allows in a key)."""
    return f"{_KEY_CHARS.sub('_', service)}.{_KEY_CHARS.sub('_', instance)}"


def beat(service: str, instance: str, *, role: str | None = None, ok: bool = True, details: dict | None = None,
         started: float | None = None) -> dict:
    """One heartbeat of an instance."""
    return {"service": service, "instance": instance, "host": host(), "pid": os.getpid(), "version": version(),
            "role": role, "ok": bool(ok), "details": details or {}, "started": started, "memory": _memory(),
            "ts": time.time()}


def from_details(details: dict) -> tuple[dict, str | None, bool]:
    """The heartbeat fields a service put into its details ("leader": bool, "ok": bool) taken out:
    (details, role, ok)."""
    details = dict(details or {})
    details.pop("instance", None)
    leader = details.pop("leader", None)
    role = None if leader is None else (LEADER if leader else STANDBY)
    ok = details.pop("ok", True)
    return details, role, ok is not False


# --- writing ----------------------------------------------------------------------------------------------------------
class Registry:
    """Writes the heartbeats of the instances of one process into the directory, on an asyncio NATS connection."""

    def __init__(self, nc, clock: Callable[[], float] = time.time):
        self.nc = nc
        self.kv = None
        self.clock = clock
        self.failed_at: float | None = None
        self.warned = False

    async def _kv(self):
        if self.kv is None:
            from nats.js.errors import BucketNotFoundError

            js = self.nc.jetstream(timeout=3)
            try:
                self.kv = await js.key_value(BUCKET)
            except BucketNotFoundError:
                self.kv = await js.create_key_value(bucket=BUCKET, ttl=TTL, history=1, replicas=bus.replicas())
        return self.kv

    async def publish(self, data: dict) -> bool:
        """The heartbeat on its subject and in the bucket; True when it reached NATS. Never raises."""
        try:
            await self.nc.publish(subject(data["service"]), bus.dumps(data))
        except Exception as exc:  # noqa: BLE001 - NATS away: next round
            log.debug("heartbeat %s: %s", data.get("service"), exc)
            return False
        if self.failed_at is not None and self.clock() - self.failed_at < KV_RETRY:
            return True
        try:
            kv = await asyncio.wait_for(self._kv(), 5)
            await asyncio.wait_for(kv.put(key(data["service"], data["instance"]), bus.dumps(data)), 3)
            self.failed_at, self.warned = None, False
        except Exception as exc:  # noqa: BLE001 - no rights, no JetStream: the subject still has it
            self.failed_at = self.clock()
            self.kv = None
            (log.debug if self.warned else log.warning)("service directory not written (%s): %s", BUCKET,
                                                        exc or type(exc).__name__)
            self.warned = True
        return True

    async def remove(self, service: str, instance: str) -> None:
        """A clean stop: the instance leaves the directory at once. Never raises."""
        if self.failed_at is not None and self.kv is None:
            return  # the bucket was not reachable: nothing to remove (it drops out after TTL anyway)
        try:
            kv = await asyncio.wait_for(self._kv(), 3)
            await asyncio.wait_for(kv.delete(key(service, instance)), 3)
        except Exception as exc:  # noqa: BLE001 - it drops out after TTL anyway
            log.debug("service directory: %s not removed: %s", instance, exc)


class Beacon:
    """Heartbeats of a synchronous process (the web app, a script that runs long) over the process's events connection
    (flaskspark.core.events.init before). beat() never blocks or raises; start() sends them from a thread of its own
    every `every` seconds with what `details()` tells at that moment."""

    def __init__(self, service: str, instance: str | None = None, details: Callable[[], dict] | None = None,
                 every: float = EVERY):
        self.service = service
        self.instance = instance or new_instance()
        self.details = details or dict
        self.every = every
        self.started = PROCESS_STARTED
        self.registry: Registry | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def heartbeat(self) -> dict:
        try:
            details, role, ok = from_details(self.details() or {})
        except Exception as exc:  # noqa: BLE001 - a broken detail must not stop the heartbeat
            details, role, ok = {"error": str(exc)[:200]}, None, False
        return beat(self.service, self.instance, role=role, ok=ok, details=details, started=self.started)

    def beat(self) -> bool:
        """Send one heartbeat; False while the process is not connected."""
        from . import events

        data = self.heartbeat()

        async def send(nc):
            if self.registry is None or self.registry.nc is not nc:
                self.registry = Registry(nc)
            await self.registry.publish(data)
        return events.call(send)

    def start(self) -> Beacon:
        if self._thread is None:
            def run():
                while not self._stop.is_set():
                    self.beat()
                    self._stop.wait(self.every)
            self._thread = threading.Thread(target=run, name=f"heartbeat-{self.service}", daemon=True)
            self._thread.start()
        return self

    def stop(self, timeout: float = 3.0) -> None:
        """No more heartbeats; the instance leaves the directory (waits up to `timeout` for it)."""
        from . import events

        self._stop.set()
        done = threading.Event()

        async def remove(nc):
            try:
                await (self.registry or Registry(nc)).remove(self.service, self.instance)
            finally:
                done.set()
        if events.call(remove):
            done.wait(timeout)


# --- reading ----------------------------------------------------------------------------------------------------------
def unreachable(error: str) -> dict:
    return {"ok": False, "error": error, "missing": False, "instances": []}


async def read_with(nc, timeout: float = 3.0) -> dict:
    """The directory over an open connection: {ok, missing (no bucket yet), instances: [heartbeat + age]}."""
    from nats.js.errors import NotFoundError

    js = nc.jetstream(timeout=timeout)
    try:
        info = await js.stream_info(STREAM, subjects_filter=f"$KV.{BUCKET}.>")
    except NotFoundError:
        return {"ok": True, "missing": True, "instances": []}
    found = []
    for subj in ((info.state.subjects or {}) if info.state else {}):
        try:
            msg = await js.get_msg(STREAM, subject=subj)
        except NotFoundError:
            continue
        if (msg.headers or {}).get("KV-Operation") in ("DEL", "PURGE") or not msg.data:
            continue  # stopped cleanly
        try:
            data = bus.loads(msg.data)
        except ValueError:
            continue
        if isinstance(data, dict):
            found.append(data)
    now = time.time()
    for i in found:
        i["age"] = max(0.0, now - float(i.get("ts") or 0))
    return {"ok": True, "missing": False, "instances": found}


class Directory(ABC):
    """The instances in the directory (abstract: today the NATS key-value bucket)."""

    @abstractmethod
    def read(self) -> dict:
        """{ok, error, missing (no bucket yet), instances: [heartbeat + age]}; never raises."""


class NatsDirectory(Directory):
    """The bucket over a short connection of its own as NATS user `user`."""

    def __init__(self, user: str, timeout: float = 3.0, **connect_options):
        self.user, self.timeout, self.options = user, timeout, connect_options

    def read(self) -> dict:
        from .service import process_name

        async def ask() -> dict:
            nc = await bus.probe(self.user, timeout=self.timeout, name=process_name(f"{self.user}-directory"),
                                 **self.options)
            try:
                return await read_with(nc, self.timeout)
            finally:
                await nc.close()

        try:
            return asyncio.run(asyncio.wait_for(ask(), 3 * self.timeout))
        except Exception as exc:  # noqa: BLE001 - NATS away, no JetStream, no rights, timeout
            return unreachable(f"not reachable: {exc or type(exc).__name__}")


def read(user: str, timeout: float = 3.0, **connect_options) -> dict:
    return NatsDirectory(user, timeout, **connect_options).read()


def by_service(instances: list[dict]) -> dict[str, list[dict]]:
    """{service: [instances, the leader first, then the freshest]}."""
    out: dict[str, list[dict]] = {}
    for i in instances:
        out.setdefault(i.get("service") or "?", []).append(i)
    for found in out.values():
        found.sort(key=lambda i: (i.get("role") != LEADER, i.get("age", 0)))
    return out


def alive(instances: list[dict], stale: float = STALE) -> list[dict]:
    """The instances with a fresh heartbeat."""
    return [i for i in instances if i.get("age", 0) <= stale]


def usable(found: dict) -> bool:
    """A read() the readers go by: answered and the bucket is there."""
    return bool(found.get("ok")) and not found.get("missing")


def live(found: dict, service: str) -> list[dict]:
    """The live instances of a service in a read(), the leader first."""
    if not usable(found):
        return []
    return alive(by_service(found.get("instances") or []).get(service, []))
