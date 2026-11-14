"""Services: a service is a long-running process of its own (a container or a systemd unit later; in a single container
the supervisor starts them all), one process per instance. What every service does the same way lives here:

- Service: name and logging;
- AsyncService: asyncio with its own NATS connection (flaskspark.core.bus), start (optionally retried until NATS is there),
  SIGTERM/SIGINT, a clean stop (drain), heartbeats into the service directory (flaskspark.core.directory) and
  systemd READY/WATCHDOG (flaskspark.core.systemd);
- LoopService: a synchronous loop with a fixed interval (step() every INTERVAL seconds), its heartbeats into the
  service directory from a thread of its own (directory.Beacon, with the time of its last step).

A run once without a process that stays (e.g. started by a timer) is a Task (flaskspark.core.task).

A service with several instances that must not work twice takes the leadership (flaskspark.core.leader.Leadership).

Names: outside the code every service is "flaskspark-<name>" (process_name(); its systemd unit unit_name()), whatever
application runs it: the supervisor's children and log lines, the NATS connections, the status tiles, the guardian's
findings, the command line. Inside the code, on NATS subjects (ms.<name>.heartbeat), in the service directory's keys
and in the NATS users and permissions the short name stays (ServiceInfo.name, e.g. "push").
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
from abc import ABC, abstractmethod
from pathlib import Path

from . import bus, directory, systemd

log = logging.getLogger(__name__)

#: the prefix of every service's name outside the code (FlaskSpark's, not the application's)
PREFIX = "flaskspark"


def process_name(name: str) -> str:
    """The name of the service `name` outside the code: "flaskspark-<name>" (e.g. "push" -> "flaskspark-push").
    A name that already has the prefix stays as it is."""
    return name if name.startswith(f"{PREFIX}-") else f"{PREFIX}-{name}"


def unit_name(name: str) -> str:
    """The systemd unit of the service `name` unless its module names another: "flaskspark-<name>.service"."""
    return f"{process_name(name)}.service"


def configure_logging(verbose: bool = False) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("httpx", "httpcore", "aiohttp.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def write_heartbeat(state_dir: Path, name: str, started: float | None = None) -> None:
    """A service's own note of its last round: <state_dir>/heartbeat-<name>.json {ts, tick_seconds} (e.g. how long it
    was away after a restart, or a fallback for readers on the same host while NATS is away). Who runs and how tells
    the service directory. Never raises."""
    try:
        path = Path(state_dir) / f"heartbeat-{name}.json"
        data = {"ts": time.time()}
        if started is not None:
            data["tick_seconds"] = round(time.time() - started, 2)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data))
        tmp.replace(path)
    except Exception:  # noqa: BLE001 - never stop a service for this
        log.exception("heartbeat %s not written", name)


class Service(ABC):
    """A process of the application. Subclasses set NAME (e.g. "push")."""

    NAME: str = ""

    @classmethod
    @abstractmethod
    def main(cls) -> None:
        """Entry point of the process."""


class AsyncService(Service):
    """A service on asyncio and NATS. Subclasses set NATS_USER, implement create() (build the service on its
    connection), start() and stop(). START_RETRY: seconds between attempts while start() fails; None: a failing start
    ends the process (the supervisor restarts it).

    Heartbeats: every directory.EVERY seconds the instance writes itself into the service directory under HEARTBEAT
    (default NAME, the name of its ServiceInfo) with details() (counts, state; "leader": bool gives its role, "ok":
    False says it cannot work). While NATS is connected it also tells systemd it lives (WATCHDOG=1)."""

    NATS_USER: str = ""
    START_RETRY: float | None = None
    HEARTBEAT: str = ""
    #: this process's instance in the service directory (services with a leadership may set their own)
    instance: str = ""
    _registry: directory.Registry | None = None

    @classmethod
    @abstractmethod
    async def create(cls, nc) -> AsyncService:
        """The service on the connection `nc`."""

    @abstractmethod
    async def start(self) -> None:
        """Start the work (subscriptions, tasks, servers)."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the work (the connection is drained afterwards)."""

    def details(self) -> dict:
        """What the instance adds to its heartbeat (counts, state; "leader": bool, "ok": False when it can't work)."""
        return {}

    @property
    def heartbeat_name(self) -> str:
        return self.HEARTBEAT or self.NAME

    def directory_instance(self) -> str:
        if not self.instance:
            self.instance = directory.new_instance()
        return self.instance

    async def heartbeat(self, nc) -> bool:
        """One heartbeat into the service directory; tells systemd it lives while NATS is connected. Never raises."""
        if not self.heartbeat_name:
            return False
        try:
            try:
                details, role, ok = directory.from_details(self.details() or {})
            except Exception as exc:  # noqa: BLE001 - a broken detail must not stop the heartbeat
                details, role, ok = {"error": str(exc)[:200]}, None, False
            if self._registry is None or self._registry.nc is not nc:
                self._registry = directory.Registry(nc)
            sent = await self._registry.publish(directory.beat(
                self.heartbeat_name, self.directory_instance(), role=role, ok=ok, details=details,
                started=directory.PROCESS_STARTED))
            if sent and nc.is_connected:
                systemd.alive()
            return sent
        except Exception:  # noqa: BLE001
            log.debug("heartbeat %s", self.heartbeat_name, exc_info=True)
            return False

    async def _heartbeats(self, nc) -> None:
        every = min(directory.EVERY, systemd.watchdog_interval() or directory.EVERY)
        while True:
            await self.heartbeat(nc)
            await asyncio.sleep(every)

    async def leave(self, nc) -> None:
        """A clean stop: out of the service directory at once (else after its TTL). Never raises."""
        if self.heartbeat_name and self.instance:
            await (self._registry or directory.Registry(nc)).remove(self.heartbeat_name, self.instance)

    @classmethod
    async def run(cls) -> None:
        from . import config

        config.load()  # the env files into the environment (NATS_*, the module's secrets)
        nc = await bus.connect(cls.NATS_USER, name=process_name(cls.NAME))
        service = await cls.create(nc)
        while True:
            try:
                await service.start()
                break
            except Exception as exc:  # noqa: BLE001
                if cls.START_RETRY is None:
                    raise
                log.warning("%s not ready (%s), again in %.0f s", process_name(cls.NAME), exc, cls.START_RETRY)
                await asyncio.sleep(cls.START_RETRY)
        systemd.ready()
        beats = asyncio.create_task(service._heartbeats(nc))
        stopped = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stopped.set)
        await stopped.wait()
        systemd.stopping()
        beats.cancel()
        await service.stop()
        await service.leave(nc)
        try:
            await nc.drain()
        except Exception:  # noqa: BLE001 - NATS went first (the supervisor stops it last, a crash may not)
            await nc.close()

    @classmethod
    def main(cls) -> None:
        configure_logging()
        asyncio.run(cls.run())


class LoopService(Service):
    """A service that runs step() every INTERVAL seconds until SIGTERM/SIGINT. Subclasses implement setup() (once,
    before systemd READY) and step(); a failing step is logged and the loop goes on. wait() fills the time up to the
    next step (default: sleep in short naps, so a stop is quick; override it e.g. to watch something in between).

    NATS_USER: when set, run() connects the process as that user first (flaskspark.core.events.init; events.emit and
    events.call work then); else setup() may do it. HEARTBEAT (default NAME): its name in the service directory; the
    heartbeats go from a thread of their own every directory.EVERY seconds with details() and its last step
    {step: end of the last step, step_seconds}, so a long step shows as an old step, not as a process gone. After
    every step it tells systemd it lives (WATCHDOG=1)."""

    INTERVAL: float = 30.0
    NATS_USER: str = ""
    HEARTBEAT: str = ""
    NAP: float = 0.5  # seconds between two looks at `stopping` while waiting

    def __init__(self):
        self.stopping = False
        self.last_step: float | None = None
        self.step_seconds: float | None = None
        self.beacon: directory.Beacon | None = None

    @property
    def heartbeat_name(self) -> str:
        return self.HEARTBEAT or self.NAME

    def details(self) -> dict:
        """What the service adds to its heartbeat (counts, state; "leader": bool, "ok": False when it does not work)."""
        return {}

    def heartbeat_details(self) -> dict:
        return {**self.details(), "step": self.last_step, "step_seconds": self.step_seconds}

    @abstractmethod
    def setup(self) -> None:
        """Prepare (connections, state), before the service reports ready."""

    @abstractmethod
    def step(self, started: float) -> None:
        """One round of work (`started`: when it began, time.time())."""

    def interval(self) -> float:
        return self.INTERVAL

    def wait(self, started: float) -> None:
        """Until interval() seconds after the step that began at `started` (or a stop)."""
        while not self.stopping and time.time() - started < self.interval():
            time.sleep(min(self.NAP, max(0.0, self.interval() - (time.time() - started))))

    def stop(self, *_) -> None:
        """End the loop after the current step (SIGTERM/SIGINT)."""
        self.stopping = True

    def stopped(self) -> None:
        """After the last step."""
        log.info("%s stopped", process_name(self.NAME))

    def run(self) -> None:
        import threading

        handlers = {}
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGTERM, signal.SIGINT):
                handlers[sig] = signal.signal(sig, self.stop)
        try:
            if self.NATS_USER:
                from . import events

                events.init(self.NATS_USER, name=self.NAME)
            self.setup()
            if self.heartbeat_name:
                self.beacon = directory.Beacon(self.heartbeat_name, details=self.heartbeat_details).start()
            systemd.ready()
            while not self.stopping:
                started = time.time()
                try:
                    self.step(started)
                except Exception:  # noqa: BLE001 - next round again
                    log.exception("%s: step failed", process_name(self.NAME))
                self.last_step, self.step_seconds = time.time(), round(time.time() - started, 2)
                systemd.alive()
                self.wait(started)
            systemd.stopping()
            if self.beacon is not None:
                self.beacon.stop()
            self.stopped()
        finally:
            for sig, handler in handlers.items():
                signal.signal(sig, handler)

    @classmethod
    def main(cls) -> None:
        from . import config

        configure_logging()
        config.load()  # the env files into the environment (NATS_*, the module's secrets)
        cls().run()
