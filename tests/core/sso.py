"""The demo application's second web app with sign-in (web/app_sso, auth "oauth") for the tests that need users and
roles. No identity provider is contacted: a test signs a user in by putting what FlaskSpark's OAuth callback leaves
in the session (session["user"]) there itself."""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager

import pytest

from tests.core.conftest import ROOT

OAUTH = {
    "OAUTH_NAME": "idp",
    "OAUTH_AUTHORIZE_URL": "https://idp.example/authorize",
    "OAUTH_ACCESS_TOKEN_URL": "https://idp.example/token",
    "OAUTH_USERINFO_ENDPOINT": "https://idp.example/userinfo",
    "OAUTH_JWKS_URI": "https://idp.example/jwks",
    "OAUTH_CLIENT_ID": "client",
    "OAUTH_CLIENT_SECRET": "secret",
    "OAUTH_SCOPE": "openid",
}

#: test user -> role (FlaskSpark's default roles)
USERS = (("admin", "Administrators"), ("user", "Users"), ("other", "Users"), ("guest", "Guests"))


@contextmanager
def sso_app():
    """The web app with sign-in and the users of USERS (created once; the database outlives the app)."""
    from flaskspark import FlaskSpark, db as flask_db
    from flaskspark.core.web.app import create

    cwd = os.getcwd()
    os.chdir(ROOT / "web")
    sys.path.insert(0, str(ROOT / "web"))
    try:
        with pytest.MonkeyPatch.context() as mp:
            # FlaskSpark stops a start without its tables (users, roles); they are created right after.
            mp.setattr(FlaskSpark, "_check_database", lambda self: None)
            _, app = create("app_sso", extra_config=OAUTH, auth="oauth")
    finally:
        os.chdir(cwd)
        sys.path.remove(str(ROOT / "web"))
        for name in [m for m in sys.modules if m == "app_sso" or m.startswith("app_sso.")]:
            del sys.modules[name]
    app.config.update(TESTING=True)
    from flaskspark.core.web import EXTENSION
    from flaskspark.models.role import Role
    from flaskspark.models.user import User

    with app.app_context():
        flask_db.create_all()
        app.extensions[EXTENSION].ensure_defaults()
        roles = {r.name: r for r in Role.query.all()}
        users = {}
        for name, role in USERS:
            user = User.query.filter_by(username=f"{name}.demo").first()
            if user is None:
                user = User(username=f"{name}.demo", email=f"{name}@example.org", role=roles[role])
                flask_db.session.add(user)
            user.role = roles[role]
            users[name] = user
        flask_db.session.commit()
        app.test_users = {name: u.id for name, u in users.items()}
        app.test_roles = {name: r.id for name, r in roles.items()}
    try:
        yield app
    finally:
        # FlaskSpark apps built later without sign-in must not ask for these tables.
        for table in ("user", "roles"):
            if table in flask_db.metadata.tables:
                flask_db.metadata.remove(flask_db.metadata.tables[table])


def client_for(app, who: str | None = None):
    client = app.test_client()
    client.environ_base["HTTP_ACCEPT_LANGUAGE"] = "en"
    if who:
        with client.session_transaction() as session:
            session["user"] = {"id": app.test_users[who]}
    return client
