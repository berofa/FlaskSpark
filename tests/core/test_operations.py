"""The core's service building blocks without NATS: systemd notifications, the service directory's logic, the work
queue's jobs, notifications, status tiles, the guardian and the backup (fakes instead of NATS and channels)."""
from __future__ import annotations

import gzip
import json
import socket
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import pytest

from flaskspark.core import backup, config, directory, notify, queue, status, systemd
from flaskspark.core.config import Config
from flaskspark.core.core_module import Core
from flaskspark.core.module import ServiceInfo
from flaskspark.core.services.guardian import Guard, GuardContext, settings
from flaskspark.core.services.guardian.base import CRITICAL, WARNING, Finding, GuardCheck
from flaskspark.core.services.guardian.checks import NatsCheck, NotifyQueueCheck, ServicesCheck


# --- systemd --------------------------------------------------------------------------------------------------------
def test_systemd_notifies_over_its_socket(tmp_path, monkeypatch):
    path = tmp_path / "notify.sock"
    server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    server.bind(str(path))
    try:
        monkeypatch.setenv("NOTIFY_SOCKET", str(path))
        assert systemd.ready() and systemd.alive()
        assert server.recv(100) == b"READY=1"
        assert server.recv(100) == b"WATCHDOG=1"
    finally:
        server.close()


def test_systemd_outside_systemd_does_nothing(monkeypatch):
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    assert systemd.ready() is False
    monkeypatch.setenv("NOTIFY_SOCKET", "/nonexistent/socket")
    assert systemd.alive() is False  # logged, never raised


def test_systemd_watchdog_interval(monkeypatch):
    monkeypatch.delenv("WATCHDOG_PID", raising=False)
    monkeypatch.setenv("WATCHDOG_USEC", "20000000")
    assert systemd.watchdog_interval() == 10.0
    monkeypatch.setenv("WATCHDOG_PID", "1")  # another process's watchdog
    assert systemd.watchdog_interval() is None
    monkeypatch.delenv("WATCHDOG_USEC")
    assert systemd.watchdog_interval() is None


def test_supervisor_keeps_systemd_to_itself():
    from flaskspark.core import supervisor

    env = supervisor.child_env({"NOTIFY_SOCKET": "/run/x", "WATCHDOG_USEC": "1", "WATCHDOG_PID": "2", "PATH": "/bin"})
    assert env == {"PATH": "/bin"}


# --- service directory ------------------------------------------------------------------------------------------------
def test_heartbeat_fields_from_the_details():
    details, role, ok = directory.from_details({"leader": True, "ok": False, "instance": "x", "done": 3})
    assert (details, role, ok) == ({"done": 3}, directory.LEADER, False)
    assert directory.from_details({"leader": False})[1:] == (directory.STANDBY, True)
    assert directory.from_details({})[1:] == (None, True)
    beat = directory.beat("push", "host-1", ok=True, details={"n": 1})
    assert {"service", "instance", "host", "pid", "version", "role", "ok", "details", "ts"} <= set(beat)


def test_directory_keys_and_grouping():
    assert directory.key("my service", "host.a/1") == "my_service.host_a_1"
    instances = [{"service": "a", "instance": "1", "age": 50}, {"service": "a", "instance": "2", "age": 3},
                 {"service": "a", "instance": "3", "age": 9, "role": "leader"}, {"service": "b", "age": 1}]
    grouped = directory.by_service(instances)
    assert [i["instance"] for i in grouped["a"]] == ["3", "2", "1"]  # the leader first, then the freshest
    found = {"ok": True, "missing": False, "instances": instances}
    assert [i["instance"] for i in directory.live(found, "a")] == ["3", "2"]  # the stale one is gone
    assert directory.live({"ok": True, "missing": True, "instances": instances}, "a") == []
    assert not directory.usable(directory.unreachable("away"))


def test_beacon_without_a_connection_never_raises():
    beacon = directory.Beacon("web", details=lambda: 1 / 0)
    assert beacon.heartbeat()["ok"] is False  # a broken detail: an error in the heartbeat, not an exception
    assert beacon.beat() is False  # no events.init: nothing sent
    beacon.stop()


# --- work queue -----------------------------------------------------------------------------------------------------
def test_job_subjects_and_retries():
    assert queue.subject("notify", 1) == "job.notify.p1"
    for kind, priority in (("a.b", 2), ("", 2), ("x", 4), ("a>", 1)):
        with pytest.raises(ValueError):
            queue.subject(kind, priority)
    assert [queue.retry_delay(n) for n in (1, 2, 6, 7, 99)] == [5, 15, 300, 300, 300]
    job = queue.Job("notify", {"title": "x"}, priority=queue.HIGH, key="k")
    assert queue.Job.from_dict(job.to_dict()).to_dict() == job.to_dict()


# --- notifications --------------------------------------------------------------------------------------------------
class FakeChannel(notify.NotificationChannel):
    kind = "fake"

    def __init__(self, fail: bool = False):
        self.fail, self.delivered = fail, []

    def deliver(self, entry, title=None):
        if self.fail:
            raise ConnectionError("down")
        self.delivered.append(title or entry["title"])


def cfg_of(**data) -> Config:
    return Config(data)


def test_ntfy_channel_from_the_environment():
    assert notify.NtfyChannel.from_env({}) is None
    assert notify.NtfyChannel.from_env({"NTFY_URL": "https://ntfy.example"}) is None
    channel = notify.NtfyChannel.from_env({"NTFY_URL": "https://ntfy.example/", "NTFY_TOPIC": "alerts",
                                           "NTFY_TOKEN": "secret"})
    assert channel.endpoint == "https://ntfy.example/alerts"
    headers = channel.headers({"title": "Hi", "priority": 4, "tags": ["warning"], "click": "https://x"})
    assert headers["Authorization"] == "Bearer secret" and headers["Tags"] == "warning" and headers["Priority"] == "4"


def test_ntfy_refusals_and_failures():
    import httpx

    def answering(code):
        def post(url, **kwargs):
            return httpx.Response(code, request=httpx.Request("POST", url))
        return post

    entry = {"title": "t", "message": "m", "priority": 3}
    notify.NtfyChannel("https://n", "t", post=answering(200)).deliver(entry)
    with pytest.raises(notify.Undeliverable):
        notify.NtfyChannel("https://n", "t", post=answering(400)).deliver(entry)
    with pytest.raises(httpx.HTTPStatusError):
        notify.NtfyChannel("https://n", "t", post=answering(503)).deliver(entry)  # again later
    with pytest.raises(httpx.HTTPStatusError):
        notify.NtfyChannel("https://n", "t", post=answering(429)).deliver(entry)


def test_notifier_sends_keeps_and_sends_late(tmp_path):
    channel = FakeChannel(fail=True)
    notifier = notify.Notifier(cfg_of(), channels_=[channel], outbox_dir=tmp_path)
    assert notifier.queue is False  # the notifications service is off by default
    assert notifier.send("First", "one")  # kept in the outbox
    assert notifier.send("Second", "two")
    assert len((tmp_path / notify.OUTBOX).read_text().splitlines()) == 2
    channel.fail = False
    waiting = [json.loads(line) for line in (tmp_path / notify.OUTBOX).read_text().splitlines()]
    for entry in waiting:
        entry["ts"] -= 600  # written ten minutes ago
    (tmp_path / notify.OUTBOX).write_text("".join(json.dumps(e) + "\n" for e in waiting))
    assert notifier.send("Third", "three")
    assert [t.split(" (late")[0] for t in channel.delivered] == ["First", "Second", "Third"]
    assert "(late, " in channel.delivered[0] and channel.delivered[2] == "Third"
    assert (tmp_path / notify.OUTBOX).read_text() == ""


def test_notifier_mutes_and_needs_a_channel(tmp_path):
    channel = FakeChannel()
    notifier = notify.Notifier(cfg_of(), channels_=[channel], outbox_dir=tmp_path, enabled=lambda c: c != "noisy")
    notifier.send("Muted", "x", category="noisy")
    notifier.send("Loud", "x", category="other")
    assert channel.delivered == ["Loud"]
    assert notify.Notifier(cfg_of(), channels_=[], outbox_dir=tmp_path).send("Nobody", "x") is False


def test_notifier_queues_when_the_service_is_on(tmp_path, monkeypatch):
    from flaskspark.core import jobs

    submitted = []
    monkeypatch.setattr(jobs, "submit", lambda kind, payload, **kw: submitted.append((kind, payload, kw)) or True)
    channel = FakeChannel()
    notifier = notify.Notifier(cfg_of(notifications={"enabled": True}), channels_=[channel], outbox_dir=tmp_path)
    notifier.send("Queued", "x", priority=notify.URGENT, key="once")
    assert channel.delivered == []
    kind, payload, kw = submitted[0]
    assert kind == notify.KIND and payload["channel"] == "fake"
    assert kw["priority"] == queue.HIGH and kw["key"] == "once:fake"
    monkeypatch.setattr(jobs, "submit", lambda *a, **kw: False)  # the queue can't take it: at once instead
    notifier.send("Direct", "x")
    assert channel.delivered == ["Direct"]


def test_channels_registry(monkeypatch):
    monkeypatch.delenv("NTFY_URL", raising=False)
    assert notify.channels() == []
    notify.register_channel(FakeChannel)
    try:
        assert [c.kind for c in notify.channels()] == ["fake"]
    finally:
        notify._factories.remove(FakeChannel)


def test_late_title():
    now = time.time()
    assert notify.late_title({"title": "T", "ts": now - 10}, now) == "T"
    assert notify.late_title({"title": "T", "ts": now - 600}, now).startswith("T (late, ")


# --- the core's optional services -------------------------------------------------------------------------------------
def test_optional_services_are_off_by_default():
    assert [s.name for s in Core(cfg_of()).SERVICES] == ["web", "push", "router"]
    assert [s.name for s in Core().SERVICES] == ["web", "push", "router"]
    core = Core(cfg_of(notifications={"enabled": True}, guardian={"enabled": True}, backup={}))
    assert [s.name for s in core.SERVICES] == ["web", "push", "router", "notifications", "guardian"]
    assert [t.KEY for t in core.status_tiles()] == ["web", "router", "nats", "modules", "notifications", "guardian",
                                                    "backup"]
    assert [type(c).__name__ for c in core.guard_checks()] == ["NatsCheck", "ServicesCheck", "NotifyQueueCheck"]
    assert [s.name for s in Core.SERVICES] == ["web", "push", "router"]  # the class stays as it is


# --- status tiles -----------------------------------------------------------------------------------------------------
NOW = 1_800_000_000.0


def ctx_with(instances=None, nats=None, cfg=None, missing=False):
    found = {"ok": True, "missing": missing, "instances": [{**i, "age": NOW - i["ts"]} for i in instances or []]}
    return status.StatusContext(cfg or config.load(), NOW, read_directory=lambda: found,
                                read_nats=lambda: nats or {"ok": True, "jetstream": True, "nodes": [], "down": []})


def instance(service, ago=2.0, **extra):
    return {"service": service, "instance": f"{service}-1", "host": "host-1", "ts": NOW - ago, "started": NOW - 3600,
            "version": "1.0", **extra}


def test_status_tiles_of_the_demo_app():
    tiles = status.collect(config.load(), ctx=ctx_with([instance("web"), instance("push"), instance("router")]))
    # push: a plain tile (no tile claims it)
    assert [t["key"] for t in tiles] == ["web", "push", "router", "nats", "modules"]
    web, push, _router, nats, mods = tiles
    assert web["level"] == push["level"] == nats["level"] == "ok"
    assert push["summary"] == "running for 60 min"
    assert ["Instance", "host-1 (2 s ago)"] in push["details"]
    assert mods["summary"] == "1 loaded" and ["Loaded", "demo"] in mods["details"]
    # the demo's tables come from create_all, without a revision of the migrations: an earlier history
    assert mods["level"] == "error" and ["Database", "an earlier history: run «db adopt»"] in mods["details"]


def test_status_service_without_heartbeat_and_with_errors():
    tile = status.ServiceTile(ServiceInfo("worker", "Worker", "x:main"))
    t = status.collect(None, ctx=ctx_with([instance("worker", ago=600)]), shown=[tile])[0]
    assert (t["level"], t["summary"]) == ("error", "no heartbeat")
    t = status.collect(None, ctx=ctx_with([instance("worker", ok=False)]), shown=[tile])[0]
    assert (t["level"], t["summary"]) == ("warning", "reports errors")
    t = status.collect(None, ctx=ctx_with(nats={"ok": False, "error": "refused"}), shown=[tile])[0]
    assert (t["level"], t["summary"]) == ("warning", "unknown")


@pytest.fixture(autouse=True)
def no_host_units(monkeypatch):
    """The units of the host running the tests (e.g. a live flaskspark-web) must not count; tests of the systemd
    fallback pass read_systemd themselves."""
    monkeypatch.setattr(status, "systemd_units", lambda units: {})


def test_status_web_tile_answers_without_nats():
    t = status.collect(None, ctx=ctx_with(nats={"ok": False}), shown=[status.WebTile()])[0]
    assert (t["level"], t["summary"]) == ("ok", "answers")


def test_status_nats_tile():
    t = status.collect(None, ctx=ctx_with(nats={"ok": True, "jetstream": False, "version": "2.10"}),
                       shown=[status.NatsTile()])[0]
    assert t["level"] == "warning" and t["details"][-1][0] == "JetStream"
    t = status.collect(None, ctx=ctx_with(nats={"ok": False, "error": "connection refused"}),
                       shown=[status.NatsTile()])[0]
    assert (t["level"], t["summary"]) == ("error", "not reachable")
    nodes = [{"name": "a", "ok": True}, {"name": "b", "ok": False}, {"name": "c", "ok": True}]
    t = status.collect(None, ctx=ctx_with(nats={"ok": True, "jetstream": True, "nodes": nodes, "down": ["b"]}),
                       shown=[status.NatsTile()])[0]
    assert (t["level"], t["summary"]) == ("warning", "2/3 nodes")


def test_status_guardian_and_notification_tiles():
    findings = [{"key": "x", "level": "critical", "title": "Disk full", "message": "99 %"}]
    beat = instance("guardian", details={"last_check": NOW - 10, "interval": 30, "findings": findings})
    t = status.collect(None, ctx=ctx_with([beat]), shown=[status.GuardianTile()])[0]
    assert (t["level"], t["summary"]) == ("error", "1 finding") and ["Disk full", "99 %"] in t["details"]
    beat = instance("notifications", details={"channels": ["ntfy"]})
    tile = status.NotificationsTile(read_queue=lambda: {"ok": True, "waiting": 3, "oldest": 900})
    t = status.collect(None, ctx=ctx_with([beat]), shown=[tile])[0]
    assert t["level"] == "warning" and t["summary"] == "3 waiting"


def test_guardian_findings_and_notifications_in_the_applications_language(tmp_path, app):
    from flaskspark.core import i18n

    assert i18n.gettext("Guardian: %(title)s", locale="de", title="X") == "Wächter: X"
    assert i18n.language(cfg_of(app={"locales": ["de", "en"]})) == "de"
    assert i18n.language(cfg_of(app={"locales": ["de"]}, notifications={"language": "en"})) == "en"

    german = cfg_of(app={"locales": ["de", "en"]})
    found = ServicesCheck([ServiceInfo("worker", "Worker", "x:main")]).run(guard_ctx([instance("worker", ago=900)]))
    title, message = found[0].render(cfg=german)
    assert title == "Worker: kein Lebenszeichen" and "Letztes Lebenszeichen vor 15 Min. von host-1" in message

    check, notifier = Switch(), FakeNotifier()
    guard = Guard(german, notifier, checks=[check, ServicesCheck([ServiceInfo("worker", "Worker", "x:main")])],
                  state_file=tmp_path / "findings.json",
                  context=lambda cfg, opt, now: guard_ctx([instance("worker", ago=900)]))
    check.on = True
    guard.run_once(NOW)
    guard.run_once(NOW + 200)
    assert [t for t, _ in notifier.sent] == ["Wächter: Switched on", "Wächter: Worker: kein Lebenszeichen"]
    summary = guard.summary()["findings"]
    worker = next(f for f in summary if f["key"] == "service:worker")
    assert worker["title"] == "Worker: kein Lebenszeichen" and worker["source"]["title"] == "%(label)s: no heartbeat"
    # the status tile shows the source texts in the visitor's language
    beat = instance("guardian", details={"last_check": NOW - 10, "interval": 30, "findings": summary})
    with app.test_request_context("/", headers={"Accept-Language": "en"}):
        t = status.collect(None, ctx=ctx_with([beat]), shown=[status.GuardianTile()])[0]
    assert "Worker: no heartbeat" in [d[0] for d in t["details"]]

    channel = FakeChannel()
    sent = notify.Notifier(german, channels_=[channel], outbox_dir=tmp_path).send(
        "Resolved: %(title)s", "x", params={"title": "Backup"})
    assert sent and channel.delivered == ["Behoben: Backup"]


def test_the_notification_history_is_opt_in(tmp_path, monkeypatch):
    from flaskspark.core import paths

    monkeypatch.setattr(paths, "STATE_DIR", tmp_path / "state")
    channel = FakeChannel()
    notify.Notifier(cfg_of(), channels_=[channel], outbox_dir=tmp_path).send("Off", "x")
    assert notify.history() == [] and not notify.history_file().exists()
    on = notify.Notifier(cfg_of(notifications={"history": True}), channels_=[channel], outbox_dir=tmp_path,
                         enabled=lambda c: c != "noisy")
    on.send("First", "one", priority=notify.HIGH)
    on.send("Muted", "two", category="noisy")
    found = notify.history()
    assert [(e["title"], e.get("muted", False)) for e in found] == [("Muted", True), ("First", False)]
    assert found[1]["priority"] == notify.HIGH and notify.history(limit=1)[0]["title"] == "Muted"
    assert notify.history_file() == tmp_path / "state" / "notifications" / "history.jsonl"
    monkeypatch.setattr(notify, "HISTORY_MAX_BYTES", 400)
    for n in range(10):
        on.send(f"Message {n}", "x" * 40)
    assert notify.history_file().stat().st_size <= 800 and notify.history()[0]["title"] == "Message 9"


def test_a_broken_tile_does_not_take_the_others():
    class Broken(status.StatusTile):
        KEY, NAME = "broken", "Broken"

        def fill(self, t, ctx):
            raise RuntimeError("boom")

    tiles = status.collect(None, ctx=ctx_with(), shown=[Broken(), status.NatsTile()])
    assert tiles[0]["level"] == "error" and tiles[0]["details"][0][2] == "boom"
    assert tiles[1]["level"] == "ok"


def test_a_tile_may_link_to_a_page():
    class Linked(status.StatusTile):
        KEY, NAME, HREF = "linked", "Linked", "/things"

        def fill(self, t, ctx):
            t["summary"] = "fine"

    class Broken(Linked):
        def fill(self, t, ctx):
            raise RuntimeError("boom")

    linked, broken, nats = status.collect(None, ctx=ctx_with(), shown=[Linked(), Broken(), status.NatsTile()])
    assert linked["href"] == broken["href"] == "/things" and nats["href"] == ""


def test_the_router_tile_shows_its_heartbeat():
    details = {"routes": 2, "open": 3, "websockets": 1, "requests_per_minute": 1200, "upstream_failures": 0}
    (t,) = status.collect(config.load(), ctx=ctx_with([instance("router", details=details)]),
                          shown=[status.RouterTile()])
    assert t["level"] == "ok" and t["process"] == "flaskspark-router" and t["unit"] == "flaskspark-router.service"
    assert ["Routes", "2"] in t["details"]
    assert ["Open connections", "3 requests, 1 WebSockets"] in t["details"]
    assert ["Requests", "1'200 in the last minute"] in t["details"]

    (t,) = status.collect(config.load(), ctx=ctx_with([instance("router", details={**details, "upstream_failures": 4})]),
                          shown=[status.RouterTile()])
    assert t["level"] == "warning" and t["details"][-1][:2] == [
        "Not reachable", "4 requests in the last minute found their service away"]

    (t,) = status.collect(config.load(), ctx=ctx_with([instance("web")]), shown=[status.RouterTile()])
    assert t["level"] == "error" and t["summary"] == "no heartbeat"  # no NATS user, not running: seen


def test_status_api_for_admins(client, monkeypatch):
    from flaskspark.core import health

    monkeypatch.setattr(health, "nats_health", lambda *a, **kw: {"ok": False, "error": "no NATS in tests"})
    data = client.get("/api/status/services").get_json()
    assert [s["key"] for s in data["services"]][:2] == ["web", "push"]
    html = client.get("/").get_data(as_text=True)
    assert "<ui-service-status" in html and "flaskspark/js/ui-service-status.js" in html


def test_status_component_and_its_stylesheet_are_served(client):
    html = client.get("/").get_data(as_text=True)
    import re

    src = re.search(r'<script type="module" src="([^"]*/flaskspark/js/ui-service-status\.js)"', html).group(1)
    assert client.get(src).status_code == 200
    assert client.get(src.replace("js/ui-service-status.js", "css/ui-service-status.css")).status_code == 200


# --- guardian ---------------------------------------------------------------------------------------------------------
class FakeNotifier:
    def __init__(self):
        self.sent = []

    def send(self, title, message, **kw):
        self.sent.append((title, kw.get("priority")))

    def flush(self):
        return True


class Switch(GuardCheck):
    def __init__(self):
        self.on, self.reacted = False, []

    def run(self, ctx):
        return [Finding("switch", WARNING, "Switched on", "it is on", grace=60)] if self.on else []

    def react(self, ctx, finding):
        self.reacted.append(finding.key)
        return "Reacted."


def test_guard_reports_after_grace_reminds_and_resolves(tmp_path):
    check, notifier = Switch(), FakeNotifier()
    guard = Guard(cfg_of(), notifier, checks=[check], state_file=tmp_path / "findings.json",
                  context=lambda cfg, opt, now: GuardContext(cfg, opt, now, read_nats=lambda: {"ok": True}))
    check.on = True
    assert guard.run_once(NOW) == []  # within its grace
    assert [n["title"] for n in guard.run_once(NOW + 61)] == ["Switched on"]
    assert check.reacted == ["switch"]
    assert guard.run_once(NOW + 120) == []
    assert [n["title"] for n in guard.run_once(NOW + 61 + 240 * 60)] == ["Switched on (still)"]
    check.on = False
    assert [n["level"] for n in guard.run_once(NOW + 20000)] == ["resolved"]
    assert [t for t, _ in notifier.sent] == ["Guardian: Switched on", "Guardian: Switched on (still)",
                                            "Guardian: Resolved: Switched on"]
    again = Guard(cfg_of(), notifier, checks=[check], state_file=tmp_path / "findings.json")
    assert again.state["last_check"] == NOW + 20000  # kept across a restart
    assert guard.summary()["findings"] == []


def test_guard_reports_its_own_failure(tmp_path):
    class Failing(GuardCheck):
        def run(self, ctx):
            raise OSError("database locked")

    notifier = FakeNotifier()
    guard = Guard(cfg_of(), notifier, checks=[Failing()], state_file=tmp_path / "f.json",
                  opt={**settings(cfg_of()), "failing_minutes": 0})
    assert [n["title"] for n in guard.run_once(NOW)] == ["Guardian can't check"]


def guard_ctx(instances=None, nats=None, missing=False):
    found = {"ok": True, "missing": missing, "instances": [{**i, "age": NOW - i["ts"]} for i in instances or []]}
    return GuardContext(cfg_of(), settings(cfg_of()), NOW, read_directory=lambda: found,
                        read_nats=lambda: nats or {"ok": True})


def test_services_check():
    services = [ServiceInfo("web", "Web", "x:main", single=True), ServiceInfo("worker", "Worker", "x:main")]
    check = ServicesCheck(services)
    assert check.run(guard_ctx([instance("web"), instance("worker")])) == []
    keys = [f.key for f in check.run(guard_ctx([instance("web"), {**instance("web"), "instance": "web-2"},
                                                instance("worker", ok=False)]))]
    assert keys == ["service:web:twice", "service:worker:failing"]
    found = check.run(guard_ctx([instance("web"), instance("worker", ago=900)]))
    assert [(f.key, f.level) for f in found] == [("service:worker", CRITICAL)]
    assert "15 min ago from host-1" in found[0].render()[1]
    assert found[0].render()[0] == "Worker: no heartbeat"
    assert check.run(guard_ctx(missing=True)) == []  # nobody wrote a heartbeat yet
    assert check.run(guard_ctx(nats={"ok": False})) == []  # NatsCheck's finding


def test_nats_and_queue_checks():
    assert [f.key for f in NatsCheck().run(guard_ctx(nats={"ok": False, "error": "refused"}))] == ["nats:down"]
    nodes = [{"name": "a", "ok": True}, {"name": "b", "ok": False}, {"name": "c", "ok": True}]
    assert [f.key for f in NatsCheck().run(guard_ctx(nats={"ok": True, "nodes": nodes, "down": ["b"]}))] == \
        ["nats:degraded"]
    stuck = NotifyQueueCheck(read_queue=lambda ctx: {"ok": True, "waiting": 4, "oldest": 900})
    assert [f.key for f in stuck.run(guard_ctx())] == ["notify:stuck"]
    fine = NotifyQueueCheck(read_queue=lambda ctx: {"ok": True, "waiting": 1, "oldest": 30})
    assert fine.run(guard_ctx()) == []


def test_guardian_settings_from_config():
    opt = settings(cfg_of(guardian={"enabled": True, "interval": 10}), [Switch()])
    assert opt["interval"] == 10 and "enabled" not in opt and opt["service_grace"] == 120


# --- backup -----------------------------------------------------------------------------------------------------------
def make_db(path: Path, rows: int = 3) -> str:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE note (id INTEGER PRIMARY KEY, text TEXT)")
    con.executemany("INSERT INTO note (text) VALUES (?)", [(f"n{i}",) for i in range(rows)])
    con.commit()
    con.close()
    return f"sqlite:///{path}"


def test_backup_copy_check_and_restore(tmp_path):
    url = make_db(tmp_path / "live.db")
    copy = backup.backup_db(tmp_path / "backups", "20260101-120000", url)
    assert copy.name == "db-20260101-120000.db.gz"
    assert backup.verify(copy, url) == {"integrity": "ok", "counts": {"note": 3}}
    con = sqlite3.connect(tmp_path / "live.db")
    con.execute("DELETE FROM note")
    con.commit()
    con.close()
    result = backup.restore(copy, url)
    assert Path(result["kept"]).is_file()  # the database before the restore
    con = sqlite3.connect(tmp_path / "live.db")
    assert con.execute("SELECT count(*) FROM note").fetchone()[0] == 3
    con.close()


def test_backup_refuses_a_broken_copy(tmp_path):
    url = make_db(tmp_path / "live.db")
    broken = tmp_path / "db-20260101-120000.db.gz"
    with gzip.open(broken, "wb") as f:
        f.write(b"SQLite format 3\x00" + b"\x00" * 200)
    with pytest.raises(Exception):
        backup.restore(broken, url)
    con = sqlite3.connect(tmp_path / "live.db")
    assert con.execute("SELECT count(*) FROM note").fetchone()[0] == 3  # untouched
    con.close()


def test_backup_prune_keeps_hours_then_one_per_day(tmp_path):
    now = datetime(2026, 1, 10, 12, 0).timestamp()
    stamps = ["20260110-113000", "20260109-130000", "20260109-090000", "20260108-230000", "20260108-100000",
              "20260101-120000"]
    for s in stamps:
        (tmp_path / f"db-{s}.db.gz").write_bytes(b"x")
    (tmp_path / "unrelated.txt").write_text("stays")
    removed = {p.name for p in backup.prune(tmp_path, keep_hours=24, keep_days=7, now=now)}
    # within 24 h: all; then the newest of each day not kept yet, for 7 days
    assert removed == {"db-20260109-090000.db.gz", "db-20260108-100000.db.gz", "db-20260101-120000.db.gz"}
    assert (tmp_path / "unrelated.txt").exists()
    assert backup.latest(tmp_path).name == "db-20260110-113000.db.gz"


def test_backup_of_the_state_directory_leaves_out_what_it_must(tmp_path):
    state = tmp_path / "state"
    for name in ("mod/data.json", "mod/keys/secret.key", "mod/keys/.nobackup", "sessions/s1", "nats/jetstream/x",
                 "app.db", "mod/run.log", "backups/old.gz"):
        (state / name).parent.mkdir(parents=True, exist_ok=True)
        (state / name).write_text("x")
    out = backup.backup_state(state, tmp_path / "out", "20260101-120000",
                              exclude=(state / "app.db", state / "backups"))
    import tarfile

    with tarfile.open(out) as tar:
        names = set(tar.getnames())
    assert "state/mod/data.json" in names
    assert not [n for n in names if "keys" in n or "sessions" in n or "nats" in n or n.endswith((".db", ".log"))]
    assert not [n for n in names if "backups" in n]


def test_backup_includes_further_directories_of_the_config_and_the_modules(app, tmp_path, monkeypatch):
    import tarfile

    from flaskspark.core import modules, paths
    from flaskspark.core.module import Module

    monkeypatch.setattr(paths, "STATE_DIR", tmp_path / "state")
    (tmp_path / "state").mkdir()
    for name in ("files/a.txt", "files/cache/.nobackup", "files/cache/x", "media/b.bin", "files/run.log"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("x")

    class Media(Module):
        NAME, LABEL = "media", "Media"

        def backup_paths(self, cfg):
            return [tmp_path / "media", tmp_path / "files"]  # files twice: once in the archive

    monkeypatch.setattr(modules, "load", lambda cfg: [Media()])
    cfg = cfg_of(backup={"dir": str(tmp_path / "backups"), "include": [str(tmp_path / "files"),
                                                                       str(tmp_path / "missing")]})
    assert backup.included(cfg) == [tmp_path / "files", tmp_path / "missing", tmp_path / "media"]
    result = backup.run(cfg)
    with tarfile.open(result["state"]) as tar:
        names = set(tar.getnames())
    root = "extra/" + str(tmp_path).lstrip("/")
    assert f"{root}/files/a.txt" in names and f"{root}/media/b.bin" in names
    assert not [n for n in names if "cache" in n or n.endswith(".log") or "missing" in n]

    # without the state directory (backup.state: false) the archive holds the further directories alone
    only = backup.run(cfg_of(backup={"dir": str(tmp_path / "backups2"), "state": False,
                                     "include": [str(tmp_path / "files")]}))
    with tarfile.open(only["state"]) as tar:
        assert {n for n in tar.getnames() if not n.startswith("extra/")} == set()


def test_backup_run_and_cli(app, tmp_path, monkeypatch):
    from flaskspark.core import cli, paths

    monkeypatch.setattr(paths, "STATE_DIR", tmp_path / "state")
    (tmp_path / "state" / "mod").mkdir(parents=True)
    (tmp_path / "state" / "mod" / "data.json").write_text("{}")
    cfg = cfg_of(backup={"dir": str(tmp_path / "backups")})
    result = backup.run(cfg)
    assert Path(result["db"]).is_file() and Path(result["state"]).is_file()
    with pytest.raises(SystemExit) as exit_:
        cli.main(["backup-check", result["db"]])
    assert exit_.value.code == 0
    assert cli._operations(type("Args", (), {"command": "backup-list"})(), cfg) == 0
    ctx = status.StatusContext(cfg, time.time(), read_directory=dict, read_nats=lambda: {"ok": False})
    tile = status.collect(cfg, ctx=ctx, shown=[status.BackupTile()])[0]
    assert tile["level"] == "ok" and tile["summary"].startswith("last ")


def test_backup_mirror_copies_and_removes_and_the_tile_tells(app, tmp_path, monkeypatch):
    from flaskspark.core import paths

    monkeypatch.setattr(paths, "STATE_DIR", tmp_path / "state")
    (tmp_path / "state").mkdir()
    share = tmp_path / "share"
    cfg = cfg_of(backup={"dir": str(tmp_path / "backups"), "mirror_dir": str(share), "state": False})
    result = backup.run(cfg)
    assert "not reachable" in result["mirror"]["error"]  # the share away: the local backup is there
    ctx = status.StatusContext(cfg, time.time(), read_directory=dict, read_nats=lambda: {"ok": False})
    tile = status.collect(cfg, ctx=ctx, shown=[status.BackupTile()])[0]
    assert tile["level"] == "warning" and tile["details"][-1][0] == "Mirror"
    share.mkdir()
    (share / "db-20000101-000000.db.gz").write_bytes(b"old")  # pruned locally long ago
    (share / "notes.txt").write_text("kept")  # not a backup: left alone
    result = backup.run(cfg, now=time.time() + 1)
    assert result["mirror"] == {"copied": 2, "removed": 1}
    assert sorted(p.name for p in share.iterdir() if p.name.startswith("db-")) == \
        sorted(p.name for p in (tmp_path / "backups").iterdir())
    assert (share / "notes.txt").exists()
    tile = status.collect(cfg, ctx=ctx, shown=[status.BackupTile()])[0]
    assert tile["level"] == "ok" and tile["details"][-1] == ["Mirror", "current (2 database backups)"]


def test_gunicorns_control_socket_is_the_apps_own(monkeypatch):
    """Not gunicorn's default (one path per user, shared by every app on the host): the app's STATE_DIR."""
    from types import SimpleNamespace

    from gunicorn import config

    from flaskspark.core import paths
    from flaskspark.core.services import web

    monkeypatch.setattr(config, "KNOWN_SETTINGS", [SimpleNamespace(name="bind"), SimpleNamespace(name="control_socket")])
    assert web.control_socket_args() == ["--control-socket", str(paths.STATE_DIR / "gunicorn.ctl")]
    monkeypatch.setattr(config, "KNOWN_SETTINGS", [SimpleNamespace(name="bind")])  # an older gunicorn: no such option
    assert web.control_socket_args() == []
