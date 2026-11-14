"""A new version of an application no longer delivers a module (tests/core/installed_app.py, «fsgone»): the start goes
on with a warning, the status tile names it, its tables and data stay, and it continues when it comes back. What it
left behind is listed and cleaned up (flaskspark.core.leftovers: «Settings › Data», `<app> data`), after a backup."""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from tests.core.installed_app import (
    KEEP_REVISION,
    KEEP_REVISION_2,
    OMEGA_REVISION,
    OMEGA_REVISION_2,
    add_revision,
    deliver,
    write_gone,
)


@pytest.fixture(scope="module")
def distribution(tmp_path_factory):
    """The distribution «fsgone» on sys.path for this module's tests, gone again afterwards (its packages are imported
    once: their tables are in the models' metadata)."""
    from flaskspark.core import modules

    path = write_gone(tmp_path_factory.mktemp("site"))
    sys.path.insert(0, str(path))
    modules.reset()
    yield path
    sys.path.remove(str(path))
    for name in [m for m in sys.modules if m == "fsgone" or m.startswith("fsgone.")]:
        sys.modules.pop(name)
    modules.reset()


@pytest.fixture()
def site(distribution):
    """Every test starts with the first version: keep and omega delivered, each with its first revision only."""
    from flaskspark.core import modules

    for later in (KEEP_REVISION_2, OMEGA_REVISION_2):
        for path in distribution.glob(f"fsgone/modules/*/migrations/versions/{later}_*.py"):
            path.unlink()
    deliver(distribution, "keep", "omega")
    modules.reset()
    yield distribution
    modules.reset()


@pytest.fixture()
def cfg(site, tmp_path):
    from flaskspark.core.config import Config

    return Config({"app": {"name": "fsgone"}, "auth": "none", "backup": {"dir": str(tmp_path / "backups")}})


@pytest.fixture()
def url(tmp_path, monkeypatch):
    """The test's own database, also the default one (the start, the status)."""
    from flaskspark.core import db

    found = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", found)
    yield found
    db.dispose()


@pytest.fixture()
def state_dir():
    """The state directory of omega (STATE_DIR/omega), removed afterwards."""
    from flaskspark.core import paths

    directory = paths.STATE_DIR / "omega"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "cache.json").write_text("{}")
    yield directory
    shutil.rmtree(directory, ignore_errors=True)


def _sql(url: str, *statements: str, args=()) -> list:
    con = sqlite3.connect(url.removeprefix("sqlite:///"))
    try:
        rows = []
        for statement in statements:
            rows = con.execute(statement, args).fetchall() if args else con.execute(statement).fetchall()
        con.commit()
        return rows
    finally:
        con.close()


def _tables(url: str) -> set[str]:
    return {r[0] for r in _sql(url, "SELECT name FROM sqlite_master WHERE type='table'")}


def _versions(url: str) -> set[str]:
    return {r[0] for r in _sql(url, "SELECT version_num FROM alembic_version")}


def _vanish(site, cfg, url):
    """omega in use (a row in its table), then a version of the application without it."""
    from flaskspark.core import modules
    from flaskspark.core.db import migrations

    migrations.upgrade(cfg, url)
    _sql(url, "INSERT INTO omega_entry (text) VALUES ('kept')")
    deliver(site, "keep")
    modules.reset()


# --- the start ----------------------------------------------------------------------------------------------------
def test_the_start_records_the_delivered_modules(cfg, url):
    from flaskspark.core.db import migrations

    migrations.upgrade(cfg, url)
    found = migrations.recorded(url)
    assert found["omega"]["revision"] == OMEGA_REVISION
    assert found["omega"]["tables"] == ["omega_entry", "omega_more"]
    assert found["omega"]["label"] == "Omega" and found["omega"]["version"] == "1.0"
    assert found["keep"]["revision"] == KEEP_REVISION


def test_a_module_no_longer_delivered_does_not_stop_the_start(site, cfg, url, caplog):
    from flaskspark.core import status
    from flaskspark.core.db import migrations

    _vanish(site, cfg, url)
    add_revision(site, "keep", KEEP_REVISION_2, KEEP_REVISION, "keep_more")  # the new version brings one of keep
    with caplog.at_level("WARNING"):
        result = migrations.upgrade(cfg, url)
    assert result["applied"] == {"keep": [KEEP_REVISION, KEEP_REVISION_2]}  # the delivered ones migrate as usual
    assert result["backup"]
    assert "module 'omega' is no longer delivered" in caplog.text and "omega_entry" in caplog.text
    assert any("omega" in w for w in result["warnings"])
    # nothing of omega touched: its revision, its table, its data, its record
    assert _versions(url) >= {OMEGA_REVISION, KEEP_REVISION_2}
    assert _sql(url, "SELECT text FROM omega_entry") == [("kept",)]
    assert migrations.recorded(url)["omega"]["revision"] == OMEGA_REVISION
    found = migrations.state(cfg, url)
    assert found.vanished == {"omega": {"revisions": [OMEGA_REVISION], "label": "Omega", "tables": ["omega_entry"]}}
    assert found.foreign == [] and found.pending == []

    migrations.upgrade_on_start(cfg)  # what the web service and the supervisor do: no SystemExit

    tile = status.collect(cfg, shown=[status.ModulesTile()])[0]
    assert ["omega", "no longer delivered: omega — its tables are kept"] in tile["details"]
    assert ["Database", "current"] in tile["details"]
    assert tile["level"] == "warning"


def test_a_module_that_comes_back_goes_on_where_it_stood(site, cfg, url):
    from flaskspark.core import modules
    from flaskspark.core.db import migrations

    _vanish(site, cfg, url)
    migrations.upgrade(cfg, url)
    deliver(site, "keep", "omega")
    add_revision(site, "omega", OMEGA_REVISION_2, OMEGA_REVISION, "omega_more")
    modules.reset()
    result = migrations.upgrade(cfg, url)
    assert result["applied"] == {"omega": [OMEGA_REVISION, OMEGA_REVISION_2]}
    assert _sql(url, "SELECT text FROM omega_entry") == [("kept",)]
    assert migrations.state(cfg, url).vanished == {}
    assert migrations.recorded(url)["omega"]["revision"] == OMEGA_REVISION_2


def test_a_revision_of_no_known_module_is_left_alone(cfg, url, caplog):
    from flaskspark.core import status
    from flaskspark.core.db import migrations

    migrations.upgrade(cfg, url)
    _sql(url, "INSERT INTO alembic_version VALUES ('f0re19000001')")
    with caplog.at_level("WARNING"):
        migrations.upgrade(cfg, url)
    assert "revision f0re19000001" in caplog.text and "belongs to no module" in caplog.text
    assert "f0re19000001" in _versions(url)
    found = migrations.state(cfg, url)
    assert found.foreign == ["f0re19000001"] and found.vanished == {}
    tile = status.collect(cfg, shown=[status.ModulesTile()])[0]
    assert ["Database", "revisions of no known module: f0re19000001"] in tile["details"]


def test_a_module_left_out_by_the_configuration_is_still_delivered(site, cfg, url, monkeypatch):
    """config.yaml `modules:` leaves omega out: not «no longer delivered», and the start does not import it."""
    from flaskspark.core import leftovers, modules
    from flaskspark.core.config import Config
    from flaskspark.core.db import migrations

    migrations.upgrade(cfg, url)
    _sql(url, "INSERT INTO omega_entry (text) VALUES ('kept')")
    only_keep = Config({**cfg.data, "modules": ["keep"]})
    modules.reset()
    imported = []
    manifest = modules._manifest
    monkeypatch.setattr(modules, "_manifest", lambda package: imported.append(package) or manifest(package))
    result = migrations.upgrade(only_keep, url)
    assert result["warnings"] == [] and "fsgone.modules.omega" not in imported
    assert migrations.state(only_keep, url).vanished == {}
    assert migrations.recorded(url)["omega"]["revision"] == OMEGA_REVISION
    assert leftovers.find(only_keep, url) == []  # its table is no unknown table either


def test_adopt_keeps_the_revision_of_a_module_no_longer_delivered(site, cfg, url):
    from flaskspark.core.db import migrations

    _vanish(site, cfg, url)
    _sql(url, "INSERT INTO alembic_version VALUES ('0ldh15t0ry01')")
    report = migrations.adopt(cfg, url)
    assert report["dropped"] == ["0ldh15t0ry01"]
    assert report["kept"]["no longer delivered"] == [OMEGA_REVISION]
    assert OMEGA_REVISION in _versions(url)


# --- one history depends on another (depends_on) --------------------------------------------------------------------
def _depend(site, keep_needs: str) -> None:
    """The next version: omega gets a second revision, keep's second one depends on `keep_needs` (a revision of
    omega, e.g. for a foreign key to its table)."""
    from flaskspark.core import modules

    add_revision(site, "omega", OMEGA_REVISION_2, OMEGA_REVISION, "omega_more")
    add_revision(site, "keep", KEEP_REVISION_2, KEEP_REVISION, "keep_more", depends_on=keep_needs)
    modules.reset()


def _at_heads(cfg, url) -> None:
    from flaskspark.core.db import migrations

    found = migrations.state(cfg, url)
    assert found.current == {**found.current, "keep": KEEP_REVISION_2, "omega": OMEGA_REVISION_2}
    assert found.pending == [] and found.unversioned == {} and found.unknown == []
    assert migrations.upgrade(cfg, url)["applied"] == {}  # nothing left to do, no `db adopt` demanded
    recorded = migrations.recorded(url)
    assert recorded["keep"]["revision"] == KEEP_REVISION_2 and recorded["omega"]["revision"] == OMEGA_REVISION_2
    report = migrations.adopt(cfg, url)
    assert report["dropped"] == [] and report["stamped"] == {} and report["new"] == []
    assert {"keep_more", "omega_more"} <= _tables(url)


@pytest.mark.parametrize("needs", [OMEGA_REVISION, OMEGA_REVISION_2])
def test_a_history_may_depend_on_another(site, cfg, url, needs):
    """Alembic keeps only the dependent revision in alembic_version (the one it depends on is «contained»): the
    histories still stand where they are, nothing is pending and nothing needs adopting."""
    from flaskspark.core.db import migrations

    migrations.upgrade(cfg, url)
    _depend(site, needs)
    result = migrations.upgrade(cfg, url)
    assert set(result["applied"]) == {"keep", "omega"}
    _at_heads(cfg, url)


def test_a_new_database_with_dependent_histories(site, cfg, url):
    from flaskspark.core.db import migrations

    _depend(site, OMEGA_REVISION_2)
    assert {"keep", "omega"} <= set(migrations.upgrade(cfg, url)["applied"])
    _at_heads(cfg, url)


# --- the leftovers ------------------------------------------------------------------------------------------------
def _leave_everything(site, cfg, url):
    """omega gone, with a setting, access cells, personal settings; a table and a revision nobody knows."""
    from flaskspark.core import settings
    from flaskspark.core.db import migrations

    migrations.upgrade(cfg, url)
    _sql(url, "INSERT INTO omega_entry (text) VALUES ('kept')")
    settings.save(_omega_config(cfg), {"omega.limit": "5"}, url=url)
    _sql(url, "INSERT INTO core_role_area (role_id, area, allowed) VALUES (1, 'omega', 1), (2, 'omega', 0)")
    _sql(url, "INSERT INTO core_user_settings (user_id, key, value, updated) VALUES "
              "(1, 'omega.columns', '{}', 0), (2, 'omega.columns', '{}', 0), (1, 'keep.columns', '{}', 0)")
    _sql(url, "CREATE TABLE stray (id INTEGER PRIMARY KEY)", "INSERT INTO stray VALUES (1)")
    _sql(url, "INSERT INTO alembic_version VALUES ('f0re19000001')")
    deliver(site, "keep")
    from flaskspark.core import modules

    modules.reset()
    migrations.upgrade(cfg, url)


def _omega_config(cfg):
    from flaskspark.core import modules

    return tuple(modules.get(cfg, "omega").CONFIG)


def test_the_leftovers_are_listed(site, cfg, url, state_dir):
    from flaskspark.core import leftovers

    _leave_everything(site, cfg, url)
    found = {item["id"]: item for item in leftovers.find(cfg, url)}
    assert list(found) == ["module:omega", "table:stray", "revision:f0re19000001", "setting:omega.limit",
                           "area:omega", "user-setting:omega.columns", "state:omega"]
    module = found["module:omega"]
    assert module["tables"] == [{"name": "omega_entry", "rows": 1}] and module["revisions"] == [OMEGA_REVISION]
    assert module["label"] == "Omega" and module["version"] == "1.0"
    assert found["table:stray"]["rows"] == 1
    assert found["setting:omega.limit"]["value"] == 5
    assert found["area:omega"]["rows"] == 2
    assert found["user-setting:omega.columns"] == {**found["user-setting:omega.columns"], "module": "omega", "rows": 2}
    assert found["state:omega"]["path"] == str(state_dir) and found["state:omega"]["size"] == 2


def test_nothing_is_left_over_while_every_module_is_delivered(cfg, url):
    from flaskspark.core import leftovers
    from flaskspark.core.db import migrations

    migrations.upgrade(cfg, url)
    assert leftovers.find(cfg, url) == []


def test_a_module_is_cleaned_up_after_a_backup_and_starts_afresh_when_it_comes_back(site, cfg, url, state_dir):
    from flaskspark.core import backup, leftovers, modules
    from flaskspark.core.db import migrations

    _leave_everything(site, cfg, url)
    result = leftovers.clean(cfg, ["module:omega"], url)
    assert result["removed"] == ["module:omega"]
    copy = Path(result["backup"]["db"])
    assert copy.is_file() and copy.parent == backup.settings(cfg)["dir"]
    assert backup.verify(copy)["counts"]["omega_entry"] == 1  # the data is in the backup
    assert "omega_entry" not in _tables(url) and OMEGA_REVISION not in _versions(url)
    assert "omega" not in migrations.recorded(url)
    assert "stray" in _tables(url) and state_dir.is_dir()  # only what was chosen

    deliver(site, "keep", "omega")
    modules.reset()
    assert migrations.upgrade(cfg, url)["applied"] == {"omega": [None, OMEGA_REVISION]}
    assert _sql(url, "SELECT count(*) FROM omega_entry") == [(0,)]


def test_clean_up_all(site, cfg, url, state_dir):
    from flaskspark.core import leftovers, settings

    _leave_everything(site, cfg, url)
    result = leftovers.clean(cfg, ["all"], url)
    assert len(result["removed"]) == 7
    assert Path(result["backup"]["db"]).is_file()
    archive = Path(result["backup"]["state"])
    assert archive.name.startswith("removed-") and archive.is_file()
    assert not state_dir.exists()
    assert leftovers.find(cfg, url) == []
    assert {"stray", "omega_entry"} & _tables(url) == set()
    assert "f0re19000001" not in _versions(url)
    assert "omega.limit" not in settings.stored(url)
    assert _sql(url, "SELECT key FROM core_user_settings") == [("keep.columns",)]
    assert _sql(url, "SELECT count(*) FROM core_role_area") == [(0,)]


def test_an_id_that_is_not_left_over_removes_nothing(site, cfg, url):
    from flaskspark.core import leftovers

    _leave_everything(site, cfg, url)
    with pytest.raises(leftovers.LeftoverError, match="table:keep_item"):
        leftovers.clean(cfg, ["table:stray", "table:keep_item"], url)
    assert "stray" in _tables(url)


def test_tables_are_dropped_through_the_database_api(url):
    from flaskspark.core import db

    _sql(url, "CREATE TABLE parent (id INTEGER PRIMARY KEY)",
         "CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id))",
         "INSERT INTO parent VALUES (1)", "INSERT INTO child VALUES (1, 1)", "CREATE TABLE other (id INTEGER)")
    assert db.table_names(url) == ["child", "other", "parent"]
    assert db.row_count("child", url) == 1
    assert db.drop_tables(["parent", "child", "nowhere"], url) == ["child", "parent"]
    assert db.table_names(url) == ["other"]


# --- the command line ---------------------------------------------------------------------------------------------
def _cli_environment(site, tmp_path) -> dict:
    """A process of its own on «fsgone» (it delivers no app package: config.yaml in the project directory)."""
    from tests.core.test_installed_app import _environment

    env = _environment(site, tmp_path)
    env["APP_NAME"] = "fsgone"
    (Path(env["APP_PROJECT_DIR"]) / "config.yaml").write_text("app:\n  name: fsgone\nauth: none\n"
                                                              "nats:\n  embedded: false\n")
    return env


def test_the_command_line(site, tmp_path):
    from tests.core.test_installed_app import _run

    env = _cli_environment(site, tmp_path)
    first = _run(env, "-m", "flaskspark.core.cli", "db", "upgrade")
    assert first.returncode == 0, first.stderr
    url = f"sqlite:///{tmp_path / 'state' / 'app.db'}"
    _sql(url, "INSERT INTO omega_entry (text) VALUES ('kept')")
    deliver(site, "keep")

    again = _run(env, "-m", "flaskspark.core.cli", "db", "upgrade")
    assert again.returncode == 0, again.stderr
    assert "module 'omega' is no longer delivered" in again.stderr
    listed = _run(env, "-m", "flaskspark.core.cli", "data")
    assert listed.returncode == 0, listed.stderr
    assert "module:omega" in listed.stdout and "omega_entry (1 rows)" in listed.stdout

    refused = _run(env, "-m", "flaskspark.core.cli", "data", "clean", "table:keep_item", "--yes")
    assert refused.returncode == 1 and "not left over" in refused.stderr
    cleaned = _run(env, "-m", "flaskspark.core.cli", "data", "clean", "module:omega", "--yes")
    assert cleaned.returncode == 0, cleaned.stderr
    result = json.loads(cleaned.stdout[cleaned.stdout.index("{"):])
    assert result["removed"] == ["module:omega"] and Path(result["backup"]["db"]).is_file()
    assert "omega_entry" not in _tables(url)
    assert "nothing left over" in _run(env, "-m", "flaskspark.core.cli", "data").stdout


def test_the_command_line_asks_first(site, tmp_path):
    env = _cli_environment(site, tmp_path)
    subprocess.run([sys.executable, "-m", "flaskspark.core.cli", "db", "upgrade"], env=env, capture_output=True,
                   text=True, timeout=120, cwd=env["APP_PROJECT_DIR"], check=True)
    deliver(site, "keep")
    asked = subprocess.run([sys.executable, "-m", "flaskspark.core.cli", "data", "clean", "all"], env=env, input="n\n",
                           capture_output=True, text=True, timeout=120, cwd=env["APP_PROJECT_DIR"])
    assert asked.returncode == 1 and "This deletes for good" in asked.stdout
    assert "omega_entry" in _tables(f"sqlite:///{tmp_path / 'state' / 'app.db'}")
