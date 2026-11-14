---
name: flaskspark-new-app
description: Neue App auf FlaskSpark (flaskspark.core) anlegen oder eine bestehende auf das Paket-Layout bringen -
  Paketstruktur, Entry Points flaskspark.apps/modules/themes in pyproject.toml, config.yaml, Konsolenskript,
  Theme-Paket, erster Start mit Migrationen, `<app> run` in der Entwicklung, Testsetup mit der eingebauten Web-App.
  Verwenden, wenn ein neues Projekt auf FlaskSpark entsteht, eine App ihr pyproject/config.yaml/Theme bekommt oder
  ein Projekt im «klassischen Layout» (web/, src/modules/) umgestellt wird.
---

# Neue App auf FlaskSpark

FlaskSpark ist die Laufzeit: die App **liefert nur Module** (und ein Theme) als installiertes Python-Paket mit Entry
Points. Web-App, CLI, Services, Router, Migrationen kommen von FlaskSpark. Massgebend: README von FlaskSpark, Abschnitte
«Modular apps», «Project layout», «Minimal example», «`config.yaml`», «Environment variables».

## 1. Paket anlegen

```text
myapp/
  pyproject.toml
  .env                      # nur Entwicklung: SECRET_KEY=…  (nie committen)
  tests/conftest.py
  src/myapp/
    __init__.py
    config.yaml             # Defaults der Installation (keine Secrets!)
    locales/                # optional: Katalog der App, gewinnt über die der Module
    theme/                  # optional: __init__.py, theme.yaml, theme.css, images/
    modules/__init__.py
    modules/notes/…         # je Modul ein Paket → Skill flaskspark-new-module
```

Leere `__init__.py` in `src/myapp/`, `modules/`, `theme/`, jedem Modul, dessen `web/` und `web/views/`.

```toml
[project]
name = "myapp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["FlaskSpark[core]"]          # Thumbnails von Anhängen: "FlaskSpark[core,files]"

[project.scripts]
myapp = "flaskspark.core.cli:main"            # Alias von `flaskspark`

[project.entry-points."flaskspark.apps"]
myapp = "myapp"                               # genau eine App pro Installation (sonst APP_NAME)

[project.entry-points."flaskspark.modules"]
notes = "myapp.modules.notes"                 # Name = Module.NAME

[project.entry-points."flaskspark.themes"]
mybrand = "myapp.theme"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
myapp = ["config.yaml", "**/*.yaml", "**/*.html", "**/*.css", "**/*.js", "**/*.svg", "**/*.png",
         "**/*.po", "**/*.mo", "**/migrations/versions/*.py"]
```

- Jedes installierte Modul wird geladen (es gibt kein Ein-/Ausschalten); was ein Besucher sieht, entscheidet der
  Zugriff (Bereiche pro Rolle). `modules:` in `config.yaml` bzw. `APP_MODULES` nur zum Einschränken/Ordnen.
- Nach jeder Änderung an Entry Points neu installieren (`uv pip install -e .`), sonst findet FlaskSpark sie nicht.
- Fehlt etwas in `package-data` (Templates, `.mo`, Migrationen, Theme-Bilder), geht es bei editierbarer
  Installation, aber nicht im gebauten Paket/Container.

## 2. `config.yaml`

```yaml
app:
  name: myapp
  title: My App
  locales: [en, de]          # erste = Default
  # start: /notes            # optional: wohin «/» führt (Pfad oder Endpoint)
theme: mybrand               # Entry Point in flaskspark.themes; ohne: «default»
auth: none                   # none (OpenAccess) | oauth / sso (RoleAccess) → Skill flaskspark-access-and-settings
nats:
  embedded: true             # `myapp run` startet nats-server selbst (Binary nötig)
  port: 4222
# notifications: {enabled: true}   guardian: {enabled: true}   backup: {dir: …}  → Skill flaskspark-operations
# flask: {PERMANENT_SESSION_LIFETIME: 3600, ROLE_DEFAULTS: …}   Flask-/FlaskSpark-Einstellungen
notes:                       # Abschnitt pro Modul: cfg.section("notes")
  page_size: 20
```

Secrets nie in `config.yaml`: Umgebung bzw. `~/.config/<app>/app.env` und `<modul>.env` (`APP_CONFIG_DIR`), in der
Entwicklung `.env` im Projektverzeichnis. Top-Level `modules`, `theme`, `auth` sind nie Admin-Einstellungen.

## 3. Theme (optional)

`src/myapp/theme/theme.yaml` (`title`, `short_name`, `logo`, `logo_dark`, `favicon` – Dateien in `images/` –,
`theme_color`, `theme_color_dark`, `default_mode: light|dark|system`, `footer`) und `theme.css` **nur mit Tokens**
(`--app-accent`, `--app-page-bg`, … mit `light-dark()`); Token-Tabelle im README «Themes». Wo was hingehört:
Skill `flaskspark-ui`.

## 4. Erster Start

```bash
uv venv .venv && uv pip install -e .            # bzw. -e ../FlaskSpark[core] für eine lokale FlaskSpark-Kopie
echo "SECRET_KEY=change-me" > .env
.venv/bin/myapp db upgrade                       # ZUERST: Kern-Historie anlegen (revision verlangt Heads)
.venv/bin/myapp db revision -m "notes tables" --module notes   # erste Migration jedes Moduls mit Tabellen
.venv/bin/myapp db upgrade
.venv/bin/myapp modules                          # geladen? Theme? Module mit fehlenden DEPENDS?
.venv/bin/myapp run                              # Migrationen, (nats-server), web, push, Module-Services, Router
```

- Die App antwortet auf dem Router: `http://<host>:8100` (`APP_PORT`; Web intern 8101, Push 8102).
  Mehrere Apps auf einem Rechner: `APP_PORT`, `WEB_PORT`, `PUSH_PORT`, `NATS_PORT` pro App setzen.
- Ohne NATS laufen Web und Router trotzdem (Live-Daten fehlen, Push versucht es weiter). Ohne `nats-server`:
  `nats.embedded: false` und `NATS_URL`.
- Zustand (DB, Sessions, NATS-Store, Modulzustand) liegt in `~/.local/state/<app>` (`APP_STATE_DIR`), lokal, nie NFS.
- Die Web-App startet nicht auf einem Schema, das nicht auf den Heads ist (`… Run \`myapp db upgrade\``).

## 5. Tests der App

Pfade liest FlaskSpark beim Import aus der Umgebung: **vor** jedem Import von `flaskspark.core` setzen.

```python
# tests/conftest.py
import os
import tempfile

ROOT = tempfile.mkdtemp(prefix="myapp-tests-")
os.environ.update({
    "APP_STATE_DIR": f"{ROOT}/state",
    "APP_CONFIG_DIR": f"{ROOT}/conf",
    "SQLALCHEMY_DATABASE_URI": f"sqlite:///{ROOT}/app.db",
    "APP_NO_DOTENV": "1",
    "SECRET_KEY": "test",
})

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def app():
    from flaskspark.core import config
    from flaskspark.core.db import migrations
    from flaskspark.core.web.app import create

    migrations.upgrade(config.load(), backup_first=False)   # testet auch die Migrationen
    _, app = create()                                        # die eingebaute Web-App mit allen Modulen
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(app):
    client = app.test_client()
    client.environ_base["HTTP_ACCEPT_LANGUAGE"] = "en"
    return client
```

Pflichttest pro App: `assert migrations.differences(config.load()) == {}` (Modelle = Migrationen). Mit Anmeldung
testen: `create(auth="oauth")` mit `OAUTH_*`-Variablen und angemeldetem Benutzer in der Session, ohne echten
Identity Provider (Muster: `tests/core/sso.py` in FlaskSpark). NATS-Tests mit echtem `nats-server` pro Test-Modul (Muster:
`tests/core/test_nats_services.py` in FlaskSpark), ohne Binary `pytest.skip`.

## 6. Klassisches Layout umstellen

Projekte mit `web/wsgi.py`, `web/migrations`, `src/modules/<name>` laufen weiter. Umstellen nach README «The classic
layout» (Module ins App-Paket, Imports `modules.x` → `myapp.modules.x`, auch in `MODELS` und `ServiceInfo.entry`;
Entry Points; eine Migrationshistorie pro Modul, deren erste Revision die Tabellen exakt beschreibt; `web/` löschen;
Produktiv-DB einmal mit `myapp db adopt` übernehmen → Skill `flaskspark-database`).

## Siehe auch

`flaskspark-new-module`, `flaskspark-database`, `flaskspark-operations`, `flaskspark-ui`, `flaskspark-i18n`.
