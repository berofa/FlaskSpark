---
name: flaskspark-live-data
description: Live-Daten und Kommunikation in Apps auf FlaskSpark (flaskspark.core) - events.emit/publish/request/
  subscribe, NATS-Subjects benennen, PUSH_TOPICS mit Bereich und latest, pushChannel() im Browser, hidden-json-feed
  und hidden-push-fragment, TopicSource für Themen auf Abruf, Requests zwischen Services, client.py über NATS mit
  Rückfall. Verwenden, wenn eine Seite sich ohne Neuladen aktualisieren soll, ein Service dem Browser etwas meldet,
  Module/Web-App mit einem Service reden oder ein NATS-Subject neu eingeführt wird.
---

# Live-Daten und NATS

Server-Code publiziert über NATS, der Push-Service liefert an die Browser-Tabs, die das Thema abonniert haben und es
sehen dürfen (Server-Sent Events über `/events`). Nie eine eigene WebSocket-/SSE-Verbindung für Live-Daten bauen.
Massgebend: README von FlaskSpark «Live data», «Browser JavaScript»; Code `flaskspark/core/events.py`,
`services/push/`, `web/static/flaskspark/js/push-channel.js`.

## 1. Subjects benennen

| Subject | Wofür | Rechte |
|---|---|---|
| `ev.all.<thema>` | «hat sich geändert» an alle (`events.emit("notes")`) | jeder Tab |
| `ev.user.<id>.<thema>` | an einen Benutzer (`events.emit("notes", user_id=3)`) | nur dieser Benutzer |
| `<modul>.<…>` | Daten-Themen des Moduls (`notes.changed`, `notes.user.{uid}`) | `PUSH_TOPICS` (Bereich) |
| `<modul>.rpc`, `<modul>.health`, `<modul>.<verb>` | Requests an den Service | NATS-Benutzer |
| `ms.<service>.heartbeat`, `job.<kind>.…`, `$KV.…` | Kern (Herzschlag, Queue, Buckets) | nicht selbst benutzen |

Immer mit dem Modulnamen beginnen; Kleinbuchstaben, Punkte als Trenner.

## 2. Publizieren (Server)

```python
from flaskspark.core import events

events.emit("notes")                         # -> ev.all.notes  {}
events.emit("notes", user_id=3, id=7)        # -> ev.user.3.notes  {"id": 7}
events.emit_users("notes", {3, 5}, id=7)     # an mehrere Benutzer
events.publish("notes.changed", {"id": 7})   # Daten-Thema des Moduls (PUSH_TOPICS)
```

- `emit`/`publish` blockieren und werfen nie; ohne NATS (Tests, CLI) tun sie nichts. Die Web-App verbindet sich
  selbst (`start_modules()`), ein `LoopService` mit `NATS_USER`, ein Skript mit `events.init("<user>")`.
- In einem `AsyncService`: `await nc.publish("notes.changed", bus.dumps({...}))` (`flaskspark.core.bus`).
- Nach einer DB-Änderung erst nach dem Commit melden (nach dem `with`-Block bzw. `db.after_commit`).
- Lieber «hat sich geändert» + Seite lädt per API neu, als grosse Daten pushen. Daten pushen, wenn sie ohnehin aus
  einem Service fliessen (Messwerte, Fortschritt).

## 3. Rechte: `PUSH_TOPICS`

```python
PUSH_TOPICS = (
    PushTopic("notes.changed", "notes"),                  # Bereich "notes"
    PushTopic("notes.user.{uid}", "notes", latest=True),  # {uid}: nur das eigene; latest: letzter Stand sofort
    PushTopic("notes.progress.*", "notes"),               # NATS-Wildcards * und >
)
```

Tabs dürfen `ev.all.>`, ihr `ev.user.<id>.>` und die `PUSH_TOPICS` der Bereiche, die der Benutzer nutzen darf.
`latest=True` für Zustände (der neue Tab bekommt sofort das Letzte), nicht für Ereignisse. Der NATS-Benutzer `push`
braucht subscribe auf die Themen, der Absender publish.

## 4. Requests und `client.py`

Service-Seite: `AsyncService` mit `await nc.subscribe("notes.rpc", queue="notes", cb=handler)`, Antwort
`await msg.respond(bus.dumps({...}))` (Skill `flaskspark-new-service`).

Aufrufer (Web-App, andere Module) nur über `client.py` des Moduls:

```python
# myapp/modules/notes/client.py
"""How other code talks to the notes service: every answer is a dict, without an answer {"error": ...}."""
from flaskspark.core import db, events
from myapp.modules.notes.models import Note


def ask(subject: str, payload: dict, timeout: float = 10.0) -> dict:
    try:
        return events.request(subject, payload, timeout)
    except events.RequestError as exc:            # kein NATS, niemand hört zu, Zeitlimit
        return {"error": f"notes service not answering ({exc})"}


def rebuild(note_id: int) -> dict:
    return ask("notes.rpc", {"action": "rebuild", "id": note_id})


def count(owner_id: int) -> int:                  # Rückfall ohne Service: eigene Tabellen lesen
    found = ask("notes.count", {"owner_id": owner_id}, timeout=3)
    if "error" not in found:
        return found["count"]
    with db.for_module("notes").session() as s:
        return s.scalar(db.select(db.func.count()).select_from(Note).where(Note.owner_id == owner_id))
```

- Zeitlimit immer setzen; der Aufrufer zeigt `error` an, statt zu hängen oder abzustürzen.
- Fremde Module importieren nur `client.py` (und nennen das Modul in `DEPENDS`/`OPTIONAL_DEPENDS`).
- Nachrichten im eigenen Prozess abonnieren: `off = events.subscribe("notes.changed", callback)`.
- Statusabfrage mit eigener kurzer Verbindung (Kacheln): `health.request(user, "notes.health", timeout)`.

## 5. Browser

```html
{% block page_scripts %}
<script type="module">
  import { pushChannel } from "flaskspark/push-channel.js";
  import { request } from "flaskspark/ui.js";

  const channel = pushChannel();
  const off = channel.subscribe("notes.changed", (data, topic) => reload());
  channel.subscribe("ev.user.{user}.notes", () => reload());   // {user}: wird nach dem «hello» ersetzt
  channel.addEventListener("resync", () => reload());           // nach Reconnect können Events fehlen
</script>
{% endblock %}
```

Deklarativ statt eigenem Skript:
- `<hidden-json-feed id="stats" src="/api/notes/stats" push-topics="notes.changed" interval="60">`: lädt JSON
  einmal für alle Abonnenten (`subscribe(callback)`, `feed="stats"` bei `LightFeedElement`).
- `<hidden-push-fragment push-topics="notes.changed" target="#list">`: lädt die Seite bei einem Thema neu und
  morpht nur `#list` (serverseitig gerenderte Listen).

Achtung: im Manifest heisst der Platzhalter `{uid}`, im Browser `{user}`.

Auf einem Infobildschirm (`layouts/screen.html`, niemand lädt die Seite neu) gilt dasselbe, dazu
`flaskspark/screen.js`: Ist der Push-Kanal 5 Minuten weg, lädt die Seite neu, sobald der Server antwortet (Wartezeit
verdoppelt sich bis 1 h), und täglich um `Screen.reload_at`. Was vom Datum abhängt (z.B. «heute aktuell»), mit
`import { onNewDay } from "flaskspark/screen.js"; onNewDay(() => reload());` nachführen. Ohne offenen Kanal
zusätzlich selbst pollen (wie die anderen Seiten).

## 6. Themen auf Abruf (`TopicSource`)

Für Daten, die nur entstehen, solange jemand zuschaut (z.B. ein Feed, den ein Service bei einem Fremdsystem
mietet): `Module.push_sources(nc)` gibt `TopicSource`-Instanzen zurück (`flaskspark.core.services.push.sources`),
die im Push-Service laufen. Methoden: `handles(topic)`, `valid(topic)`, `async subscribe(topic, on_update, on_last)`
→ Handle, `async unsubscribe(handle)`, `max_age(topic)`, `async close()`. Ein Thema startet einmal für alle Tabs und
endet 30 s nach dem letzten. Rechte weiterhin über `PUSH_TOPICS`. Beispiel: README «Live data».

## 7. Prüfen

- Ohne NATS darf nichts hängen oder werfen (Test ohne `events.init`).
- Mit echtem `nats-server`: publizieren und Antworten testen (Skill `flaskspark-new-service` §8).
- Im Browser: zwei Tabs, Änderung im einen erscheint im anderen; Netzwerk kurz trennen → `resync` lädt neu
  (ungeprüft, solange nicht im Browser angesehen).
