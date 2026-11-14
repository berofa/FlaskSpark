---
name: flaskspark-new-service
description: Einen Service (eigenen Prozess) eines Moduls auf FlaskSpark (flaskspark.core) anlegen - AsyncService,
  LoopService oder Task, ServiceInfo im Manifest, Name flaskspark-<name>, NATS-Benutzer und Rechte, Herzschläge und
  details(), Führung bei mehreren Instanzen, Statuskachel, Wächter-Prüfung, Start über Supervisor/Container/Unit,
  Router-Routen, Push-Themen, Job-Queue. Verwenden, wenn ein Modul Arbeit im Hintergrund braucht (Polling, Sync,
  Feeds, Worker, WebSocket-Server, zeitgesteuerte Läufe) oder ein bestehender Service geändert wird.
---

# Neuer Service

Ein Service ist ein **eigener Prozess pro Instanz**; die Web-App rechnet nichts im Hintergrund. Massgebend: README von
FlaskSpark «Services and the command line», «Service directory and status tiles», «Leadership», «Job queue»,
«NATS users and permissions»; Code `flaskspark/core/service.py`, `task.py`, `leader.py`, `queue.py`.

## 1. Welche Basis?

| Fall | Basis |
|---|---|
| asyncio, NATS-Subscriptions, Requests beantworten, Server (aiohttp, WebSocket) | `AsyncService` |
| synchrone Schleife alle N Sekunden (Sync, Polling) | `LoopService` (`INTERVAL`, `setup()`, `step(started)`) |
| einmaliger Lauf (systemd-Timer, cron) | `Task` (`run(cfg)` → dict, `main()` gibt JSON aus, Exit 0/1) |
| Arbeit, die nicht zeitkritisch ist, auf mehrere Worker verteilt | Job-Queue (`jobs.submit`, `queue.Worker`) in einem der obigen |

## 2. AsyncService

```python
# myapp/modules/notes/service.py
import asyncio

from flaskspark.core import bus
from flaskspark.core.leader import Leadership
from flaskspark.core.service import AsyncService


class NotesService(AsyncService):
    NAME, NATS_USER = "notes", "notes"      # NAME = ServiceInfo.name; NATS_USER: NATS_NOTES_USER/_PASSWORD
    START_RETRY = 5.0                       # start() bei Fehler wiederholen (None: Prozess endet, Supervisor startet neu)

    def __init__(self, nc):
        self.nc, self.subs, self.count = nc, [], 0
        self.stopped = asyncio.Event()
        self.leadership = Leadership(nc, "notes_leader", self.directory_instance(),
                                     on_lead=self.lead, on_resign=self.resign)

    @classmethod
    async def create(cls, nc):
        return cls(nc)

    async def start(self):
        self.subs.append(await self.nc.subscribe("notes.rpc", queue="notes", cb=self.answer))
        self.task = asyncio.create_task(self.leadership.run(self.stopped))

    async def answer(self, msg):
        data = bus.loads(msg.data) or {}
        await msg.respond(bus.dumps({"ok": True, "id": data.get("id")}))

    async def lead(self):     # nur die führende Instanz arbeitet
        ...

    async def resign(self):
        ...

    async def stop(self):
        self.stopped.set()
        await self.leadership.release()
        for sub in self.subs:
            await sub.unsubscribe()

    def details(self):        # in jedem Herzschlag; "ok": False = kann nicht arbeiten
        return {"leader": self.leadership.leader, "count": self.count}


main = NotesService.main
```

- `run()` erledigt Konfiguration laden, NATS-Verbindung (`flaskspark-<NAME>`), Retry, systemd `READY`/`WATCHDOG`,
  Herzschläge alle 10 s, SIGTERM/SIGINT, Abmelden aus dem Verzeichnis, `drain`. Nicht selbst nachbauen.
- Führung (`Leadership`) nur, wenn mehrere Instanzen laufen können und die Arbeit nicht doppelt laufen darf; sonst
  `ServiceInfo(..., single=True)`. Requests mit `queue=` beantworten, dann teilen sich Instanzen die Last.
- **Ausfälle überleben:** NATS, DB, externe Quelle weg → weitermachen, nichts doppelt, nichts auf veralteten Daten
  entscheiden; Fehler in `details()` zeigen statt abstürzen.

## 3. LoopService

```python
from flaskspark.core.service import LoopService


class Sync(LoopService):
    NAME, NATS_USER, INTERVAL = "sync", "sync", 60    # mit NATS_USER: events.init() vorher, emit/publish gehen

    def setup(self):               # einmal, vor READY
        self.client = connect_upstream()

    def step(self, started):       # Fehler wird geloggt, Schleife läuft weiter
        self.count = self.client.sync()

    def details(self):
        return {"synced": self.count}


main = Sync.main
```

`wait(started)` überschreiben, um zwischen zwei Schritten etwas zu beobachten. Herzschläge kommen aus einem eigenen
Thread (`directory.Beacon`) mit `step`/`step_seconds`.

## 4. Im Manifest anmelden und starten

```python
SERVICES = (ServiceInfo("notes", N_("Notes"), "myapp.modules.notes.service:main", single=False, unit=""),)
ROUTES = (Route("/ws/notes", "NOTES_PORT", 8110, websocket=True),)   # nur wenn der Service HTTP/WS selbst bedient
```

- Name überall ausserhalb des Codes `flaskspark-<name>` (Prozess, Log, NATS-Verbindung, Kachel, Container, Unit
  `flaskspark-<name>.service`); im Code, auf NATS-Subjects (`ms.<name>.heartbeat`), Verzeichnis-Keys und NATS-Benutzern
  der Kurzname. Nie `myapp-<name>`.
- Entwicklung/ein Container: `myapp run` startet ihn automatisch (Supervisor, Neustart mit wachsender Pause).
- Einzeln: `myapp service notes` (auch `myapp service flaskspark-notes`), z.B. Container `flaskspark-notes` oder
  systemd-Unit `flaskspark-notes.service` (`Type=notify`, `WatchdogSec=60`; Vorlage README «systemd»).
  `myapp services`, `myapp units`, `myapp routes` zeigen, was FlaskSpark daraus macht.
- Ein Route-Service hört selbst auf `os.environ.get("NOTES_PORT", 8110)`; der Router (bzw. ein Reverse Proxy mit den
  Routen aus `myapp routes`) leitet den Pfad weiter.

## 5. NATS-Benutzer und Rechte

Pro Service ein eigener Benutzer (`NATS_<USER>_USER`/`_PASSWORD` in `~/.config/<app>/notes.env` bzw. der Umgebung;
ohne: anonym). Er braucht mindestens: subscribe `_INBOX.<user>.>`, publish `ms.<name>.>`, das KV-Bucket `services`
(`$KV.services.>`, `$JS.API.STREAM.INFO.KV_services` …), dazu seine eigenen Subjects, ggf. Führungs-Bucket
`$KV.notes_leader.>`, Job-Queue-Rechte. Die Web-App (`web`) braucht publish auf die Requests (`notes.rpc`), der
Push-Service (`push`) subscribe auf die `PUSH_TOPICS`. Tabelle: README «NATS users and permissions».

## 6. Status und Wächter

```python
# myapp/modules/notes/status.py
from flaskspark.core import health
from flaskspark.core.module import N_
from flaskspark.core.services.guardian import Finding, GuardCheck
from flaskspark.core.status import StatusTile, _, problem, thousands


class NotesTile(StatusTile):
    KEY, NAME, SERVICE = "notes", N_("Notes"), "notes"   # base(): Instanzen, Version, Speicher aus dem Herzschlag

    def fill(self, t, ctx):
        found = ctx.ask(lambda user: health.request(user, "notes.health"))   # NO_NATS / {ok: False, error}
        if found.get("ok") is False:
            ctx.not_answering(t, found)
            return
        t["details"].append([_("Notes"), thousands(found.get("count"))])    # status._: übersetzt im Request
        if found.get("error"):
            problem(t, _("Sync"), found["error"])


class NotesCheck(GuardCheck):
    DEFAULTS = {"notes_max_lag": 600}

    def run(self, ctx):
        beat = (ctx.instances("notes") or [{}])[0].get("details") or {}
        if beat.get("lag", 0) > ctx.opt["notes_max_lag"]:
            # Texte als N_()-Quelltexte mit %(name)s, Werte in params: übersetzt beim Melden und auf der Kachel
            return [Finding("notes:lag", "warning", N_("Notes lag behind"), N_("%(lag)s s behind"), grace=300,
                            params={"lag": beat["lag"]})]
        return []
```

Der Service beantwortet dazu `notes.health` (wie `notes.rpc` oben) mit `{"ok": True, "count": …}`; die Kachel fragt
als NATS-Benutzer `web` (Default von `StatusContext`), der braucht publish auf `notes.health`.
Im Manifest `def status_tiles(self): return [NotesTile()]` und `def guard_checks(self): return [NotesCheck()]`
(Import in der Methode). Ohne eigene Kachel bekommt der Service eine einfache aus seinem Herzschlag. Hilfen in
`flaskspark.core.status`: `problem`, `failing`, `worse`, `age`, `next_run`. Prüfen: `myapp status`,
`myapp guard-check`.

## 7. Live-Daten, Queue, Notifications

- An den Browser: `await nc.publish("notes.changed", bus.dumps({...}))` (Themen in `PUSH_TOPICS`); im synchronen
  Code `events.publish`/`events.emit`. Details: Skill `flaskspark-live-data`.
- Job-Queue: `await queue.submit(nc, "notes-export", payload, priority=queue.HIGH, key=...)`,
  `queue.Worker(nc, "notes-export", handler)` (`await worker.start(); await worker.run()`); Handler idempotent,
  `queue.Skip` für Jobs, die nicht mehr passen.
- Meldungen an Menschen: `notify.Notifier().send(title, message, priority=notify.HIGH, category="notes")`.

## 8. Tests

Echter `nats-server` pro Test-Modul (freier Port, `-js -sd <tmp>`), ohne Binary überspringen; Muster
`tests/core/test_nats_services.py` in FlaskSpark. Logik (step, answer, Kachel, Check) ohne NATS mit Fakes testen
(`GuardContext(cfg, opt, read_directory=…, read_nats=…)`).
