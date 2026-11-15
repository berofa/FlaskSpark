"""The admins' settings (flaskspark.core.settings, «Settings»), the visitor's own settings, the core's tables and the
browser scripts, with the demo application of conftest.py (OpenAccess: everyone is an admin)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from flaskspark.core import config, db, modules, settings
from flaskspark.core.models import StoredSetting
from flaskspark.core.settings import Setting, SettingError

JS = Path(__file__).resolve().parents[2] / "flaskspark" / "core" / "web" / "static" / "flaskspark" / "js"


@pytest.fixture()
def clean_settings(app):
    yield
    with db.session() as s:
        s.execute(db.delete(StoredSetting))
    settings.invalidate()


def test_paths_into_the_yaml():
    data = {"a": {"b": 1, 60: {"c": 2}}}
    assert settings.get(data, "a.b") == 1
    assert settings.get(data, "a.60.c") == 2
    assert settings.get(data, "a.x.y", "none") == "none"
    settings.put(data, "a.n.m", 3)
    assert data["a"]["n"] == {"m": 3}


def test_overlay_is_a_copy_and_leaves_protected_keys():
    data = {"demo": {"page_size": 20}, "modules": ["demo"]}
    out = settings.overlay(data, {"demo.page_size": 5, "modules": []})
    assert out == {"demo": {"page_size": 5}, "modules": ["demo"]}
    assert data["demo"]["page_size"] == 20


def test_a_setting_checks_its_definition():
    with pytest.raises(TypeError):
        Setting("demo.x", "X", "list")
    with pytest.raises(TypeError):
        Setting("modules", "Modules")
    with pytest.raises(TypeError):
        Setting("demo.c", "C", "choice")
    assert Setting("demo.c", "C", "choice", choices=("a", ("b", "Bee"))).options() == [("a", "a"), ("b", "Bee")]


@pytest.mark.parametrize("kind, raw, value", [
    ("int", "12", 12),
    ("int", 7, 7),
    ("float", "1,5", 1.5),
    ("bool", "on", True),
    ("bool", False, False),
    ("str", "  hello ", "hello"),
    ("int", "", None),
    ("str", None, None),
    ("text", " hello ", "hello"),
    ("time", "7:05", "07:05"),
    ("time", "off", "off"),
    ("ints", "1, 2,3", [1, 2, 3]),
    ("ints", [4, 5], [4, 5]),
    ("texts", "a, b c ,", ["a", "b c"]),
    ("json", '{"60": 3.0}', {"60": 3.0}),
    ("json", [1, {"a": 2}], [1, {"a": 2}]),
])
def test_clean_values(kind, raw, value):
    assert settings.clean(Setting("demo.x", "X", kind), raw) == value


@pytest.mark.parametrize("setting, raw", [
    (Setting("demo.x", "X", "int"), "1.5"),
    (Setting("demo.x", "X", "int"), True),
    (Setting("demo.x", "X", "int", min=1, max=10), "11"),
    (Setting("demo.x", "X", "float", min=0), "-1"),
    (Setting("demo.x", "X", "bool"), "maybe"),
    (Setting("demo.x", "X", "choice", choices=("a",)), "b"),
    (Setting("demo.x", "X", "time"), "24:00"),
    (Setting("demo.x", "X", "time"), "7:5"),
    (Setting("demo.x", "X", "time"), "noon"),
    (Setting("demo.x", "X", "ints"), "1, two"),
    (Setting("demo.x", "X", "ints", min=1, max=5), "1, 6"),
    (Setting("demo.x", "X", "json"), "{broken"),
    (Setting("demo.x", "X", "json"), "3"),
])
def test_clean_refuses(setting, raw):
    with pytest.raises(SettingError) as error:
        settings.clean(setting, raw)
    assert "«X»" in str(error.value)


def test_save_overlays_config_and_keeps_the_defaults(app, clean_settings):
    module = modules.get(config.load(), "demo")
    changed = settings.save(module.CONFIG, {"demo.page_size": "5", "demo.title": ""}, user_id=0)
    assert changed == ["demo.page_size"]
    cfg = config.load()
    assert cfg.section("demo")["page_size"] == 5
    assert cfg.defaults["demo"]["page_size"] == 20
    assert config.load().modules == ("demo",)
    # one wrong value stores none
    with pytest.raises(SettingError):
        settings.save(module.CONFIG, {"demo.title": "New", "demo.page_size": "0"})
    assert config.load().section("demo")["title"] == "Notes"
    with pytest.raises(SettingError):
        settings.save(module.CONFIG, {"demo.unknown": "1"})
    # empty: the default again
    assert settings.save(module.CONFIG, {"demo.page_size": None}) == ["demo.page_size"]
    assert config.load().section("demo")["page_size"] == 20


def test_other_processes_see_changes_after_the_check_interval(app, clean_settings, monkeypatch):
    assert config.load().section("demo")["title"] == "Notes"
    with db.session() as s:  # another process writes
        s.add(StoredSetting(path="demo.title", value='"Elsewhere"'))
    monkeypatch.setattr(settings, "CHECK_SECONDS", 3600)
    assert config.load().section("demo")["title"] == "Notes"  # cached
    monkeypatch.setattr(settings, "CHECK_SECONDS", 0)
    assert config.load().section("demo")["title"] == "Elsewhere"


def test_settings_page_has_a_tab_per_module(client):
    html = client.get("/settings").get_data(as_text=True)
    # the demo module declares dashboards: its settings are in the tab «Dashboards», not in a tab of their own
    assert 'data-settings-screen-module="demo"' in html and "data-settings-form" in html
    assert 'name="demo.page_size"' in html and 'min="1"' in html and 'max="100"' in html
    assert "<ui-check switch" in html and "<ui-select" in html and "Newest first" in html
    assert 'name="access"' not in html  # no sign-in: no matrix
    assert "flaskspark/js/settings.js" in html


def test_settings_page_is_in_the_sidebar_for_admins(client):
    html = client.get("/").get_data(as_text=True)
    assert 'href="/settings"' in html


def test_settings_api(client, clean_settings):
    data = client.get("/api/settings/config/demo").get_json()
    by_path = {s["path"]: s for s in data["settings"]}
    assert by_path["demo.page_size"]["default"] == 20 and by_path["demo.page_size"]["value"] is None
    assert by_path["demo.sort"]["choices"][0] == {"value": "new", "label": "Newest first"}

    response = client.post("/api/settings/config/demo", json={"values": {"demo.archive": "true", "demo.sort": "old"}})
    assert response.status_code == 200
    data = response.get_json()
    assert sorted(data["changed"]) == ["demo.archive", "demo.sort"]
    assert data["restart"] == [{"name": "push", "label": "Live channel"}]
    assert "restart" in data["message"]
    assert config.load().section("demo")["archive"] is True

    response = client.post("/api/settings/config/demo", json={"values": {"demo.page_size": "500"}})
    assert response.status_code == 400
    assert "between 1 and 100" in response.get_json()["error"]
    assert client.post("/api/settings/config/demo", json={"values": {}}).get_json()["message"] == "Nothing changed."
    assert client.post("/api/settings/config/unknown", json={"values": {}}).status_code == 404
    assert client.get("/api/settings/access", headers={"Accept": "application/json"}).status_code == 404


def test_settings_page_marks_changed_values(client, clean_settings):
    client.post("/api/settings/config/demo", json={"values": {"demo.title": "Mine"}})
    html = client.get("/settings").get_data(as_text=True)
    assert 'data-reset="demo.title"' in html and 'value="Mine"' in html


def test_user_settings_without_sign_in_live_in_the_session(app, client):
    assert client.get("/api/user-settings/demo.columns").get_json() == {"key": "demo.columns", "value": {}}
    response = client.put("/api/user-settings/demo.columns", json={"value": {"shown": ["a", "b"]}})
    assert response.status_code == 200
    assert client.get("/api/user-settings/demo.columns").get_json()["value"] == {"shown": ["a", "b"]}
    other = app.test_client()
    assert other.get("/api/user-settings/demo.columns").get_json()["value"] == {}
    assert client.put("/api/user-settings/demo.columns", json={"value": [1]}).status_code == 400
    assert client.get("/api/user-settings/bad key").status_code == 404


def test_core_manifest_names_its_tables(app):
    core = modules.get(config.load(), "core")
    assert set(core.TABLES) == {"core_settings", "core_role_area", "core_user_settings", "core_user_role",
                                "core_module_chains", "core_accounts", "core_account_types", "core_shares",
                                "core_share_members", "core_share_notices", "core_attachments"}
    assert set(core.TABLES) <= set(db.load_models().tables)


def test_migration_helper(app):
    from flaskspark.core.db import migrations

    with app.app_context():
        tables = migrations.metadata()
    assert len(tables) == 2 and "core_settings" in tables[1].tables
    assert migrations.missing() == []


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize("script", sorted(p.name for p in JS.glob("*.js")))
def test_browser_scripts_parse(script):
    result = subprocess.run(["node", "--check", str(JS / script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_a_stored_structure_takes_the_number_keys_of_its_default():
    data = {"demo": {"ratios": {60: 3.0, 240: 2.0}, "names": {"a": 1}}}
    out = settings.overlay(data, {"demo.ratios": {"60": 4.0, "15": 1.0}, "demo.names": {"1": 2}})
    assert out["demo"]["ratios"] == {60: 4.0, 15: 1.0}
    assert out["demo"]["names"] == {"1": 2}  # the default has text keys: they stay
    assert data["demo"]["ratios"] == {60: 3.0, 240: 2.0}


def test_the_form_shows_lists_and_structures():
    from flaskspark.core.web.views.settings import _shown

    assert _shown([1, 2], "ints") == "1, 2" and _shown(["a", "b"], "texts") == "a, b"
    assert _shown({"a": [1]}, "json") == '{"a": [1]}' and _shown([1], "json") == "[1]"
    assert _shown("07:00", "time") == "07:00"


def test_settings_page_shows_times_lists_and_json(client, clean_settings):
    html = client.get("/settings").get_data(as_text=True)
    assert 'name="demo.quiet_from"' in html and 'placeholder="22:00"' in html
    assert 'placeholder="10, 20"' in html
    assert '<ui-textarea name="demo.ratios"' in html and "&#34;60&#34;: 3.0" in html
    response = client.post("/api/settings/config/demo", json={"values": {"demo.sizes": "5, 50",
                                                                         "demo.ratios": '{"60": 4.5}'}})
    assert response.status_code == 200
    section = config.load().section("demo")
    assert section["sizes"] == [5, 50] and section["ratios"] == {60: 4.5}
    assert 'value="5, 50"' in client.get("/settings").get_data(as_text=True)


# --- «Data»: what modules no longer delivered left behind (flaskspark.core.leftovers) ----------------------------
def _stray(name: str, create: bool = True) -> None:
    import sqlite3

    con = sqlite3.connect(db.default_url().removeprefix("sqlite:///"))
    try:
        con.execute(f"CREATE TABLE {name} (id INTEGER PRIMARY KEY)" if create else f"DROP TABLE IF EXISTS {name}")
        if create:
            con.execute(f"INSERT INTO {name} VALUES (1)")
        con.commit()
    finally:
        con.close()


def test_the_data_tab_lists_the_leftovers_and_cleans_them_up(client):
    html = client.get("/settings").get_data(as_text=True)
    assert 'name="data"' in html and "data-leftovers-empty" in html
    _stray("stray_api")
    try:
        html = client.get("/settings").get_data(as_text=True)
        assert 'data-leftover="table:stray_api"' in html and "Table no module describes" in html
        assert "table stray_api (1 row)" in html  # what the confirmation lists
        data = client.get("/api/settings/data").get_json()
        assert [i["id"] for i in data["items"]] == ["table:stray_api"]

        assert client.post("/api/settings/data", json={"items": []}).status_code == 400
        assert client.post("/api/settings/data", json={"items": ["table:core_settings"]}).status_code == 400
        response = client.post("/api/settings/data", json={"items": ["table:stray_api"]})
        assert response.status_code == 200, response.get_json()
        data = response.get_json()
        assert data["removed"] == ["table:stray_api"] and data["items"] == []
        assert data["backup"]["db"] in data["message"] and Path(data["backup"]["db"]).is_file()
        assert "stray_api" not in db.table_names()
    finally:
        _stray("stray_api", create=False)


def test_the_data_tab_in_german(client):
    _stray("stray_de")
    try:
        html = client.get("/settings", headers={"Accept-Language": "de"}).get_data(as_text=True)
        assert "Daten" in html and "Tabelle, die kein Modul beschreibt" in html
    finally:
        _stray("stray_de", create=False)
