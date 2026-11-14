"""Sharing (flaskspark.core.shares): the demo module's notes (NoteShareable, area "demo": the roles Users and
Administrators may use it, Guests may not) shared with roles, the access matrix, joining, notices, the API."""
from __future__ import annotations

import pytest

from tests.core.sso import client_for, sso_app


@pytest.fixture(scope="module")
def sso(app):
    with sso_app() as found:
        yield found


@pytest.fixture()
def note(sso):
    """A note of «user» (no shares yet), gone afterwards with its shares."""
    from flaskspark.core import db, shares
    from modules.demo.models import Note

    with db.for_module("demo").session() as s:
        row = Note(text="Shopping", owner_id=sso.test_users["user"])
        s.add(row)
        s.flush()
        note_id = row.id
    yield note_id
    shares.forget("note", note_id)
    with db.for_module("demo").session() as s:
        s.execute(db.delete(Note).where(Note.id == note_id))


def _ids(sso):
    return sso.test_users, sso.test_roles


def test_the_registry_has_the_modules_and_the_cores_kinds(app):
    from flaskspark.core import shares

    found = shares.registry()
    assert found["note"].MODULE == "demo" and found["account"].MODULE == "core"
    with pytest.raises(shares.ShareError):
        shares.get("nothing")


def test_access_matrix(sso, note):
    from flaskspark.core import shares

    users, roles = _ids(sso)
    assert shares.access(users["user"], "note", note) == shares.OWNER
    assert shares.access(users["other"], "note", note) is None
    assert shares.access(users["admin"], "note", note) is None
    assert shares.access(users["user"], "note", 999999) is None  # unknown item

    shares.set_targets("note", note, users["user"], {roles["Users"]: "read"})
    assert shares.access(users["other"], "note", note) == shares.READ
    assert shares.can_read(users["other"], "note", note) and not shares.can_write(users["other"], "note", note)
    assert shares.access(users["admin"], "note", note) is None  # another role
    assert shares.shared_with(users["other"], "note") == {note: "read"}
    assert shares.shared_with(users["user"], "note") == {}  # one's own is not «shared with»

    shares.grant("note", note, roles["Administrators"], "write", owner_id=users["user"])
    assert shares.can_write(users["admin"], "note", note)
    assert shares.targets("note", note) == {roles["Users"]: "read", roles["Administrators"]: "write"}
    assert shares.audience("note", note) == {users["user"], users["other"], users["admin"]}

    shares.revoke("note", note, roles["Users"], owner_id=users["user"])
    assert shares.access(users["other"], "note", note) is None
    assert shares.can_write(users["admin"], "note", note)


def test_only_the_owner_shares_and_only_with_roles_of_the_area(sso, note):
    from flaskspark.core import shares

    users, roles = _ids(sso)
    with pytest.raises(shares.ShareError, match="owner"):
        shares.set_targets("note", note, users["other"], {roles["Users"]: "read"})
    with pytest.raises(shares.ShareError, match="role"):
        shares.set_targets("note", note, users["user"], {roles["Guests"]: "read"})  # Guests may not use «demo»
    with pytest.raises(shares.ShareError, match="permission"):
        shares.set_targets("note", note, users["user"], {roles["Users"]: "admin"})
    assert {r["name"] for r in shares.dialog("note", note, users["user"])["roles"]} == {"Administrators", "Users"}


def test_a_share_that_ends_leaves_a_notice_once_for_who_joined(sso, note, monkeypatch):
    from flaskspark.core import shares

    users, roles = _ids(sso)
    monkeypatch.setattr(shares.get("note"), "JOINS", True)
    shares.set_targets("note", note, users["user"], {roles["Users"]: "write"})
    assert shares.access(users["other"], "note", note) is None  # invited, not joined yet
    assert [i["status"] for i in shares.invitations(users["other"], "note")] == [shares.INVITED]
    shares.join(users["other"], "note", note)
    assert shares.access(users["other"], "note", note) == shares.WRITE
    shares.leave(users["other"], "note", note)
    assert shares.access(users["other"], "note", note) is None
    shares.join(users["other"], "note", note)
    with pytest.raises(shares.ShareError):
        shares.join(users["admin"], "note", note)  # not invited

    shares.set_targets("note", note, users["user"], {})
    assert shares.access(users["other"], "note", note) is None
    assert shares.take_notices(users["other"], "note") == ["«Shopping» is no longer shared by user.demo."]
    assert shares.take_notices(users["other"], "note") == []


def test_forget_drops_every_row_of_an_item(sso, note):
    from flaskspark.core import db, shares
    from flaskspark.core.models import Share

    users, roles = _ids(sso)
    shares.set_targets("note", note, users["user"], {roles["Users"]: "read"})
    shares.forget("note", note)
    with db.session() as s:
        assert s.scalars(db.select(Share).filter_by(object_type="note", object_id=note)).first() is None


def test_a_modules_session_keeps_its_rights_and_reaches_the_shares(sso, note):
    from flaskspark.core import db, shares
    from flaskspark.core.models import Share

    users, roles = _ids(sso)
    with db.for_module("demo").session() as s:
        shares.set_targets("note", note, users["user"], {roles["Users"]: "read"}, session=s)
        assert shares.can_read(users["other"], "note", note, session=s)
        with pytest.raises(db.DatabaseAccessError):
            s.scalars(db.select(Share)).all()  # the core's table: only through the API


def test_the_share_api(sso, note):
    users, roles = _ids(sso)
    owner, other = client_for(sso, "user"), client_for(sso, "other")
    data = owner.get(f"/api/shares/note/{note}").get_json()
    assert data["name"] == "Shopping" and data["shares"] == {} and data["label"] == "Note"
    assert other.get(f"/api/shares/note/{note}").status_code == 404  # not the owner
    response = owner.post(f"/api/shares/note/{note}", json={"shares": {str(roles["Users"]): "write"}})
    assert response.status_code == 200 and response.get_json()["shares"] == {str(roles["Users"]): "write"}
    assert [m["username"] for m in response.get_json()["members"]] == ["other.demo"]
    assert other.get("/api/shares/note").get_json()["invitations"][0]["id"] == note
    assert owner.post(f"/api/shares/note/{note}", json={"shares": {str(roles["Guests"]): "read"}}).status_code == 400
    assert client_for(sso, "guest").get(f"/api/shares/note/{note}").status_code == 404  # no area «demo»
    assert owner.get("/api/shares/nothing/1").status_code == 404


def test_sharing_needs_a_sign_in(client):
    response = client.get("/api/shares/note/1")
    assert response.status_code == 404 and "sign-in" in response.get_json()["error"]


def test_the_share_dialog_script_is_served(client):
    response = client.get("/static/flaskspark/js/ui-share-dialog.js")
    assert response.status_code == 200 and b'registerComponent("ui-share-dialog"' in response.data


def test_messages_come_in_the_visitors_language(client):
    response = client.get("/api/shares/note/1", headers={"Accept-Language": "de"})
    assert response.get_json()["error"] == "Teilen gibt es nur mit Anmeldung."


def test_the_dialog_shows_the_kinds_label_in_the_visitors_language(sso, note):
    """Shareable.LABEL is an N_() source text: shares.dialog() translates it (also when a module calls it itself)."""
    from flaskspark.core import i18n, shares

    users, _roles = _ids(sso)
    assert shares.dialog("note", note, users["user"])["label"] == "Note"
    with i18n.using("de"):
        assert shares.dialog("note", note, users["user"])["label"] == "Hinweis"
    with sso.test_request_context("/", headers={"Accept-Language": "de"}):
        assert shares.dialog("note", note, users["user"])["label"] == "Hinweis"
    data = client_for(sso, "user").get(f"/api/shares/note/{note}", headers={"Accept-Language": "de",
                                                                          "Accept": "application/json"}).get_json()
    assert data["label"] == "Hinweis"
