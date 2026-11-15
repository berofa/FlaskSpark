"""Status of the application's services for the status tiles in the sidebar (GET /api/status/services, admins only) and
`<app> status`: the instances of each service from the service directory (flaskspark.core.directory: where they run,
who leads, how old their last heartbeat is) plus what the service itself tells (its heartbeat's details).

Every tile: {key, name, service, process, unit, level ok|warning|error, summary, details: [[label, text(, full text)]],
instances, href (a page with more, "" for none)}; service: the short name (ServiceInfo.name, as in the service directory), process: the name shown outside the
code ("flaskspark-<service>", flaskspark.core.service.process_name), "" for a tile without a service.

A tile is a StatusTile; every module brings its own (Module.status_tiles()), the core its tiles for the web app,
NATS, the notifications, the guardian and the backup. Every service of a manifest that no tile claims (StatusTile.
SERVICE) gets a plain ServiceTile, so nothing runs unseen. collect() reads the directory and NATS once for all tiles.

While the directory can't be read (NATS away, no JetStream), a service shows what systemd on this host knows of its
unit instead (ServiceInfo.unit, default "flaskspark-<service>.service"; systemctl show), so a host without NATS still
sees its units; a unit systemd does not know (e.g. everything under one supervisor) leaves the tile «unknown».

Texts are English source texts, translated with the app's catalogue while a request is there (the JSON API).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from . import directory, health
from .module import N_
from .service import process_name

log = logging.getLogger(__name__)

OK, WARNING, ERROR = "ok", "warning", "error"
ERROR_CHARS = 120  # characters of an error in a tile's row; the whole text goes along (the page shows it on a click)
TOPIC = "services"  # events.emit(TOPIC): the status tiles reload (ev.all.services)


def _(text: str, **params) -> str:
    """gettext in a request (the visitor's language), else the English source text."""
    try:
        from flask import has_request_context

        if has_request_context():
            from flask_babel import gettext

            return gettext(text, **params)
    except ImportError:
        pass
    return text % params if params else text


def age(ts: float | None, now: float) -> str:
    if ts is None:
        return "–"
    s = max(0.0, now - ts)
    if s < 90:
        return f"{s:.0f} s"
    if s < 5400:
        return f"{s / 60:.0f} min"
    if s < 172800:
        return f"{s / 3600:.1f} h"
    return f"{s / 86400:.0f} d"


def thousands(value) -> str:
    """1234567 -> "1'234'567" (counts on tiles)."""
    return f"{value or 0:,}".replace(",", "'")


def read_json(path: Path) -> dict:
    """A JSON file a service keeps (e.g. its heartbeat-<name>.json, flaskspark.core.service.write_heartbeat), {}
    when it is missing or broken."""
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def next_run(ts: float | None) -> str:
    """When something runs next (e.g. a timer), for a tile's row."""
    return datetime.fromtimestamp(ts).strftime("%d.%m. %H:%M") if ts else _("on request only")


def short(text: str, n: int = ERROR_CHARS) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def problem(t: dict, label: str, error: str | None, warn: bool = True) -> None:
    """A row with an error: [label, the error shortened, the whole error]; the tile becomes a warning (unless it is
    worse already)."""
    full = str(error or "").strip() or "–"
    t["details"].append([label, short(full), full])
    if warn and t["level"] == OK:
        t["level"] = WARNING


def failing(t: dict, items, one: str = "", many: str = "") -> None:
    """Every failing item a service reports (e.g. accounts it can't reach) as a row: «<label> (<owner>)»: error; the
    tile becomes a warning. items: [{label, owner, error}] (the service's status answer); a number: only the count
    (one/many: the words for it, default "item"/"items")."""
    if isinstance(items, int):
        if items:
            word = (one or _("item")) if items == 1 else (many or _("items"))
            problem(t, _("Failing"), f"{items} {word}")
        return
    for f in items or []:
        owner = f.get("owner")
        problem(t, f"{f.get('label') or '?'}{f' ({owner})' if owner else ''}", f.get("error"))


def worse(t: dict, level: str) -> None:
    """Raise the tile's level to `level` (never lower it)."""
    order = (OK, WARNING, ERROR)
    if order.index(level) > order.index(t["level"]):
        t["level"] = level


def describe(i: dict, now: float) -> str:
    """One instance for people: "host-1 (leader, 3 s ago)"."""
    roles = {directory.LEADER: _("leader"), directory.STANDBY: _("standby")}
    parts = [roles[i["role"]]] if i.get("role") in roles else []
    parts.append(_("%(age)s ago", age=age(i.get("ts"), now)))
    if i.get("ok") is False:
        parts.append(_("reports errors"))
    return f"{i.get('host') or i.get('instance')} ({', '.join(parts)})"


#: what systemctl show tells of a unit
PROPS = ("Id", "LoadState", "ActiveState", "SubState", "ActiveEnterTimestamp", "NRestarts", "MemoryCurrent", "Result")
#: StatusContext.ask() without NATS
NO_NATS = {"ok": False, "error": "NATS not reachable"}


def systemd_units(units: list[str]) -> dict[str, dict]:
    """systemctl show of the units on this host: {unit: {prop: value}} ({} outside systemd). Never raises."""
    if not units:
        return {}
    try:
        out = subprocess.run(["systemctl", "show", "--timestamp=unix", *units, *(f"-p{p}" for p in PROPS)],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    result, cur = {}, {}
    for line in out.splitlines() + [""]:
        if not line.strip():
            if cur.get("Id"):
                result[cur["Id"]] = cur
            cur = {}
            continue
        key, _sep, value = line.partition("=")
        cur[key] = value
    return result


def _unix(value: str | None) -> float | None:
    """A timestamp of systemctl show --timestamp=unix ("@1700000000")."""
    try:
        return float(value[1:]) if value and value.startswith("@") else None
    except ValueError:
        return None


class StatusContext:
    """What the tiles of one collect() share: config, time, NATS health, the service directory and systemd on this host
    (each asked once). read_directory / read_nats / read_systemd: instead of NATS and systemctl (tests)."""

    def __init__(self, cfg, now: float | None = None, user: str = "web",
                 read_directory: Callable[[], dict] | None = None, read_nats: Callable[[], dict] | None = None,
                 read_systemd: Callable[[list[str]], dict] | None = None):
        self.cfg, self.now, self.user = cfg, now or time.time(), user
        self._read_directory = read_directory or (lambda: directory.read(self.user))
        self._read_nats = read_nats or (lambda: health.nats_health(self.user))
        self._read_systemd = read_systemd or systemd_units
        self._nats: dict | None = None
        self._directory: dict | None = None
        self._units: dict[str, dict] | None = None

    def ask(self, request: Callable[[str], dict]) -> dict:
        """The answer of a service's status request (request: NATS user -> dict, e.g. a function around
        health.request), NO_NATS without NATS, {ok: False, error} when nobody answers. Never raises."""
        if not self.nats_ok():
            return dict(NO_NATS)
        try:
            return request(self.user)
        except Exception as exc:  # noqa: BLE001 - not answering is the answer
            return {"ok": False, "error": str(exc) or type(exc).__name__}

    @staticmethod
    def not_answering(t: dict, result: dict) -> None:
        """A service that did not answer its status request: the tile says so and becomes an error."""
        t["summary"] = _("not answering")
        problem(t, _("Error"), result.get("error"), warn=False)
        worse(t, ERROR)

    def unit_of(self, service: str) -> str:
        """The systemd unit of a service (ServiceInfo.unit, default "flaskspark-<service>.service"), "" for a service
        the manifests do not have."""
        from . import modules

        found = next((s for s in modules.services(self.cfg) if s.name == service), None)
        return getattr(found, "unit", "") or ""

    def units(self) -> dict[str, dict]:
        """systemd on this host of every service with a unit (asked once)."""
        if self._units is None:
            from . import modules

            wanted = sorted({s.unit for s in modules.services(self.cfg) if getattr(s, "unit", "")})
            self._units = self._read_systemd(wanted) if wanted else {}
        return self._units

    def unit(self, unit: str) -> dict:
        """What systemd on this host tells of `unit` ({} outside systemd or without it)."""
        if not unit:
            return {}
        if self._units is not None and unit in self._units:
            return self._units[unit]
        found = self.units().get(unit)
        if found is None:
            found = self._read_systemd([unit]).get(unit, {})
            self._units[unit] = found
        return found

    def nats(self) -> dict:
        if self._nats is None:
            self._nats = self._read_nats()
        return self._nats

    def nats_ok(self) -> bool:
        return bool(self.nats().get("ok"))

    def directory(self) -> dict:
        """The service directory; not asked without NATS."""
        if self._directory is None:
            self._directory = self._read_directory() if self.nats_ok() else directory.unreachable(
                _("NATS not reachable"))
        return self._directory

    def directory_usable(self) -> bool:
        return directory.usable(self.directory())

    def all_instances(self, service: str) -> list[dict]:
        """Every instance of a service in the directory (stale ones too), the leader first."""
        if not self.directory_usable():
            return []
        return directory.by_service(self.directory().get("instances") or []).get(service, [])

    def instances(self, service: str) -> list[dict]:
        """The live instances of a service, the leader first."""
        return directory.alive(self.all_instances(service))

    def beat(self, service: str) -> dict | None:
        """The details of the first live instance of a service (the leader), None without one."""
        live = self.instances(service)
        return (live[0].get("details") or {}) if live else None


class StatusTile(ABC):
    """One tile. KEY: stable id, NAME: shown name (an English source text, N_()), SERVICE: the service it shows
    (ServiceInfo.name; its instances fill the tile's base), "" for a tile without a service of its own."""

    KEY: str = ""
    NAME: str = ""
    SERVICE: str = ""
    UNIT: str = ""  # its systemd unit, default the ServiceInfo.unit of SERVICE (the fallback without the directory)
    HREF: str = ""  # a page with more about it: the tile links there (e.g. a module's list page)

    def base(self, ctx: StatusContext) -> dict:
        """The tile before fill(): from the service's instances in the directory, or empty without a service."""
        t = {"key": self.KEY, "name": _(self.NAME), "service": self.SERVICE,
             "process": process_name(self.SERVICE) if self.SERVICE else "",
             "unit": self.UNIT or (ctx.unit_of(self.SERVICE) if self.SERVICE else ""), "level": OK,
             "summary": "", "details": [], "instances": [], "since": None, "href": self.HREF}
        if self.SERVICE:
            service_base(t, ctx)
        return t

    @abstractmethod
    def fill(self, t: dict, ctx: StatusContext) -> None:
        """Complete the tile `t`: summary, details, level."""


def service_base(t: dict, ctx: StatusContext) -> None:
    """A tile's base from its service's instances: live ones with host, role and the age of their heartbeat; none
    alive: error (with where it was last seen); the directory not readable: warning (unknown)."""
    if not ctx.directory_usable():
        d = ctx.directory()
        source = _("no heartbeats yet") if d.get("missing") else short(d.get("error") or _("not readable"))
        if from_systemd(t, ctx):
            t["details"].append([_("Source"), _("systemd on this host (service directory: %(why)s)", why=source)])
            return
        t["level"], t["summary"] = WARNING, _("unknown")
        t["details"].append([_("Service directory"), source])
        return
    found = ctx.all_instances(t["service"])
    live = directory.alive(found)
    if live:
        t["details"].append([_("Instances") if len(live) > 1 else _("Instance"),
                             ", ".join(describe(i, ctx.now) for i in live)])
        versions = sorted({str(i.get("version")) for i in live if i.get("version")})
        if versions:
            t["details"].append([_("Version"), ", ".join(versions)])
        memory = [i.get("memory") for i in live if i.get("memory")]
        if memory:
            t["details"].append([_("Memory"), ", ".join(f"{m / 1048576:.0f} MB" for m in memory)])
        t["since"] = min((i.get("started") for i in live if i.get("started")), default=None)
        t["summary"] = _("running for %(age)s", age=age(t["since"], ctx.now)) if t["since"] else _("running")
        if all(i.get("ok") is False for i in live):
            t["level"], t["summary"] = WARNING, _("reports errors")
        t["instances"] = live
    else:
        last = max(found, key=lambda i: i.get("ts") or 0, default=None)
        t["details"].append([_("Heartbeat"), _("none for %(age)s (%(host)s)", age=age(last.get("ts"), ctx.now),
                                                 host=last.get("host")) if last else _("none")])
        t["level"], t["summary"] = ERROR, _("no heartbeat")


def from_systemd(t: dict, ctx: StatusContext) -> bool:
    """A tile's base from systemd on this host (the service's ServiceInfo.unit), while the directory can't be read;
    False when the service has no unit or systemd does not know it."""
    unit = t.get("unit") or ctx.unit_of(t["service"])
    state = ctx.unit(unit) if unit else {}
    active = state.get("ActiveState")
    if not active or state.get("LoadState") == "not-found":
        return False
    since = _unix(state.get("ActiveEnterTimestamp"))
    t["details"].append(["systemd", f"{unit}: {active} ({state.get('SubState') or '–'})"])
    restarts = int(state["NRestarts"]) if str(state.get("NRestarts") or "").isdigit() else 0
    if restarts:
        t["details"].append([_("Restarts by systemd"), str(restarts)])
    try:
        memory = int(state.get("MemoryCurrent") or "")
        t["details"].append([_("Memory"), f"{memory / 1048576:.0f} MB"])
    except ValueError:
        pass
    if active == "active":
        t["since"] = since
        t["summary"] = _("running for %(age)s", age=age(since, ctx.now)) if since else _("running")
    elif active in ("failed", "inactive"):
        t["level"], t["summary"] = ERROR, _("not running (%(state)s)", state=active)
    else:
        t["level"], t["summary"] = WARNING, active
    return True


class ServiceTile(StatusTile):
    """The plain tile of a service: its instances, nothing more (for every service no other tile claims)."""

    def __init__(self, service, key: str = ""):
        self.KEY, self.NAME, self.SERVICE = key or service.name, service.label, service.name
        self.UNIT = getattr(service, "unit", "") or ""

    def fill(self, t, ctx):
        pass


def tiles(cfg) -> list[StatusTile]:
    """Every tile in the order shown: the core's first one (the web app), the modules' tiles and a ServiceTile for
    each service no tile claims, then the rest of the core's tiles (infrastructure)."""
    from . import modules

    core, *others = modules.load(cfg)
    first, *rest = core.status_tiles() or [None]
    claimed = {t.SERVICE for m in (core, *others) for t in m.status_tiles() if t.SERVICE}
    unclaimed = [ServiceTile(s) for m in (core, *others) for s in m.SERVICES if s.name not in claimed]
    shown = [first, *(t for m in others for t in m.status_tiles()), *unclaimed, *rest]
    return [t for t in shown if t is not None]


def collect(cfg, now: float | None = None, ctx: StatusContext | None = None,
            shown: list[StatusTile] | None = None) -> list[dict]:
    ctx = ctx or StatusContext(cfg, now)
    out = []
    for tile in tiles(cfg) if shown is None else shown:
        try:
            t = tile.base(ctx)
            tile.fill(t, ctx)
        except Exception as exc:  # noqa: BLE001 - one broken tile must not take the others with it
            log.exception("status tile %s", tile.KEY)
            t = {"key": tile.KEY, "name": _(tile.NAME), "service": tile.SERVICE,
                 "process": process_name(tile.SERVICE) if tile.SERVICE else "", "level": ERROR,
                 "summary": _("tile failed"), "details": [], "instances": [], "since": None,
                 "href": getattr(tile, "HREF", "")}
            problem(t, _("Error"), str(exc))
        out.append(t)
    return out


# --- tiles of the core ------------------------------------------------------------------------------------------------
class WebTile(StatusTile):
    KEY, NAME, SERVICE = "web", N_("Web"), "web"

    def fill(self, t, ctx):
        # This process answers, so it runs (its heartbeat is missing e.g. outside gunicorn or before NATS is there).
        t["details"].append([_("Process"), _("PID %(pid)s on %(host)s", pid=os.getpid(), host=directory.host())])
        if t["level"] != OK:
            t["level"], t["summary"] = (WARNING, _("answers, but without a heartbeat")) if ctx.nats_ok() else \
                (OK, _("answers"))


class RouterTile(StatusTile):
    """The router (flaskspark.core.services.router): its routes, the connections it holds open, its requests and the
    upstream failures of the last minute, from its heartbeat; a warning while services it routes to are not reachable."""

    KEY, NAME, SERVICE = "router", N_("Router"), "router"

    def fill(self, t, ctx):
        live = ctx.instances(self.SERVICE)
        if not live:
            return
        beats = [i.get("details") or {} for i in live]
        total = lambda key: sum(int(b.get(key) or 0) for b in beats)  # noqa: E731 - every instance together
        t["details"].append([_("Routes"), str(max(int(b.get("routes") or 0) for b in beats))])
        t["details"].append([_("Open connections"), _("%(open)s requests, %(ws)s WebSockets", open=total("open"),
                                                      ws=total("websockets"))])
        t["details"].append([_("Requests"), _("%(n)s in the last minute", n=thousands(total("requests_per_minute")))])
        failures = total("upstream_failures")
        if failures:
            problem(t, _("Not reachable"), _("%(n)s requests in the last minute found their service away", n=failures))


class NatsTile(StatusTile):
    KEY, NAME = "nats", N_("NATS")

    def fill(self, t, ctx):
        n = ctx.nats()
        if not n.get("ok"):
            t["level"], t["summary"] = ERROR, _("not reachable")
            problem(t, _("Error"), n.get("error"), warn=False)
            return
        nodes, down = n.get("nodes") or [], n.get("down") or []
        if len(nodes) > 1:
            t["summary"] = _("%(up)s/%(all)s nodes", up=len(nodes) - len(down), all=len(nodes))
            t["details"].append([_("Nodes"), ", ".join(f"{x['name']} {'ok' if x['ok'] else '–'}" for x in nodes)])
            if down:
                worse(t, WARNING)
        else:
            t["summary"] = _("connected")
        if n.get("version"):
            t["details"].append([_("Version"), str(n["version"])])
        if n.get("connections") is not None:
            t["details"].append([_("Connections"), str(n["connections"])])
        if n.get("jetstream"):
            t["details"].append(["JetStream", _("%(streams)s streams, %(size)s MiB", streams=n.get("js_streams") or 0,
                                                size=f"{(n.get('js_storage') or 0) / 2**20:.1f}")])
        else:
            problem(t, "JetStream", _("not available: no service directory, work queue or leadership"))
        if n.get("slow_consumers"):
            t["details"].append([_("Slow consumers"), str(n["slow_consumers"])])


class NotificationsTile(StatusTile):
    """The notifications service and its queue."""

    KEY, NAME, SERVICE = "notifications", N_("Notifications"), "notifications"
    STUCK = 300  # seconds the oldest waiting message may wait before the tile warns

    def __init__(self, read_queue: Callable[[], dict] | None = None):
        self.read_queue = read_queue

    def fill(self, t, ctx):
        from . import notify

        beat = ctx.beat(self.SERVICE)
        if beat is not None and not beat.get("channels"):
            problem(t, _("Channels"), _("none configured"))
        if not ctx.nats_ok():
            return
        q = (self.read_queue or (lambda: health.queue_health(ctx.user, notify.KIND)))()
        if not q.get("ok"):
            problem(t, _("Queue"), q.get("error"))
            return
        waiting, oldest = q.get("waiting") or 0, q.get("oldest")
        text = _("%(n)s waiting", n=waiting)
        if oldest is not None:
            text += ", " + _("the oldest for %(age)s", age=age(ctx.now - oldest, ctx.now))
        t["details"].append([_("Queue"), text])
        if t["level"] == OK:
            t["summary"] = _("nothing waiting") if not waiting else _("%(n)s waiting", n=waiting)
        if oldest is not None and oldest > self.STUCK:
            worse(t, WARNING)


class GuardianTile(StatusTile):
    """The guardian: its findings and its last check, from its heartbeat."""

    KEY, NAME, SERVICE = "guardian", N_("Guardian"), "guardian"

    def fill(self, t, ctx):
        beat = ctx.beat(self.SERVICE)
        if beat is None:
            return
        last, findings = beat.get("last_check"), beat.get("findings") or []
        interval = float(beat.get("interval") or 30)
        t["details"].append([_("Last check"), _("%(age)s ago", age=age(last, ctx.now))])
        from flaskspark.core.services.guardian.base import render

        for f in findings:
            source = f.get("source") or {}
            if source.get("title"):  # the source texts: in the visitor's language
                title, message = (render(source["title"], source.get("params"), _),
                                  render(source.get("message") or "", source.get("params"), _))
            else:
                title, message = f.get("title"), f.get("message")
            t["details"].append([title or _("Finding"), message or ""])
        if not last or ctx.now - last > 4 * interval:
            worse(t, ERROR)
            t["summary"] = _("no longer checks (last %(age)s ago)", age=age(last, ctx.now))
        elif findings:
            worse(t, ERROR if any(f.get("level") == "critical" for f in findings) else WARNING)
            t["summary"] = _("%(n)s findings", n=len(findings)) if len(findings) != 1 else _("1 finding")
        else:
            t["summary"] = _("no findings")


class BackupTile(StatusTile):
    """The latest backup (flaskspark.core.backup) and its age."""

    KEY, NAME = "backup", N_("Backup")

    def fill(self, t, ctx):
        from . import backup

        opt = backup.settings(ctx.cfg)
        last = backup.latest(opt["dir"])
        if last is None:
            t["level"], t["summary"] = WARNING, _("no backup yet")
            t["details"].append([_("Folder"), str(opt["dir"])])
            return
        ts = last.stat().st_mtime
        t["summary"] = _("last %(age)s ago", age=age(ts, ctx.now))
        t["details"].append([_("Last backup"), f"{last.name} ({last.stat().st_size // 1024} kB)"])
        if opt["max_age_hours"] and ctx.now - ts > opt["max_age_hours"] * 3600:
            worse(t, WARNING)
        m = backup.mirrored(opt)
        if m is not None:
            if m["ok"]:
                t["details"].append([_("Mirror"), _("current (%(n)s database backups)", n=m["count"])])
            else:
                problem(t, _("Mirror"), m["error"] or (_("lags behind") if m["count"] else _("empty")))


class ModulesTile(StatusTile):
    """The installed modules: how many are loaded, the ones that are not (a missing dependency), the ones no longer
    delivered (their revision and tables stay in the database), and whether the database is at the heads of their
    migrations (flaskspark.core.db.migrations)."""

    KEY, NAME = "modules", N_("Modules")

    def fill(self, t, ctx):
        from . import modules
        from .db import migrations

        loaded = modules.names(ctx.cfg)
        t["summary"] = _("%(n)s loaded", n=len(loaded))
        if loaded:
            t["details"].append([_("Loaded"), ", ".join(loaded)])
        for name, why in modules.skipped(ctx.cfg).items():
            worse(t, WARNING)
            t["details"].append([name, _("not loaded: %(why)s", why=why)])
        if migrations.classic():
            return
        try:
            found = migrations.state(ctx.cfg)
        except Exception as exc:  # noqa: BLE001 - shown, not raised
            problem(t, _("Database"), short(str(exc)))
            return
        for name, entry in found.vanished.items():
            worse(t, WARNING)
            t["details"].append([name, _("no longer delivered: %(name)s — its tables are kept", name=name)])
        if found.foreign:
            worse(t, WARNING)
            t["details"].append([_("Database"), _("revisions of no known module: %(revisions)s",
                                                  revisions=", ".join(found.foreign))])
        if found.unversioned:
            worse(t, ERROR)
            t["details"].append([_("Database"), _("an earlier history: run «db adopt»")])
        elif found.pending:
            worse(t, WARNING)
            t["details"].append([_("Database"), _("not migrated: %(names)s", names=", ".join(found.pending))])
        else:
            t["details"].append([_("Database"), _("current")])
