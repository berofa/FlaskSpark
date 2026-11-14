"""Attachments (flaskspark.core.attachments): the demo module's notes have files (NoteFiles: the rights of the note's
shares). Upload, thumbnails (skipped without Pillow / pypdfium2), the size limit, the rights of other users, deleting
with the item, the backups."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from tests.core.sso import client_for, sso_app


def _png(size=(64, 48), color=(200, 30, 30)) -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", size, color).save(out, "PNG")
    return out.getvalue()


def _pdf() -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (200, 280), (255, 255, 255)).save(out, "PDF")
    return out.getvalue()


@pytest.fixture(scope="module")
def sso(app):
    with sso_app() as found:
        yield found


def _note(owner_id: int, text: str = "Holiday") -> int:
    from flaskspark.core import db
    from modules.demo.models import Note

    with db.for_module("demo").session() as s:
        row = Note(text=text, owner_id=owner_id)
        s.add(row)
        s.flush()
        return row.id


@pytest.fixture()
def note(app):
    """A note of the anonymous visitor (user 0: the app without sign-in)."""
    note_id = _note(0)
    yield note_id
    from flaskspark.core import attachments

    attachments.delete_for("note", note_id)


def _upload(client, note_id: int, data: bytes, name: str, mime: str = "", **headers):
    return client.post(f"/api/attachments/note/{note_id}", data=data,
                       headers={"X-File-Name": name, "Content-Type": mime or "application/octet-stream", **headers})


def test_upload_list_change_and_delete(client, note):
    from flaskspark.core import attachments, paths

    response = _upload(client, note, b"hello world", "Read%20me.txt", "text/plain")
    assert response.status_code == 200, response.get_json()
    att = response.get_json()["attachment"]
    assert (att["title"], att["name"], att["kind"], att["size"], att["mime"]) == \
        ("Read me", "Read me.txt", "document", 11, "text/plain")
    data = client.get(f"/api/attachments/note/{note}").get_json()
    assert data["ready"] and data["max_size"] == 100 * 1024 * 1024 and [a["id"] for a in data["attachments"]] == [att["id"]]

    (row,) = attachments.of_owner("note", note)
    stored = paths.STATE_DIR / "attachments" / "demo" / row.path
    assert stored.read_bytes() == b"hello world" and "Read me" not in row.path  # never the user's file name
    assert row.module == "demo"

    download = client.get(att["url"] + "&download=1")
    assert download.status_code == 200 and download.data == b"hello world"
    assert "attachment" in download.headers["Content-Disposition"]

    changed = client.post(f"/api/attachments/{att['id']}", json={"action": "update", "title": "Notes",
                                                                  "description": "first"})
    assert changed.get_json()["attachment"]["title"] == "Notes"
    assert client.post(f"/api/attachments/{att['id']}", json={"action": "update", "title": " "}).status_code == 400

    assert client.post(f"/api/attachments/{att['id']}", json={"action": "delete"}).get_json()["ok"]
    assert not stored.exists() and attachments.of_owner("note", note) == []


def test_html_is_never_shown_inline(client, note):
    att = _upload(client, note, b"<script>alert(1)</script>", "page.html", "text/html").get_json()["attachment"]
    response = client.get(att["url"])
    assert response.headers["Content-Type"] == "application/octet-stream"
    assert "attachment" in response.headers["Content-Disposition"]


def test_order(client, note):
    ids = [_upload(client, note, f"file {n}".encode(), f"{n}.txt", "text/plain").get_json()["attachment"]["id"]
           for n in range(3)]
    data = client.post(f"/api/attachments/note/{note}/order", json={"ids": [ids[2], ids[0]]}).get_json()
    assert [a["id"] for a in data["attachments"]] == [ids[2], ids[0], ids[1]]


def test_an_empty_or_too_large_file_is_refused(client, note, monkeypatch):
    from flaskspark.core import attachments, paths

    assert _upload(client, note, b"", "empty.txt").status_code == 400
    monkeypatch.setattr(attachments, "max_size", lambda cfg=None: 10)
    response = _upload(client, note, b"x" * 11, "big.bin")
    assert response.status_code == 413 and "too large" in response.get_json()["error"]
    # the streamed check, without a Content-Length: nothing stays on the disk
    stream = io.BytesIO(b"y" * 4096)
    with pytest.raises(attachments.TooLarge):
        attachments.store(None, "note", note, stream, "big.bin")
    assert not list((paths.STATE_DIR / "attachments" / "demo").rglob("*.part"))
    assert attachments.of_owner("note", note) == []


def test_unknown_owner_types_and_items(client, note):
    assert client.get("/api/attachments/nothing/1").status_code == 404
    assert client.get("/api/attachments/note/999999").status_code == 404  # no such note: nobody owns it
    assert client.get("/attachments/999999/file").status_code == 404


def test_delete_for_removes_rows_and_files_after_the_commit(client, note):
    from flaskspark.core import attachments, db, paths

    _upload(client, note, b"one", "a.txt", "text/plain")
    _upload(client, note, b"two", "b.txt", "text/plain")
    files = [paths.STATE_DIR / "attachments" / "demo" / a.path for a in attachments.of_owner("note", note)]
    assert all(f.is_file() for f in files)
    with pytest.raises(RuntimeError):
        with db.for_module("demo").session() as s:
            assert attachments.delete_for("note", note, session=s) == 2
            raise RuntimeError("the module's deletion fails")
    assert all(f.is_file() for f in files) and len(attachments.of_owner("note", note)) == 2  # rolled back: all stays
    with db.for_module("demo").session() as s:
        attachments.delete_for("note", [note], session=s)
        assert all(f.is_file() for f in files)  # not before the commit
    assert not any(f.exists() for f in files) and attachments.of_owner("note", note) == []


def test_an_upload_in_a_session_that_rolls_back_leaves_no_file(app, note):
    from flaskspark.core import attachments, db, paths

    before = set((paths.STATE_DIR / "attachments" / "demo").rglob("*"))
    with pytest.raises(RuntimeError):
        with db.for_module("demo").session() as s:
            attachments.store(None, "note", note, io.BytesIO(b"data"), "x.txt", session=s)
            raise RuntimeError("the module's work fails")
    after = {p for p in (paths.STATE_DIR / "attachments" / "demo").rglob("*") if p.is_file()}
    assert after <= before and attachments.of_owner("note", note) == []


def test_thumbnails_of_images_and_pdfs(client, note):
    pytest.importorskip("PIL")
    pytest.importorskip("pypdfium2")
    from flaskspark.core import attachments

    image = _upload(client, note, _png(), "photo.png", "image/png").get_json()["attachment"]
    assert image["kind"] == "image" and image["thumb"]
    response = client.get(image["thumb"])
    assert response.status_code == 200 and response.mimetype == "image/webp"
    pdf = _upload(client, note, _pdf(), "scan.pdf", "application/pdf").get_json()["attachment"]
    assert pdf["kind"] == "document" and pdf["thumb"]
    assert client.get(pdf["url"]).mimetype == "application/pdf"
    text = _upload(client, note, b"plain", "plain.txt", "text/plain").get_json()["attachment"]
    assert text["thumb"] is None
    assert client.get(f"/attachments/{text['id']}/thumb").status_code == 404
    thumbs = attachments.thumbs_dir()
    assert (thumbs / f"{image['id']}.webp").is_file() and (thumbs / ".nobackup").is_file()
    assert attachments.first_images("note", [note]) == {note: image["thumb"]}


def test_without_pillow_there_is_no_thumbnail_but_the_file_is_kept(client, note, monkeypatch):
    import builtins

    real = builtins.__import__

    def without_pil(name, *args, **kwargs):
        if name == "PIL" or name.startswith("PIL."):
            raise ImportError("no Pillow")
        return real(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_pil)
    response = _upload(client, note, b"\x89PNG not really", "photo.png", "image/png")
    assert response.status_code == 200 and response.get_json()["attachment"]["thumb"] is None


def test_the_rights_follow_the_shares(sso):
    from flaskspark.core import attachments, shares

    users, roles = sso.test_users, sso.test_roles
    note_id = _note(users["user"], "Shared note")
    try:
        owner, other, admin = client_for(sso, "user"), client_for(sso, "other"), client_for(sso, "admin")
        att = _upload(owner, note_id, b"secret", "s.txt", "text/plain").get_json()["attachment"]
        assert other.get(f"/api/attachments/note/{note_id}").status_code == 404
        assert other.get(att["url"]).status_code == 404
        assert client_for(sso, "guest").get(f"/api/attachments/note/{note_id}").status_code == 403  # no area

        shares.set_targets("note", note_id, users["user"], {roles["Users"]: "read",
                                                           roles["Administrators"]: "write"})
        assert other.get(att["url"]).data == b"secret"
        assert _upload(other, note_id, b"x", "x.txt").status_code == 404  # read only
        assert other.post(f"/api/attachments/{att['id']}", json={"action": "delete"}).status_code == 404
        assert _upload(admin, note_id, b"from admin", "y.txt", "text/plain").status_code == 200
    finally:
        attachments.delete_for("note", note_id)
        shares.forget("note", note_id)


def test_a_modules_own_session_and_configuration(app, note, tmp_path):
    """Everything in the module's session (the row not committed yet: only that session sees it), and the storage of
    the configuration handed over (cfg) also when the files are removed."""
    from flaskspark.core import attachments, db
    from flaskspark.core.config import Config

    cfg = Config({"attachments": {"stores": {"demo": str(tmp_path / "files")}}})
    with db.for_module("demo").session() as s:
        att = attachments.store(None, "note", note, io.BytesIO(b"abc"), "a.txt", cfg=cfg, session=s)
        assert attachments.attachment_of(None, att.id, session=s).id == att.id
        attachments.update(None, att.id, {"title": "Renamed"}, cfg=cfg, session=s)
        assert attachments.attachment_of(None, att.id, session=s).title == "Renamed"
    stored = tmp_path / "files" / att.path
    assert stored.is_file()
    with db.for_module("demo").session() as s:
        attachments.delete(None, att.id, cfg=cfg, session=s)
        assert stored.is_file()  # until the commit
    assert not stored.exists()
    assert attachments.tidy("note", cfg=cfg) == 0


def test_the_storage_of_a_store_and_its_marker(tmp_path):
    from flaskspark.core import attachments
    from flaskspark.core.config import Config

    cfg = Config({"attachments": {"dir": str(tmp_path), "require_marker": True, "max_size_mb": 2}})
    st = attachments.storage("demo", cfg)
    assert st.root == tmp_path / "demo" and not st.ready()
    with pytest.raises(attachments.StorageUnavailable):
        st.require()
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / attachments.MARKER).touch()
    assert st.ready() and attachments.max_size(cfg) == 2 * 1024 * 1024
    explicit = Config({"attachments": {"stores": {"demo": str(tmp_path / "elsewhere")}}})
    assert attachments.storage("demo", explicit).root == tmp_path / "elsewhere"


def test_the_backup_keeps_the_attachments_but_not_the_thumbnails(tmp_path):
    import tarfile

    from flaskspark.core import backup

    state = tmp_path / "state"
    (state / "attachments" / "demo" / "2026" / "11").mkdir(parents=True)
    (state / "attachments" / "demo" / "2026" / "11" / "f.txt").write_text("kept")
    (state / "attachments" / ".thumbs").mkdir()
    (state / "attachments" / ".thumbs" / backup.NOBACKUP).touch()
    (state / "attachments" / ".thumbs" / "1.webp").write_text("regenerable")
    out = backup.backup_state(state, tmp_path / "backups", backup.stamp())
    with tarfile.open(out) as tar:
        names = set(tar.getnames())
    assert "state/attachments/demo/2026/11/f.txt" in names
    assert not any(".thumbs" in n for n in names)


def test_the_script_is_served(client):
    response = client.get("/static/flaskspark/js/ui-attachments.js")
    assert response.status_code == 200 and b'registerComponent("ui-attachments"' in response.data


def test_an_owner_without_checks_lets_no_one_in(app):
    from flaskspark.core import attachments

    class Closed(attachments.AttachmentOwner):
        TYPE = "closed-test"

    attachments.register(Closed())
    try:
        with pytest.raises(attachments.NotFound):
            attachments.check(0, "closed-test", 1)
    finally:
        attachments._registered.pop("closed-test", None)
        attachments._cache.clear()


def test_paths_never_leave_the_store(app, tmp_path):
    from flaskspark.core import attachments

    st = attachments.Storage(tmp_path / "store", tmp_path / "thumbs")

    class Row:
        id, path = 1, "../../etc/passwd"

    with pytest.raises(attachments.NotFound):
        st.original(Row())
    assert Path(tmp_path / "store").is_dir()
