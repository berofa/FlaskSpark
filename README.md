# FlaskSpark

FlaskSpark is a lightweight Flask framework with a clear project structure, automatic class-based view registration, built-in SQLAlchemy + Flask-Migrate wiring, optional OAuth/OIDC login, and an asset pipeline for SCSS/JS.

## Features
- App bootstrap with configurable `app_module`
- Auto-registration of class-based views (`as_view()`)
- SQLAlchemy + Flask-Migrate integration
- Pluggable login providers (`Default`, `OAuth`)
- OAuth/OIDC support via `authlib`
- Built-in i18n with Flask-Babel
- Static/template fallback (app first, FlaskSpark second)
- Optional SCSS/JS bundling via Flask-Assets

## Requirements
- Python 3.8+
- pip

## Installation
```bash
pip install FlaskSpark
```

Development (editable):
```bash
pip install -e .
```

## Quick Start
```python
from flaskspark import FlaskSpark

app = FlaskSpark(
    app_module="app",
    config={
        "SECRET_KEY": "change-me",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///instance/app.db",
        "BABEL_SUPPORTED_LOCALES": ["en", "de"],
    },
).app
```

Expected app layout:
```text
app/
  __init__.py
  views/
    home.py
  models/
    __init__.py
  templates/
  static/
```

## Class-Based Views
Any class in `app.views` implementing `as_view()` is auto-registered.

```python
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView
from flask import render_template

class HomeView(FlaskSparkMethodView):
    url = "/"
    endpoint = "home"

    def get(self):
        return render_template("index.html")
```

## OAuth (OIDC) Login Provider
Enable OAuth provider:
```python
FlaskSpark(login_provider="OAuth")
```

Required config:
```text
OAUTH_NAME
OAUTH_AUTHORIZE_URL
OAUTH_ACCESS_TOKEN_URL
OAUTH_USERINFO_ENDPOINT
OAUTH_JWKS_URI
OAUTH_CLIENT_ID
OAUTH_CLIENT_SECRET
OAUTH_SCOPE
```

Optional role mapping:
```text
OAUTH_GROUPS_CLAIM=groups
OAUTH_ROLE_PRIORITY=admins,editors,users
OAUTH_ROLE_MAP=admins:Administrators,editors:Editors,users:Users
```

## Database & Migrations
```bash
FLASK_APP=app.py python -m flask db init
FLASK_APP=app.py python -m flask db migrate -m "init"
FLASK_APP=app.py python -m flask db upgrade
```

## Assets (SCSS / JS)
FlaskSpark can build SCSS and JS bundles:

```python
FlaskSpark(
    app_module="app",
    config={
        "ASSETS_ENABLE": True,
        "ASSETS_AUTO_BUILD": True,
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

## i18n
FlaskSpark initializes Babel and provides a client-side translation endpoint:

```text
GET /_flaskspark/i18n?keys=Key%201,Key%202
```

## Configuration
Common keys:
```python
SECRET_KEY = "..."
SQLALCHEMY_DATABASE_URI = "sqlite:///instance/app.db"
APP_BIND_HOST = "0.0.0.0"
APP_PORT = 5067
BABEL_DEFAULT_LOCALE = "en"
BABEL_SUPPORTED_LOCALES = ["en", "de"]
```

## License
MIT License. See `LICENSE`.
