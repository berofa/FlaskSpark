# FlaskSpark

FlaskSpark is a framework on top of [Flask](https://flask.palletsprojects.com) for server-rendered web applications in
Python. It has three parts that build on each other:

- **FlaskSpark apps**: a Flask application with conventions instead of boilerplate: class-based views that register
  themselves, SQLAlchemy with Flask-Migrate, an optional OAuth/OIDC sign-in, translations (Flask-Babel), an asset
  pipeline, sanitised Markdown and a base layout.
- **Modular apps** (`flaskspark.core`, optional): the runtime for larger applications made of **modules**. An
  application only delivers modules in an installed Python package; FlaskSpark builds the web app from their manifests
  (navigation, access per role, settings, database tables with a migration history per module, translations), brings a
  ready layout with themes, and runs the modules' background services, with live data in the browser over
  [NATS](https://nats.io).
- **Web components**: a library of custom elements on Bootstrap 6 (`ui-button`, `ui-dialog`, `ui-table`,
  `ui-datepicker`, a Markdown editor, …). FlaskSpark apps load them with one setting; any other website uses an
  exported copy, without Python.

It is meant for developers who build internal tools, dashboards and self-hosted applications for a team, a company or
a household: applications that run on one host or in a few containers, where a ready layout, access control and
operations matter more than a front-end build of their own.

## Contents

- [Getting started](#getting-started)
  - [Requirements](#requirements) · [Installation](#installation) · [Your first app](#your-first-app) ·
    [Your first modular app](#your-first-modular-app) · [Web components without Python](#web-components-without-python)
- [FlaskSpark apps](#flaskspark-apps): [project structure](#project-structure-and-discovery),
  [configuration](#configuration), [class-based views](#class-based-views), [templates](#templates),
  [assets](#assets-scss--js), [sign-in](#oauth-oidc-login-provider), [database](#database--migrations), [i18n](#i18n)
- [Modular apps (flaskspark.core)](#modular-apps-flasksparkcore): [project layout](#project-layout),
  [`config.yaml`](#configyaml), [environment](#environment-variables), [module manifest](#module-manifest),
  [access](#access), [start page](#start-page), [info screens](#info-screens), [settings](#settings), [personal settings](#personal-settings),
  [accounts](#accounts), [shares](#shares), [attachments](#attachments), [database](#database),
  [migrations](#migrations), [themes](#themes), [layout and pages](#layout-and-pages),
  [browser JavaScript](#browser-javascript), [translations](#translations), [live data](#live-data)
- [Running modular apps](#running-modular-apps): [services and the command line](#services-and-the-command-line),
  [status](#service-directory-and-status-tiles), [systemd](#systemd), [leadership](#leadership),
  [job queue](#job-queue), [notifications](#notifications), [guardian](#guardian), [backups](#backups),
  [secrets](#secrets), [NATS users](#nats-users-and-permissions), [sessions](#sessions), [deployment](#deployment)
- [Web components](#web-components)
- [Markdown](#markdown)
- [Development and tests](#development-and-tests)
- [Security notes](#security-notes)
- [License](#license)
- [Disclaimer](#disclaimer)

## Getting started

### Requirements
- Python 3.11 or newer.
- For modular apps: a [NATS](https://nats.io) server with JetStream for live data, heartbeats and the job queue. With
  `nats-server` on the `PATH`, FlaskSpark starts one itself (embedded mode). Without NATS the pages still work; live
  data, the status tiles and the job queue don't, and the log warns.
- Optional: `ffmpeg` on the `PATH` for thumbnails of videos (attachments).

### Installation
FlaskSpark is on PyPI. Install it into a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install FlaskSpark                  # FlaskSpark apps, Markdown and the web components
pip install "FlaskSpark[core]"          # + modular apps (flaskspark.core) and the command `flaskspark`
pip install "FlaskSpark[core,files]"    # + thumbnails of attachments
```

| Extra | Adds | For |
| --- | --- | --- |
| (none) | Flask, Flask-Login, Flask-SQLAlchemy, Flask-Migrate, Flask-Babel, Flask-Session, Flask-Assets with libsass, rcssmin and rjsmin, authlib, markdown-it-py, nh3, requests, python-dotenv | FlaskSpark apps, `flaskspark.markdown`, the web components |
| `core` | SQLAlchemy 2, Alembic, nats-py, aiohttp, httpx, gunicorn, cryptography, cachelib, PyYAML | modular apps (`flaskspark.core`) and the command line `flaskspark` |
| `files` | Pillow, pillow-heif, pypdfium2 | thumbnails of [attachments](#attachments) (images, HEIC photos, the first page of PDFs); without it attachments work, only without thumbnails |
| `dev` | pytest | the [tests](#development-and-tests) |

To work with a checkout of the repository instead, install it editable, e.g. from a project next to it:

```bash
pip install -e "../FlaskSpark[core,files]"
```

### Your first app
The smallest FlaskSpark app: one page, no database, no sign-in.

```text
myproject/
  .env
  app.py
  app/
    __init__.py
    views/
      home.py
    templates/
      home.html
```

`.env` (only `SECRET_KEY` is required; every other setting has a default, see [Configuration](#configuration)):
```dotenv
SECRET_KEY=change-me
```

`app/__init__.py`:
```python
from flaskspark import FlaskSpark

app = FlaskSpark(
    app_module="app",
).app
```

`app_module` is the name of your app's package directory (`app_module="tasks"` for `./tasks/`; then import
`from tasks import app` below).

`app/views/home.py`: every class-based view in `app/views/` is registered by itself:
```python
from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

class HomeView(FlaskSparkMethodView):
    url = "/"
    endpoint = "home"

    def get(self):
        return render_template("home.html")
```

`app/templates/home.html`:
```jinja2
{% extends "layouts/framework.html" %}

{% block title %}Home{% endblock %}

{% block app_body %}
<main class="container py-4">
  <h1>Hello from FlaskSpark</h1>
  <p>Your first page is running.</p>
</main>
{% endblock %}
```

`app.py`:
```python
from app import app

if __name__ == "__main__":
    app.run(
        host=app.config["APP_BIND_HOST"],
        port=app.config["APP_PORT"],
        debug=app.config["DEBUG"],
    )
```

Start it and open `http://localhost:5067`:
```bash
python app.py
```

This is Flask's development server: it listens on all interfaces (`APP_BIND_HOST=0.0.0.0`) and runs in debug mode
until `ENVIRONMENT=production` is set. In production set `ENVIRONMENT=production` and run the app under a WSGI server,
e.g. `pip install gunicorn` and `gunicorn --bind 127.0.0.1:5067 app:app` (the package `app`, its variable `app`).

Next steps: [models and migrations](#database--migrations), [a sign-in](#oauth-oidc-login-provider),
[translations](#i18n), [the web components](#web-components) (`VENDOR_INCLUDE_WEBCOMPONENTS=true`) and
[Markdown](#markdown).

### Your first modular app
A modular app is a Python package that delivers modules; FlaskSpark provides the web app, the layout and the command
line. This example builds the app «myapp» with one module «notes» and a theme of its own.

```text
myproject/
  pyproject.toml
  .env
  src/
    myapp/
      __init__.py
      config.yaml
      theme/
        __init__.py
        theme.yaml
        theme.css
        images/
          logo.svg
      modules/
        __init__.py
        notes/
          __init__.py
          module.py
          models.py
          web/
            __init__.py
            views/
              __init__.py
              notes.py
            templates/
              notes/
                index.html
```

The `__init__.py` files are empty.

**1. The package and its entry points** (`pyproject.toml`). The entry points tell FlaskSpark which package is the app,
which modules and which themes it delivers:
```toml
[project]
name = "myapp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["FlaskSpark[core]"]

[project.scripts]
myapp = "flaskspark.core.cli:main"       # optional: an alias of `flaskspark`

[project.entry-points."flaskspark.apps"]
myapp = "myapp"

[project.entry-points."flaskspark.modules"]
notes = "myapp.modules.notes"

[project.entry-points."flaskspark.themes"]
mybrand = "myapp.theme"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
myapp = ["config.yaml", "theme/theme.yaml", "theme/images/*", "**/*.html", "**/*.css", "**/*.js", "**/*.po",
         "**/*.mo", "**/migrations/versions/*.py"]
```

**2. The configuration** (`src/myapp/config.yaml`; every key: [`config.yaml`](#configyaml)):
```yaml
app:
  name: myapp
  title: My App
  locales: [en, de]
theme: mybrand
auth: none          # no sign-in: only in a trusted network (see Access)
nats:
  embedded: true    # `myapp run` starts nats-server itself
  port: 4222
```

**3. The module's manifest** (`src/myapp/modules/notes/module.py`): its access area, its entry in the navigation, its
tile on the start page and its tables ([all fields](#module-manifest)):
```python
from flaskspark.core.module import Area, Module, N_, NavItem, Tile

class Notes(Module):
    NAME = "notes"
    LABEL = N_("Notes")
    AREAS = (Area("notes", N_("Notes"), N_("Read and write notes")),)
    NAVIGATION = (NavItem(N_("Notes"), N_("All notes"), "/notes", "notes", icon="journal"),)
    TILES = (Tile(N_("Notes"), "/notes", "notes", N_("Short notes"), "journal"),)
    MODELS = ("myapp.modules.notes.models",)
    TABLES = ("notes_note",)
```

**4. Its table** (`src/myapp/modules/notes/models.py`), through FlaskSpark's [database API](#database):
```python
from flaskspark.core.db import Integer, Mapped, Model, String, mapped_column

class Note(Model):
    __tablename__ = "notes_note"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(200), nullable=False, default="")
```

**5. Its page**: a class-based view with the area it belongs to (`src/myapp/modules/notes/web/views/notes.py`):
```python
from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core import db
from myapp.modules.notes.models import Note

class NotesView(FlaskSparkMethodView):
    url = "/notes"
    endpoint = "notes"
    area = "notes"

    def get(self):
        with db.for_module("notes").session() as s:
            notes = [n.text for n in s.scalars(db.select(Note))]
        return render_template("notes/index.html", notes=notes)
```

and its template on FlaskSpark's layout (`src/myapp/modules/notes/web/templates/notes/index.html`):
```jinja2
{% extends "layouts/main.html" %}

{% block page_title %}{{ _("Notes") }}{% endblock %}

{% block content %}
<div class="app-page-head">
  <div><h1>{{ _("Notes") }}</h1></div>
</div>
<div class="app-stack">
  {% for note in notes %}<ui-card>{{ note }}</ui-card>{% endfor %}
</div>
{% endblock %}
```

**6. The theme** (optional; without one FlaskSpark's neutral theme `default` applies). `src/myapp/theme/theme.yaml`
names the branding, `theme.css` sets [tokens](#themes), the images live in `images/`:
```yaml
title: My Brand
short_name: Brand
logo: logo.svg
favicon: logo.svg
theme_color: "#ffffff"
theme_color_dark: "#000000"
default_mode: system
```

```css
:root {
  --app-accent: #0f766e;
  --app-accent-fg: light-dark(#0f766e, #5eead4);
}
```

**7. Install and start.** In the project directory:
```bash
pip install -e .
echo "SECRET_KEY=change-me" > .env
myapp db upgrade                                     # a new database: the core's tables
myapp db revision -m "notes tables" --module notes   # once: the module's first migration
myapp run                                            # migrations, nats-server, web, push and the router
```

Open `http://localhost:8100` (the router; the web service listens on 8101, the push service on 8102, NATS on 4222).
The database, the sessions and the NATS store live in `~/.local/state/myapp` (`APP_STATE_DIR`); `myapp modules` lists
what was loaded, `myapp --help` every command.

**8. A command of the module** (optional): a [click](https://click.palletsprojects.com) command or group named in the
manifest becomes part of the command line, in the web app's context:
```python
# src/myapp/modules/notes/cli.py
import click

from flaskspark.core import db
from myapp.modules.notes.models import Note

@click.group("notes")
def notes():
    """Notes."""

@notes.command("import")
@click.argument("text")
def import_note(text):
    """Add one note."""
    with db.for_module("notes").session() as s:
        s.add(Note(text=text))
    click.echo("imported")
```

```python
class Notes(Module):
    ...
    CLI = "myapp.modules.notes.cli:notes"
```

```bash
myapp notes import "Buy milk"
```

From here: [project layout](#project-layout) (services, translations, public JS of a module), [access with a
sign-in](#access), [settings the admins change](#settings) and [running it in production](#running-modular-apps).

### Web components without Python
Any website (a static site, a CMS theme, another framework) can use the web components. Make a copy of their plain
JS and CSS files in any environment with FlaskSpark installed:

```bash
python -m webcomponents.export public/assets/webcomponents bootstrap   # the module "bootstrap" with Bootstrap 6
```

Serve the directory and load the Bootstrap 6 CSS and the module:

```html
<!doctype html>
<html lang="en" data-bs-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Web components</title>
  <link rel="stylesheet" href="/assets/webcomponents/vendor/bootstrap6/css/bootstrap.min.css">
  <script type="module" src="/assets/webcomponents/modules/bootstrap/bootstrap.js"></script>
</head>
<body>
  <main class="container py-4">
    <ui-alert variant="info">Hello from a web component</ui-alert>
    <ui-button variant="primary">Save</ui-button>
  </main>
</body>
</html>
```

Nothing has to be built. More (single components, without the vendor libraries, the page tokens): [Web
components](#web-components) and [`webcomponents/README.md`](./webcomponents/README.md#export-without-python).

## FlaskSpark apps
A FlaskSpark app is a Flask application that `FlaskSpark(...)` builds from your app package. What it brings:

- a configurable app package (`app_module`), its views and models discovered and imported automatically
- class-based routing with `FlaskSparkMethodView` (routes register themselves), HTML and JSON from the same view
- SQLAlchemy and Flask-Migrate, wired up
- pluggable login providers with OAuth/OIDC (`authlib`)
- i18n with Flask-Babel
- templates and static files of the app first, FlaskSpark's as the fallback, and a base layout
  (`layouts/framework.html`) with hooks
- an SCSS/JS asset pipeline with optional minification and extra bundles, optionally with Bootstrap 5
- the [web components](#web-components) on Bootstrap 6 (opt-in) and [Markdown](#markdown)

### Project structure and discovery
A FlaskSpark app is one package (here `app/`) next to the script that starts it:

```text
myproject/
  .env              # settings and secrets (see Configuration)
  app.py            # starts the development server
  app/
    __init__.py     # app = FlaskSpark(app_module="app").app
    views/          # class-based views, registered automatically
    models/         # SQLAlchemy models, imported automatically
    templates/
    static/         # scss/app.scss and js/app.js are the asset entries (optional)
    helpers/        # e.g. a login provider of your own (optional)
    locales/        # translations (optional)
  migrations/       # Flask-Migrate (created by `flask db init`)
```

#### Automatic discovery behavior
- Views: Files under `app/views/` are auto-imported, and view classes inheriting from `FlaskSparkMethodView` are auto-registered as routes.
- Models: Files under `app/models/` are auto-imported and included in SQLAlchemy metadata.
- Templates/static: App files are resolved first; FlaskSpark files are fallback.
- A submodule that fails to import is skipped with a warning; with `STRICT_IMPORTS` it stops the start instead.

#### Module packages
Larger apps can keep each feature in a package of its own, next to `app/`:

```python
FlaskSpark(app_module="app", login_provider="OAuth", modules=["modules.mail.web", "modules.calendar.web"])
```

Each module package is set up like the app itself:

- `<package>/views/` and `<package>/models/` are auto-imported and registered (same rules as `app/views/`);
- `<package>/templates/` is searched after the app's templates and before FlaskSpark's (keep a module's
  templates in a folder of its own, e.g. `templates/mail/`, so names don't clash);
- `<package>/static/` is served under `/static/` after the app's static files and before FlaskSpark's.

`FlaskSpark.static_dirs` lists the static directories in this lookup order (e.g. for tools that read the files).
A package that doesn't exist stops the start.

### Configuration
All configuration values are read from environment variables (or overridden via the `config={...}` dict in `FlaskSpark(...)`).

#### Configuration precedence
FlaskSpark resolves configuration in this order (later entries override earlier entries):

1. FlaskSpark defaults (`flaskspark/config.py`)
2. `.env` values loaded via `dotenv_path`
3. explicit `config={...}` values passed to `FlaskSpark(...)`
4. explicit runtime arguments in `app.run(...)` (for host/port/debug only)

Recommendation:
- Keep runtime/environment values in `.env`.
- Use `config={...}` mainly for app-structure settings that are hard to express as env values (for example complex `ASSETS_BUNDLES` lists).
- In `app.py`, pass `host/port/debug` from `app.config` so env/config values are respected.

FlaskSpark's settings (the table below) are read from the environment when `FlaskSpark(...)` is created (after its `.env` is loaded), not when `flaskspark` is imported (`flaskspark.config.from_environment()`; `flaskspark.config.Config` stays as the snapshot of the import).

Why not just `app.run()`?
- `app.run()` without arguments uses Flask defaults (`127.0.0.1:5000`, `debug=False`) and does not automatically apply your `APP_BIND_HOST` / `APP_PORT` settings.
- `app.run(host=app.config["APP_BIND_HOST"], port=app.config["APP_PORT"], debug=app.config["DEBUG"])` keeps startup aligned with FlaskSpark config and `.env`.

| Key | Default | Description |
| --- | --- | --- |
| `SECRET_KEY` | `None` | Flask secret key. Required for sessions/security features. |
| `ENVIRONMENT` | `development` | High-level mode. `production` disables debug defaults; any other value is treated as development. |
| `FLASK_ENV` | Derived | Computed from `ENVIRONMENT` (`production` or `development`). |
| `DEBUG` | Derived | Computed from `ENVIRONMENT` (`False` in production, else `True`). |
| `SQLALCHEMY_DATABASE_URI` | `sqlite:///app.db` | Database connection string (a relative SQLite path lies in Flask's instance folder, `instance/`). If unset, `DATABASE_URL` is checked first. |
| `DATABASE_URL` | `None` | Optional fallback source for `SQLALCHEMY_DATABASE_URI`. |
| `SQLALCHEMY_TRACK_MODIFICATIONS` | `False` | SQLAlchemy tracking flag (fixed default in FlaskSpark config). |
| `OAUTH_NAME` | `None` | OAuth provider name/alias. |
| `OAUTH_AUTHORIZE_URL` | `None` | OAuth authorize endpoint URL. |
| `OAUTH_ACCESS_TOKEN_URL` | `None` | OAuth access token endpoint URL. |
| `OAUTH_USERINFO_ENDPOINT` | `None` | OAuth userinfo endpoint URL. |
| `OAUTH_JWKS_URI` | `None` | JWKS URI for token validation metadata. |
| `OAUTH_CLIENT_ID` | `None` | OAuth client ID. |
| `OAUTH_CLIENT_SECRET` | `None` | OAuth client secret. |
| `OAUTH_SCOPE` | `None` | OAuth scope string. |
| `OAUTH_REDIRECT_URI` | `None` | Optional explicit callback URL (otherwise auto-generated). |
| `OAUTH_GROUPS_CLAIM` | `groups` | Claim name used for group extraction. |
| `OAUTH_ROLE_PRIORITY` | `[]` | Ordered group names for role mapping (CSV env input). |
| `OAUTH_ROLE_MAP` | `{}` | Group-to-role mapping (format: `group:Role,group2:Role2`). |
| `ROLE_DEFAULTS` | `[]` | Default roles created at login/startup (format: `Name:rank[:admin],Name2:rank2`; in code a list of `(name, is_admin, rank)`). Empty: Administrators, Editors, Users, Guests. |
| `STRICT_IMPORTS` | `false` | A view or model module that fails to import stops the start instead of being skipped with a warning. |
| `BABEL_DEFAULT_LOCALE` | `en` | Fallback locale. |
| `BABEL_SUPPORTED_LOCALES` | `["en"]` | Allowed locales (CSV env input). |
| `BABEL_TRANSLATION_DIRECTORIES` | `locales` | Translation directory path(s) for Flask-Babel. |
| `ASSETS_ENABLE` | `true` | Enables Flask-Assets pipeline. |
| `ASSETS_AUTO_BUILD` | `true` | Enables on-demand asset builds. |
| `ASSETS_DEBUG` | `false` | Asset debug flag. |
| `ASSETS_BUILD_ON_START` | `false` | Forces bundle builds at startup. |
| `ASSETS_FORCE_BUILD` | `false` | Forces rebuild even when cached outputs exist. |
| `ASSETS_CACHE` | `true` in production | webassets filter cache. It is keyed on the entry file's content, so changes in imported SCSS partials are missed; set `False` (app config) together with `ASSETS_FORCE_BUILD` to rebuild from all sources on start. |
| `ASSETS_SCSS_ENTRY` | `scss/app.scss` | Main SCSS entry file (relative to app static root). |
| `ASSETS_JS_ENTRY` | `js/app.js` | Main JS entry file (relative to app static root). |
| `ASSETS_SCSS_OUTPUT` | `styles/app.min.css` | Main CSS output path. |
| `ASSETS_JS_OUTPUT` | `scripts/app.min.js` | Main JS output path. |
| `ASSETS_SCSS_FILTERS` | `libsass,rcssmin` | SCSS filter chain. |
| `ASSETS_JS_FILTERS` | `rjsmin` | JS filter chain. |
| `ASSETS_SCSS_INCLUDE_PATHS` | `[]` | Extra SCSS include paths (CSV env input). |
| `ASSETS_BUNDLES` | `[]` | Extra bundles list (config dict only, not env string). |
| `VENDOR_INCLUDE_BOOTSTRAP` | `false` | If `true`, FlaskSpark prepends vendored Bootstrap SCSS/JS into app bundles. |
| `VENDOR_INCLUDE_WEBCOMPONENTS` | `false` | If `true`, FlaskSpark registers the blueprint of the web components (`/webcomponents/…`) and `layouts/framework.html` loads the Bootstrap 6 CSS and their `bootstrap` module. Excludes `VENDOR_INCLUDE_BOOTSTRAP`. See [Web components](#web-components). |
| `APP_LAYOUT_TEMPLATE` | `layouts/framework.html` | Default layout injected into template context as `layout`. |
| `APP_HOST` | `0.0.0.0` | Optional app host value for app-level logic. |
| `APP_BIND_HOST` | `0.0.0.0` | Socket bind address used by `app.run(...)`. |
| `APP_PORT` | `5067` | Socket bind port used by `app.run(...)` (in a modular app: the router's port, default `8100`). |

### Class-Based Views
FlaskSpark is designed around class-based views.

Recommended pattern:
- put your view classes in `app/views/*.py`
- inherit from `FlaskSparkMethodView`
- define `url` and `endpoint` on the class
- implement HTTP methods as class methods (`get`, `post`, `put`, `delete`, ...)

Avoid `@app.route(...)` in your app code.  
FlaskSpark auto-discovers and registers class-based views from `app/views/`, so route decorators are usually unnecessary and can make routing behavior inconsistent.

#### How auto-registration works
- FlaskSpark imports modules under `app/views/`
- each class with `as_view()` is considered a view
- route is registered via:
  - `url` class attribute (fallback: `/<module_name>`)
  - `endpoint` class attribute (fallback: `<module_name>`)
- a view with `fallback = True` is a default: it is registered only when no other view (of the app or a module) has the same `url` (e.g. a start page a module may replace)

Use explicit `url` and `endpoint` to keep routes stable and readable.

#### Example: regular HTML view (GET + POST)
```python
from flask import redirect, render_template, request, url_for
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

class ContactView(FlaskSparkMethodView):
    url = "/contact"
    endpoint = "contact"

    def get(self):
        return render_template("contact.html")

    def post(self):
        name = request.form.get("name", "").strip()
        if not name:
            return render_template("contact.html", error="Name is required"), 400

        # Save/process data here
        return redirect(url_for("contact"))
```

#### Example: API collection endpoint (GET + POST)
```python
from flask import jsonify, request
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

class TasksApiView(FlaskSparkMethodView):
    url = "/api/tasks"
    endpoint = "api_tasks"

    def get(self):
        tasks = [{"id": 1, "title": "Buy milk"}]
        return jsonify(tasks), 200

    def post(self):
        payload = request.get_json(silent=True) or {}
        title = (payload.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title is required"}), 400

        created = {"id": 2, "title": title}
        return jsonify(created), 201
```

#### Example: API detail endpoint (GET + PUT + DELETE)
```python
from flask import jsonify, request
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

class TaskDetailApiView(FlaskSparkMethodView):
    url = "/api/tasks/<int:task_id>"
    endpoint = "api_task_detail"

    def get(self, task_id):
        return jsonify({"id": task_id, "title": "Example"}), 200

    def put(self, task_id):
        payload = request.get_json(silent=True) or {}
        title = (payload.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title is required"}), 400

        return jsonify({"id": task_id, "title": title}), 200

    def delete(self, task_id):
        return "", 204
```

#### HTML and JSON from the same view: `return_response(...)`
Every action of a `FlaskSparkMethodView` can serve both browsers (HTML) and API clients (JSON) from the same URL.
`return_response(...)` decides per request (content negotiation):

1. Query parameter `?format=json` (or `?format=html` to force HTML)
2. `Accept` header that prefers `application/json` over `text/html`
3. Fallback: JSON request body (`Content-Type: application/json`)

A wildcard `Accept: */*` (e.g. curl's default) gets HTML. `self.wants_json()` exposes the decision to your own code.

Signature:
```python
self.return_response(data, template=None, status=200, context=None,
                     redirect_to=None, message=None, category="success")
self.return_error(message, status=400, redirect_to=None, category="danger", **details)
```

- **JSON:** `data` is returned with `status`. Values are made JSON-serialisable first
  (`datetime`/`date` as ISO 8601, `Decimal` as float, sets/tuples as lists, dataclasses, objects with `to_dict()`).
- **HTML:** `template` is rendered with the keys of `data` plus `context` as template variables.
  `context` is for template-only values that should not be part of the JSON.
- **HTML after a POST:** with `redirect_to` the client is redirected (Post/Redirect/Get), `message` is flashed.
- **Errors:** `return_error(...)` returns `{"error": message, **details}` with `status` to JSON clients and
  flashes + redirects HTML clients.
- **HTTP errors** (404, 405, 500 …) are returned as `{"error", "message", "status"}` to JSON clients;
  HTML clients keep the regular error pages.

Example:
```python
from flask import request
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

class TasksView(FlaskSparkMethodView):
    url = "/tasks"
    endpoint = "tasks"

    def get(self):
        return self.return_response({"tasks": load_tasks()}, template="tasks.html")

    def post(self):
        # Form fields from the page or a JSON body from API clients
        payload = (request.get_json(silent=True) if request.is_json else request.form) or {}
        title = (payload.get("title") or "").strip()
        if not title:
            return self.return_error("title is required", redirect_to="/tasks")
        task = create_task(title)
        return self.return_response(task, status=201, redirect_to="/tasks", message="Task created")
```

```sh
curl http://localhost:5067/tasks                                   # HTML
curl -H 'Accept: application/json' http://localhost:5067/tasks     # JSON
curl http://localhost:5067/tasks?format=json                       # JSON
curl -H 'Content-Type: application/json' -d '{"title":"Buy milk"}' http://localhost:5067/tasks  # 201 + JSON
```

#### Login-protected class-based views
If you use a login provider, you can require authentication per view:

```python
class AdminView(FlaskSparkMethodView):
    url = "/admin"
    endpoint = "admin"
    require_login = True

    def get(self):
        return "Admin area"
```

If `require_login = True` is set but no login provider is configured, FlaskSpark raises an error at startup.

### Templates
FlaskSpark provides a framework base layout:
- `layouts/framework.html`

You have three common options:

1. Use framework layout directly in page templates
```jinja2
{% extends "layouts/framework.html" %}

{% block title %}Home{% endblock %}
{% block app_body %}
<main class="container py-4">
  <h1>Hello</h1>
</main>
{% endblock %}
```

2. Create your own app layout that inherits from framework layout (recommended)
```jinja2
{# app/templates/layouts/main.html #}
{% extends "layouts/framework.html" %}

{% block app_head %}
  {% block head_extra %}{% endblock %}
{% endblock %}

{% block app_body %}
  <header>...</header>
  {% block content %}{% endblock %}
{% endblock %}

{% block app_scripts %}
  {% block scripts %}{% endblock %}
{% endblock %}
```

Then your pages extend your app layout:
```jinja2
{# app/templates/home.html #}
{% extends "layouts/main.html" %}

{% block content %}
<main>Home page</main>
{% endblock %}
```

3. Do not inherit from framework layout
- This is possible, but then your template must include all required HTML structure and asset tags itself (for example `styles/app.min.css` and `scripts/app.min.js`).
- You also skip framework-provided hook blocks and conventions.

Template/static resolution order:
- App templates/static files are resolved first.
- If not found, FlaskSpark falls back to its own templates/static.

Available framework hooks in `layouts/framework.html`:
- `flaskspark_head_start`
- `flaskspark_vendor_styles` (Bootstrap 6 CSS with `VENDOR_INCLUDE_WEBCOMPONENTS`)
- `flaskspark_head_assets`
- `app_head`
- `body_attrs`
- `flaskspark_body_start`
- `app_body`
- `flaskspark_body_end`
- `flaskspark_vendor_scripts` (the web components' `bootstrap` module with `VENDOR_INCLUDE_WEBCOMPONENTS`)
- `flaskspark_scripts`
- `app_scripts`

FlaskSpark itself does not ship page views. It provides framework plumbing
(layout base, helpers, auth/database/assets integration), while applications
provide their own frontend views/templates.

### Assets (SCSS / JS)
FlaskSpark uses Flask-Assets to build your frontend bundles.  
In normal usage you define source entries once and FlaskSpark serves the generated outputs in the framework layout.

#### What assets are for
- Compile SCSS to CSS
- Minify CSS/JS (depending on configured filters and environment)
- Bundle app-level JavaScript and optional vendor sources (for example Bootstrap)
- Keep output paths stable so templates can always include `styles/app.min.css` and `scripts/app.min.js`

#### When to configure assets
- You can skip most asset config if you follow defaults:
  - SCSS entry: `app/static/scss/app.scss`
  - JS entry: `app/static/js/app.js`
  - CSS output: `app/static/styles/app.min.css`
  - JS output: `app/static/scripts/app.min.js`
- Configure asset keys only when:
  - you use different source filenames/paths
  - you want different output filenames
  - you need extra bundle definitions (`ASSETS_BUNDLES`)
  - you need extra SCSS include paths

#### Minimal default setup
No extra config required, just create:
```text
app/static/scss/app.scss
app/static/js/app.js
```

FlaskSpark will build and serve:
```text
app/static/styles/app.min.css
app/static/scripts/app.min.js
```

#### Typical `.env` asset settings
```dotenv
ASSETS_ENABLE=true
ASSETS_AUTO_BUILD=true
ASSETS_BUILD_ON_START=true
ASSETS_FORCE_BUILD=true
ASSETS_SCSS_FILTERS=libsass,rcssmin
ASSETS_JS_FILTERS=rjsmin
VENDOR_INCLUDE_BOOTSTRAP=true
```

Notes:
- `VENDOR_INCLUDE_BOOTSTRAP=true` prepends FlaskSpark's vendored Bootstrap SCSS/JS into your main app bundles.
- In development, keep auto-build enabled for fast iteration.
- In production, you typically build on startup and avoid unnecessary rebuilds.

#### Advanced example (`config={...}`)
Use this only when you need extra app-specific bundles:
```python
FlaskSpark(
    app_module="app",
    config={
        "ASSETS_BUNDLES": [
            {
                "name": "reports_js",
                "type": "js",
                "entry": "js/reports.js",
                "output": "scripts/reports.min.js",
                "filters": "rjsmin",
            },
        ],
    },
)
```

What this does:
- Each entry in `ASSETS_BUNDLES` registers an additional build target.
- FlaskSpark will generate the configured output file (for example `scripts/reports.min.js`) using the given filters.
- You can then include that generated file in templates via `url_for('static', filename='...')`.

When to add bundle entries:
- Add a new JS/SCSS file and you want it built as a separate output (for example page-specific assets).
- Add an entry to `ASSETS_BUNDLES` so FlaskSpark knows source, output, and filters.
- Without an entry, only the main default bundle (`app.min.css` / `app.min.js`) is generated.

### OAuth (OIDC) Login Provider
Login is optional in FlaskSpark.

If you do not need authentication, do not pass a login provider:
```python
from flaskspark import FlaskSpark

app = FlaskSpark(app_module="app").app
```

If you need authentication, configure a provider:
- `login_provider="Default"` reserved for the upcoming built-in default provider (currently a stub)
- `login_provider="OAuth"` for OAuth/OIDC via `authlib`

Current implementation status:
- `OAuth` is implemented and usable.
- `Default` exists as a provider stub but is not fully implemented yet.

Example:
```python
from flaskspark import FlaskSpark

app = FlaskSpark(
    app_module="app",
    login_provider="OAuth",
).app
```

#### Important: database is required for login providers
When a login provider is enabled, FlaskSpark expects database tables/models and checks DB availability at startup.

Before running with a login provider, create/update the DB schema (see [Database & Migrations](#database--migrations)):

```bash
FLASK_APP=app.py python -m flask db init
FLASK_APP=app.py python -m flask db migrate -m "init auth"
FLASK_APP=app.py python -m flask db upgrade
```

(If `db init` was already run once, only `migrate` + `upgrade` are needed.)

#### OAuth/OIDC required configuration
Set these values in `.env`:

```dotenv
OAUTH_NAME=your-provider-name
OAUTH_AUTHORIZE_URL=https://idp.example.com/oauth2/authorize
OAUTH_ACCESS_TOKEN_URL=https://idp.example.com/oauth2/token
OAUTH_USERINFO_ENDPOINT=https://idp.example.com/oauth2/userinfo
OAUTH_JWKS_URI=https://idp.example.com/.well-known/jwks.json
OAUTH_CLIENT_ID=...
OAUTH_CLIENT_SECRET=...
OAUTH_SCOPE=openid profile email
```

Optional:

```dotenv
OAUTH_REDIRECT_URI=https://your-app.example.com/auth/callback
OAUTH_GROUPS_CLAIM=groups
OAUTH_ROLE_PRIORITY=admins,editors,users
OAUTH_ROLE_MAP=admins:Administrators,editors:Editors,users:Users
```

Notes:
- If `OAUTH_REDIRECT_URI` is not set, FlaskSpark builds the callback URL automatically.
- OAuth routes are provided by FlaskSpark (`/auth/login`, `/auth/callback`, `/auth/logout`).

#### Build your own login provider
You can add custom providers by implementing `AbstractLoginProvider`.

Provider naming convention:
- class name: `<Name>LoginProvider`
- module name in your app: `<app_module>/helpers/login_provider_<name>.py`
- runtime value: `login_provider="<Name>"`

Lookup order:
1. `<app_module>.helpers.login_provider_<name>` (your app)
2. `flaskspark.helpers.login_provider_<name>` (framework fallback)

Minimal example:
```python
from flaskspark.helpers.login_provider import AbstractLoginProvider

class SsoLoginProvider(AbstractLoginProvider):
    requires_user_model = True
    requires_role_model = False

    def check_configuration(self, config):
        if not config.get("SSO_ISSUER"):
            raise ValueError("SSO_ISSUER is required")

    def configure(self):
        self.login_manager.login_view = "auth.login"
        # register blueprint/routes/user loading here
```

Example project path (for `app_module="app"`):
- `app/helpers/login_provider_<name>.py`

### Database & Migrations
FlaskSpark wires SQLAlchemy + Flask-Migrate automatically.

When you define models in your app package, FlaskSpark imports them from:
- `app/models/*.py` (or `<app_module>/models/*.py`)

Those models are then included in SQLAlchemy metadata and migration diffs.

#### 1. Configure your database
Set a DB URL in `.env` (recommended):

```dotenv
SQLALCHEMY_DATABASE_URI=sqlite:///app.db
```

Notes:
- A relative SQLite path is relative to Flask's instance folder: `sqlite:///app.db` is `instance/app.db` next to the app package (created on first use).
- If `SQLALCHEMY_DATABASE_URI` is not set, FlaskSpark falls back to `DATABASE_URL`.
- If neither is set, default is `sqlite:///app.db`.

#### 2. Create a model
Example file: `app/models/task.py`

```python
from flaskspark import db

class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    done = db.Column(db.Boolean, default=False, nullable=False)
```

Make sure `app/models/__init__.py` exists (can be empty).

#### 3. Initialize migrations (once per project)
```bash
FLASK_APP=app.py python -m flask db init
```

This creates the `migrations/` directory.

#### 4. Create and apply migrations
After creating/changing models:

```bash
FLASK_APP=app.py python -m flask db migrate -m "add tasks table"
FLASK_APP=app.py python -m flask db upgrade
```

Typical workflow:
1. Change model classes in `app/models/`
2. Run `flask db migrate -m "..."`
3. Review generated migration in `migrations/versions/`
4. Run `flask db upgrade`

#### Useful commands
```bash
FLASK_APP=app.py python -m flask db current
FLASK_APP=app.py python -m flask db history
FLASK_APP=app.py python -m flask db downgrade -1
```

#### When is DB required?
- No database-related models and no login provider: DB can be omitted.
- Login provider enabled (`Default` or `OAuth`): DB is required and schema must be migrated before startup.

### i18n
FlaskSpark initializes Flask-Babel automatically.

#### 1. Configure locales
Minimal `.env` example:

```dotenv
BABEL_DEFAULT_LOCALE=en
BABEL_SUPPORTED_LOCALES=en,de
BABEL_TRANSLATION_DIRECTORIES=locales
```

This means:
- default language is `en`
- allowed languages are `en` and `de`
- translation files are read from `locales/` inside the app package (`app/locales`; relative paths are relative to it)

#### 2. Mark strings for translation
In Python:

```python
from flask_babel import gettext as _

title = _("Overview")
```

In Jinja templates:

```jinja2
<h1>{{ _("Overview") }}</h1>
```

#### 3. Add Babel extraction config
Create `babel.cfg` in your project root:

```ini
[python: **.py]
[jinja2: **/templates/**.html]
```

#### 4. Extract / init / update / compile translations
Run these commands from your project root (they scan the app package only, not the virtual environment):

```bash
pybabel extract -F babel.cfg -o messages.pot app
pybabel init -i messages.pot -d app/locales -l de
pybabel update -i messages.pot -d app/locales
pybabel compile -d app/locales
```

What they do:
- `extract`: scans code/templates and builds the source catalog (`messages.pot`)
- `init`: creates a new language (for example German)
- `update`: refreshes existing language files after text changes
- `compile`: builds `.mo` files used at runtime (required before running in production)

#### 5. Set active language at runtime
FlaskSpark selects locale in this order:

0. `FlaskSpark.locale_preferences`: callables asked first (the first supported code one returns wins; `flaskspark.core` adds the signed-in user's language from the profile)
1. `lang` cookie (if valid and supported)
2. browser `Accept-Language`
3. `BABEL_DEFAULT_LOCALE`

#### Optional: client-side translations endpoint
FlaskSpark also provides:

```text
GET /_flaskspark/i18n?keys=Overview,Logout
```

Response example:

```json
{
  "Overview": "Übersicht",
  "Logout": "Abmelden"
}
```

## Modular apps (flaskspark.core)
`flaskspark.core` is the core of larger applications that consist of **modules**. Every feature (for example notes, a calendar, a shop) is a module with a manifest. FlaskSpark is the runtime: an application only **delivers modules** (as an installed Python package with entry points), and FlaskSpark loads every installed module automatically and builds the app from their manifests: navigation, start page tiles, access areas, database tables with rights per module and their migrations, translations, live data for the browser and the module's own background services. There is nothing to switch a module on or off: what a visitor may use decides the access (the areas per role). A **theme** brings the branding (name, logos, colours). The core knows no module and no theme itself.

What you get:
- a built-in web app on FlaskSpark with a ready layout (sidebar navigation, colour mode, language switch) built on the [web components](#web-components); the application brings no web app of its own
- migrations per module (Alembic): every module keeps its own history, FlaskSpark runs them at the start
- the command line `flaskspark` (services, migrations, status, backups)
- a database API (SQLAlchemy) where every module only reaches its own tables
- services as separate processes that talk over [NATS](https://nats.io), live data in the browser via Server-Sent Events
- a router (one port in front of all services) and a supervisor that runs everything in one process tree (one container, development)
- access: views carry their area; without sign-in (a trusted network) or with an OAuth/OIDC sign-in and a role × area matrix the admins edit, without touching the modules
- settings of `config.yaml` the admins change in the web app, personal settings of every user
- operations: a service directory (heartbeats), status tiles, systemd readiness and watchdog, leadership, a durable job queue, notifications, a guardian and backups
- sessions on the server
- the core's texts in English and German (its own catalogue)

It needs the extra `core` (`pip install "FlaskSpark[core]"`). A complete small example, step by step: [Your first modular app](#your-first-modular-app).

### Project layout
An application is one Python package that declares its parts as entry points:

```text
myapp/
  pyproject.toml              # the package, its entry points and (optionally) its own console script
  .env                        # secrets for development (SECRET_KEY, ...)
  src/
    myapp/
      __init__.py
      config.yaml             # app, theme, NATS (the defaults of the installation)
      locales/                # the app's own catalogue (optional, wins over the modules')
      theme/                  # the theme (optional; without one the built-in "default")
        __init__.py
        theme.yaml
        theme.css
        images/
      modules/
        __init__.py
        notes/                # one module
          __init__.py
          module.py           # the manifest (a Module subclass)
          models.py           # its tables (optional)
          migrations/versions/  # its migrations (its own Alembic history, optional)
          locales/            # its catalogue (optional)
          service.py          # its own long-running service (optional)
          client.py           # how other code talks to its service (optional)
          cli.py              # its commands of the command line (Module.CLI, optional)
          web/                # its web part (optional)
            __init__.py
            views/            # class-based views, auto-registered
              __init__.py
              notes.py
            templates/notes/  # its templates (in a folder of its own)
            static/notes/     # its CSS/JS, served under /static/notes/
            static/public/notes/  # JS other modules may import as "modules/notes/..."
```

```toml
# pyproject.toml
[project.entry-points."flaskspark.apps"]
myapp = "myapp"                          # the app's package: config.yaml, locales/, templates/, static/

[project.entry-points."flaskspark.modules"]
notes = "myapp.modules.notes"            # module name -> its package

[project.entry-points."flaskspark.themes"]
mybrand = "myapp.theme"                  # theme name -> a package directory with theme.yaml
```

- **Modules:** every installed module (entry point group `flaskspark.modules`, from any installed distribution) is loaded. Order: the manifest's `POSITION` (default 100), then the name. A module whose `DEPENDS` is not loaded is not loaded either; the start logs it as an error, `flaskspark modules` and the status tile «Modules» show it.
- **The application:** one installation runs exactly one application (entry point group `flaskspark.apps`; with several installed, `APP_NAME` picks one). Its package holds `config.yaml` (`APP_CONFIG_FILE` overrides the file); its name is the default of `APP_NAME` (the state and config directories).
- **The web app** is FlaskSpark's (`flaskspark.core.web.wsgi:app`): the app's package is its FlaskSpark application package (its `templates/`, `static/` and `views/` come first, before the modules'), the modules' `web` parts follow.
- **The command line** is `flaskspark` (FlaskSpark's console script); an app may add an alias, e.g. `myapp = "flaskspark.core.cli:main"` in `[project.scripts]`.

#### The classic layout (older projects)
Projects with `config.yaml`, `themes/<name>/` and `web/` (`web/app`, `web/wsgi.py`, `web/migrations`) in the project directory and their modules as `src/modules/<name>/` (imported as `modules.<name>`) keep working: the modules are those `config.yaml` names in `modules:`, the web service serves `web/wsgi.py`, and the migrations stay with Flask-Migrate in `web/migrations` (FlaskSpark runs nothing itself there). To move such a project to the package layout:

1. Move `src/modules/` and `themes/<name>/` into the app's package (`src/myapp/modules/`, `src/myapp/theme/`), `config.yaml` too; rename the imports `modules.<name>` to `myapp.modules.<name>` (also in the manifests' `MODELS` and `ServiceInfo.entry`).
2. Declare the entry points (above); drop `modules:` from `config.yaml` (or keep it to restrict and order the modules).
3. Split the migrations into one history per module (see [Migrations](#migrations)), delete `web/` and take over the production database once with `flaskspark db adopt`.
4. Move the app's translations into the modules' `locales/` (or the app's `locales/`).

### `config.yaml`
| Key | Default | Description |
| --- | --- | --- |
| `app.name` | `APP_NAME`, else the app's entry point name (classic layout: the project directory's name) | Name of the app (e.g. the CLI's program name). |
| `app.title` | `app.name` | Title of the app (`Config.title`). The pages' titles and the branding come from the theme's `title`. |
| `app.locales` | `[en]` | Languages of the web app; the first one is the default (also of the guardian's and the notifications' texts). |
| `app.start` | – | Where the start page («/») sends the visitor: a path (`/notes`) or an endpoint (`notes_list`). See [Start page](#start-page). |
| `flask` | – | Flask's and FlaskSpark's settings by their names, applied when the web app is created, e.g. `PERMANENT_SESSION_LIFETIME: 86400` (seconds) or `ROLE_DEFAULTS: ["Owners:90:admin", "Staff:10"]` (also as one comma separated text or `[name, admin, rank]` lists). They win over FlaskSpark's defaults from the environment; `create(extra_config=...)` wins over them. |
| `theme` | `default` | The theme (an entry point in `flaskspark.themes`, `themes/<name>/` in the classic layout, else a built-in one). `APP_THEME` overrides. |
| `auth` | `none` | The access: `none` (`OpenAccess`, no sign-in) or `oauth` / `sso` (`RoleAccess`, sign-in). See [Access](#access). |
| `modules` | – (every installed module) | Optional: restricts the installed modules to these and orders them (the classic layout names its modules here). `APP_MODULES` overrides. |
| `nats.embedded` | `false` | `<app> run` starts a local `nats-server` itself. `NATS_EMBEDDED` overrides. |
| `nats.port` | `4222` | Port of the embedded `nats-server`. `NATS_PORT` overrides. |
| `notifications.enabled` | `false` | Runs the notifications service; messages then go through the job queue. See [Notifications](#notifications). |
| `notifications.click` | – | Default link of a notification (e.g. the app's URL). |
| `notifications.language` | the first of `app.locales` | The language of the guardian's findings and of notifications sent as source texts. |
| `notifications.history` | `false` | Keep every notification sent in `STATE_DIR/notifications/history.jsonl` (`notify.history()`). |
| `guardian.enabled` | `false` | Runs the guardian. Its other keys override the guardian's settings. See [Guardian](#guardian). |
| `backup` | – | Settings of `<app> backup` (`dir`, `keep_hours`, `keep_days`, `state`, `max_age_hours`, `mirror_dir`, `include`); with the section the status shows a backup tile. See [Backups](#backups). |

A module may keep its own settings in a section of its name (`cfg.section("notes")`). The settings the admins changed in the web app are laid over `config.yaml` in every process (see [Settings](#settings)). Secrets never go into `config.yaml`; they come from the environment, filled from env files at the start of every process (the real environment wins, then the first file that names a variable):

1. `CONFIG_DIR/app.env` and `CONFIG_DIR/<module>.env` of every module
2. `PROJECT_DIR/.env` (development; skipped with `APP_NO_DOTENV`)

What FlaskSpark reads from the environment counts from these files too: its settings (e.g. `ROLE_DEFAULTS`, `OAUTH_*`) are read when the web app is created, after the files are loaded (`flaskspark.config.from_environment()`), `NATS_ENV_FILE` when NATS is first needed and `APP_SECRET_KEY_ENV` when a secret is first read. Only the variables that locate the files (`APP_PROJECT_DIR`, `APP_CONFIG_DIR`, `APP_CONFIG_FILE`, `APP_STATE_DIR`, `APP_NAME`) and the services' ports and bind addresses must be in the real environment.

### Environment variables
| Variable | Default | Description |
| --- | --- | --- |
| `APP_PROJECT_DIR` | The working directory (classic layout: the first directory with a `config.yaml` from the working directory upwards) | Where the processes run (`.env` for development). |
| `APP_NAME` | The app's entry point name (classic layout: the project directory's name) | Name used for the default directories (`<app>`) and default of `app.name`; picks the app when several are installed. |
| `APP_CONFIG_FILE` | `config.yaml` of the app's package (classic layout: `PROJECT_DIR/config.yaml`) | The configuration file. |
| `APP_CONFIG_DIR` | `~/.config/<app>` | Env files with secrets (`app.env`, `<module>.env`). |
| `APP_STATE_DIR` | `$XDG_STATE_HOME/<app>` or `~/.local/state/<app>` | Database, sessions, the embedded NATS store and the state of each module (`<module>/`). Keep it on a local disk. |
| `APP_THEMES_DIR` | `PROJECT_DIR/themes` | Themes in directories (classic layout; looked up before the installed ones). |
| `APP_THEME` | – | Overrides `theme` in `config.yaml`. |
| `APP_MODULES` | – | Overrides `modules` in `config.yaml` (comma separated): only these installed modules, in this order. |
| `APP_NO_DOTENV` | – | Do not read `PROJECT_DIR/.env` (tests). |
| `APP_SKIP_MIGRATION_CHECK` | – | Start the web app even if the database schema is not at the heads of the migrations. |
| `SQLALCHEMY_DATABASE_URI` | `sqlite:///STATE_DIR/app.db` | The database of every process. |
| `SECRET_KEY` | – | Flask secret key (see [Configuration](#configuration)). |
| `APP_PORT` | `8100` | Port of the router (also `ROUTER_PORT`; `APP_PORT` wins). |
| `ROUTER_HOST` | `0.0.0.0` | Bind address of the router. |
| `WEB_PORT` | `8101` | Port of the web service (gunicorn). |
| `WEB_HOST` | `127.0.0.1` | Bind address of the web service. |
| `WEB_THREADS` | `24` | Threads of the web service (one worker). |
| `PUSH_PORT` | `8102` | Port of the push service. |
| `PUSH_HOST` | `127.0.0.1` | Bind address of the push service. |
| `PUSH_SESSION_URL` | `http://127.0.0.1:<WEB_PORT>/api/push/session` | Where the push service checks a browser's session. |
| `NATS_URL` | `nats://127.0.0.1:4222` | NATS server(s), comma separated for a cluster. Set by the supervisor in the embedded mode. |
| `NATS_EMBEDDED` | `nats.embedded` | `1`/`true`/`yes`: the supervisor starts `nats-server`. |
| `NATS_PORT` | `nats.port` | Port of the embedded `nats-server`. |
| `NATS_SERVER` | `nats-server` | The `nats-server` binary of the embedded mode. |
| `NATS_<USER>_USER`, `NATS_<USER>_PASSWORD` | – | Credentials of a service's NATS user (the core's: `WEB`, `PUSH`, `NOTIFY`, `GUARDIAN`, e.g. `NATS_PUSH_USER`); without them the connection is anonymous. See [NATS users](#nats-users-and-permissions). |
| `NATS_REPLICAS` | `1` | Copies of new JetStream streams and key-value buckets. |
| `NATS_ENV_FILE` | – | An extra env file with `NATS_*` values (the environment wins); may itself be set in `CONFIG_DIR/app.env`. |
| `NATS_MONITOR` | – | Monitoring endpoints of the NATS servers, comma separated (e.g. `http://nats1:8222`): the NATS tile and the guardian read `/healthz`, `/varz` and `/jsz` there (a cluster is ok while a majority of its servers is); without, a short client connection. |
| `APP_HOST` | the host name | Where an instance runs, as the service directory shows it (e.g. the host of a container). |
| `APP_VERSION` | the version of the distribution `APP_NAME` | The version the heartbeats report. |
| `NTFY_URL`, `NTFY_TOPIC`, `NTFY_TOKEN` | – | The ntfy channel of the notifications (`NTFY_TOKEN` optional); without URL and topic there is no channel. |
| `OAUTH_*` | – | The identity provider with `auth: oauth` (see [OAuth](#oauth-oidc-login-provider)). |
| `APP_SECRET_KEY` | – | The key of the secrets modules store encrypted (see [Secrets](#secrets)). |
| `APP_SECRET_KEY_ENV` | `APP_SECRET_KEY` | The name of the variable holding that key (an application that already has one of its own); may be set in `CONFIG_DIR/app.env` like the key. |
| `APP_SECRET_KEY_<MODULE>` | – | A module's own key (else the shared one). |

### Module manifest
Every module has exactly one `Module` subclass in `<package>/module.py`. `NAME` (the name of its entry point) and `LABEL` are required, everything else is optional:

| Field | Description |
| --- | --- |
| `NAME`, `LABEL` | Name of the module and its label. |
| `EXPOSURE` | `INTERNAL` (default) or `PUBLIC` (`flaskspark.core.module`): whether the module may be part of an instance reachable from the internet. Anything else stops the import. `modules.internal(cfg)` lists the loaded modules that are not `PUBLIC`; what to do with that (e.g. refuse to start) is the application's choice. |
| `POSITION` | Its place among the modules (default 100; equal ones by `NAME`): the order of the navigation, and of tiles and areas of equal position. An explicit `modules:` list orders them instead. |
| `DEPENDS` | Modules it needs: without all of them loaded it is not loaded either (logged as an error, shown by `flaskspark modules` and the status tile «Modules»). |
| `OPTIONAL_DEPENDS` | Modules it uses when they are there; it asks `flaskspark.core.modules.is_enabled(cfg, name)` before it does (and imports nothing of theirs otherwise). |
| `SERVICES` | Its long-running processes: `ServiceInfo(name, label, entry, single=False, unit="")`; `name` is the short name (outside the code the service is `flaskspark-<name>`, see [Names](#services-and-the-command-line)), `entry` is `"<python module>:<function>"`, `unit` its systemd unit, default `flaskspark-<name>.service` (the status tiles fall back to systemd on the host while the service directory can't be read; `myapp units` lists them). |
| `ROUTES` | Paths the router sends to one of its services instead of the web app: `Route(prefix, port_env, default_port, websocket=False)`. |
| `AREAS` | Its access areas: `Area(key, label, description="", defaults=frozenset(), start="", position=100)`; `defaults`: the names of the roles that may use it until an admin changes it, `start`: its start page (default: its first navigation entry), `position`: its place among all areas (the matrix; the start page of the first one a visitor may use). |
| `NAVIGATION` | Entries of the sidebar: `NavItem(group, label, href, area, icon="", position=100, badge=None)`; `icon` is a [Bootstrap Icons](https://icons.getbootstrap.com) name, `badge` the name of a count the module's script fills (`[data-nav-badge="<badge>"]`, hidden until it does). |
| `NAV_BADGES` | Its counts on menu entries of any module: `NavBadge(href, badge, area)`; the layout adds a `[data-nav-badge="<badge>"]` to the entry with that `href`, for visitors with `area` only, after the entry's own badge. The module's script (`LAYOUT`) fills it. |
| `TILES` | Tiles on the start page: `Tile(label, href, area, description="", icon="", position=100)`. |
| `PUSH_TOPICS` | NATS topics the push service forwards to the browser: `PushTopic(pattern, area, latest=False)`; `{uid}` in the pattern stands for the user's id, `latest` sends the last update to a tab that subscribes. |
| `MODELS` | Its Python modules with tables (e.g. `"myapp.modules.notes.models"`), for the migrations. |
| `TABLES` | Its own tables: its database sessions reach only these and `SHARED_TABLES`. |
| `SHARED_TABLES` | Tables of others it may use. |
| `ACCOUNT_TYPES` | The [account types](#accounts) it uses, e.g. `("imap", "smtp")`: the profile offers only types a loaded module names, and `accounts.for_module(NAME)` reads only these. |
| `APP_ACCOUNT_TYPES` | The [account types](#accounts) it reads as accounts of the application (not of a person), e.g. `("gitlab",)`: the admins keep them in «Settings» → «Accounts», `accounts.for_module(NAME).app(type)` reads them. |
| `SHAREABLES` | Its kinds of items users may [share](#shares): `"<python module>:<class>"` of `flaskspark.core.shares.Shareable` subclasses. |
| `ATTACHMENT_OWNERS` | Its kinds of items with [files](#attachments): `"<python module>:<class>"` of `flaskspark.core.attachments.AttachmentOwner` subclasses. |
| `CONFIG` | Its settings of `config.yaml` the admins may change: `Setting(...)` (see [Settings](#settings)). |
| `SETTINGS` | Templates of its own sections in its tab of «Settings» (admins), above the generated form of `CONFIG`, e.g. `("notes/settings.html",)`; each brings its own script and API. |
| `PUBLIC_ENDPOINTS` | Endpoints reachable without a sign-in (e.g. an API for agents with its own authentication). |
| `PAGE_SECTIONS` | Templates it adds to a page: `"home"` (the core's start page), `"profile"` (the [profile](#accounts), with sign-in; in an app without sign-in the profile of the workstation; only of modules the visitor may use) and `"screen:<key>"` (an [info screen](#info-screens) of any module), e.g. `{"home": ("notes/home_section.html",), "profile": ("notes/profile.html",)}`. |
| `SCREENS` | Its [info screens](#info-screens): `Screen(key, title, area, description="", icon="", mode="", reload_at="04:00", position=100, show_title=True)`, each a page `/screen/<key>` for a display on the wall (`show_title=False`: only the logo in the head row). |
| `LAYOUT` | Templates included in every page (dialogs, scripts of the navigation). |
| `CLI` | `"<python module>:<click command or group>"`: a command of the app's command line (`myapp <command> …`, in the web app's context) and of the `flask` CLI (`flask --app flaskspark.core.web.app:create_app <command>`). |
| `PACKAGE` | Set by the loader: the module's package. |

Methods a module may override: `register()` (called once when the manifests are loaded, e.g. to register a notification channel), `template_filters()` and `template_globals()` (Jinja), `start_web(cfg)` (once in the web process, e.g. connections to other services), `status_tiles()` (its [status tiles](#service-directory-and-status-tiles)), `guard_checks()` (its checks for the [guardian](#guardian)), `push_sources(nc)` (its [topics served on demand](#live-data)), `backup_paths(cfg)` (directories outside the state directory that belong into every [backup](#backups)) and `account_change_veto(change)` (refuse a change of an [account](#accounts)).

Labels are English source texts; the web app translates them when shown. Mark them with `N_()` so the extraction finds them (e.g. `pybabel extract -k N_ ...`).

### Access
Every view says which area it belongs to with the class attribute `area`:

```python
from flaskspark.core.web import ADMIN, OPEN

class NotesView(FlaskSparkMethodView):
    area = "notes"                            # an area of a manifest
    # area = OPEN                             # everyone who may use the app
    # area = ADMIN                            # admin roles only (the default without `area`)
    # area = {"GET": "notes", "*": ADMIN}     # per HTTP method
```

Navigation entries, tiles and push topics carry an area as well and only show up for visitors who may use it. In code and templates ask with `can(area)` (`flaskspark.core.web.can`, in templates `can`); `user_id()` and `user_name()` name the visitor.

Which access applies is the web app's choice (`auth:` in `config.yaml`); the modules stay the same:

- `none`: `OpenAccess`, no sign-in, everyone may use every area (and the admin pages). Run such an app in a trusted network only.
- `oauth` (also `sso`): `RoleAccess`, sign-in over FlaskSpark's [OAuth login provider](#oauth-oidc-login-provider) (`OAUTH_*`; the provider maps the user's groups to a role, `OAUTH_ROLE_MAP`). Every page needs a sign-in: a page redirects to it (and back afterwards), a background request gets 401. Admin roles (`Role.is_admin`) may use everything and `ADMIN`; `OPEN` is every signed-in user; an area is decided by the **role × area matrix** (table `core_role_area`, edited on «Settings › Access»; a cell nobody set yet follows `Area.defaults`). FlaskSpark's users and roles need its tables in the database (see [Migrations](#migrations)).
- **A user's role by hand** (`RoleAccess`): on «Settings › Users» an admin sets the role of a user over the one the sign-in gives (table `core_user_role`). It applies at once and is put back after every later sign-in (Flask-Login's `user_logged_in`); the sign-in's last role is remembered, so «From the sign-in» returns to it at once. The user's admin flag follows the effective role. An admin can't change their own role. Users appear after their first sign-in.

A page the visitor may not use answers 403 with the page `flaskspark/no_access.html` (a background request gets a plain 403). When the [start page](#start-page) itself is closed to the visitor, they go to the start page of the first area they may use (`Area.start`) instead. Endpoints in `PUBLIC_ENDPOINTS` of a manifest (and the static files, the sign-in flow, the language switch) need no sign-in. With a sign-in the sidebar shows the user and «Sign out».

Other kinds of access are subclasses of the abstract `Access` (`flaskspark.core.web.access`: `can`, `user_id`, `user_name`, `signed_in`, `logout_url`, `check`) registered in `ACCESS`. `roles_with(area)` (`flaskspark.core.web`) names the roles that may use an area (e.g. whom a module may share with).

### Start page
The core's start page (`/`, endpoint `index`: the modules' tiles and their `PAGE_SECTIONS["home"]`) is a fallback: a view of a module or of the app with `url = "/"` replaces it (FlaskSpark registers a view with `fallback = True` only when no other view claims its URL). `config.yaml` `app.start` (a path or an endpoint) makes the core's start page send the visitor there instead. «The start page» for the access is whatever `/` is and what `app.start` names (`flaskspark.core.web.start_endpoints()`, `start_url()`): a visitor who may not use it goes to the start page of the first area they may use. The navigation's «Home» entry follows it: shown while `/` is the core's start page, hidden otherwise; `app.home_entry` (`true`/`false`) overrides that.

### Info screens
An info screen is a page for a display on the wall that nobody operates (a TV, designed for 1920 × 1080): no navigation, no page chrome, no buttons, no context menus, and it keeps itself up to date. A module declares it in its manifest; any module (the same or another) fills it with sections, just like the start page:

```python
from flaskspark.core.module import Area, Module, N_, Screen

class Wall(Module):
    NAME = "wall"
    LABEL = N_("Info screens")
    AREAS = (Area("wall", N_("Info screens"), N_("Pages for an info screen on the wall")),)
    SCREENS = (Screen("office", N_("Office"), "wall", N_("Open tasks and today's dates"), "display"),)

class Notes(Module):  # another module adds a section to it
    PAGE_SECTIONS = {"home": ("notes/home_section.html",), "screen:office": ("notes/home_section.html",)}
```

- `/screen/<key>` shows the sections of `PAGE_SECTIONS["screen:<key>"]` of all loaded modules, in the order of the modules; `/screen` lists the screens the visitor may use. The admins find all of them, with module, area, colour mode and reload time, in «Settings › Screens» ([Settings](#settings)). The screen needs its `area`; each section asks for its own (`{% if can("notes") %}`) like those of the start page. A section may tell a screen from other pages by `screen` (the `Screen`, defined only there), e.g. to leave out its dialogs.
- Layout `layouts/screen.html` (the head of `layouts/main.html`: theme, colour mode, import map, translations; no sidebar, no top bar, no `LAYOUT` templates of the modules): a slim head row with the logo, the screen's title, the live state and a clock, then the page filling the viewport (`.app-screen-sections`; helpers `app-screen-section`, `app-screen-section-head`, `app-screen-section-title`, `app-screen-fill` for the section that takes the height left, `app-screen-aside` for a section in a column on the right, `--app-screen-aside-width` wide and as high as the page, beside the others).
- Sizes follow the viewport: 1rem is 16px × `--app-screen-scale` at 1920 × 1080 and in proportion elsewhere, so a screen looks the same on every display. `?scale=1.5` in the URL overrides the theme's token for one display.
- Colour mode: the app's (the browser's stored choice, else the theme's `default_mode`) unless `Screen.mode` fixes one; `?mode=dark|light|system` in the URL wins. A fixed mode is `<html data-theme-fixed="…">` (webcomponents' `theme.js` then neither reads nor stores the choice).
- `<html data-screen="<key>">` makes the page display-only: `frame.css` hides `ui-button`, `ui-button-group`, `ui-close-button`, `ui-pagination`, `ui-dialog`, `ui-drawer`, toasts, `button`, `.btn`, `.app-page-actions` and `.app-toolbar`; the web components hide their own controls (close and remove buttons, a card's chevron and actions; `--ui-screen: on`, see [Web components](#web-components)); the content takes no pointer events. `flaskspark/screen.js` swallows right clicks (neither the browser's menu nor `ui-context-menu`: `contextMenu()` attaches none and `UiContextMenu.open()` refuses), clicks and the activating keys. `[data-screen-keep]` keeps an element visible and working, `[data-screen-hide]` hides any element (also inside a component's shadow tree).
- Recovery: the push channel reconnects by itself and sections reload their data on `resync` (as everywhere). Should the channel stay down for 5 minutes, the page loads itself anew once the server answers again (the wait doubles after every such reload, up to an hour); every day at `Screen.reload_at` (default `04:00`, `""` never) it reloads too, so new code arrives after a deployment. `onNewDay(callback)` of `flaskspark/screen.js` tells a section that the date changed (e.g. to show what is current today).

### Settings
A module names the settings of `config.yaml` the admins may change in its manifest:

```python
from flaskspark.core.settings import Setting

class Notes(Module):
    ...
    CONFIG = (
        Setting("notes.page_size", N_("Notes per page"), "int", N_("How many notes a page shows"), N_("Display"),
                min=1, max=100),
        Setting("notes.sort", N_("Order"), "choice", choices=(("new", N_("Newest first")), ("old", N_("Oldest first")))),
        Setting("notes.archive", N_("Archive old notes"), "bool", services=("archiver",)),
    )
```

`Setting(path, label, kind="str", help="", group="", min=None, max=None, unit="", choices=(), services=())`: `path` points into `config.yaml` (`section.key`, deeper too), `kind` is `int`, `float`, `bool`, `str` (also `text`), `time` (`"HH:MM"` or `"off"`), `choice`, `ints` or `texts` (a list, comma separated in the form; `min`/`max` bound every number) or `json` (a list or an object, edited as JSON; digit keys become numbers again where the default in `config.yaml` has numbers); texts are English source texts (`N_()`); settings of the same `group` share a box; `services` names the services that read the setting only at their start (the page says they need a restart).

- The default stays in `config.yaml`; a changed value is stored in the table `core_settings` and laid over `config.yaml` by `config.load()` in every process (seen within 5 seconds; `.defaults` is `config.yaml` alone). An emptied field takes the default again.
- Every value is checked (kind, choices, bounds); one value that does not fit stores none.
- Never a setting: secrets (they live in the environment) and the top-level keys `modules`, `theme` and `auth` (refused).
- The page `/settings` (admins; «Settings» in the sidebar's footer) has the tabs «Access» (the role × area matrix) and «Users» (the users' roles) with sign-in, «Accounts» (the application's accounts, when a module names `APP_ACCOUNT_TYPES`), «Dashboards» (when a module declares [info screens](#info-screens)), a tab per module with its own sections (`SETTINGS`) and its settings (`CONFIG`) — a module that declares info screens has them in «Dashboards» instead, below the list —, and «Data»; `/settings#<module>` opens one.
- «Dashboards» lists every info screen of the loaded modules (read only): title and description, the module that declares it, its area, its colour mode (`Screen.mode`, else «as in the app»), its daily reload (`Screen.reload_at`) and its address as a link opening it in a new tab; a screen no module adds a section to yet says so. `/settings#screens` opens it.
- «Data» lists what is left over and no longer needed, if anything (`flaskspark.core.leftovers`):
  - modules no longer delivered (see [Migrations](#migrations)): their tables with their rows, their revision in `alembic_version` and FlaskSpark's record of them, removed together;
  - tables in the database that no model of the core or of a delivered module describes (not `alembic_version`, not FlaskSpark's `user` and `roles`), with their rows; revisions of `alembic_version` of no known module;
  - rows of the core that belong to what is gone: stored settings (`core_settings`) whose path no delivered module defines, the cells of `core_role_area` of an area no delivered module has, personal settings (`core_user_settings`) whose key belongs to a module no longer delivered (the key is the module's name or starts with it and `.`, `:`, `-` or `_`);
  - state directories `STATE_DIR/<module>/` of modules no longer delivered, with their size.

  Each item can be removed on its own, or all at once («Clean up all»), after a confirmation that lists exactly what is deleted. Before deleting, FlaskSpark makes a backup ([Backups](#backups)): the database as `db-<stamp>.db.gz`, state directories whole (also what a `.nobackup` marker keeps out of the regular backups) as `removed-<stamp>.tar.gz` in the backup folder, neither mirrored nor pruned; the answer names it. It cannot be undone except from that backup. Tables are dropped through the database API (`Database.drop_tables`). The guardian's findings of a service that is gone resolve themselves at its next check and are not listed.
- JSON APIs (admins): `GET`/`POST /api/settings/access` (`{role_id, area, allowed}`: one cell of the matrix), `GET`/`POST /api/settings/users` (`{user_id, role_id}`, `role_id: null`: the sign-in's role again), `GET`/`POST /api/settings/config/<module>` (`{values: {path: value}}`, `null` or `""`: the default again; the answer names what changed and the services to restart), `GET /api/settings/data` (`{items: [{id, kind, name, …, deletes}]}`) and `POST /api/settings/data` (`{items: ["module:notes", …]}` or `{items: ["all"]}`: `{removed, backup: {db, state}, message, items}`; an id that names nothing left over removes nothing, 400).
- The command line does the same: `flaskspark data` lists the items with their ids (`module:<name>`, `table:<name>`, `revision:<rev>`, `setting:<path>`, `area:<key>`, `user-setting:<key>`, `state:<name>`), `flaskspark data clean <id…|all> [--yes]` removes them after the backup (it asks first without `--yes`).

### Personal settings
Per user and key a dict (e.g. the columns a list shows):

```python
from flaskspark.core.web import save_user_setting, user_setting

columns = user_setting("notes.columns").get("shown", [])
save_user_setting("notes.columns", {"shown": ["title", "date"]})
```

Scripts use `GET /api/user-settings/<key>` (`{key, value}`) and `PUT /api/user-settings/<key>` (`{value: {...}}`, at most 64 KB). Signed in (`RoleAccess`) they are stored in the table `core_user_settings`, the same on every device; with `OpenAccess` (no user) they live in the browser's session on the server, i.e. per browser and as long as the session.

### Accounts
A user connects an account once – one login (user name and password) at a provider – and switches on what it offers, e.g. mail (IMAP), sending (SMTP), calendars (CalDAV) and contacts (CardDAV) on the same host. The modules use these accounts without asking the user again (`flaskspark.core.accounts`).

- **Types** (`AccountType`): a key, a label, an icon, its fields (`Field(key, label, kind, default, required, choices, help, min, max, placeholder)`, kinds `text`, `int`, `bool`, `choice`, `url`, `host`), `clean()` (the settings checked), `test(account, timeout)` (the connection test: a `Result(text, params)` or `AccountTestError`) and `describe()`. The core ships `imap`, `smtp` (standard library), `caldav`, `carddav` (a `PROPFIND` with httpx) and `gitlab` (the address of the instance, e.g. `https://gitlab.example.com`, an access token and `verify_tls`; the test asks `GET <address>/api/v4/user` with the header `PRIVATE-TOKEN` and answers «Connected as <name>»). A type is offered only when a loaded module names it. A type that signs in with a secret alone sets `USERNAME = False` and `SECRET_LABEL` (e.g. `N_("Access token")`): the form asks for no user name, and the secret is stored like a password (encrypted). A module registers more types in `Module.register()` with `accounts.register_type(...)`.
- **A module names the types it uses** (`ACCOUNT_TYPES`). The page «Profile» (`/profile`, the button with the person in the sidebar's footer; it also shows the modules' `PAGE_SECTIONS["profile"]` and exists with sign-in whenever there is a section or a type to offer) offers only those types, and only to users who may use one of the modules that name them (one of its areas, or it has none). It lists the user's accounts with the modules that use them, connects, edits (in dialogs), tests, switches off and on, shares (with roles, see [Shares](#shares)) and removes them, and lists the accounts others shared with the user's role. A new account is kept only if every chosen type signs in; a type added later that fails is not added; a new password tests every type again.
- **Without sign-in** (`OpenAccess`) there is no user: no personal accounts and no personal language (the accounts' API answers 404). The profile still exists when a module adds a section (`PAGE_SECTIONS["profile"]`): settings of this workstation or browser, e.g. kept by an agent running on it.
- **Accounts of the application.** A user's account belongs to that user (the profile, sharing with roles). An account a service needs for everyone (e.g. one GitLab token that polls GitLab for all users) belongs to the application instead: a module names its type in `APP_ACCOUNT_TYPES`, and «Settings» (admins; without sign-in everyone) gets the tab «Accounts» (`/api/settings/accounts`, the same API and form as the profile, without sharing and without presets with `sso_user`). These accounts have the owner `accounts.APP` (user id 0); they never appear among a user's accounts (`for_user`, `all`), and a module reads them with `app(type)` (every one, oldest first) or `app_account(type, name=None)` (the first active one, or the one with that name). The same type may be in both lists (personal and application accounts).
- **Storage**: the table `core_accounts` (the login; the password encrypted with [Secrets](#secrets) under the name `accounts`, i.e. `APP_SECRET_KEY` or `APP_SECRET_KEY_ACCOUNTS`) and `core_account_types` (one row per account and type: its settings as JSON, `verified`, `error`, `checked`). One JSON column instead of a table per type: types come and go with modules, and a module that needs more per account keeps it in its own table keyed by the account's id.
- **Presets**: `config.yaml` `accounts.providers` (or `accounts.register_provider(Provider(...))`) set per type what a provider fixes; the form asks only for the rest. `sso_user: true` takes the signed-in user's name as the user name. `accounts.timeout` (default 20 s) bounds a connection test.

```yaml
accounts:
  timeout: 20
  providers:
    example:
      label: Example Mail
      imap: {host: imap.example.org, port: 993, security: ssl}
      smtp: {host: smtp.example.org, port: 465, security: ssl}
```

The API for a module, with its rights like the database's (only the types its manifest names, else `AccountAccessError`; the core reaches all):

```python
from flaskspark.core import accounts

mail = accounts.for_module("mail")
for account in mail.for_user(user_id, "imap"):          # AccountAccess: id, name, username, password, settings, …
    connect(account.settings["host"], account.settings["port"], account.username, account.password)
mail.for_user(user_id, "imap", shared=True)             # also the accounts shared with the user's role (permission)
mail.all("imap")                                        # every active user's account with IMAP (a service)
mail.get(account_id, "imap")
mail.test(account_id, "imap")                           # test now, keep the result
mail.record_test(account_id, "imap", ok=False, error="refused")   # a sign-in the module made itself
accounts.listen(lambda change: ...)                     # AccountChange(action, account_id, user_id, types) in this process
accounts.account_types()                                # every known type (formerly accounts.types(), deprecated)

tracker = accounts.for_module("tracker")                # its manifest: APP_ACCOUNT_TYPES = ("gitlab",)
account = tracker.app_account("gitlab")                 # the application's GitLab account (AccountAccess) or None
account = tracker.create_app_account("gitlab", "GitLab", url="https://gitlab.example.com", secret=token)
                                                        # a new one from code (an import, a command); test=True signs in first
```

`create_app_account(type, name, *, secret="", username="", settings=None, test=False, **fields)` checks the fields like the form (`settings` and keyword arguments such as `url=` are the type's fields), stores the secret encrypted, asks the vetoes and tells the listeners «connected»; with `test=True` a failing sign-in removes the account again (`AccountTestError`). `AccountError` when a field does not fit or the name is taken.

`password` is decrypted on access only. The changes are `connected`, `changed`, `removed`, `activated`, `deactivated` and `shared` (its shares changed); each is told to the `listen()` callbacks once it is committed and sent as the event `accounts` to the user's pages (`ev.user.<id>.accounts`, see [Live data](#live-data)), for `shared` also to the users of the roles before and after.

**Refusing a change.** Before a change a module may veto it: `Module.account_change_veto(change)` returns a reason (an English source text, `N_()`; the profile shows it translated) or `None`. The change is then not made (a new account is not kept). E.g. a module whose job still uses an account refuses `removed` and `deactivated`. An application without a manifest of its own registers such a check with `accounts.add_veto(callback)`.

```python
class Mail(Module):
    def account_change_veto(self, change):
        if change.action in ("removed", "deactivated") and jobs_running(change.account_id):
            return N_("A mail import still uses this account.")
        return None
```

JSON API: `GET`/`POST /api/accounts`, `PUT`/`POST /api/accounts/<id>` (`{action: test|activate|deactivate|delete}`). For the application's accounts the same under `/api/settings/accounts` (admins).

**GitLab** (`flaskspark.core.gitlab`): a small client for GitLab's REST API, for the type `gitlab` or any address and token:

```python
from flaskspark.core import accounts
from flaskspark.core.gitlab import GitLab, GitLabError, project_path

account = accounts.for_module("tracker").app_account("gitlab")
if account is not None:
    try:
        with GitLab.from_account(account, timeout=20) as gitlab:       # or GitLab(url, token, verify_tls=True)
            me = gitlab.user()                                          # GET /api/v4/user
            project = gitlab.get(f"/projects/{project_path('group/app')}")
            for issue in gitlab.pages("/issues", {"scope": "all", "state": "opened"}, limit=500):
                ...
    except GitLabError as error:                                        # .status (HTTP or None), .timeout
        ...
```

`pages()` follows `X-Next-Page`, else the `Link` header's `rel="next"` (keyset pagination; a link that names another host, e.g. GitLab's `external_url` behind a proxy, is asked at the configured address instead). The token (`PRIVATE-TOKEN`) goes only to the configured host and port (never from https down to http); a redirect to another host is followed without it. Every request has a timeout; failures are `GitLabError`.

### Shares
One mechanism for every item a module lets its users share (`flaskspark.core.shares`): shared with roles (never single users), per role `read` or `write`; only the owner changes an item's shares, and a user whose role changes takes the access along. A kind that is joined first (`JOINS`) appears for an invited user only after joining (they may decline, leave and join again). When a share ends, who had joined sees a notice once. With `AREA` an item is shared only with roles that may use that area, and only their users get access.

```python
# manifest
SHAREABLES = ("myapp.modules.notes.sharing:NoteShareable",)

# myapp/modules/notes/sharing.py
from flaskspark.core import shares

class NoteShareable(shares.Shareable):
    TYPE, AREA, LABEL = "note", "notes", N_("Note")      # JOINS = True: invited users join first

    def owner_of(self, s, object_id):
        note = s.get(Note, object_id)
        return note.owner_id if note else None

    def name_of(self, s, object_id):
        note = s.get(Note, object_id)
        return note.title if note else "?"
```

```python
shares.access(user_id, "note", 7)            # "owner", "write", "read" or None
shares.can_read(user_id, "note", 7) / shares.can_write(user_id, "note", 7)
shares.shared_with(user_id, "note")          # {note id: permission} of others' notes the user may use
shares.grant("note", 7, role_id, "read", owner_id=user_id) / shares.revoke("note", 7, role_id, owner_id=user_id)
shares.set_targets("note", 7, user_id, {role_id: "write"})   # exactly these roles ({}: the share ends)
shares.invitations(user_id, "note") / shares.join(...) / shares.leave(...) / shares.take_notices(user_id, "note")
shares.audience("note", 7)                   # owner and everyone with access, e.g. whose pages to tell
shares.forget("note", 7)                     # the note is deleted: its shares go
```

A Shareable may also refuse a change of its item's shares (`check_change(s, object_id, owner_id, wanted)`: raise `ShareError`) and hear of it once it is committed (`shares_changed(object_id, owner_id, concerned)`); the accounts use both.

Every function takes `session=` (a session of the module, `db.for_module("notes")`) to be part of the module's transaction; without one it opens one. The Shareable's methods run with the module's rights, the tables `core_shares`, `core_share_members` and `core_share_notices` with the core's. Without sign-in there are no roles: nothing can be shared.

The dialog is a web component for every page: `<ui-share-dialog>` (`flaskspark/ui-share-dialog.js`, with `<ui-share-editor>`); `dialog.open("note", 7, {name, hint})` reads and saves the sharing at `GET`/`POST /api/shares/<type>/<id>` and fires `share-dialog:saved`. More API: `GET /api/shares/<type>` (`{invitations, notices}` of the visitor), `POST /api/shares/<type>/<id>/join` and `/leave`. Who is concerned by a change gets the event `shares`.

### Attachments
Files attached to an item of a module (`flaskspark.core.attachments`): images, videos and documents with a title and a description.

```python
# manifest
ATTACHMENT_OWNERS = ("myapp.modules.notes.files:NoteFiles",)

# myapp/modules/notes/files.py
from flaskspark.core import attachments

class NoteFiles(attachments.AttachmentOwner):
    TYPE, AREA = "note", "notes"
    SHAREABLE = "note"            # read / write as the note's shares say; or override can_read / can_write

# deleting a note: its files go along (rows now, files after the commit)
with db.for_module("notes").session() as s:
    s.delete(note)
    attachments.delete_for("note", note.id, session=s)
```

```html
<ui-attachments owner-type="note" owner-id="12"></ui-attachments>
<script type="module" src="{{ url_for('static', filename='flaskspark/js/ui-attachments.js') }}"></script>
```

- `<ui-attachments>`: a drop zone (`ui-dropzone`, uploads one after the other with progress), images and videos in a gallery with a lightbox (`ui-gallery`, sortable by dragging), documents as a list (open, download), edit title and description, delete; `readonly` shows only. It fires `attachments:changed`.
- **Storage**: below the directory of the owner type's store (`AttachmentOwner.STORE`, default the module's name): `attachments.stores.<store>`, else `<attachments.dir>/<store>`, else `STATE_DIR/attachments/<store>` (part of the [backups](#backups)). Files are named `<yyyy>/<mm>/<uuid><ext>`, or by the owner's `folder()` (`<folder…>/<kind>-<NN><ext>`; `attachments.tidy(type)` moves them after a rename), never by the user's file name. `require_marker: true`: a configured directory must carry the file `.flaskspark-attachments` (e.g. a network mount that is not there: nothing is written or read).
- **Uploads** are streamed to the disk with their size and SHA-256, at most `attachments.max_size_mb` (default 100, 0: no limit; 413 above it).
- **Thumbnails** (WebP) in `attachments.thumbs_dir` (default `STATE_DIR/attachments/.thumbs`, marked `.nobackup`: they are made again from the originals, `attachments.make_thumbs()`): images with Pillow (HEIC with pillow-heif), PDFs their first page (pypdfium2), videos a frame (`ffmpeg` on the `PATH`). All optional (the extra `files`). HEIC and TIFF get a JPEG for the lightbox.
- Files are delivered as downloads unless they are safe to show (images, videos, audio, PDF, plain text); never HTML or SVG inline.
- Python API (`session=` as with shares, also `attachment_of()`, which then sees the module's work not committed yet; `user_id=None` is the module itself, without checks; `cfg=` the configuration of the storage): `store(user_id, type, id, stream, name, mime, cfg=)`, `attachment_of(user_id, attachment_id, write=False)`, `of_owner(type, id)`, `counts(type, ids)`, `first_images(type, ids)`, `update(..., cfg=)`, `reorder(...)`, `delete(user_id, attachment_id, cfg=)` and `delete_for(type, ids, cfg=)` (the files go from the storage of `cfg` after the commit), `tidy(type, cfg=)`.
- JSON API: `GET`/`POST /api/attachments/<type>/<id>` (list; upload as the raw body with `X-File-Name`), `POST /api/attachments/<type>/<id>/order`, `POST /api/attachments/<att>` (`{action: update|delete}`), `GET /attachments/<att>/thumb` and `/file` (`?display=1`, `?download=1`). After a change the item's audience gets the event `attachments`.

```yaml
attachments:
  max_size_mb: 100
  dir: /srv/files                 # optional: a root for every store (<dir>/<store>)
  stores: {notes: /mnt/share/notes}   # optional: a directory per store
  require_marker: false
  thumbs_dir: ~/.cache/myapp/thumbs   # optional
```

### Database
Modules use the database only through `flaskspark.core.db`, never `sqlalchemy` directly:

```python
from flaskspark.core import db
from myapp.modules.notes.models import Note

with db.for_module("notes").session() as s:   # commits at the end, rolls back on an error
    s.add(Note(text="Buy milk"))
    notes = s.scalars(db.select(Note).order_by(db.desc(Note.id))).all()
```

- `db.for_module(name).session()` (alias `.transaction()`): a unit of work with the module's rights.
- `db.Model`: the base class of every table.
- The building blocks are handed through from SQLAlchemy: column types (`Integer`, `String`, `DateTime`, `JSON`, …), `Mapped`, `mapped_column`, `relationship`, `ForeignKey`, `select`, `update`, `delete`, `func`, `and_`, `or_`, … (see `flaskspark/core/db/sql.py`).
- **Rights:** a module's session reaches only its `TABLES` and `SHARED_TABLES` (checked for every statement and every flush); anything else raises `DatabaseAccessError`. Plain SQL (`text`) is refused in a module's session. A module that names no tables reaches none.
- The database systems are subclasses of the abstract `Database`, chosen by the URL; today `SqliteDatabase` (WAL, busy timeout and foreign keys, so the web app and the services can write concurrently). Besides connections and copies for the backup it has the few operations on whole tables the core needs: `db.table_names()`, `db.row_count(table)` and `db.drop_tables([...])` (the clean-up of «Settings › Data»; a table another one still refers to with rows is not dropped).
- `db.load_models()` imports the `MODELS` of every loaded module and returns `Model.metadata`.
- `db.USER` and `db.ROLES`: FlaskSpark's users and roles (the sign-in's tables `user` and `roles`) as targets of foreign keys, in a `MetaData` of their own (they are not part of the modules' metadata and their history is `signin`): `owner_id: Mapped[int | None] = mapped_column(Integer, ForeignKey(db.USER.c.id, ondelete="SET NULL"))`, without importing FlaskSpark. Reading them needs the table in `SHARED_TABLES`.

#### Migrations
Every module keeps its own migration history (Alembic, no Flask-Migrate): its revisions live in `<package>/migrations/versions/`, as a branch of its own in the database's history (`branch_labels = ("<module name>",)`; its first revision has `down_revision = None`). The histories are independent; a revision that needs another module's table names that module's revision in `depends_on` (Alembic then applies that revision first, also on a new database). Alembic keeps only the dependent revision in `alembic_version` then (the one it depends on is «contained» in it); FlaskSpark derives from the rows and everything they depend on where every history stands, so the other history is neither pending nor «without a revision» (`db adopt` is not needed). The core has its own history `core` (`core_settings`, `core_role_area`, `core_user_settings`, `core_user_role`, `core_module_chains`, the [accounts](#accounts), [shares](#shares) and [attachments](#attachments)) and, with sign-in (`auth: oauth`), `signin` (FlaskSpark's `roles` and `user`). All of them share Alembic's table `alembic_version` (one row per history).

FlaskSpark runs them: the web service and `flaskspark run` (the supervisor) bring every loaded module's history and the core's to their heads at their start, with a backup of the database first ([Backups](#backups), `db-<stamp>.db.gz`) when there is something to do. The web app refuses to start on a schema that is not at the heads (skip with `APP_SKIP_MIGRATION_CHECK`).

```bash
flaskspark db upgrade                                     # what the start does: every history to its head
flaskspark db current                                     # where every history stands
flaskspark db check                                       # differences between the models and the database (exit 1)
flaskspark db revision -m "notes: add a column" --module notes          # autogenerated against notes' tables only
flaskspark db revision -m "notes: data fix" --module notes --empty      # an empty one to fill in by hand
```

`revision` compares only the module's own tables (its `TABLES` and the tables of its `MODELS`) with the database, writes into the module's `migrations/versions/` (created for the first revision, which starts the module's branch) and writes nothing when there is no change. The database must be at the heads first (`db upgrade`). Review every generated script.

**Adopting a database of an earlier history.** A database whose tables come from one single history (e.g. the classic layout's Flask-Migrate in `web/migrations`) holds a revision no module knows and tables without a revision of their module's history; the start refuses such tables (`run db adopt`). Take it over once:

1. Bring it to the last revision of the old history (with the old version of the application).
2. Give every module (and the core) a first revision that describes its tables exactly as the old history left them.
3. `flaskspark db adopt`: drops the revisions no history knows from `alembic_version` (but those of recorded modules that are no longer delivered), stamps every history whose tables **all** exist at its first revision, and leaves the histories without any table to the upgrade (they are created). A history with only some of its tables stops it, and nothing is changed. A backup is made first.
4. `flaskspark db upgrade` (or just start): applies what came after the first revisions and creates the new histories. `flaskspark db check` shows remaining differences (none, if the first revisions match).

The sign-in's first revision describes today's `user` and `roles`; older tables of an earlier history that lack the columns added later (the user's `role_id`, `first_name`, `last_name`, `admin`, the role's `is_admin`, `rank`) are still stamped there, and the next revision of `signin` adds whichever is missing (on tables it created itself it does nothing).

A module that is installed but not loaded (a missing dependency, or left out by `config.yaml` `modules:`) keeps its revisions known; it is only not upgraded.

**A module that is no longer delivered.** An application delivers its modules; there is no installing or uninstalling. A new version of the application may no longer deliver a module that existed before (removed or renamed). Its revision then stays in `alembic_version`, which no history knows any more. That is no error:

- The start warns (`module 'notes' is no longer delivered: its revision … stays in alembic_version and its tables are kept (…)`), the status tile «Modules» shows «no longer delivered: notes — its tables are kept», and the start goes on: the histories of the delivered modules and the core are migrated as usual. Alembic only ever sees the revisions it knows; the other rows of `alembic_version` stay untouched.
- Its tables and data are never touched automatically.
- When the module comes back (a later version delivers it again), its history goes on from where it stood.
- To name the module and its tables later, FlaskSpark keeps a record of every delivered module in the core's table `core_module_chains` (name, history's revision, tables, label, version of the distribution that delivered it, when it was last seen), updated at every start and `db upgrade`.
- A revision that belongs to no module ever recorded (e.g. a database of another application, or one older than the record) is treated the same way, with a warning of its own («belongs to no module this application delivers or delivered»); the tile lists it as «revisions of no known module».
- What such a module left behind is cleaned up on purpose, on «Settings › Data» or with `flaskspark data` (see [Settings](#settings)). Cleaning up a module drops its tables and removes its rows of `alembic_version` and its record: a module that comes back afterwards starts its history from the beginning (its tables are created anew).

`db adopt` is only for the one-time adoption of a database from an earlier single history (it keeps the revisions of recorded modules that are no longer delivered).

The classic layout (`web/migrations` present) keeps its Flask-Migrate history: `flask db migrate` / `flask db upgrade` in `web/`, with `flaskspark.core.db.migrations.metadata()` in its `env.py`; FlaskSpark runs nothing there itself.

### Themes
A theme is a directory with a `theme.yaml`; the app ships it as a package directory with an entry point (`flaskspark.themes`: `mybrand = "myapp.theme"`), the classic layout as `themes/<name>/` in the project:

```text
src/myapp/theme/
  theme.yaml
  theme.css
  images/
    logo.svg
    logo-dark.svg
    favicon.svg
```

```yaml
# theme.yaml
title: My Brand
short_name: Brand
logo: logo.svg            # inside images/
logo_dark: logo-dark.svg
favicon: favicon.svg
theme_color: "#ffffff"
theme_color_dark: "#000000"
default_mode: system      # light | dark | system
footer: "© My Brand"
apple_touch_icon: apple-touch-icon.png   # optional, inside images/
manifest:                 # optional: the web app manifest's fields (or a file inside images/: manifest: site.webmanifest)
  icons:
    - {src: icon-192.png, sizes: 192x192, type: image/png}
    - {src: icon-512.png, sizes: 512x512, type: image/png}
```

The layout links the touch icon and the manifest. With the manifest's fields it is served as
`/theme/manifest.webmanifest`: `name`, `short_name`, `start_url` (`/`), `scope`, `display` (`standalone`) and the colours
come from the theme unless given; icons name files inside `images/`. `manifest: true` serves the defaults alone (with
the touch icon as its icon).

```css
/* theme.css: plain CSS, light-dark() for both colour modes */
:root {
  --app-accent: #0f766e;
  --app-accent-fg: light-dark(#0f766e, #5eead4);
  --app-page-bg: light-dark(#f8fafc, #0b1220);
}
```

The layout lives in FlaskSpark only (`flaskspark/core/web/static/flaskspark/css/frame.css`: plain modern CSS with nesting, custom properties, `color-mix()`, `light-dark()` and logical properties, no preprocessor). A theme sets tokens, not layout rules: whatever a brand may want different is one of these tokens (defaults in `frame.css`, mapped to Bootstrap's tokens). Should a theme need more, the way is a new token in FlaskSpark rather than a rule in the theme.

| Token | Default | Description |
| --- | --- | --- |
| `--app-accent`, `--app-accent-hover`, `--app-accent-contrast` | `#0d6efd`, 15 % darker, white | The brand colour, its hover, text on it. |
| `--app-accent-fg` | the accent (lighter in dark mode) | The brand colour as text (readable in both modes). |
| `--app-accent-tint` | 12 % of the accent | A light wash of the brand colour (active entries, chosen language). |
| `--app-glow` | `transparent` | The glow behind the page (`transparent`: none). |
| `--app-glow-opacity`, `--app-glow-blur` | `0.7`, `6px` | How strong and how soft the glow is. |
| `--app-page-bg` | light grey / near black | The page background (colour or gradient). |
| `--app-surface`, `--app-surface-alt`, `--app-border` | white / dark grey, … | Cards and fields. |
| `--app-chrome-bg`, `--app-chrome-border`, `--app-chrome-blur` | translucent, `18px` | The top bar's background, the line of top bar and sidebar, the blur behind both. |
| `--app-sidebar-bg` | the surface, 90 % (a little lighter in the dark) | The docked sidebar's background (milky, blurred). |
| `--app-sidebar-width` | `18rem` | The docked sidebar's width. |
| `--app-sidebar-inset` | `1rem` | The docked sidebar floats this far from the window's edges; `0` attaches it as a column (a line at its end, no corners, no shadow). |
| `--app-sidebar-radius` | `--bs-radius-7` | The floating sidebar's corners. |
| `--app-sidebar-shadow` | a soft shadow (stronger in dark mode) | The floating sidebar's shadow. |
| `--app-radius`, `--app-radius-sm` | `12px`, `8px` | Corners of cards and fields. |
| `--app-shadow` | a soft shadow (stronger in dark mode) | The shadow of cards and tiles. |
| `--app-card-radius`, `--app-card-shadow`, `--app-card-border` | `--app-radius`, `--app-shadow`, `--app-border` | Cards, tabbed cards and the start page's tiles. |
| `--app-nav-radius`, `--app-nav-font-weight` | `10px`, `600` | The navigation's entries (and the services' rows in the sidebar). |
| `--app-nav-hover-bg` | a faint grey | An entry under the pointer. |
| `--app-nav-group-color` | `--bs-fg-3` | The titles of the navigation's groups. |
| `--app-nav-active-bg`, `--app-nav-active-fg` | `--app-accent-tint`, `--app-accent-fg` | The current entry's background and text. |
| `--app-nav-active-border`, `--app-nav-active-border-width` | `--app-accent`, `3px` | The bar at the current entry's start (`transparent` or `0`: none). |
| `--app-btn-radius`, `--app-btn-font-weight` | `10px`, `600` | Buttons (and menus). |
| `--app-brand-max-height` | `8rem` | The logo in the docked sidebar takes the column's width, up to this height. |
| `--app-brand-compact-height` | `36px` | The logo in the top bar and the drawer's heading. |
| `--app-card-icon-color` | `--app-accent-fg` | The icon in a card's heading (`ui-card icon`, `.app-card-head`, `.app-section-title`). |
| `--app-field-bg` | `--bs-bg-body` | The background of fields (`ui-input`, `ui-select`, `ui-textarea`). |
| `--app-tooltip-max-width`, `--app-tooltip-text-align` | `200px`, `center` | Tooltips (long hints: wider, `start`). |
| `--app-table-cell-padding-y` | unset (Bootstrap's) | The rows of `.app-table`. |
| `--app-table-last-row-border-width` | `0` | The line under the last row of `.app-table` and `ui-table`. |
| `--app-font` | Bootstrap's | The page font (optional). |
| `--app-screen-scale` | `1.25` | [Info screens](#info-screens): the size (1rem = 16px × the scale at 1920 × 1080, in proportion on other displays). |
| `--app-screen-padding`, `--app-screen-gap` | `1.25rem`, `1rem` | Info screens: the margin around the page, the gap between sections. |
| `--app-screen-logo-height` | `2.25rem` | Info screens: the logo in the head row. |
| `--app-screen-aside-width` | `28%` | Info screens: the width of the column on the right (a section with `.app-screen-aside`). |
| `--app-screen-section-title-size` | `1.05rem` | Info screens: the titles of the sections (`.app-screen-section-title`). |
| `--app-screen-text-value`, `--app-screen-text`, `--app-screen-text-small` | `1.45rem`, `0.85rem`, `0.72rem` | Info screens: the few text sizes for everything else (key figures, texts, secondary texts); a screen that keeps to them stays calm. |

A page background per colour mode that `light-dark()` cannot hold (a gradient) is the same token set per mode:
`html.theme-dark { --app-page-bg: linear-gradient(…); }` (likewise `html.theme-light`).

FlaskSpark ships a neutral theme `default`; a theme of the app with the same name wins. The theme's files are served under `/theme/`.

### Layout and pages
Pages extend `layouts/main.html` (sidebar navigation from the manifests, the theme's branding, flash messages as toasts; in the sidebar's footer the status of the services and «Settings» for admins, colour mode, language and, with a sign-in, the user with «Sign out»). Its blocks:

| Block | Description |
| --- | --- |
| `page_title` | The page's title (the app's title is appended). |
| `content` | The page. |
| `page_header` | Above `content`. |
| `page_styles` | Extra stylesheets in `<head>`. |
| `page_scripts` | The page's scripts (after the core's script). |
| `sidebar_footer` | Extra content in the sidebar's footer. |

On every page of the layout, emoticons typed into a text field (inputs, textareas, the editable area of
`ui-markdown-editor` and `ui-richtext`) become emoji: `:-)` → 🙂, `;)` → 😉, `<3` → ❤️ and more
(`webcomponents/core/emoticons.js`). Only at the start or after a space; those that could go on as a word (`:D`, `:P`,
`:/`) turn when a space or punctuation follows. Ctrl+Z brings the emoticon back; password, e-mail, URL, phone and
number fields, code, and anything inside `data-emoticons="off"` keep what was typed.

Helper classes for pages (from `frame.css`):
- `app-page-head` (with `app-page-actions`): the page's heading with its buttons
- `app-stack`: a vertical stack with gaps
- `app-grid-2`, `app-grid-3`: responsive columns (container queries)
- `app-toolbar` (with `app-grow`): a row of controls
- `app-kpis` / `app-kpi`: key figures as small tiles in the page (`<ui-kpi-group>` / `<ui-kpi>` do the same with a
  line below, a trend and sizes, also inside shadow trees)
- `app-log`: a log or console output (see `activityLog` below)
- `app-card-head`, `app-table`, `app-muted`, `app-mono`, `app-nowrap`, `app-cell-wide` (a table cell with a control that needs room)
- `app-total-row`: a total row of an `app-table` (in `<tfoot>`; in `ui-table`: `table-total`)
- `app-section` with `app-section-head`, `app-section-title`, `app-section-foot` (and `app-sections` around several):
  titled sections inside a card
- `ui-accordion class="app-card-accordion"`: an accordion whose items look like cards
- `app-fold-toggle` with `app-fold-chevron`: a button that folds something away (title at the start, a chevron at the
  end that turns while `aria-expanded="true"`); a whole card folds with `<ui-card heading="…" collapsible>`

Cards with a heading row: `<ui-card heading="Revenue" icon="graph-up">` puts an icon (Bootstrap Icons by name; the
layout names their sprite) and the title into the header, the slot `actions` at its end; `collapsible` (+
`collapsed`) folds the card from its header.

The navigation starts with «Home» while «/» is the core's start page; `config.yaml` `app.home_entry: false` hides it
(`true` shows it always). When a module or the app answers «/» itself or `app.start` leads elsewhere, it is hidden by
default.

Templates can include icons as inline SVG: `{% from "flaskspark/icons.html" import icon %}{{ icon("trash", _("Delete")) }}`.

### Browser JavaScript
The page's import map names four prefixes: `webcomponents/` (the web components), `flaskspark/` (the core's scripts), `modules/` (the public JS of the modules, `web/static/public/<name>/`) and `app/` (the app's own JS: `static/app/` of the app's package, e.g. `import { card } from "app/ui/card.js"`).

```html
{% block page_scripts %}
<script type="module">
  import { request, notice, activityLog } from "flaskspark/ui.js";
  import { t, preload } from "flaskspark/i18n.js";
  import { icon } from "flaskspark/icons.js";
  import { pushChannel } from "flaskspark/push-channel.js";

  await preload(["Saved"]);
  const data = await request("/api/notes", "POST", { text: "Buy milk" });  // JSON in and out; throws with the server's "error"
  notice(t("Saved"));                                                   // a toast

  const channel = pushChannel();
  channel.subscribe("notes.changed", (data, topic) => reload());
  channel.addEventListener("resync", () => reload());                  // after a reconnect
</script>
{% endblock %}
```

- `ui.js`: `request(url, method, body)`, `notice(message, variant, box)`, `activityLog(target)` (lines with time and level in an `app-log` element)
- `i18n.js`: `t(text, params)`, `nt(singular, plural, n, params)`, `preload(texts)` and `preloadCatalog(...parts)`; the page's module's catalogue comes with the page, others via `/api/i18n/catalog` ([Translations](#translations))
- `icons.js`: `icon(name, label)` and `iconElement(name, label)` (Bootstrap Icons as inline SVG, also inside shadow trees)
- `push-channel.js`: `pushChannel()`, the live channel (one event stream per tab, shared subscriptions, reconnects)
- `forms.js`: forms on the web components' fields sent as JSON: `validateForm(root)`, `formJson(form)`, `submitForm(form, options)` (checked, sent, the answer's message as a notice, the page's content refreshed), `refreshPage(selector)` (morph, no reload); `<form data-fetch>` does all of it on submit
- `hidden-json-feed.js`: `<hidden-json-feed src="/api/..." push-topics="..." interval="60">` loads JSON once for any number of subscribers (`subscribe(callback)`), reloads on a pushed topic or by polling
- `hidden-push-fragment.js`: `<hidden-push-fragment push-topics="..." target="#list">` keeps a part of a server-rendered page current: on a pushed topic it loads the page again and morphs only `target`
- `context-menu.js`: `contextMenu(root, {selector, items})` (right click, long press, menu key; none on an info screen), `quietRightClick()`
- `screen.js`: the script of an [info screen](#info-screens) (display only, clock, live state, recovery); `onNewDay(callback)`
- `ui-service-status.js`: `<ui-service-status>`, the status tiles in the sidebar (included by the layout for admins)
- `ui-share-dialog.js`: `<ui-share-dialog>` and `<ui-share-editor>`, sharing an item with roles ([Shares](#shares))
- `attachments.js` and `ui-attachments.js`: the attachments' API and `<ui-attachments>` ([Attachments](#attachments))
- `ui-user-accounts.js`: `<ui-user-accounts>`, the profile's accounts ([Accounts](#accounts))

### Translations
Every part brings its own catalogue, loaded automatically in this order (a later one overrides an earlier one for the texts it translates too):

1. the core's (`flaskspark/core/locales`, English and German: layout, settings, access, status; `scripts/core-i18n` in the FlaskSpark repository updates it),
2. every loaded module's `<package>/locales/` (in the modules' order),
3. the app's own `<app package>/locales/` (the classic layout: `web/<app>/locales`).

So a module's catalogue only needs the module's texts, and the app's catalogue only what it wants to say differently. Source texts are English everywhere; placeholders are `%(name)s` in Python and Jinja, `{name}` in scripts.

**The visitor's language** (the first that applies): the signed-in user's choice in the profile (the personal setting `core.language` in `core_user_settings`, the same on every device), the cookie `lang` (the sidebar's language buttons), the browser's `Accept-Language`, the first of `app.locales`. A signed-in user who picks a language in the sidebar or in the profile («Profile» → «Language») changes the profile's choice; «browser default» removes it. Without sign-in only the cookie, the browser and the default count. (FlaskSpark apps in general: `FlaskSpark.locale_preferences`, callables asked before the cookie.)

**Python** (`flaskspark.core.i18n`): one helper for code that runs in requests and in services alike.

```python
from flaskspark.core.i18n import N_, current_language, ntr, tr, using

LABEL = N_("Notes")                           # marks only (manifests, constants); translated where it is shown
tr("Saved")                                   # in a request the visitor's language, else the application's
tr("Said: %(text)s", text="hi")               # the text is positional-only: a placeholder may be called text
ntr("%(num)s file", "%(num)s files", n)       # the plural for n (%(num)s is n)
current_language()                            # "de": the language tr() uses right now
with using("de"):                             # a block in a chosen language (e.g. a notification for one user)
    body = tr("Your export is ready")
```

Which language `tr()` takes: `using()`, else inside a request the visitor's, else the application's (config.yaml `notifications.language`, else the first of `app.locales`). The catalogues are loaded once per process and language and loaded again when a `.mo` file changes (its mtime, looked at once a second), so `tr()` costs microseconds. The older `gettext(text, locale=None, cfg=None, **params)` (always the application's language unless `locale` is given) and `language(cfg)` (the application's language) remain. Views and templates may keep using Flask-Babel's `_()`/`gettext`/`ngettext`.

**Templates**: `{{ _("Notes") }}`, `{{ _("%(n)s notes", n=count) }}`, `{{ ngettext("%(num)s note", "%(num)s notes", count) }}`.

**Scripts** (`flaskspark/i18n.js`): the layout puts the catalogue of the page's module (the module whose view answers; the app's own views: `app`) into the page, so `t()` and `nt()` work at once, without waiting for the server:

```js
import { t, nt, preload, preloadCatalog } from "flaskspark/i18n.js";

t("Saved");                                         // a text of the page's module
t("{n} of {total}", { n: 3, total: 7 });
nt("{n} file", "{n} files", count);                 // the language's plural rule; {n} and {num} are count
await preloadCatalog("calendar", "core");           // every text of other parts (module names, "core", "app")
await preload(["Saved", ["{n} day", "{n} days"]]);  // single texts and plurals, asked once each
```

A page names other parts for the layout with `{% set i18n_modules = ["calendar", "core"] %}` (top level of the page's template). The server side: `GET /api/i18n/catalog?modules=…` and `POST /api/i18n/catalog` (`{keys, plurals, modules}`) answer `{language, nplurals, plural, texts, plurals}`; `POST /api/i18n` (`{"keys": [...]}` → `{key: translation}`) stays.

**Extracting.** pybabel needs a mapping file (`babel.cfg`, paths relative to the directory extracted). Babel's own JavaScript extractor loses calls inside template literals (`` `<b title="${t("Save")}">` ``, nested `${…}`), so scripts go through FlaskSpark's (`flaskspark.core.i18n_extract:extract_js`, also the entry point `flaskspark_js`): every call of a keyword anywhere, a string, a template literal without `${}` or strings joined with `+` as its argument, each string of `t(cond ? "Yes" : "No")` and `t(label || "Untitled")`, and `nt()`'s singular and plural.

```ini
[extractors]
flaskspark_js = flaskspark.core.i18n_extract:extract_js

[python: **.py]

[jinja2: **/templates/**.html]

[flaskspark_js: **/static/**.js]
```

Then per module (keywords: `_`, `gettext`, `ngettext` (a default), `tr`, `ntr:1,2` and `N_` for Python, `t` and `nt:1,2` for scripts):

```bash
K="-k _ -k gettext -k lazy_gettext -k N_ -k tr -k ntr:1,2 -k t -k nt:1,2"
pybabel extract -F babel.cfg $K -o notes.pot src/myapp/modules/notes
pybabel init -i notes.pot -d src/myapp/modules/notes/locales -l de      # once per language
pybabel update -i notes.pot -d src/myapp/modules/notes/locales
pybabel compile -d src/myapp/modules/notes/locales
```

Ship the compiled `.mo` files with the package. A source text with a `%` that is no placeholder (e.g. `"{pct} % of {size}"`) is taken for a Python format and fails `pybabel compile`'s check: put the number with its unit into the placeholder instead (`"{percent} of {size}"`).

**Services over NATS.** `events.request()` sends the current language as the header `Accept-Language` (the visitor's in a request; `headers=` adds more or names another). A service answers in it:

```python
from flaskspark.core import i18n

class Sync(AsyncService):
    async def start(self):
        await self.nc.subscribe("sync.rpc", cb=self.on_request)   # self.nc: the connection create() got

    @i18n.with_request_language                     # tr() inside: the requester's language
    async def on_request(self, msg):
        await msg.respond(bus.dumps({"message": i18n.tr("Sync started")}))
```

`i18n.language_of(msg)` reads the header (also `lang`; only languages of `app.locales`, else None), `with i18n.using(language_of(msg)):` does the same for a block, and `i18n.request_headers()` builds the headers for a client of its own.

### Live data
Code on the server publishes over NATS; the push service delivers to the browser tabs that subscribed and may see the topic:

```python
from flaskspark.core import events

events.emit("notes")                    # -> ev.all.notes (every visitor)
events.emit("notes", user_id=3, id=7)   # -> ev.user.3.notes (one user)
events.publish("notes.changed", {"id": 7})   # a topic of the module (manifest PUSH_TOPICS)
answer = events.request("notes.rpc", {"id": 7})   # a request to a service and its answer (header Accept-Language)
```

`emit()` and `publish()` never block or raise; without a NATS connection they do nothing. The web process connects in `start_modules()` (`flaskspark.core.web.app`). Tabs may subscribe to `ev.all.>`, their own `ev.user.<id>.>` and the `PUSH_TOPICS` of the areas they may use.

**Topics served on demand.** Some data is only produced while someone looks at it (e.g. a feed a service of the module leases from an outside system). The module then serves those topics itself with a `TopicSource` (`flaskspark.core.services.push.sources`), returned by `Module.push_sources(nc)` on the push service's NATS connection; the rights still come from `PUSH_TOPICS`:

```python
from flaskspark.core.services.push.sources import TopicSource

class FeedSource(TopicSource):
    def __init__(self, nc):
        self.nc = nc

    def handles(self, topic):              # its topics
        return topic.startswith("feed.")

    def valid(self, topic):                # one it handles but can't serve is refused
        return topic.count(".") == 1

    async def subscribe(self, topic, on_update, on_last):
        await on_last(await self.cached(topic))   # the latest update at once (optional)
        return await self.lease(topic, on_update)  # a handle

    async def unsubscribe(self, handle):   # no tab wants it any more (after the linger time)
        await handle.end()

    def max_age(self, topic):              # its latest update goes to a later tab while younger (None: always)
        return 60.0
```

The push service starts such a topic once, however many tabs want it, ends it 30 seconds after the last tab left (a reloaded page finds it running) and calls `close()` when it stops.

## Running modular apps
The processes of a modular app, the command line and what keeps an installation running.

### Services and the command line
Each service is a process of its own:
- **web**: the built-in web app (`flaskspark.core.web.wsgi:app`, the classic layout's `web/wsgi.py`) under gunicorn (`WEB_PORT`), after the migrations
- **push**: the browser's live channel as Server-Sent Events (`GET /events`, `POST /events/sub`), fed from NATS (`PUSH_PORT`)
- **router**: one port in front of all services (`APP_PORT`); it sends the paths of `Module.ROUTES` to their service (the core routes `/events` to push) and everything else to the web app, WebSockets included. A service of the core like web and push (`ServiceInfo("router", …)`, unit `flaskspark-router.service`): it proxies from its start, with or without NATS; once NATS is reachable (user `router`, optional) it sends heartbeats with its routes, the connections it holds open (requests in flight, WebSockets) and its requests and upstream failures of the last minute. Its status tile shows them (a warning while services it routes to are away), and the guardian watches it like every service. The supervisor starts it last.
- **notifications** and **guardian**: optional, switched on in `config.yaml` (see [Notifications](#notifications), [Guardian](#guardian))
- the services of the modules (`SERVICES`); `flaskspark.core.service.AsyncService` is the base for one on asyncio with its own NATS connection, heartbeats and systemd notifications; `LoopService` the base for a synchronous loop (see below)

**Names.** Outside the code every service is called `flaskspark-<service>`, whatever application runs it (FlaskSpark runs the services, the application only brings modules): `flaskspark-web`, `flaskspark-push`, `flaskspark-router`, `flaskspark-notifications`, `flaskspark-guardian`, and a module's service `releases` is `flaskspark-releases`. That name is used by the supervisor's children and its log lines, the NATS connection names (`flaskspark-<service>`; the short probes of the status `flaskspark-<user>-health` / `-directory`), gunicorn's process name of the web service, the status tiles, the guardian's findings, the command line and the default systemd unit `flaskspark-<service>.service` (`ServiceInfo.unit` when a module names another). `flaskspark.core.service.process_name(name)` and `unit_name(name)` build them. Inside the code the short name stays (`ServiceInfo.name`, `myapp service push`, also `myapp service flaskspark-push`), and so do everything on NATS: the heartbeat subject `ms.<service>.heartbeat`, the keys `<service>.<instance>` of the service directory, the NATS users (`web`, `push`, `router`, `notify`, `guardian`, a module's own) and their permissions, so a running installation keeps its NATS configuration; the guardian's findings keep their keys (`service:<service>`).

A **synchronous service** runs `step()` every `INTERVAL` seconds (`flaskspark.core.service.LoopService`): `setup()` once before systemd `READY=1`, a failing step is logged and the loop goes on, `wait()` fills the time up to the next step (override it to watch something in between), SIGTERM/SIGINT end it after the current step. With `NATS_USER` it connects the process first (`events.init`); its heartbeats go from a thread of their own (`directory.Beacon`, name `HEARTBEAT` or `NAME`) with `details()` and its last step (`step`, `step_seconds`), so a long step shows as an old step and not as a process gone. After every step it sends `WATCHDOG=1`.

```python
from flaskspark.core.service import LoopService

class Sync(LoopService):
    NAME, NATS_USER, INTERVAL = "sync", "sync", 60

    def setup(self):
        self.client = connect_upstream()

    def step(self, started):
        self.count = self.client.sync()

    def details(self):
        return {"synced": self.count}

main = Sync.main   # ServiceInfo("sync", N_("Sync"), "myapp.modules.shop.sync:main")
```

A **run once** (from a timer or cron) is a `Task` (`flaskspark.core.task`): `run(cfg)` returns what it did, `main()` prints it as JSON and exits with 0, or logs the failure and exits with 1. `service.write_heartbeat(state_dir, name, started)` keeps a service's own note of its last round in a file (`heartbeat-<name>.json`), e.g. for readers on the same host while NATS is away.

With `flaskspark` (or the app's alias, e.g. `myapp = "flaskspark.core.cli:main"` in `pyproject.toml`):

```bash
myapp run             # migrations, then everything in one process tree: nats-server (embedded mode), the services, the router
myapp service push    # one service (e.g. in its own container)
myapp router          # the router alone (the same as `myapp service router`)
myapp services        # the services of this installation: name, process name, systemd unit, label, entry
myapp routes          # the router's routes
myapp modules         # the loaded modules (and the installed ones that are not, with the reason) and the theme
myapp db upgrade      # migrations: also current, check, revision -m <msg> --module <name>, adopt
myapp data            # what modules no longer delivered left behind; data clean <id…|all> [--yes] removes it (backup first)
myapp status          # the status tiles (exit 1 with an error)
myapp units           # the systemd units of the services (ServiceInfo.unit, default flaskspark-<service>.service)
myapp guard-check     # the guardian's checks once, nothing sent (exit 1 with a finding)
myapp backup          # one backup run; also backup-list, backup-check <file>, backup-restore <file>
myapp notes import    # a module's command (Module.CLI), the same as `flask --app flaskspark.core.web.app:create_app notes import`
```

The modules' commands (`Module.CLI`) run in the web app's context (`current_app`, the database), like under `flask`; `myapp --help` lists them, `myapp <command> --help` shows theirs. A built-in command wins over a module's of the same name.

`myapp run` (the supervisor) restarts a process that ends, with a growing pause after quick failures, and stops all of them on SIGTERM/SIGINT.

### Service directory and status tiles
Every instance of every service sends a heartbeat every 10 seconds (`flaskspark.core.directory`): on `ms.<service>.heartbeat` and into the NATS key-value bucket `services` (key `<service>.<instance>`, TTL 60 s; a clean stop removes it at once). It names the service, the instance, host (`APP_HOST`), PID, version (`APP_VERSION`), role (leader or standby), memory, start time and the service's own `details()` (`{"ok": False}` says it cannot work). `AsyncService` does this by itself; the web process uses a `Beacon` (started in `start_modules()`). Without NATS or JetStream nothing blocks or raises.

The status tiles (`flaskspark.core.status`) read the directory once and show every service: the core's tiles (web, router, NATS, modules: the loaded ones, those not loaded and the state of the migrations; notifications, guardian, backup), the tiles of the modules (`Module.status_tiles()`, subclasses of `StatusTile` with `KEY`, `NAME`, `SERVICE` and `fill(t, ctx)`) and a plain tile for every service no tile claims. Admins see them in the sidebar (`<ui-service-status>`, reloaded when the guardian publishes `ev.all.services`), as JSON at `GET /api/status/services`, and on the command line with `myapp status`. The NATS tile reads the servers' monitoring endpoints when `NATS_MONITOR` is set. Each tile names its service as `flaskspark-<service>` (`process` in the JSON; `service` keeps the short name). While the directory can't be read (NATS away, no JetStream), a service shows what systemd on this host knows of its unit (`ServiceInfo.unit`, default `flaskspark-<service>.service`; `systemctl show`); a unit systemd does not know (e.g. everything runs under one supervisor) leaves the tile «unknown».

Helpers for a module's tile (`flaskspark.core.status`): `ctx.ask(request)` asks the service for its status (`request(user)`, e.g. `lambda user: health.request(user, "shop.health")`; `NO_NATS` without NATS, `{ok: False, error}` when nobody answers) and `ctx.not_answering(t, result)` marks the tile; `problem(t, label, error)` adds an error row, `failing(t, items)` one row per failing item (`[{label, owner, error}]`) or a count, `worse(t, level)` raises the level; `age()`, `thousands()`, `next_run()` and `read_json()` format and read.

### systemd
Under a unit with `Type=notify`, a service (`AsyncService`) and the supervisor send `READY=1` once they work, `WATCHDOG=1` while they live (with `WatchdogSec=`; a service only while NATS is connected) and `STOPPING=1` on a stop (`flaskspark.core.systemd`, no library needed). The supervisor keeps `NOTIFY_SOCKET` and the watchdog variables from its children: it alone talks to systemd for the whole process tree. Outside systemd nothing happens.

One unit per service, named `flaskspark-<service>.service` (the status tiles look for that name; a module that runs its service under another unit sets `ServiceInfo.unit`), e.g. for the push service:

```ini
# /etc/systemd/system/flaskspark-push.service
[Unit]
Description=flaskspark-push
After=network-online.target

[Service]
Type=notify
WatchdogSec=60
User=myapp
Environment=APP_CONFIG_DIR=/etc/myapp
ExecStart=/opt/myapp/.venv/bin/flaskspark service push
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

The same for `flaskspark-web`, `flaskspark-router` (`flaskspark service router`; it reports `READY=1` once it listens and `WATCHDOG=1` while its loop runs, NATS or not) and every other service (`myapp units` lists them). Everything in one unit instead: `ExecStart=… flaskspark run` (the supervisor), e.g. `flaskspark.service`; the services' own units then do not exist and their tiles fall back to «unknown» without NATS.

### Leadership
A service with several instances whose work must not run twice takes the lead over a NATS key-value bucket (`flaskspark.core.leader`):

```python
from flaskspark.core.leader import Leadership

leadership = Leadership(nc, "notes_leader", self.directory_instance(), on_lead=start_work, on_resign=stop_work)
task = asyncio.create_task(leadership.run(stopped))
...
await leadership.release()   # on a clean stop: the next instance takes over at once
```

The key lives 15 seconds and is renewed every 5; an instance that dies or loses NATS gives the lead up after at most the TTL. Report the role in the heartbeat with `{"leader": leadership.leader}` in `details()`.

### Job queue
A durable work queue on NATS JetStream for work that is not critical in time (`flaskspark.core.queue`, async; `flaskspark.core.jobs` for synchronous code such as the web app):

```python
from flaskspark.core import jobs, queue

jobs.submit("report", {"id": 7}, priority=queue.HIGH, valid_for=86400, key="report-7")   # False: not queued

worker = jobs.SyncWorker("report", ack_wait=900)   # in a loop of a process with events.init()
job = worker.take()
if job:
    try:
        run_report(job.payload)
        worker.done(job)
    except Exception as error:
        worker.done(job, error)   # comes again later
```

On asyncio: `await queue.submit(nc, kind, payload, ...)` and `queue.Worker(nc, kind, handler)` (`await worker.start(); await worker.run()`). Jobs live in the stream `JOBS` (subjects `job.<kind>.p<priority>`, kept at most 7 days); each kind has its own durable consumers `<kind>-p1` … `<kind>-p3`, the highest priority goes first. A job taken after `valid_for` is dropped, a `key` keeps a second submission out (10 minutes) and a job whose key ran already from running again (bucket `jobs_done`), a failed job comes again after a growing pause; a handler raises `queue.Skip` for a job that no longer fits. Workers on several hosts share a kind; handlers must allow a second run.

### Notifications
Messages to people (an alert, a finished report) over channels (`flaskspark.core.notify`):

```python
from flaskspark.core import notify

notify.Notifier().send("Import failed", "The file had no rows.", priority=notify.HIGH, category="import")
```

- The core's channel is ntfy (`NTFY_URL`, `NTFY_TOPIC`, `NTFY_TOKEN`); a module adds others with `notify.register_channel(factory)` in `Module.register()` (a factory returning a `NotificationChannel` or `None`). Without a channel `send()` only logs.
- With `notifications: {enabled: true}` the message goes into the job queue and the notifications service delivers it, with retries. Otherwise (or when the queue can't take it) it goes out at once; what can't be sent waits in `STATE_DIR/notify/outbox.jsonl` and goes out later.
- A message delivered late says so in its title. `Notifier(enabled=...)` takes the sending module's mute switches per `category`.
- **Texts**: title and message may be English source texts (`N_()`, with `%(name)s` filled from `params=`): `send()` translates them into the application's language (`notifications.language`, else the first of `app.locales`) with the catalogues of the core, the modules and the app (`flaskspark.core.i18n.gettext(text, locale=None, **params)`, for any text outside a request). A text that is no source text goes out as it is.
- **History** (opt-in, `notifications: {history: true}`): every message sent (muted ones marked `muted`) is appended to `STATE_DIR/notifications/history.jsonl` (cut to its newer half beyond 2 MB); `notify.history(limit=100)` reads the latest, newest first.

```python
notify.Notifier().send(N_("Import of %(file)s failed"), N_("The file had no rows."), params={"file": name})
```

### Guardian
With `guardian: {enabled: true}` the guardian service runs every check every `interval` seconds and notifies (straight to the channels, not through the queue) about new, lasting and resolved findings. The core checks NATS, the services (no live instance for `service_grace` seconds) and, with the notifications service, the queue; a module adds checks with `Module.guard_checks()`: subclasses of `GuardCheck` (`flaskspark.core.services.guardian`) with `run(ctx)` returning `Finding`s (`Finding(key, level, title, message, grace=0, params={})`: title and message are English source texts with `%(name)s` from `params`, a param whose name ends in `label` is a source text too; the guardian sends them in the application's language, the status tile shows them in the visitor's), optional `react()` and `DEFAULTS` (settings, overridable in the `guardian` section). Its settings: `interval` (30), `reminder_critical_minutes` (30), `reminder_warning_minutes` (240), `failing_minutes` (5), `nats_grace` (60), `service_grace` (120), `notify_stuck_minutes` (5). After each run the status tiles reload.

Between its runs the guardian watches the service directory (it subscribes to `$KV.services.>`) and, with `NATS_MONITOR`, the servers' `/healthz` every 3 seconds (`flaskspark.core.services.guardian.watch.StatusWatch`): a new or stopped instance, a change of `ok` or of the role, a heartbeat gone stale or a server going away reloads the status tiles at once (at most one event per 2 seconds) and brings the next run of the checks forward (at most one per 5 seconds). Its notifications still wait for their grace time, so a short blip shows on the tiles but alerts nobody. `myapp guard-check` runs the checks once and prints the findings.

### Backups
`myapp backup` (e.g. from a systemd timer or cron every 15 minutes) copies the database consistently through the database API (also while the services write), checks and gzips it (`db-<stamp>.db.gz`), archives the state directory (`state-<stamp>.tar.gz`, with the [attachments](#attachments) below `STATE_DIR/attachments`, without the database, backups, sessions, the NATS store, temporary files and any folder with a `.nobackup` file, e.g. the attachments' thumbnails) and prunes: every backup of the last `keep_hours`, then the newest per day for `keep_days`. Secrets are never part of a backup.

```yaml
backup:
  dir: /var/backups/myapp   # default STATE_DIR/backups
  keep_hours: 48
  keep_days: 7
  state: true               # the state directory too
  max_age_hours: 26         # the backup tile warns when the latest one is older
  mirror_dir: /mnt/share/myapp   # optional: every run copies the backup folder there (and removes what was pruned)
  include: [/srv/myapp/files]    # optional: further directories into the state archive
```

Further directories outside the state directory come into the same archive (`state-<stamp>.tar.gz`, below `extra/<absolute path>`, with `.nobackup`, temporary files and logs left out like in the state directory): those of `backup.include` and those the modules name with `Module.backup_paths(cfg)` (e.g. a store of [attachments](#attachments) configured elsewhere). With `state: false` the archive holds only these.

With `mirror_dir` the backups also go to a second folder (e.g. a network share with backup jobs of its own); when it is not there, the run only skips the mirror and the backup tile warns until it is current again.

`myapp backup-list` lists them, `myapp backup-check <file>` checks a database backup (integrity, rows per table), `myapp backup-restore <file>` puts it in place of the live database (stop the services first).

### Secrets
Secrets a module stores (API keys, passwords of accounts it signs in to) go into its tables encrypted (`flaskspark.core.secrets`, needs `cryptography`, part of the `core` extra):

```python
from flaskspark.core import secrets

box = secrets.for_module("shop")
row.api_key = box.encrypt(api_key)      # store
api_key = box.decrypt(row.api_key)      # read; secrets.SecretKeyError when the key can't read it
secrets.mask(api_key)                   # "sk-a…" for a page
```

The key is the environment variable `APP_SECRET_KEY` (in `CONFIG_DIR/app.env` or the container's environment, never in `config.yaml`); `APP_SECRET_KEY_ENV` names another variable instead, e.g. one an application already had. A module may get a key of its own (`APP_SECRET_KEY_<MODULE>`, e.g. in `CONFIG_DIR/shop.env`), so the key need only live where the module runs; without one it uses the shared key. The scheme is Fernet with the key `urlsafe_b64(SHA-256(<the variable's value>))`: any text is a key, and secrets another program stored with the same scheme and key stay readable. Changing the key makes the stored secrets unreadable.

### NATS users and permissions
Each service connects as its own NATS user (`NATS_<USER>_USER` / `_PASSWORD`; the core's users are `web`, `push`, `router`, `notify` and `guardian`) under the connection name `flaskspark-<service>` (what the server's monitoring, e.g. `/connz`, shows). The users, subjects and permissions use the short names, not `flaskspark-…`. Besides the subjects of its work, a user needs:

| For | Permissions |
| --- | --- |
| Replies (every user) | subscribe `_INBOX.<user>.>` (requests and the JetStream API answer there) |
| Heartbeats (every service, also `router`: `ms.router.>`) | publish `ms.<service>.>`; the bucket `services`: `$KV.services.>`, `$JS.API.STREAM.INFO.KV_services` and the bucket's other API calls |
| Reading the directory (`web` for the status tiles, `guardian`) | `$JS.API.STREAM.INFO.KV_services`, `$JS.API.DIRECT.GET.KV_services` (or `$JS.API.STREAM.MSG.GET.KV_services`) |
| Watching the directory (`guardian`) | subscribe `$KV.services.>` |
| Leadership | the API of its bucket (`$KV.<bucket>.>`, `$JS.API.STREAM.INFO.KV_<bucket>`, creating the bucket the first time) |
| Job queue: submitting | publish `job.<kind>.>` (and the JetStream acknowledgement) |
| Job queue: working | the stream `JOBS` (create/update, its consumers `<kind>-p1..3`, `$JS.API.CONSUMER.MSG.NEXT.JOBS.<kind>-p*`, acks) and the bucket `jobs_done` |
| Live data (`push`) | subscribe `ev.>` and the modules' `PUSH_TOPICS` |

`NATS_REPLICAS` sets the copies of the streams and buckets the core creates.

### Sessions
Sessions are kept on the server (Flask-Session, files in `STATE_DIR/sessions`); the browser only holds the session id. So workflows may keep larger state in the session without the 4 KB limit and readability of a signed cookie.

### Deployment
- **Production checklist:** `SECRET_KEY` set, and `APP_SECRET_KEY` as soon as modules store secrets or accounts (env files or the container's environment), `auth: oauth` unless the network is trusted, `APP_STATE_DIR` on a local disk with [backups](#backups), NATS with users per service, only the router's port published (see [Security notes](#security-notes)).
- **One container:** run `myapp run` as the container's command and publish the router's port (`APP_PORT`). Point `APP_STATE_DIR` and `APP_CONFIG_DIR` to volumes; with `nats.embedded: true` the image needs `nats-server`, otherwise set `NATS_URL`. Its log names the processes `flaskspark-<service>` (e.g. `start flaskspark-push`, `flaskspark-push ended (exit 1), again in 2 s`).
- **Separate containers:** run `myapp service <name>` per container and name the container (and its compose service) `flaskspark-<name>`, e.g. `flaskspark-push`, `flaskspark-router`, so containers, units, logs and status tiles agree; set `APP_HOST` to where it runs. A reverse proxy (e.g. nginx, Traefik) takes the router's place with the routes `myapp routes` prints.

## Web components
FlaskSpark includes a library of web components built on Bootstrap 6 (package `webcomponents`): custom elements (`ui-button`, `ui-dialog`, `ui-table`, `ui-datepicker`, …) that render in a Shadow DOM, are grouped into modules and submodules and are themed via CSS variables. They are plain ES modules and plain CSS, nothing has to be built.

The detailed documentation (structure, every component, writing components, tests) is in [`webcomponents/README.md`](./webcomponents/README.md); the [docs app](#development-and-tests) shows every component with examples.

Display-only pages (an [info screen](#info-screens): `<html data-screen>`, which sets `--ui-screen: on`): every component hides its own controls (close and remove buttons, a card's chevron and actions, and anything marked `data-screen-hide` inside its shadow tree), through a style query on `--ui-screen` (`:host-context(html[data-screen])` where style queries are missing). `ui-context-menu` opens no menu there.

### Use them in a FlaskSpark app
The components are installed with FlaskSpark. Switch them on in `.env`:

```dotenv
VENDOR_INCLUDE_WEBCOMPONENTS=true
```

FlaskSpark then:
- registers their blueprint under `/webcomponents/…` (versioned URLs, cached for a year)
- loads the Bootstrap 6 CSS and the `bootstrap` module (all Bootstrap components) in `layouts/framework.html`
- provides `webcomponents_url(filename)` and `vendor_include_webcomponents` in templates

```jinja2
{% extends "layouts/framework.html" %}

{% block app_body %}
<main class="container py-4">
  <ui-alert variant="info">Hello from a web component</ui-alert>
  <ui-button variant="primary">Save</ui-button>
</main>
{% endblock %}

{% block app_scripts %}
<script type="module" src="{{ webcomponents_url('modules/calendar/calendar.js') }}"></script>
{% endblock %}
```

Notes:
- `VENDOR_INCLUDE_WEBCOMPONENTS` and `VENDOR_INCLUDE_BOOTSTRAP` (Bootstrap 5) exclude each other; the start fails if both are set.
- Apps must not register the `webcomponents` blueprint themselves.
- Modular apps (`flaskspark.core`) have the components switched on and import them as `webcomponents/…` through the page's import map (see [Browser JavaScript](#browser-javascript)).

### Use them without Python
Projects without Python (for example a CMS theme or a static site) take a snapshot of the plain JS/CSS files (a first example: [Web components without Python](#web-components-without-python)). Any environment with FlaskSpark installed can make it:

```bash
python -m webcomponents.export TARGET_DIR                        # all modules
python -m webcomponents.export TARGET_DIR bootstrap              # one module
python -m webcomponents.export TARGET_DIR bootstrap/ui-tooltip   # single submodules (+ the ones they require)
python -m webcomponents.export TARGET_DIR bootstrap --no-vendor  # without vendor libraries (e.g. Bootstrap 6)
```

The target keeps the package layout (`core/`, `modules/…`, `vendor/…`), so relative imports and stylesheet URLs keep working wherever the directory is served. `webcomponents.json` in the target records what was exported. Take a new snapshot after every FlaskSpark update. See [`webcomponents/README.md`](./webcomponents/README.md#export-without-python) for details.

## Markdown
`flaskspark.markdown` renders Markdown the way GitHub and GitLab do and turns HTML back into Markdown. The browser
has the same rules (`webcomponents/modules/bootstrap/ui-markdown/markdown.js`), so a text rendered on the server and
in the editor looks the same; shared test cases keep both in step.

- **Syntax:** CommonMark with tables, strikethrough (`~~x~~`), autolinks (`https://…`, `www.…`, e-mail addresses),
  task lists (`- [ ]` / `- [x]`), alerts (`> [!note]`, `[!tip]`, `[!important]`, `[!warning]`, `[!caution]`, an
  optional title after the marker), collapsible sections (`<details><summary>`), a table of contents (`[[_TOC_]]` or
  `[TOC]` alone in a paragraph; headings get ids like GitLab's), code blocks with `class="language-…"`. Mermaid and
  PlantUML are not drawn: they stay code blocks.
- **Sanitised** with an allowlist (nh3 on the server, the same list in the browser): no scripts, styles, frames, forms
  or event handlers; links only http(s), mailto, tel and relative (`rel="noopener noreferrer"`), images only http(s)
  and relative; task list boxes are disabled checkboxes.
- **Libraries:** markdown-it-py with linkify-it-py and nh3 (MIT) on the server, markdown-it 14.1.0 (MIT, vendored,
  loaded on first use) in the browser; HTML to Markdown is FlaskSpark's own, in both.

```python
from flaskspark import markdown

html = markdown.render(text)                                   # Markup, safe in a template
html = markdown.render(text, base_url="https://git.example.com/group/project")   # /uploads/a.png -> …/project/uploads/a.png
html = markdown.render(text, rewrite_url=lambda url, kind: f"/img?u={url}" if kind == "image" else url)  # e.g. a proxy
html = markdown.render(text, breaks=True, alert_titles={"note": "Hinweis"})
text = markdown.to_markdown(html)                              # tables, lists, task lists, code, links, alerts, details
```

- `base_url` is a prefix for relative links and images (not `#…`), `rewrite_url(url, kind)` (`kind` `"link"` or
  `"image"`) may change every URL afterwards or drop it (`None`); the scheme check comes last.
- Jinja filter (every FlaskSpark app): `{{ issue.description|markdown }}`, `{{ text|markdown(base_url=project_url) }}`;
  the alert titles follow the page's language.
- Editor in a form: `<ui-markdown-editor name="description" value="{{ text }}"></ui-markdown-editor>` submits
  Markdown (modes «Text» and «Markdown», toolbar like GitLab's, `/` and `+` commands an app can extend, attachments
  through `uploadHandler` or the event `ui-markdown-editor:attach`). Apps on `flaskspark.core` pass its texts in the
  page's language: `labels='{{ markdown_editor_labels()|tojson }}'`. Showing Markdown in the browser:
  `<ui-markdown value="…">` or `<ui-markdown>{{ text|markdown }}</ui-markdown>`. Details and examples: docs app,
  `/components/markdown`.

## Development and tests
From a checkout of the repository:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[core,files,dev]"
python -m pytest                       # the whole Python suite (tests/)
node --test tests/webcomponents/js/    # the JavaScript tests of the web components (Node.js 20+; or: npm test)
```

The NATS tests start a `nats-server` of their own and are skipped without one on the `PATH`. `tests/core` covers
`flaskspark.core`, `tests/webcomponents` the components (the grid layout logic is tested in Python and JavaScript
against the same fixtures), `tests/test_markdown.py` Markdown.

The docs app (examples and usage of every web component) lives in `docs/`:

```bash
cp docs/.env.example docs/.env  # optional, defaults work
python docs/run.py              # http://localhost:5067
```

The core's own translations are updated with `scripts/core-i18n`. Changes are listed in [`CHANGELOG.md`](./CHANGELOG.md).

## Security notes
- **Development server.** `python app.py` runs Flask's development server on all interfaces (`APP_BIND_HOST=0.0.0.0`)
  and, unless `ENVIRONMENT=production`, in debug mode with the interactive debugger. Never expose it; in production
  set `ENVIRONMENT=production` and use a WSGI server (modular apps run gunicorn behind the router themselves).
- **`SECRET_KEY`** signs the sessions: a long random value per installation, kept out of the repository.
- **Without sign-in** (`auth: none` in a modular app, or a FlaskSpark app without a login provider) every visitor may
  use everything, the admin pages included. Run such an app in a trusted network only, or use `auth: oauth`.
- **Secrets** live in the environment or in env files (`CONFIG_DIR/*.env`), never in `config.yaml` or the database
  in plain text; what modules store is encrypted with `APP_SECRET_KEY` ([Secrets](#secrets)). Backups contain no
  secrets.
- **User content**: Markdown is sanitised with an allowlist ([Markdown](#markdown)); attachments are delivered as
  downloads unless they are safe to show, never HTML or SVG inline ([Attachments](#attachments)).
- **Forms**: FlaskSpark has no CSRF tokens. Modular apps set the session cookie `SameSite=Lax` and `HttpOnly`;
  protect forms of your own as your application needs it.
- **Behind a proxy**: the web app of a modular app trusts the `X-Forwarded-For`, `-Proto` and `-Host` headers of one
  hop (the router). Publish only the router's port, never the web or push service's.
- **NATS**: give every service its own NATS user with only the permissions it needs
  ([NATS users and permissions](#nats-users-and-permissions)); an anonymous NATS server belongs on `127.0.0.1` only.

## License
FlaskSpark is released under the MIT License; see [`LICENSE`](./LICENSE).

It includes third-party components (among them Bootstrap 5 and 6, Bootstrap Icons, Vanilla Calendar Pro, FullCalendar
and markdown-it); see [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md) for attribution and license
references.

## Disclaimer
- FlaskSpark is provided "as is", without warranty of any kind. The author accepts no liability for any damage or loss
  arising from its use.
- There is no claim that FlaskSpark or this documentation is complete, correct or fit for a particular purpose, nor
  that it works in every environment or without interruption.
- FlaskSpark was created with the help of AI.
- It is tailored to the author's own needs, but everyone is welcome to use it under the terms of the
  [MIT License](./LICENSE).
- Feature requests and bug reports are welcome as [issues on GitHub](https://github.com/berofa/FlaskSpark/issues).
