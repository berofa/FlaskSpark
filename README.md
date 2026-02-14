# FlaskSpark

FlaskSpark is a lightweight Flask framework that provides a structured application layout, auto‑registration of class‑based views, built‑in SQLAlchemy + Flask‑Migrate wiring, and a pluggable login provider system (including OAuth/OIDC). It is designed to let applications focus on features while FlaskSpark handles the app scaffolding and cross‑cutting concerns.

## Features
- Application factory with configurable `app_module`
- Auto‑registration of class‑based views via `as_view()`
- SQLAlchemy + Flask‑Migrate pre‑wired
- Pluggable login providers (`Default`, `OAuth`)
- OAuth/OIDC integration via `authlib`
- Built‑in i18n with Flask‑Babel (cookie `lang`, browser fallback, default `en`)
- Client‑side i18n JSON endpoint for frontend translations
- Template/static fallback lookup (app first, then FlaskSpark)
- Optional user model with OAuth fields
- Optional asset pipeline for SCSS/JS via Flask‑Assets

## Requirements
- Python 3.8+
- pip
- Virtual environment recommended

### Python Dependencies
Installed automatically via `pip`:
- `flask`
- `flask-sqlalchemy`
- `flask-migrate`
- `flask-login`
- `flask-session`
- `flask-babel`
- `authlib`
- `python-dotenv`
- `flask-assets` (optional, for asset pipelines)
- `libsass` + `rcssmin` (SCSS compilation/minification)
- `rjsmin` (JS minification)

## Installation
### Editable install (recommended for development)
```bash
pip install -e /path/to/FlaskSpark
```

### Regular install
```bash
pip install /path/to/FlaskSpark
```

## Quick Start
Create a FlaskSpark app:
```python
from flaskspark import FlaskSpark

app = FlaskSpark(
    app_module="app",
    config={
        "SECRET_KEY": "replace-me",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///instance/app.db",
        "BABEL_SUPPORTED_LOCALES": ["en", "de"],
    },
).app
```

Application layout:
```
app/
  __init__.py
  views/
    home.py
  models/
    __init__.py
  templates/
    layouts/
      main.html
  static/
```

### App module conventions
- `app/views/`: class‑based views (auto‑registered)
- `app/models/`: SQLAlchemy models (auto‑imported)
- `app/templates/`: templates (app overrides FlaskSpark)
- `app/static/`: static assets (app overrides FlaskSpark)

## Class‑Based Views
FlaskSpark registers any class under `app.views` that implements `as_view()`.

Basic view:
```python
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView
from flask import render_template

class HomeView(FlaskSparkMethodView):
    url = "/"
    endpoint = "home"

    def get(self):
        return render_template("index.html")
```

### Supported HTTP methods
Flask uses method names to route requests. Implement any of:
- `get`
- `post`
- `put`
- `patch`
- `delete`
- `head`
- `options`

Example with GET + POST:
```python
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView
from flask import jsonify, request

class TaskView(FlaskSparkMethodView):
    url = "/tasks"
    endpoint = "tasks"

    def get(self):
        return jsonify({"ok": True})

    def post(self):
        payload = request.get_json(silent=True) or {}
        return jsonify({"created": payload})
```

### Route metadata
Each view must define:
- `url`: the route path (e.g. `"/tasks"`)
- `endpoint`: unique endpoint name (e.g. `"tasks"`)

FlaskSpark auto‑registers the view at app startup.

## API Endpoints
FlaskSpark does not force a specific API structure, but class‑based views make it easy
to implement API endpoints alongside page routes.

Recommended approach:
- Keep page views under normal routes (e.g. `/settings`).
- Keep API endpoints under `/api/...` and return JSON.

Example API view:
```python
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView
from flask import jsonify, request

class ApiExampleView(FlaskSparkMethodView):
    url = "/api/example"
    endpoint = "api_example"

    def post(self):
        payload = request.get_json(silent=True) or {}
        return jsonify({"ok": True, "payload": payload})
```

## i18n (Flask‑Babel)
FlaskSpark initializes Babel automatically.

Behavior:
- If cookie `lang` is set and supported, that locale is used.
- Otherwise, browser language is used.
- Fallback is `BABEL_DEFAULT_LOCALE` (default `en`).

Config keys:
```python
BABEL_DEFAULT_LOCALE = "en"
BABEL_SUPPORTED_LOCALES = ["en", "de"]
BABEL_TRANSLATION_DIRECTORIES = "locales"
```

### Client‑side i18n endpoint
FlaskSpark exposes a JSON endpoint for frontend translations:
```
GET /_flaskspark/i18n?keys=Message%20ID,Another%20ID
```
It returns a JSON map of message IDs to localized strings. Use this to avoid inline JSON
in templates and keep translations server‑driven.

Example (JS):
```js
const res = await fetch("/_flaskspark/i18n?keys=Entry%20saved.,Delete%20failed.");
const translations = await res.json();
console.log(translations["Entry saved."]);
```

## Login Providers
### OAuth (OIDC)
Enabled with:
```python
FlaskSpark(login_provider="OAuth")
```

Required config keys:
```
OAUTH_NAME
OAUTH_AUTHORIZE_URL
OAUTH_ACCESS_TOKEN_URL
OAUTH_USERINFO_ENDPOINT
OAUTH_JWKS_URI
OAUTH_CLIENT_ID
OAUTH_CLIENT_SECRET
OAUTH_SCOPE
```

Optional role mapping config:
```
OAUTH_GROUPS_CLAIM=groups
OAUTH_ROLE_PRIORITY=administrators,weissen.private,weissen.users
OAUTH_ROLE_MAP=administrators:Administrators,weissen.private:Editors,weissen.users:Users
```
If group claims are present, FlaskSpark will assign the first matching role based on
`OAUTH_ROLE_PRIORITY`. If no groups are provided, it falls back to the first user
as `Administrator` and all others as `Guest`.

Routes provided:
- `GET /auth/login`
- `GET /auth/callback`
- `GET /auth/logout`

The provider uses Flask‑Login and stores user info in session.

### Roles
FlaskSpark includes a simple role model and user role assignment:
- Default roles: `Administrator` (admin) and `Guest` (non‑admin).
- The OAuth login provider assigns the first user to `Administrator` and all
  subsequent users to `Guest` (unless already assigned).
- `User.is_admin` reflects the assigned role (and mirrors the legacy `admin` flag).

You can manage roles and user assignments from your application layer (e.g. a settings
page backed by `/api/roles/...` and `/api/users/role` endpoints).

## Database & Migrations
FlaskSpark wires SQLAlchemy + Flask‑Migrate.

Initialize migrations:
```bash
FLASK_APP=app.py python -m flask db init
```

Create a migration:
```bash
FLASK_APP=app.py python -m flask db migrate -m "init"
```

Apply migrations:
```bash
FLASK_APP=app.py python -m flask db upgrade
```

If the DB exists and you only need to mark it as current:
```bash
FLASK_APP=app.py python -m flask db stamp head
```

## Configuration
FlaskSpark loads defaults from `flaskspark.config.Config` and then applies any overrides from `config` passed into `FlaskSpark(...)`.
It also reads environment variables via `.env` if provided.

Common config keys:
```python
SECRET_KEY = "..."
SQLALCHEMY_DATABASE_URI = "sqlite:///instance/app.db"
BABEL_DEFAULT_LOCALE = "en"
BABEL_SUPPORTED_LOCALES = ["en", "de"]
```

Environment defaults:
- `ENVIRONMENT=development` sets `FLASK_ENV=development` and `DEBUG=True`.
- `ENVIRONMENT=production` sets `FLASK_ENV=production` and `DEBUG=False`.

Development note:
- With `ENVIRONMENT=development`, assets rebuild on demand. A simple app restart is enough to see SCSS/JS changes.

## Assets (SCSS / JS)
FlaskSpark can compile SCSS and bundle JS using Flask‑Assets.

Config keys:
```python
ASSETS_ENABLE = True
ASSETS_AUTO_BUILD = True        # Build on request (on-demand)
ASSETS_DEBUG = False
ASSETS_BUILD_ON_START = False   # Force build at app startup
ASSETS_SCSS_ENTRY = "scss/app.scss"
ASSETS_JS_ENTRY = "js/app.js"
ASSETS_SCSS_OUTPUT = "styles/app.min.css"
ASSETS_JS_OUTPUT = "scripts/app.min.js"
ASSETS_SCSS_FILTERS = "libsass,rcssmin"
ASSETS_JS_FILTERS = "rjsmin"
ASSETS_BUNDLES = [
    {
        "name": "emails_show_js",
        "type": "js",
        "entry": "js/emails_show.js",
        "output": "scripts/emails_show.min.js",
        "filters": "rjsmin",
    },
]
```

Notes:
- `ASSETS_AUTO_BUILD=True` rebuilds bundles when source files change.
- `ASSETS_BUILD_ON_START=True` builds bundles at startup (useful for deployments).
- `ASSETS_BUNDLES` can be used to register additional bundles per page/module.
- Each bundle entry must include: `name`, `type`, `entry`, `output`.

### Environment-specific defaults
FlaskSpark reads the `ENVIRONMENT` variable and applies asset defaults:

- `ENVIRONMENT=development`
  - No minification for CSS/JS.
  - SCSS compiles on demand (when files change).
  - Asset caching disabled.
  - Build-on-start disabled.

- `ENVIRONMENT=production`
  - Minified assets.
  - Asset caching enabled.
  - Build-on-start enabled.

All of these defaults can be overridden via the `ASSETS_*` variables.

Example bundle configuration:
```python
FlaskSpark(
    app_module="app",
    config={
        "ASSETS_BUNDLES": [
            {
                "name": "settings_js",
                "type": "js",
                "entry": "js/settings.js",
                "output": "scripts/settings.min.js",
                "filters": "rjsmin",
            },
            {
                "name": "emails_scss",
                "type": "scss",
                "entry": "scss/emails.scss",
                "output": "styles/emails.min.css",
                "filters": "libsass,rcssmin",
            },
        ],
    },
)
```

### Using per-page bundles in templates
Only include bundles on pages that need them to avoid unnecessary JS/CSS payloads:
```html
{% block scripts %}
  <script src="{{ url_for('static', filename='scripts/settings.min.js') }}"></script>
{% endblock %}
```

Example (Portal):
- `emails-show.html` → `scripts/emails_show.min.js`
- `emails-manage.html` → `scripts/emails_manage.min.js`
- `settings.html` → `scripts/settings.min.js`

## Static and Template Resolution
FlaskSpark resolves templates and static files from the application first and then
falls back to FlaskSpark defaults. This allows you to override any framework
template or asset at the app level.

## Error Handling
If the database is missing or incomplete, FlaskSpark prints a clear console error
and exits. This is intended to prevent running with a partially‑migrated schema.

## License
MIT License. See `LICENSE`.
