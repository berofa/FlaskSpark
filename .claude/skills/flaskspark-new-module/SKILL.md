---
name: flaskspark-new-module
description: Neues Modul einer App auf FlaskSpark (flaskspark.core) anlegen oder ein Manifest ändern - Paketstruktur,
  Module-Unterklasse in module.py mit NAME/LABEL/POSITION/AREAS/NAVIGATION/TILES/DEPENDS/OPTIONAL_DEPENDS/MODELS/
  TABLES/SHARED_TABLES/CONFIG/SETTINGS/PAGE_SECTIONS/SCREENS/LAYOUT/CLI/PUSH_TOPICS/ROUTES/SERVICES/ACCOUNT_TYPES/SHAREABLES/
  ATTACHMENT_OWNERS/EXPOSURE/NAV_BADGES, Views mit `area`, Templates, Static, client.py als Schnittstelle,
  Übersetzungen, Migrationen, Tests. Verwenden, wenn ein neues Thema/Feature als Modul kommt, ein Modul eine Seite,
  einen Menüeintrag, eine Kachel, einen Bereich oder eine Abhängigkeit zu einem anderen Modul bekommt.
---

# Neues Modul

Jedes Thema (Notizen, Kalender, Shop …) ist ein **eigenes Modul**; nie unter ein fremdes Modul legen. Der Kern kennt
kein Modul; ein Modul bringt alles über sein Manifest mit. Massgebend: README von FlaskSpark «Module manifest»,
`flaskspark/core/module.py`.

## 1. Paket

```text
src/myapp/modules/notes/
  __init__.py
  module.py                # das Manifest: genau eine Module-Unterklasse
  models.py                # Tabellen (optional) → Skill flaskspark-database
  migrations/versions/     # eigene Alembic-Historie (von `db revision --module notes` angelegt)
  locales/                 # eigener Katalog (optional) → Skill flaskspark-i18n
  client.py                # die Schnittstelle für andere Module und die Web-App (optional)
  service.py               # eigener Prozess (optional) → Skill flaskspark-new-service
  status.py                # StatusTile/GuardCheck (optional)
  web/__init__.py
  web/views/__init__.py
  web/views/notes.py       # Klassenbasierte Views, automatisch registriert
  web/templates/notes/     # Templates immer im Unterordner mit Modulnamen
  web/static/notes/        # CSS/JS, URL /static/notes/…
  web/static/public/notes/ # JS, das andere Module importieren dürfen: "modules/notes/…"
```

Entry Point in `pyproject.toml` der App: `[project.entry-points."flaskspark.modules"] notes = "myapp.modules.notes"`,
dann `uv pip install -e .`. Der Entry-Point-Name muss `NAME` sein.

## 2. Manifest

```python
from flaskspark.core.module import (INTERNAL, Area, Module, N_, NavBadge, NavItem, PushTopic, Route, Screen,
                                    ServiceInfo, Tile)
from flaskspark.core.settings import Setting


class Notes(Module):
    NAME = "notes"                                   # Pflicht
    LABEL = N_("Notes")                              # Pflicht, englischer Quelltext
    EXPOSURE = INTERNAL                              # oder PUBLIC (darf auf eine Instanz im Internet)
    POSITION = 100                                   # Reihenfolge (Navigation, Kacheln, Bereiche)
    DEPENDS = ()                                     # fehlt eines: Modul wird nicht geladen (geloggt)
    OPTIONAL_DEPENDS = ("calendar",)                 # vorher modules.is_enabled(cfg, "calendar") fragen
    AREAS = (Area("notes", N_("Notes"), N_("Read and write notes"), defaults=frozenset({"Users"})),)
    NAVIGATION = (NavItem(N_("Notes"), N_("All notes"), "/notes", "notes", icon="journal", badge="notes-open"),)
    NAV_BADGES = (NavBadge("/tasks", "notes-linked", "notes"),)   # Zähler auf dem Eintrag eines anderen Moduls
    TILES = (Tile(N_("Notes"), "/notes", "notes", N_("Short notes"), "journal"),)
    MODELS = ("myapp.modules.notes.models",)
    TABLES = ("notes_note",)                         # nur diese (+ SHARED_TABLES) erreicht seine Session
    SHARED_TABLES = ()
    CONFIG = (Setting("notes.page_size", N_("Notes per page"), "int", min=1, max=100),)
    SETTINGS = ("notes/settings.html",)              # eigene Abschnitte im Reiter «Settings» des Moduls
    PAGE_SECTIONS = {"home": ("notes/home_section.html",), "profile": ("notes/profile.html",),
                     "screen:office": ("notes/home_section.html",)}  # Abschnitt auf einem Infobildschirm
    SCREENS = (Screen("office", N_("Office"), "notes", N_("Notes on the wall"), "display"),)  # /screen/office
    LAYOUT = ("notes/badge_script.html",)            # auf JEDER Seite: nur Dialoge/Navigationsskripte
    PUSH_TOPICS = (PushTopic("notes.changed", "notes"), PushTopic("notes.user.{uid}", "notes", latest=True))
    SERVICES = (ServiceInfo("notes", N_("Notes"), "myapp.modules.notes.service:main"),)
    ROUTES = (Route("/ws/notes", "NOTES_PORT", 8110, websocket=True),)
    ACCOUNT_TYPES = ("imap",)
    SHAREABLES = ("myapp.modules.notes.sharing:NoteShareable",)
    ATTACHMENT_OWNERS = ("myapp.modules.notes.files:NoteFiles",)
    PUBLIC_ENDPOINTS = ()                            # Endpoints ohne Anmeldung (eigene Authentisierung)
    CLI = "myapp.modules.notes.cli:notes"            # click-Gruppe: myapp notes … (gleich wie flask --app flaskspark.core.web.app:create_app notes …)
```

Nur setzen, was das Modul braucht. Bedeutung jedes Felds: README «Module manifest». Methoden zum Überschreiben:
`register()` (Typen/Kanäle registrieren), `template_filters()`, `template_globals()`, `start_web(cfg)` (einmal im
Web-Prozess), `status_tiles()`, `guard_checks()`, `push_sources(nc)`, `backup_paths(cfg)`,
`account_change_veto(change)`.

Entscheide:
- **Bereiche:** ein Bereich pro Gruppe von Rechten, die ein Admin getrennt vergeben will (z.B. «lesen» und
  «verwalten»), nicht pro Seite. Jede View, jeder Menüeintrag, jede Kachel, jedes Push-Thema nennt einen Bereich.
- **Tabellennamen** mit Modulpräfix (`notes_…`), alle in `TABLES`.
- **Ein anderes Modul nutzen:** nur über dessen `client.py` (Python) bzw. `modules/<x>/…` (JS aus
  `web/static/public/<x>/`); `<x>` in `DEPENDS` (Pflicht) oder `OPTIONAL_DEPENDS` (+ `is_enabled`, dann erst
  importieren). Nie fremde Tabellen, Templates oder Interna importieren.
- **Seite eines anderen Moduls erweitern:** dort `{% for t in page_sections("<seite>") %}{% include t %}{% endfor %}`,
  hier `PAGE_SECTIONS = {"<seite>": (…,)}`. Kern-Seiten: `home`, `profile`, `screen:<key>`.
- **Infobildschirm** (Seite für einen Bildschirm an der Wand, ohne Navigation und Buttons, 1920 × 1080): ein Modul
  deklariert ihn mit `SCREENS = (Screen(key, title, area, …),)`, jedes Modul füllt ihn mit
  `PAGE_SECTIONS["screen:<key>"]`; URL `/screen/<key>`, Liste `/screen`. Ein Abschnitt erkennt den Bildschirm an
  `screen` (nur dort definiert) und lässt dann z.B. seine Dialoge weg. Admins finden alle Bildschirme unter
  «Einstellungen › Dashboards» (dort auch die Einstellungen des Moduls). Details: Skill `flaskspark-ui` §6, README
  «Info screens».

## 3. Views

```python
from flask import request
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core import db, events
from flaskspark.core.web import ADMIN, user_id
from myapp.modules.notes.models import Note


class NotesView(FlaskSparkMethodView):
    url = "/notes"
    endpoint = "notes"                       # global eindeutig: mit Modulnamen
    area = {"GET": "notes", "*": ADMIN}      # oder "notes", OPEN, ADMIN; ohne area: ADMIN

    def get(self):
        with db.for_module("notes").session() as s:
            notes = s.scalars(db.select(Note).order_by(db.desc(Note.id))).all()
        return self.return_response({"notes": [{"id": n.id, "text": n.text} for n in notes]},
                                    template="notes/index.html")

    def post(self):
        text = ((request.get_json(silent=True) or {}).get("text") or "").strip()
        if not text:
            return self.return_error("text is required")
        with db.for_module("notes").session() as s:
            s.add(Note(text=text, owner_id=user_id()))
        events.publish("notes.changed", {})
        return self.return_response({"ok": True}, status=201)
```

- Templates erweitern `layouts/main.html` (Blöcke `page_title`, `content`, `page_header`, `page_styles`,
  `page_scripts`); Layout, CSS, Komponenten: Skill `flaskspark-ui`. Browser-JS über `flaskspark/ui.js`
  (`request`, `notice`), `flaskspark/forms.js`.
- `can(area)`, `user_id()`, `user_name()` aus `flaskspark.core.web` (in Templates `can`).
- Moduleigene Dateien auf Platte: `flaskspark.core.paths.state_dir("notes")` (`STATE_DIR/notes/`).

## 4. `client.py`: die einzige Schnittstelle nach aussen

Was andere Module oder die Web-App vom Modul brauchen, geht über Funktionen in `client.py` (nie über `models.py`).
Hat das Modul einen Service: NATS-Request mit Zeitlimit, ohne Antwort ein Dict mit `error` (oder ein Lesezugriff
auf die eigenen Tabellen als Rückfall). Muster: Skill `flaskspark-live-data` §4.

## 5. Einstellungen, Übersetzungen, Migration, Tests

- `CONFIG`/`SETTINGS`, Konten, Teilen, Anhänge: Skill `flaskspark-access-and-settings`.
- Texte englisch, `N_()` im Manifest, Katalog in `notes/locales/`: Skill `flaskspark-i18n`.
- Erste Migration: `myapp db upgrade && myapp db revision -m "notes: tables" --module notes`, Skript prüfen,
  committen: Skill `flaskspark-database`.
- Tests (Fixtures `app`/`client` aus Skill `flaskspark-new-app` §5): Seite mit erlaubtem Bereich 200, API-Antworten,
  Rechte (Session des Moduls erreicht fremde Tabellen nicht: `db.DatabaseAccessError`), `differences() == {}`.
- Prüfen: `myapp modules` (geladen, Reihenfolge, fehlende Abhängigkeiten), `flask --app
  flaskspark.core.web.app:create_app routes`, Seite hell/dunkel im Browser (ungetestet, wenn nicht angesehen).
