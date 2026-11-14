"""Supervisor: every service of the application as child processes of one process (a single container, development).

    <app> run          NATS (optional), the services of the core and the modules, the router

Before anything starts, the database is brought to the heads of the migrations (flaskspark.core.db.migrations, with a
backup first when there is something to do); a database that needs `<app> db adopt` stops the start.

Each service runs in its own process (as it will in its own container later), named "flaskspark-<service>" in the log
(flaskspark.core.service.process_name; also flaskspark-nats); the router, a service of the core, starts last; a process
that ends is started again
after a pause that grows with every quick failure. SIGTERM/SIGINT stops all of them (router first, NATS last).

NATS: with `nats.embedded: true` in config.yaml (or NATS_EMBEDDED=1) the supervisor starts a single local node
(nats-server on 127.0.0.1:NATS_PORT, JetStream in STATE_DIR/nats) and points the services to it; otherwise they use
NATS_URL (e.g. a cluster).

systemd: as a unit with Type=notify (and WatchdogSec=) the supervisor reports READY once every child started and
WATCHDOG while its loop runs; the children never see NOTIFY_SOCKET (only the supervisor talks to systemd).
"""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field

from . import config as _config, modules, paths, systemd
from .service import process_name

log = logging.getLogger("supervisor")

QUICK = 30.0  # a process that ends within this many seconds counts as a failed start
MAX_PAUSE = 60.0
NATS = process_name("nats")  # the embedded nats-server among the children
ROUTER = "router"  # the core's service in front of the others


@dataclass
class Child:
    name: str
    args: list[str]
    process: subprocess.Popen | None = None
    started: float = 0.0
    failures: int = 0
    next_start: float = 0.0
    env: dict = field(default_factory=dict)

    def start(self, env: dict) -> None:
        log.info("start %s", self.name)
        self.process = subprocess.Popen(self.args, env={**env, **self.env}, cwd=str(paths.PROJECT_DIR))
        self.started = time.time()

    def poll(self) -> int | None:
        return None if self.process is None else self.process.poll()


def _embedded_nats(cfg) -> bool:
    value = os.environ.get("NATS_EMBEDDED")
    if value is not None:
        return value.lower() in ("1", "true", "yes")
    return bool(cfg.section("nats").get("embedded", False))


def children(cfg) -> list[Child]:
    python = sys.executable
    out: list[Child] = []
    if _embedded_nats(cfg):
        server = shutil.which(os.environ.get("NATS_SERVER") or "nats-server")
        if server is None:
            raise SystemExit("nats-server not found (NATS_SERVER), or set nats.embedded: false and NATS_URL")
        port = os.environ.get("NATS_PORT") or str(cfg.section("nats").get("port", 4222))
        store = paths.state_dir("nats")
        out.append(Child(NATS, [server, "-a", "127.0.0.1", "-p", port, "-js", "-sd", str(store)]))
        os.environ.setdefault("NATS_URL", f"nats://127.0.0.1:{port}")
    services = modules.services(cfg)
    # the router (a service of the core like the others) last: it starts after and stops before what it routes to
    for service in [s for s in services if s.name != ROUTER] + [s for s in services if s.name == ROUTER]:
        out.append(Child(process_name(service.name), [python, "-m", "flaskspark.core.cli", "service", service.name]))
    return out


#: systemd's variables stay with the supervisor: it alone talks to systemd for the whole process tree
SYSTEMD_ONLY = ("NOTIFY_SOCKET", "WATCHDOG_USEC", "WATCHDOG_PID")


def child_env(environ) -> dict:
    """The environment of the children: the supervisor's without systemd's notification variables."""
    return {k: v for k, v in environ.items() if k not in SYSTEMD_ONLY}


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    cfg = _config.load()
    from .db import migrations

    migrations.upgrade_on_start(cfg)
    procs = children(cfg)
    env = child_env(os.environ)
    stopping = False

    def _stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    for child in procs:
        child.start(env)
        if child.name == NATS:
            time.sleep(1.0)  # the services connect at once
    systemd.ready()
    watchdog, alive = systemd.watchdog_interval(), 0.0
    while not stopping:
        now = time.time()
        if watchdog is not None and now - alive >= watchdog:
            systemd.alive()  # the supervisor's loop runs: it restarts what hangs below it
            alive = now
        for child in procs:
            code = child.poll()
            if child.process is not None and code is not None:
                quick = now - child.started < QUICK
                child.failures = child.failures + 1 if quick else 0
                pause = min(MAX_PAUSE, 2.0 ** child.failures) if quick else 1.0
                log.warning("%s ended (exit %s), again in %.0f s", child.name, code, pause)
                child.process, child.next_start = None, now + pause
            if child.process is None and now >= child.next_start:
                child.start(env)
        time.sleep(0.5)
    systemd.stopping()
    for child in reversed(procs):  # router first, NATS last
        if child.process is not None and child.poll() is None:
            child.process.terminate()
            try:
                child.process.wait(15)
            except subprocess.TimeoutExpired:
                child.process.kill()
    log.info("stopped")
