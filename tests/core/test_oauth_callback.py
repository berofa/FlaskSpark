"""The OAuth callback: who signs in and with which role, from the claims of the identity provider (no provider is
contacted; the token and the userinfo answer are faked)."""
from __future__ import annotations

import pytest
from authlib.integrations.flask_client.apps import FlaskOAuth2App

from tests.core.sso import client_for, sso_app

#: the usernames the sign-ins of these tests create
SIGNED_IN = ("Anna", "bea", "carla.beispiel", "Dora")


@pytest.fixture(scope="module")
def sso(app):
    """The web app with sign-in (the demo application's app first: it creates the core tables)."""
    with sso_app() as sso_app_:
        yield sso_app_
        forget_signed_in_users(sso_app_)


def forget_signed_in_users(app):
    """Removes the users the sign-ins here created (the database outlives the app; other tests count the users)."""
    from flaskspark import db
    from flaskspark.core import db as core_db
    from flaskspark.core.models import UserRole
    from flaskspark.models.user import User

    with app.app_context():
        users = User.query.filter(User.username.in_(SIGNED_IN)).all()
        ids = [user.id for user in users]
        for user in users:
            db.session.delete(user)
        db.session.commit()
    with core_db.for_module("core").session() as s:
        s.query(UserRole).filter(UserRole.user_id.in_(ids)).delete()


@pytest.fixture
def provider(sso, monkeypatch):
    """Fakes the identity provider: `claims` are the ID token's, `userinfo` the userinfo endpoint's answer."""
    state = {"claims": {}, "userinfo": None, "userinfo_calls": 0}

    def authorize_access_token(self, **kwargs):
        return {"access_token": "token", "userinfo": dict(state["claims"])}

    class Answer:
        def raise_for_status(self):
            pass

        def json(self):
            return dict(state["userinfo"] or {})

    def get(self, url, **kwargs):
        # the userinfo request (authlib's userinfo() finds the endpoint in the client's server metadata)
        assert url == sso.config["OAUTH_USERINFO_ENDPOINT"]
        state["userinfo_calls"] += 1
        return Answer()

    monkeypatch.setattr(FlaskOAuth2App, "authorize_access_token", authorize_access_token)
    monkeypatch.setattr(FlaskOAuth2App, "get", get)
    saved = {key: sso.config.get(key) for key in ("OAUTH_USERNAME_CLAIM", "OAUTH_ROLE_PRIORITY", "OAUTH_ROLE_MAP")}
    yield state
    sso.config.update(saved)


def sign_in(app):
    client = client_for(app)
    assert client.get("/auth/login").status_code == 302
    with client.session_transaction() as session:
        state = session["oauth_state"]
    return client, client.get(f"/auth/callback?state={state}&code=code")


def signed_in_user(client):
    """What the callback left in the session: (username, first name, last name, email, role)."""
    with client.session_transaction() as session:
        user = session.get("user") or {}
    return user.get("username"), user.get("first_name"), user.get("last_name"), user.get("email"), user.get("role_name")


def test_a_gitlab_sign_in_takes_the_groups_from_the_userinfo_endpoint(sso, provider):
    # GitLab: no "username" claim, user names without a dot, the groups only from the userinfo endpoint
    sso.config.update(
        OAUTH_USERNAME_CLAIM="preferred_username",
        OAUTH_ROLE_PRIORITY=["staff"],
        OAUTH_ROLE_MAP={"staff": "Editors"},
    )
    provider["claims"] = {"sub": "14", "preferred_username": "Anna", "name": "Anna Muster",
                          "email": "anna@example.org"}
    provider["userinfo"] = {"sub": "14", "groups": ["staff", "staff/tools"]}

    client, response = sign_in(sso)

    assert response.status_code == 302
    assert provider["userinfo_calls"] == 1
    assert signed_in_user(client) == ("Anna", "Anna", "Muster", "anna@example.org", "Editors")


def test_given_and_family_name_win_over_the_full_name(sso, provider):
    sso.config.update(OAUTH_USERNAME_CLAIM="preferred_username")
    provider["claims"] = {"preferred_username": "bea", "name": "Bea van der Berg", "given_name": "Bea",
                          "family_name": "van der Berg", "email": "bea@example.org", "groups": []}

    client, response = sign_in(sso)

    assert response.status_code == 302
    assert signed_in_user(client)[:3] == ("bea", "Bea", "van der Berg")


def test_a_synology_sign_in_keeps_the_names_from_the_username(sso, provider):
    # Synology SSO: "username" as first.last, the groups in the ID token (no userinfo request)
    sso.config.update(OAUTH_ROLE_PRIORITY=["users"], OAUTH_ROLE_MAP={"users": "Users"})
    provider["claims"] = {"username": "carla.beispiel", "email": "carla@example.org", "groups": ["users"]}

    client, response = sign_in(sso)

    assert response.status_code == 302
    assert provider["userinfo_calls"] == 0
    assert signed_in_user(client) == ("carla.beispiel", "Carla", "Beispiel", "carla@example.org", "Users")


def test_a_sign_in_without_a_username_is_refused(sso, provider):
    provider["claims"] = {"email": "nobody@example.org", "groups": []}

    _, response = sign_in(sso)

    assert response.status_code == 400


def test_the_first_user_becomes_an_administrator(sso, provider):
    # without a group that names a role: the very first user is the administrator, everyone after a guest
    from flaskspark import db
    from flaskspark.models.user import User

    with sso.app_context():
        User.query.delete()  # the users of tests.core.sso come back with the next sso_app()
        db.session.commit()
    sso.config.update(OAUTH_USERNAME_CLAIM="preferred_username", OAUTH_ROLE_PRIORITY=[], OAUTH_ROLE_MAP={})
    provider["claims"] = {"preferred_username": "Dora", "email": "dora@example.org", "groups": []}

    client, response = sign_in(sso)

    assert response.status_code == 302
    assert signed_in_user(client)[4] == "Administrators"
