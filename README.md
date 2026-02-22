# FlaskSpark

FlaskSpark is a lightweight Flask framework with a clear project structure, automatic class-based view registration, built-in SQLAlchemy + Flask-Migrate wiring, optional OAuth/OIDC login, and an asset pipeline for SCSS/JS.

## License
FlaskSpark is released under the MIT License.  
See the full license text in [`LICENSE`](./LICENSE).

## Disclaimer
- This project includes third-party components. See [`THIRD_PARTY_NOTICES`](./THIRD_PARTY_NOTICES.md) for attribution and license references (currently including Bootstrap under MIT).
- FlaskSpark is developed primarily for private/personal use. No warranty is provided for fitness, compatibility, or uninterrupted operation.
- Contributions are welcome via issues and pull requests.
- GitHub repository: https://github.com/berofa/FlaskSpark

## Features
- Fast app bootstrap with a configurable app package (`app_module`)
- Automatic view/model discovery from your app package
- Class-based routing with `FlaskSparkMethodView` (auto route registration)
- Built-in SQLAlchemy + Flask-Migrate wiring
- Pluggable login providers (`Default`, `OAuth`) with OIDC support (`authlib`)
- Built-in i18n using Flask-Babel
- Template/static fallback strategy (app files first, FlaskSpark as fallback)
- SCSS/JS asset pipeline with optional minification and per-page bundles
- Framework base layout (`layouts/framework.html`) with clear override hooks
- Optional Bootstrap integration into your app bundles via env flag

## Requirements
- Python 3.8+
- pip

## Installation
```bash
pip install FlaskSpark
```

Execute this command directly in your project directory. Assuming your project is named "Tasks" and has the following project structure:

```bash
~/Projectdir/Tasks
```

Then the installation command for FlaskSpark is:

```bash
cd ~/Projectdir/Tasks
pip install FlaskSpark
```

### Development installation (editable)
If you installed FlaskSpark from `PiPY` with the command above skip this section. If you pulled FlaskSpark directly from the GitHub repository, you can install it as follows:

```bash
pip install -e <PATH_TO_FLASKSPARK>
```

Assuming your FlaskSpark app is named "Tasks" and has the following directory:

```bash
~/Projectdir/FlaskSpark
~/Projectdir/Tasks
```

Then the installation command for FlaskSpark is:

```bash
cd ~/Projectdir/Tasks
pip install -e ../FlaskSpark
```

## Quick Start
This example creates a minimal runnable app with one `/` page.

### 1. Create project files:
```text
myapp/
  app.py
  app/
    __init__.py
    views/
      home.py
    models/
      __init__.py
    templates/
      home.html
    static/
```

### 2. Install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install FlaskSpark
```

### 3. Create a minimal `.env` in the project root:
```dotenv
SECRET_KEY=change-me
```

Only `SECRET_KEY` is strictly required for this basic setup.  
For all optional settings, see the **[Configuration](#configuration)** section below.

### 4. Create `app/__init__.py`:
```python
from flaskspark import FlaskSpark

app = FlaskSpark(
    app_module="app",
).app
```

`app_module` must match your app package directory name.  
It does **not** have to be `app`.

Examples:
- `app_module="app"` -> project contains `./app/`
- `app_module="tasks"` -> project contains `./tasks/`

If you use a different package name, adjust your root imports accordingly
(for example `from tasks import app` instead of `from app import app`).

### 5. Create `app/views/home.py`:
```python
from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView


class HomeView(FlaskSparkMethodView):
    url = "/"
    endpoint = "home"

    def get(self):
        return render_template("home.html")
```

### 6. Create `app/templates/home.html`:
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

You can also create your own layout and let it inherit from `layouts/framework.html` (recommended), or skip framework layout inheritance entirely if you want full control.  
For more details, see the **[Templates](#templates)** section.

### 7. Create `app.py` (project root):
```python
from app import app

if __name__ == "__main__":
    app.run(
        host=app.config["APP_BIND_HOST"],
        port=app.config["APP_PORT"],
        debug=app.config["DEBUG"],
    )
```

`APP_BIND_HOST`, `APP_PORT`, and `DEBUG` all have default values. Your app will therefore still work even if you don't explicitly set them. See the **Configuration** section for the full list.


### 8. Start the app:
```bash
python app.py
```

### Automatic discovery behavior
- Views: Files under `app/views/` are auto-imported, and view classes inheriting from `FlaskSparkMethodView` are auto-registered as routes.
- Models: Files under `app/models/` are auto-imported and included in SQLAlchemy metadata.
- Templates/static: App files are resolved first; FlaskSpark files are fallback.

## Assets (SCSS / JS)
FlaskSpark uses Flask-Assets to build your frontend bundles.  
In normal usage you define source entries once and FlaskSpark serves the generated outputs in the framework layout.

### What assets are for
- Compile SCSS to CSS
- Minify CSS/JS (depending on configured filters and environment)
- Bundle app-level JavaScript and optional vendor sources (for example Bootstrap)
- Keep output paths stable so templates can always include `styles/app.min.css` and `scripts/app.min.js`

### When to configure assets
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

### Minimal default setup
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

### Typical `.env` asset settings
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

### Advanced example (`config={...}`)
Use this only when you need extra app-specific bundles:
```python
FlaskSpark(
    app_module="app",
    config={
        "ASSETS_BUNDLES": [
            {
                "name": "dashboard_js",
                "type": "js",
                "entry": "js/dashboard.js",
                "output": "scripts/dashboard.min.js",
                "filters": "rjsmin",
            },
        ],
    },
)
```

What this does:
- Each entry in `ASSETS_BUNDLES` registers an additional build target.
- FlaskSpark will generate the configured output file (for example `scripts/dashboard.min.js`) using the given filters.
- You can then include that generated file in templates via `url_for('static', filename='...')`.

When to add bundle entries:
- Add a new JS/SCSS file and you want it built as a separate output (for example page-specific assets).
- Add an entry to `ASSETS_BUNDLES` so FlaskSpark knows source, output, and filters.
- Without an entry, only the main default bundle (`app.min.css` / `app.min.js`) is generated.

## Templates
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
- `flaskspark_head_assets`
- `app_head`
- `body_attrs`
- `flaskspark_body_start`
- `app_body`
- `flaskspark_body_end`
- `flaskspark_scripts`
- `app_scripts`

FlaskSpark itself does not ship page views. It provides framework plumbing
(layout base, helpers, auth/database/assets integration), while applications
provide their own frontend views/templates.

## Configuration
All configuration values are read from environment variables (or overridden via the `config={...}` dict in `FlaskSpark(...)`).

### Configuration precedence
FlaskSpark resolves configuration in this order (later entries override earlier entries):

1. FlaskSpark defaults (`flaskspark/config.py`)
2. `.env` values loaded via `dotenv_path`
3. explicit `config={...}` values passed to `FlaskSpark(...)`
4. explicit runtime arguments in `app.run(...)` (for host/port/debug only)

Recommendation:
- Keep runtime/environment values in `.env`.
- Use `config={...}` mainly for app-structure settings that are hard to express as env values (for example complex `ASSETS_BUNDLES` lists).
- In `app.py`, pass `host/port/debug` from `app.config` so env/config values are respected.

Why not just `app.run()`?
- `app.run()` without arguments uses Flask defaults (`127.0.0.1:5000`, `debug=False`) and does not automatically apply your `APP_BIND_HOST` / `APP_PORT` settings.
- `app.run(host=app.config["APP_BIND_HOST"], port=app.config["APP_PORT"], debug=app.config["DEBUG"])` keeps startup aligned with FlaskSpark config and `.env`.

| Key | Default | Description |
| --- | --- | --- |
| `SECRET_KEY` | `None` | Flask secret key. Required for sessions/security features. |
| `ENVIRONMENT` | `development` | High-level mode. `production` disables debug defaults; any other value is treated as development. |
| `FLASK_ENV` | Derived | Computed from `ENVIRONMENT` (`production` or `development`). |
| `DEBUG` | Derived | Computed from `ENVIRONMENT` (`False` in production, else `True`). |
| `SQLALCHEMY_DATABASE_URI` | `sqlite:///app.db` | Database connection string. If unset, `DATABASE_URL` is checked first. |
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
| `BABEL_DEFAULT_LOCALE` | `en` | Fallback locale. |
| `BABEL_SUPPORTED_LOCALES` | `["en"]` | Allowed locales (CSV env input). |
| `BABEL_TRANSLATION_DIRECTORIES` | `locales` | Translation directory path(s) for Flask-Babel. |
| `ASSETS_ENABLE` | `true` | Enables Flask-Assets pipeline. |
| `ASSETS_AUTO_BUILD` | `true` | Enables on-demand asset builds. |
| `ASSETS_DEBUG` | `false` | Asset debug flag. |
| `ASSETS_BUILD_ON_START` | `false` | Forces bundle builds at startup. |
| `ASSETS_FORCE_BUILD` | `false` | Forces rebuild even when cached outputs exist. |
| `ASSETS_SCSS_ENTRY` | `scss/app.scss` | Main SCSS entry file (relative to app static root). |
| `ASSETS_JS_ENTRY` | `js/app.js` | Main JS entry file (relative to app static root). |
| `ASSETS_SCSS_OUTPUT` | `styles/app.min.css` | Main CSS output path. |
| `ASSETS_JS_OUTPUT` | `scripts/app.min.js` | Main JS output path. |
| `ASSETS_SCSS_FILTERS` | `libsass,rcssmin` | SCSS filter chain. |
| `ASSETS_JS_FILTERS` | `rjsmin` | JS filter chain. |
| `ASSETS_SCSS_INCLUDE_PATHS` | `[]` | Extra SCSS include paths (CSV env input). |
| `ASSETS_BUNDLES` | `[]` | Extra bundles list (config dict only, not env string). |
| `VENDOR_INCLUDE_BOOTSTRAP` | `false` | If `true`, FlaskSpark prepends vendored Bootstrap SCSS/JS into app bundles. |
| `APP_LAYOUT_TEMPLATE` | `layouts/framework.html` | Default layout injected into template context as `layout`. |
| `APP_HOST` | `0.0.0.0` | Optional app host value for app-level logic. |
| `APP_BIND_HOST` | `0.0.0.0` | Socket bind address used by `app.run(...)`. |
| `APP_PORT` | `5067` | Socket bind port used by `app.run(...)`. |

## Class-Based Views
FlaskSpark is designed around class-based views.

Recommended pattern:
- put your view classes in `app/views/*.py`
- inherit from `FlaskSparkMethodView`
- define `url` and `endpoint` on the class
- implement HTTP methods as class methods (`get`, `post`, `put`, `delete`, ...)

Avoid `@app.route(...)` in your app code.  
FlaskSpark auto-discovers and registers class-based views from `app/views/`, so route decorators are usually unnecessary and can make routing behavior inconsistent.

### How auto-registration works
- FlaskSpark imports modules under `app/views/`
- each class with `as_view()` is considered a view
- route is registered via:
  - `url` class attribute (fallback: `/<module_name>`)
  - `endpoint` class attribute (fallback: `<module_name>`)

Use explicit `url` and `endpoint` to keep routes stable and readable.

### Example: regular HTML view (GET + POST)
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

### Example: API collection endpoint (GET + POST)
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

### Example: API detail endpoint (GET + PUT + DELETE)
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

### Optional helper: `return_response(...)`
`FlaskSparkMethodView` provides `return_response(data, template=...)`:
- if request is JSON, returns JSON
- otherwise renders the given template

Example:
```python
class DashboardView(FlaskSparkMethodView):
    url = "/dashboard"
    endpoint = "dashboard"

    def get(self):
        data = {"title": "Dashboard"}
        return self.return_response(data, template="dashboard.html")
```

### Login-protected class-based views
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

## OAuth (OIDC) Login Provider
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

### Important: database is required for login providers
When a login provider is enabled, FlaskSpark expects database tables/models and checks DB availability at startup.

Before running with a login provider, create/update the DB schema:

```bash
FLASK_APP=app.py python -m flask db init
FLASK_APP=app.py python -m flask db migrate -m "init auth"
FLASK_APP=app.py python -m flask db upgrade
```

(If `db init` was already run once, only `migrate` + `upgrade` are needed.)

### OAuth/OIDC required configuration
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

### Build your own login provider
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

## Database & Migrations
FlaskSpark wires SQLAlchemy + Flask-Migrate automatically.

When you define models in your app package, FlaskSpark imports them from:
- `app/models/*.py` (or `<app_module>/models/*.py`)

Those models are then included in SQLAlchemy metadata and migration diffs.

### 1. Configure your database
Set a DB URL in `.env` (recommended):

```dotenv
SQLALCHEMY_DATABASE_URI=sqlite:///instance/app.db
```

Notes:
- If `SQLALCHEMY_DATABASE_URI` is not set, FlaskSpark falls back to `DATABASE_URL`.
- If neither is set, default is `sqlite:///app.db`.

### 2. Create a model
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

### 3. Initialize migrations (once per project)
```bash
FLASK_APP=app.py python -m flask db init
```

This creates the `migrations/` directory.

### 4. Create and apply migrations
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

### Useful commands
```bash
FLASK_APP=app.py python -m flask db current
FLASK_APP=app.py python -m flask db history
FLASK_APP=app.py python -m flask db downgrade -1
```

### When is DB required?
- No database-related models and no login provider: DB can be omitted.
- Login provider enabled (`Default` or `OAuth`): DB is required and schema must be migrated before startup.

## i18n
FlaskSpark initializes Flask-Babel automatically.

### 1. Configure locales
Minimal `.env` example:

```dotenv
BABEL_DEFAULT_LOCALE=en
BABEL_SUPPORTED_LOCALES=en,de
BABEL_TRANSLATION_DIRECTORIES=locales
```

This means:
- default language is `en`
- allowed languages are `en` and `de`
- translation files are read from `./locales`

### 2. Mark strings for translation
In Python:

```python
from flask_babel import gettext as _

title = _("Dashboard")
```

In Jinja templates:

```jinja2
<h1>{{ _("Dashboard") }}</h1>
```

### 3. Add Babel extraction config
Create `babel.cfg` in your project root:

```ini
[python: **.py]
[jinja2: **/templates/**.html]
extensions=jinja2.ext.autoescape,jinja2.ext.with_
```

### 4. Extract / init / update / compile translations
Run these commands from your project root:

```bash
pybabel extract -F babel.cfg -o messages.pot .
pybabel init -i messages.pot -d locales -l de
pybabel update -i messages.pot -d locales
pybabel compile -d locales
```

What they do:
- `extract`: scans code/templates and builds the source catalog (`messages.pot`)
- `init`: creates a new language (for example German)
- `update`: refreshes existing language files after text changes
- `compile`: builds `.mo` files used at runtime (required before running in production)

### 5. Set active language at runtime
FlaskSpark selects locale in this order:
1. `lang` cookie (if valid and supported)
2. browser `Accept-Language`
3. `BABEL_DEFAULT_LOCALE`

### Optional: client-side translations endpoint
FlaskSpark also provides:

```text
GET /_flaskspark/i18n?keys=Dashboard,Logout
```

Response example:

```json
{
  "Dashboard": "Übersicht",
  "Logout": "Abmelden"
}
```
