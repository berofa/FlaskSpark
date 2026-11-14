"""Sign-in and role x area (flaskspark.core.web.access.RoleAccess) with a second web app of the demo application
(web/app_sso, auth "oauth"). No identity provider is contacted: a test signs a user in by putting what FlaskSpark's
OAuth callback leaves in the session (session["user"]) there itself."""
from __future__ import annotations

import pytest

from tests.core.sso import client_for, sso_app


@pytest.fixture(scope="module")
def sso(app):
    """The web app with sign-in and its users: admin (Administrators), user and other (Users), guest (Guests)."""
    with sso_app() as sso_app_:
        yield sso_app_


def test_anonymous_pages_go_to_the_sign_in(sso):
    response = client_for(sso).get("/demo/notes")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"] and "next=" in response.headers["Location"]


def test_the_signed_in_user_is_loaded_without_legacy_warnings(sso):
    import warnings

    from sqlalchemy.exc import LegacyAPIWarning

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert client_for(sso, "user").get("/demo/notes").status_code == 200
    assert not [w for w in caught if issubclass(w.category, LegacyAPIWarning)]


def test_anonymous_background_requests_get_401(sso):
    client = client_for(sso)
    assert client.get("/api/push/session", headers={"Accept": "application/json"}).status_code == 401
    assert client.get("/demo/notes", headers={"Sec-Fetch-Mode": "cors"}).status_code == 401


def test_public_endpoints_need_no_sign_in(sso):
    client = client_for(sso)
    response = client.get("/auth/login")
    assert response.status_code == 302 and response.headers["Location"].startswith("https://idp.example/authorize")
    assert client.get("/theme/theme.css").status_code == 200
    assert client.post("/api/i18n", json={"keys": ["Home"]}).status_code == 200


def test_role_defaults_decide_the_areas(sso):
    user, guest = client_for(sso, "user"), client_for(sso, "guest")
    assert user.get("/demo/notes").status_code == 200
    page = user.get("/").get_data(as_text=True)
    assert 'href="/demo/notes"' in page
    assert 'href="/settings"' not in page  # not an admin
    denied = guest.get("/demo/notes")
    assert denied.status_code == 403 and "data-no-access" in denied.get_data(as_text=True)
    assert guest.get("/demo/notes", headers={"Accept": "application/json"}).status_code == 403
    # a guest has no area at all: the start page says so
    home = guest.get("/")
    assert home.status_code == 403 and "data-no-access" in home.get_data(as_text=True)


def test_admins_may_everything(sso):
    admin = client_for(sso, "admin")
    assert admin.get("/demo/notes").status_code == 200
    html = admin.get("/settings").get_data(as_text=True)
    assert 'name="access"' in html and 'data-area="demo"' in html and 'name="demo"' in html
    assert client_for(sso, "user").get("/settings").status_code == 403
    assert client_for(sso, "user").get("/api/settings/access", headers={"Accept": "application/json"}).status_code == 403
    # «Data»: what modules left behind, only for admins
    assert 'name="data"' in html
    assert admin.get("/api/settings/data").status_code == 200
    json_only = {"Accept": "application/json"}
    assert client_for(sso, "user").get("/api/settings/data", headers=json_only).status_code == 403
    assert client_for(sso, "user").post("/api/settings/data", json={"items": ["all"]}, headers=json_only).status_code == 403


def test_the_layout_names_the_user_and_signs_out(sso):
    html = client_for(sso, "user").get("/").get_data(as_text=True)
    assert "data-signed-in-user" in html and "user.demo" in html
    assert 'href="/auth/logout"' in html
    response = client_for(sso, "user").get("/auth/logout")
    assert response.status_code == 302 and response.headers["Location"] in ("/", "http://localhost/")


def test_access_matrix_api(sso):
    admin = client_for(sso, "admin")
    guests, admins = sso.test_roles["Guests"], sso.test_roles["Administrators"]
    data = admin.get("/api/settings/access").get_json()
    row = next(r for r in data["roles"] if r["id"] == guests)
    assert row["allowed"] == {"demo": False}
    assert data["areas"] == [{"key": "demo", "label": "Demo", "description": "The demo pages"}]

    response = admin.post("/api/settings/access", json={"role_id": guests, "area": "demo", "allowed": True})
    assert response.status_code == 200 and response.get_json()["message"] == "Saved."
    try:
        assert client_for(sso, "guest").get("/demo/notes").status_code == 200
        assert client_for(sso, "guest").get("/").status_code == 200
    finally:
        admin.post("/api/settings/access", json={"role_id": guests, "area": "demo", "allowed": False})
    assert client_for(sso, "guest").get("/demo/notes").status_code == 403

    refused = admin.post("/api/settings/access", json={"role_id": admins, "area": "demo", "allowed": False})
    assert refused.status_code == 400 and "Administrators" in refused.get_json()["error"]
    assert admin.post("/api/settings/access", json={"role_id": guests, "area": "nope", "allowed": True}).status_code == 400


def test_start_page_and_roles_with(sso):
    from flaskspark.core.web import EXTENSION, roles_with

    access = sso.extensions[EXTENSION]
    with sso.test_request_context("/"):
        from flask import session

        session["user"] = {"id": sso.test_users["user"]}
        assert access.permitted_areas() == ["demo"]
        assert access.start_page() == "/demo/notes"
        assert {r["name"] for r in roles_with("demo")} == {"Administrators", "Users"}


def test_push_session_names_the_signed_in_user(sso):
    data = client_for(sso, "user").get("/api/push/session").get_json()
    assert data["user"] == sso.test_users["user"] and "demo.state" in data["topics"]
    data = client_for(sso, "guest").get("/api/push/session").get_json()
    assert "demo.state" not in data["topics"]


def test_user_settings_follow_the_user(sso):
    first = client_for(sso, "user")
    assert first.put("/api/user-settings/demo.view", json={"value": {"rows": 5}}).status_code == 200
    assert client_for(sso, "user").get("/api/user-settings/demo.view").get_json()["value"] == {"rows": 5}
    assert client_for(sso, "admin").get("/api/user-settings/demo.view").get_json()["value"] == {}


def test_the_matrix_drops_cells_of_removed_roles(sso):
    from flaskspark import db as flask_db
    from flaskspark.core import db
    from flaskspark.core.models import RoleArea
    from flaskspark.core.web import EXTENSION
    from flaskspark.models.role import Role

    with sso.app_context():
        role = Role.get_or_create("Temporary")  # created when missing (the OAuth provider's role map)
        assert role.id is not None
        sso.extensions[EXTENSION].ensure_defaults()
        with db.session() as s:
            assert s.scalars(db.select(RoleArea).where(RoleArea.role_id == role.id)).first() is not None
        flask_db.session.delete(role)
        flask_db.session.commit()
        sso.extensions[EXTENSION].ensure_defaults()
        with db.session() as s:
            assert s.scalars(db.select(RoleArea).where(RoleArea.role_id == role.id)).first() is None


def test_the_open_app_keeps_its_access(client):
    # the app with sign-in lives in the same process: the demo app still has no sign-in
    assert client.get("/demo/notes").status_code == 200


# --- the role of a user set by hand («Settings › Users», core_user_role) ---------------------------------------------
def sign_in_again(sso, who: str, role_name: str) -> None:
    """What FlaskSpark's OAuth callback does: the role from the provider's groups, then login_user()."""
    from flask_login import login_user
    from flaskspark import db as flask_db
    from flaskspark.models.role import Role
    from flaskspark.models.user import User

    with sso.test_request_context("/auth/callback"):
        user = flask_db.session.get(User, sso.test_users[who])
        user.role = Role.query.filter_by(name=role_name).first()
        if hasattr(user, "admin"):  # the flag exists once FlaskSpark configured the user for OAuth
            user.admin = user.role.is_admin
        flask_db.session.commit()
        login_user(user)


def role_of(sso, who: str) -> tuple[str, bool]:
    from flaskspark import db as flask_db
    from flaskspark.models.user import User

    with sso.app_context():
        user = flask_db.session.get(User, sso.test_users[who])
        flask_db.session.refresh(user)
        return user.role.name, bool(user.is_admin)


def test_an_admin_sets_a_users_role_and_it_survives_the_next_sign_in(sso):
    admin = client_for(sso, "admin")
    guest_id, users_role = sso.test_users["guest"], sso.test_roles["Users"]
    assert client_for(sso, "guest").get("/demo/notes").status_code == 403
    response = admin.post("/api/settings/users", json={"user_id": guest_id, "role_id": users_role})
    assert response.status_code == 200 and response.get_json()["message"] == "Saved."
    try:
        row = next(u for u in response.get_json()["users"] if u["id"] == guest_id)
        assert (row["role"], row["override"], row["sso_role"]) == ("Users", users_role, "Guests")
        assert client_for(sso, "guest").get("/demo/notes").status_code == 200  # at once
        sign_in_again(sso, "guest", "Guests")  # the provider still says Guests
        assert role_of(sso, "guest") == ("Users", False)
        sign_in_again(sso, "guest", "Users")  # the provider's role changed meanwhile: remembered for later
        row = next(u for u in admin.get("/api/settings/users").get_json()["users"] if u["id"] == guest_id)
        assert row["sso_role"] == "Users" and row["override"] == users_role
    finally:
        response = admin.post("/api/settings/users", json={"user_id": guest_id, "role_id": None})
    assert response.status_code == 200
    row = next(u for u in response.get_json()["users"] if u["id"] == guest_id)
    assert row["override"] is None and row["role"] == "Users"  # back to the sign-in's last role
    sign_in_again(sso, "guest", "Guests")
    assert role_of(sso, "guest") == ("Guests", False)


def test_a_role_set_by_hand_carries_its_admin_flag(sso):
    admin = client_for(sso, "admin")
    guest_id = sso.test_users["guest"]
    admin.post("/api/settings/users", json={"user_id": guest_id, "role_id": sso.test_roles["Administrators"]})
    try:
        assert role_of(sso, "guest") == ("Administrators", True)
        assert client_for(sso, "guest").get("/settings").status_code == 200
    finally:
        admin.post("/api/settings/users", json={"user_id": guest_id, "role_id": None})
    assert role_of(sso, "guest") == ("Guests", False)
    assert client_for(sso, "guest").get("/settings").status_code == 403


def test_the_users_api_refuses_what_it_must(sso):
    admin = client_for(sso, "admin")
    own = admin.post("/api/settings/users", json={"user_id": sso.test_users["admin"], "role_id": None})
    assert own.status_code == 400 and own.get_json()["error"] == "You can't change your own role."
    assert admin.post("/api/settings/users", json={"user_id": 9999, "role_id": None}).get_json()["error"] == \
        "Unknown user."
    unknown = admin.post("/api/settings/users", json={"user_id": sso.test_users["guest"], "role_id": 9999})
    assert unknown.status_code == 400 and unknown.get_json()["error"] == "Unknown role."
    user = client_for(sso, "user")
    assert user.get("/api/settings/users", headers={"Accept": "application/json"}).status_code == 403
    data = admin.get("/api/settings/users").get_json()
    assert {u["username"] for u in data["users"]} >= {"admin.demo", "user.demo", "guest.demo"}
    assert {r["name"] for r in data["roles"]} >= {"Administrators", "Users", "Guests"}


def test_the_settings_page_has_a_users_tab(sso):
    html = client_for(sso, "admin").get("/settings").get_data(as_text=True)
    assert 'name="users"' in html and f'data-user="{sso.test_users["guest"]}"' in html
    own = html.split(f'data-user="{sso.test_users["admin"]}"')[1].split(">")[0]
    assert "disabled" in own  # not one's own role


def test_the_open_app_has_no_users(client):
    assert 'name="users"' not in client.get("/settings").get_data(as_text=True)
    assert client.get("/api/settings/users").status_code == 404


def test_nav_badges_follow_their_area(sso):
    html = client_for(sso, "user").get("/demo/notes").get_data(as_text=True)
    spans = [part.split('"')[0] for part in html.split('data-nav-badge="')[1:]]
    assert spans == ["demo-new", "demo-open"]  # not the one of the admins
