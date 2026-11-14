"""The guardian's live watch of the service directory (StatusWatch), the status tiles' fallback to systemd while the
directory can't be read, and the helpers modules use for their tiles (ask, failing, read_json, …)."""
from __future__ import annotations

import json
import time

from flaskspark.core import config, status
from flaskspark.core.module import ServiceInfo
from flaskspark.core.services.guardian import watch


class Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


def make_watch(probe=None, **kw):
    clock, emitted = Clock(), []
    w = watch.StatusWatch(lambda: emitted.append(clock.now), probe=probe, clock=clock, min_gap=2.0, stale=35.0,
                          settle=15.0, probe_every=3.0, **kw)
    return w, clock, emitted


def test_instances_heard_at_the_start_are_no_change():
    w, clock, emitted = make_watch()
    w.beat("push.host-1", {"ok": True})
    clock.now += 5
    w.beat("web.host-1", {"ok": True})  # within settle: it was there before the subscription
    assert not w.tick() and emitted == []


def test_new_stopped_failing_and_stale_instances_are_changes():
    w, clock, emitted = make_watch()
    w.beat("push.host-1", {"ok": True})
    clock.now += 20
    w.beat("push.host-2", {"ok": True})
    assert w.tick() and w.pending == set()
    clock.now += 1
    w.beat("push.host-2", None)  # a clean stop
    assert not w.tick()  # within min_gap: pending
    clock.now += 2
    assert w.tick() and len(emitted) == 2
    clock.now += 3
    w.beat("push.host-1", {"ok": False})
    assert w.tick()
    clock.now += 3
    w.beat("push.host-1", {"ok": False, "role": "leader"})
    assert w.tick()
    clock.now += 40  # no heartbeat for longer than `stale`
    assert w.tick() and len(emitted) == 5
    w.beat("push.host-1", {"ok": False, "role": "leader"})
    clock.now += 3
    assert w.tick()  # back
    clock.now += 3
    w.beat("push.host-1", {"ok": False, "role": "leader"})
    assert not w.tick()  # the same again: nothing changed


def test_nats_nodes_are_probed_and_a_change_counts():
    nodes = iter([frozenset({"a", "b"}), frozenset({"a", "b"}), frozenset({"a"})])
    w, clock, emitted = make_watch(probe=lambda: next(nodes))
    assert not w.tick()  # the first look
    clock.now += 1
    assert not w.tick()  # not due yet
    clock.now += 3
    assert not w.tick()
    clock.now += 3
    assert w.tick() and emitted


def test_a_broken_probe_does_not_stop_the_watch():
    def probe():
        raise OSError("down")
    w, clock, emitted = make_watch(probe=probe)
    assert not w.tick()


def test_sent_clears_what_is_pending():
    w, clock, emitted = make_watch()
    w.beat("a.1", {})
    clock.now += 20
    w.beat("a.2", {})
    w.sent()
    clock.now += 5
    assert not w.tick() and not emitted


def test_messages_of_the_bucket():
    assert watch.message("$KV.services.push.host-1", None, b'{"ok": true}') == ("push.host-1", {"ok": True})
    assert watch.message("$KV.services.push.host-1", {"KV-Operation": "DEL"}, b"") == ("push.host-1", None)
    assert watch.message("$KV.services.push.host-1", None, b"broken") == ("push.host-1", {})


def test_nodes_up_never_raises():
    assert watch.nodes_up(["http://127.0.0.1:9"], timeout=0.2) == frozenset()


# --- status: systemd while the directory can't be read ------------------------------------------------------------
NOW = time.time()
SHOWN = """Id=demo-worker.service
ActiveState=active
SubState=running
ActiveEnterTimestamp=@{since}
NRestarts=2
MemoryCurrent=52428800
Result=success

Id=demo-broken.service
ActiveState=failed
SubState=failed
ActiveEnterTimestamp=
NRestarts=0
MemoryCurrent=[not set]
Result=exit-code
""".format(since=int(NOW - 600))


def ctx_without_nats(**kw):
    return status.StatusContext(None, NOW, read_directory=lambda: {"ok": True, "instances": []},
                                read_nats=lambda: {"ok": False, "error": "refused"}, **kw)


def test_systemctl_show_is_parsed(monkeypatch):
    import subprocess

    class Done:
        stdout = SHOWN
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: Done())
    units = status.systemd_units(["demo-worker.service", "demo-broken.service"])
    assert units["demo-worker.service"]["ActiveState"] == "active"
    assert units["demo-broken.service"]["Result"] == "exit-code"
    assert status.systemd_units([]) == {}


def test_without_the_directory_a_service_with_a_unit_shows_systemd(monkeypatch):
    import subprocess

    class Done:
        stdout = SHOWN
    asked = []
    monkeypatch.setattr(subprocess, "run", lambda args, **kw: asked.append(args) or Done())
    worker = status.ServiceTile(ServiceInfo("worker", "Worker", "x:main", unit="demo-worker.service"))
    broken = status.ServiceTile(ServiceInfo("broken", "Broken", "x:main", unit="demo-broken.service"))
    plain = status.ServiceTile(ServiceInfo("plain", "Plain", "x:main"))
    t_worker, t_broken, t_plain = status.collect(None, ctx=ctx_without_nats(), shown=[worker, broken, plain])
    assert (t_worker["level"], t_worker["summary"]) == ("ok", "running for 10 min")
    assert ["Restarts by systemd", "2"] in t_worker["details"] and ["Memory", "50 MB"] in t_worker["details"]
    assert t_worker["details"][-1][0] == "Source" and "systemd on this host" in t_worker["details"][-1][1]
    assert (t_broken["level"], t_broken["summary"]) == ("error", "not running (failed)")
    assert (t_plain["level"], t_plain["summary"]) == ("warning", "unknown")  # flaskspark-plain.service: not there


def test_with_the_directory_systemd_is_not_asked():
    asked = []
    ctx = status.StatusContext(None, NOW, read_directory=lambda: {"ok": True, "instances": [
        {"service": "worker", "instance": "w-1", "host": "h", "ts": NOW - 1, "age": 1.0}]},
        read_nats=lambda: {"ok": True}, read_systemd=lambda units: asked.append(units) or {})
    worker = status.ServiceTile(ServiceInfo("worker", "Worker", "x:main", unit="demo-worker.service"))
    (t,) = status.collect(None, ctx=ctx, shown=[worker])
    assert t["level"] == "ok" and asked == []


def test_core_tiles_find_the_unit_of_their_service(monkeypatch):
    from flaskspark.core import modules
    from flaskspark.core.core_module import Core

    class WithUnits(Core):
        SERVICES = (ServiceInfo("web", "Web", "x:main", unit="demo-web.service"),)

        def __init__(self, cfg=None):
            self.cfg = cfg
    monkeypatch.setattr(modules, "load", lambda cfg: [WithUnits()])
    ctx = ctx_without_nats(read_systemd=lambda units: {u: {"Id": u, "ActiveState": "activating", "SubState": "start"}
                                                       for u in units})
    assert ctx.unit_of("web") == "demo-web.service" and ctx.unit_of("other") == ""
    (t,) = status.collect(None, ctx=ctx, shown=[status.WebTile()])
    assert t["unit"] == "demo-web.service" and ["systemd", "demo-web.service: activating (start)"] in t["details"]


# --- helpers of the modules' tiles ----------------------------------------------------------------------------------
def test_ask_a_service_for_its_status():
    ctx = status.StatusContext(None, NOW, read_directory=lambda: {"ok": True, "instances": []},
                               read_nats=lambda: {"ok": True})
    assert ctx.ask(lambda user: {"ok": True, "user": user}) == {"ok": True, "user": "web"}

    def silent(user):
        raise TimeoutError("nobody answered")
    assert ctx.ask(silent) == {"ok": False, "error": "nobody answered"}
    assert ctx_without_nats().ask(lambda user: {"ok": True}) == status.NO_NATS
    t = {"level": "ok", "summary": "", "details": []}
    status.StatusContext.not_answering(t, {"error": "timeout"})
    assert (t["level"], t["summary"]) == ("error", "not answering") and t["details"][0][:2] == ["Error", "timeout"]


def test_failing_items_and_counts():
    t = {"level": "ok", "details": []}
    status.failing(t, [{"label": "Main account", "owner": "user.demo", "error": "login refused"},
                       {"label": "Second", "error": "x" * 200}])
    assert t["level"] == "warning"
    assert t["details"][0] == ["Main account (user.demo)", "login refused", "login refused"]
    assert len(t["details"][1][1]) == status.ERROR_CHARS and len(t["details"][1][2]) == 200
    t = {"level": "ok", "details": []}
    status.failing(t, 0)
    assert t == {"level": "ok", "details": []}
    status.failing(t, 3, one="account", many="accounts")
    assert t["details"] == [["Failing", "3 accounts", "3 accounts"]]


def test_small_helpers(tmp_path):
    assert status.thousands(1234567) == "1'234'567" and status.thousands(None) == "0"
    (tmp_path / "state.json").write_text(json.dumps({"ts": 1}))
    (tmp_path / "list.json").write_text("[1]")
    assert status.read_json(tmp_path / "state.json") == {"ts": 1}
    assert status.read_json(tmp_path / "list.json") == {} and status.read_json(tmp_path / "missing.json") == {}
    assert status.next_run(None) == "on request only"
    assert status.next_run(0.0) == "on request only" and len(status.next_run(NOW)) == len("13.11. 08:00")


def test_the_demo_app_s_units_are_flaskspark_units():
    ctx = status.StatusContext(config.load(), NOW, read_directory=lambda: {"ok": True, "instances": []},
                               read_nats=lambda: {"ok": True}, read_systemd=lambda units: {"asked": units})
    assert ctx.units() == {"asked": ["flaskspark-push.service", "flaskspark-router.service", "flaskspark-web.service"]}


def test_a_unit_systemd_does_not_know_leaves_the_tile_unknown():
    unknown = {"Id": "flaskspark-worker.service", "LoadState": "not-found", "ActiveState": "inactive"}
    ctx = ctx_without_nats(read_systemd=lambda units: {u: dict(unknown) for u in units})
    (t,) = status.collect(None, ctx=ctx, shown=[status.ServiceTile(ServiceInfo("worker", "Worker", "x:main"))])
    assert (t["level"], t["summary"]) == ("warning", "unknown")
    assert t["unit"] == "flaskspark-worker.service" and t["process"] == "flaskspark-worker"
