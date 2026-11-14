"""Names of the services outside the code: "flaskspark-<service>" (flaskspark.core.service.process_name / unit_name),
whatever application runs them; the short name stays inside (subjects, directory keys, NATS users)."""
from __future__ import annotations

import asyncio
import time

import pytest

from flaskspark.core import bus, cli, events, modules, service
from flaskspark.core.module import ServiceInfo
from flaskspark.core.services.guardian import GuardContext, settings
from flaskspark.core.services.guardian.checks import ServicesCheck


def test_process_and_unit_names():
    assert service.process_name("push") == "flaskspark-push"
    assert service.process_name("flaskspark-push") == "flaskspark-push"  # once only
    assert service.unit_name("releases") == "flaskspark-releases.service"


def test_a_service_s_unit_is_a_flaskspark_unit_unless_its_module_names_one():
    assert ServiceInfo("sync", "Sync", "x:main").unit == "flaskspark-sync.service"
    assert ServiceInfo("sync", "Sync", "x:main", unit="other.service").unit == "other.service"


def test_cli_lists_the_names_and_starts_a_service_by_either_name(monkeypatch, capsys):
    started = []
    monkeypatch.setattr(modules, "services", lambda cfg: [ServiceInfo("push", "Push", "x:main")])
    monkeypatch.setattr(cli, "_entry", lambda entry: lambda: started.append(entry))
    cli.main(["services"])
    assert capsys.readouterr().out.split() == ["push", "flaskspark-push", "flaskspark-push.service", "Push", "x:main"]
    cli.main(["service", "push"])
    cli.main(["service", "flaskspark-push"])
    assert started == ["x:main", "x:main"]
    with pytest.raises(SystemExit):
        cli.main(["service", "flaskspark-other"])


def test_an_async_service_connects_under_its_process_name(monkeypatch):
    asked = {}

    async def connect(user, name=None, **options):
        asked.update(user=user, name=name)
        raise ConnectionRefusedError("no NATS in this test")

    monkeypatch.setattr(bus, "connect", connect)

    class Worker(service.AsyncService):
        NAME, NATS_USER = "worker", "workers"

        @classmethod
        async def create(cls, nc):
            return cls()

        async def start(self):
            pass

        async def stop(self):
            pass

    with pytest.raises(ConnectionRefusedError):
        asyncio.run(Worker.run())
    assert asked == {"user": "workers", "name": "flaskspark-worker"}


def test_the_events_connection_is_named_after_the_process(monkeypatch):
    asked = []

    async def connect(user, name=None, **options):
        asked.append((user, name))
        return object()

    monkeypatch.setattr(bus, "connect", connect)
    for user, name, expected in (("web", "", "flaskspark-web"), ("notify", "notifications", "flaskspark-notifications")):
        monkeypatch.setattr(events, "_loop", None)
        monkeypatch.setattr(events, "_nc", None)
        monkeypatch.setattr(events, "_user", None)
        monkeypatch.setattr(events, "_name", None)
        events.init(user, name=name)
        loop = events._loop
        for _ in range(100):
            if events._nc is not None:
                break
            time.sleep(0.01)
        loop.call_soon_threadsafe(loop.stop)
        assert asked[-1] == (user, expected)


def test_guardian_findings_name_the_process_and_keep_their_keys():
    ctx = GuardContext(None, settings(None), 1000.0, read_directory=lambda: {"ok": True, "instances": []},
                       read_nats=lambda: {"ok": True})
    (found,) = ServicesCheck([ServiceInfo("releases", "Releases", "x:main")]).run(ctx)
    assert found.key == "service:releases" and "flaskspark-releases" in found.render()[1]


def test_a_tile_names_the_unit_of_its_service():
    from flaskspark.core import config
    from flaskspark.core.status import StatusContext, WebTile

    tile = WebTile().base(StatusContext(config.load()))
    assert tile["unit"] == "flaskspark-web.service"
    assert tile["process"] == "flaskspark-web"
