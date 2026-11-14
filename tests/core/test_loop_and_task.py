"""Synchronous services (LoopService), one-off runs (Task) and a service's own heartbeat file, without NATS."""
from __future__ import annotations

import json
import signal
import time

import pytest

from flaskspark.core import directory, service, systemd, task


class Counter(service.LoopService):
    NAME = "counter"
    INTERVAL = 0.01
    NAP = 0.005

    def __init__(self, rounds=3, fail_at=None):
        super().__init__()
        self.rounds, self.fail_at = rounds, fail_at
        self.done: list[int] = []
        self.calls: list[str] = []

    def setup(self):
        self.calls.append("setup")

    def step(self, started):
        n = len(self.done) + 1
        self.done.append(n)
        if n >= self.rounds:
            self.stop()
        if n == self.fail_at:
            raise RuntimeError("broken step")

    def details(self):
        return {"done": len(self.done)}

    def stopped(self):
        self.calls.append("stopped")


@pytest.fixture()
def notified(monkeypatch):
    sent = []
    monkeypatch.setattr(systemd, "notify", lambda state: sent.append(state) or True)
    return sent


@pytest.fixture()
def beacons(monkeypatch):
    started = []

    class FakeBeacon:
        def __init__(self, name, details=None, **kw):
            self.name, self.details, self.stopped = name, details, False
            started.append(self)

        def start(self):
            return self

        def stop(self, timeout=3.0):
            self.stopped = True
    monkeypatch.setattr(directory, "Beacon", FakeBeacon)
    return started


def test_a_loop_service_steps_until_stopped_and_tells_systemd(notified, beacons):
    s = Counter(rounds=3)
    s.run()
    assert s.done == [1, 2, 3] and s.calls == ["setup", "stopped"]
    assert notified == ["READY=1", "WATCHDOG=1", "WATCHDOG=1", "WATCHDOG=1", "STOPPING=1"]
    (beacon,) = beacons
    assert beacon.name == "counter" and beacon.stopped
    details = beacon.details()
    assert details["done"] == 3 and details["step"] == s.last_step and details["step_seconds"] >= 0


def test_a_failing_step_does_not_end_the_loop(notified, beacons, caplog):
    s = Counter(rounds=3, fail_at=2)
    s.run()
    assert s.done == [1, 2, 3]
    assert "counter: step failed" in caplog.text


def test_a_loop_service_keeps_its_interval_and_puts_the_signal_handlers_back(notified, beacons):
    before = signal.getsignal(signal.SIGTERM)
    s = Counter(rounds=2)
    s.INTERVAL = 0.1
    started = time.time()
    s.run()
    assert time.time() - started >= 0.1  # the first wait was a whole interval
    assert signal.getsignal(signal.SIGTERM) is before


def test_heartbeat_name_and_nats_user(notified, beacons, monkeypatch):
    from flaskspark.core import events

    users = []
    monkeypatch.setattr(events, "init", lambda user, **kw: users.append((user, kw)))

    class Named(Counter):
        HEARTBEAT, NATS_USER = "counting", "counter"

    Named(rounds=1).run()
    assert users == [("counter", {"name": "counter"})] and beacons[0].name == "counting"


def test_write_heartbeat(tmp_path):
    service.write_heartbeat(tmp_path, "engine", started=time.time() - 1)
    data = json.loads((tmp_path / "heartbeat-engine.json").read_text())
    assert time.time() - data["ts"] < 5 and data["tick_seconds"] >= 1
    service.write_heartbeat(tmp_path / "missing", "engine")  # never raises


class Cleanup(task.Task):
    NAME = "cleanup"

    def run(self, cfg):
        return {"removed": 2, "app": cfg.app_name}


class Broken(task.Task):
    NAME = "broken"

    def run(self, cfg):
        raise RuntimeError("no disk")


def test_a_task_prints_its_result_as_json(capsys):
    Cleanup.main()
    assert json.loads(capsys.readouterr().out) == {"removed": 2, "app": "demo-app"}


def test_a_failing_task_ends_with_exit_code_1(capsys, caplog):
    with pytest.raises(SystemExit) as exit_:
        Broken.main()
    assert exit_.value.code == 1 and "broken failed" in caplog.text
    assert capsys.readouterr().out == ""


def test_a_task_needs_run():
    with pytest.raises(TypeError):
        task.Task()


def test_cli_units_and_guard_check(monkeypatch, capsys):
    from flaskspark.core import cli, modules
    from flaskspark.core.module import ServiceInfo
    from flaskspark.core.services import guardian
    from flaskspark.core.services.guardian.base import WARNING, Finding

    monkeypatch.setattr(modules, "services", lambda cfg: [ServiceInfo("web", "Web", "x:main", unit="demo-web.service"),
                                                         ServiceInfo("push", "Push", "x:main")])
    cli.main(["units"])
    assert capsys.readouterr().out == "demo-web.service\nflaskspark-push.service\n"  # a unit of its own, the default

    monkeypatch.setattr(guardian, "default_checks", lambda cfg: [])
    monkeypatch.setattr(guardian, "findings", lambda cfg, checks, ctx: [Finding("x", WARNING, "Disk", "almost full",
                                                                                 grace=60)])
    with pytest.raises(SystemExit) as exit_:
        cli.main(["guard-check"])
    assert exit_.value.code == 1
    assert capsys.readouterr().out == "[warning] Disk: almost full (reported after 60 s)\n1 finding(s).\n"

    # source texts with %(name)s are rendered with their params, not printed raw
    monkeypatch.setattr(guardian, "findings", lambda cfg, checks, ctx: [
        Finding("service:w", WARNING, "%(label)s: no heartbeat", "since %(name)s", params={"label": "Worker",
                                                                                         "name": "boot"})])
    with pytest.raises(SystemExit):
        cli.main(["guard-check"])
    assert capsys.readouterr().out.splitlines()[0] == "[warning] Worker: no heartbeat: since boot"


def test_config_enabled():
    from flaskspark.core.config import Config

    cfg = Config({"mail": {"enabled": False}, "shop": {}})
    assert not cfg.enabled("mail") and cfg.enabled("shop") and cfg.enabled("other")
    assert not cfg.enabled("other", default=False)
