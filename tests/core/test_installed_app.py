"""An application installed as a package (tests/core/installed_app.py): modules found through entry points and loaded
without being named, DEPENDS / OPTIONAL_DEPENDS, migrations per module (upgrade, revision, adopt), translations per
module, a theme from an entry point and the built-in web app (in a process of its own: the paths come from the
environment at import)."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from tests.core.installed_app import ALPHA_REVISION, write


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    """The distribution on sys.path for this module's tests, gone again afterwards."""
    from flaskspark.core import modules

    path = write(tmp_path_factory.mktemp("site"))
    sys.path.insert(0, str(path))
    modules.reset()
    yield path
    sys.path.remove(str(path))
    for name in [m for m in sys.modules if m == "fsdemo" or m.startswith("fsdemo.")]:
        del sys.modules[name]
    modules.reset()


@pytest.fixture()
def cfg(site):
    from flaskspark.core.config import Config

    return Config({"app": {"name": "fsdemo"}, "auth": "none", "backup": {"dir": str(site.parent / "backups")}})


@pytest.fixture()
def url(tmp_path):
    return f"sqlite:///{tmp_path / 'app.db'}"


def _tables(url: str) -> set[str]:
    con = sqlite3.connect(url.removeprefix("sqlite:///"))
    try:
        return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()


def _versions(url: str) -> set[str]:
    con = sqlite3.connect(url.removeprefix("sqlite:///"))
    try:
        return {r[0] for r in con.execute("SELECT version_num FROM alembic_version")}
    finally:
        con.close()


# --- discovery ----------------------------------------------------------------------------------------------------
def test_every_installed_module_is_loaded_in_the_order_of_position(cfg):
    from flaskspark.core import modules

    assert [m.NAME for m in modules.load(cfg)] == ["core", "beta", "alpha"]
    assert modules.get(cfg, "alpha").PACKAGE == "fsdemo.modules.alpha"


def test_a_module_without_its_dependency_is_not_loaded_and_logged(cfg, caplog):
    from flaskspark.core import modules

    modules.reset()
    with caplog.at_level("ERROR"):
        modules.load(cfg)
    assert modules.skipped(cfg) == {"needy": "needs missing"}
    assert "module 'needy' is not loaded: it needs missing" in caplog.text
    assert "fsdemo.modules.needy.web" not in modules.web_packages(cfg)


def test_optional_dependencies_are_not_required(cfg):
    from flaskspark.core import modules

    assert modules.is_enabled(cfg, "alpha")
    assert not modules.is_enabled(cfg, "gamma")  # alpha's optional dependency: alpha loads without it
    assert not modules.is_enabled(cfg, "needy")


def test_an_explicit_list_restricts_and_orders(site, monkeypatch):
    from flaskspark.core import modules
    from flaskspark.core.config import Config

    assert [m.NAME for m in modules.load(Config({"modules": ["alpha", "beta"]}))[1:]] == ["alpha", "beta"]
    monkeypatch.setenv("APP_MODULES", "beta,nowhere")
    assert modules.names(Config({})) == ("beta",)  # a name that is not installed is logged and left out


def test_the_application_and_its_theme_are_found(site):
    from flaskspark.core import discovery, theme

    found = discovery.app()
    assert (found.name, found.package) == ("fsdemo", "fsdemo")
    assert discovery.package_dir("fsdemo") == (site / "fsdemo").resolve()
    assert theme.DirectoryThemes(site / "no-themes").get("fsdemo").title == "FS Demo"


def test_the_modules_catalogues_come_after_the_core_and_before_the_app(cfg, site):
    from flaskspark.core import modules
    from flaskspark.core.web.app import CORE_LOCALES, translation_directories

    found = modules.locale_dirs(cfg)
    assert found == [(site / "fsdemo" / "modules" / "alpha" / "locales").resolve()]
    assert translation_directories("/app/locales", found).split(";") == [str(CORE_LOCALES), str(found[0]),
                                                                         "/app/locales"]


# --- migrations ---------------------------------------------------------------------------------------------------
def test_upgrade_creates_the_tables_of_the_core_and_the_modules(cfg, url):
    from flaskspark.core.db import migrations

    result = migrations.upgrade(cfg, url)
    assert set(result["applied"]) == {"core", "alpha"}  # beta has no migrations yet, signin is off (auth none)
    assert result["backup"] is None  # an empty database: nothing to keep
    assert {"alpha_item", "core_settings", "core_role_area", "core_user_settings", "core_user_role"} <= _tables(url)
    assert "beta_note" not in _tables(url)
    assert ALPHA_REVISION in _versions(url)
    assert migrations.upgrade(cfg, url)["applied"] == {}
    found = migrations.state(cfg, url)
    assert found.pending == [] and found.current["alpha"] == ALPHA_REVISION


def test_the_cores_chain_brings_accounts_shares_and_attachments(cfg, url):
    """A fresh database: the core's history creates the tables of accounts, shares and attachments, and `db check`
    (migrations.differences) finds nothing between them and the models."""
    from flaskspark.core.db import migrations

    migrations.upgrade(cfg, url)
    assert {"core_accounts", "core_account_types", "core_shares", "core_share_members", "core_share_notices",
            "core_attachments"} <= _tables(url)
    assert "7d3f9a2c1e64" in _versions(url)
    assert migrations.differences(cfg, url) == {}


def test_upgrade_backs_up_the_database_first(cfg, url, site):
    from flaskspark.core.db import migrations

    migrations.upgrade(cfg, url)
    con = sqlite3.connect(url.removeprefix("sqlite:///"))
    con.execute("DELETE FROM alembic_version WHERE version_num = ?", (ALPHA_REVISION,))
    con.execute("DROP TABLE alpha_item")
    con.commit()
    con.close()
    result = migrations.upgrade(cfg, url)
    assert list(result["applied"]) == ["alpha"]
    assert result["backup"] and Path(result["backup"]).is_file()


def test_revision_autogenerates_against_the_modules_tables_only(cfg, url, site):
    from flaskspark.core.db import migrations

    migrations.upgrade(cfg, url)
    versions = site / "fsdemo" / "modules" / "beta" / "migrations" / "versions"
    try:
        files = migrations.revision(cfg, "beta", "beta tables", url=url)
        assert len(files) == 1
        text = files[0].read_text()
        assert "branch_labels = ('beta',)" in text and "down_revision = None" in text
        assert 'op.create_table(\'beta_note\'' in text or 'op.create_table("beta_note"' in text
        assert "alpha_item" not in text and "core_settings" not in text
        migrations.upgrade(cfg, url)
        assert "beta_note" in _tables(url)
        assert migrations.revision(cfg, "beta", "nothing", url=url) == []  # no change: no file
        assert migrations.differences(cfg, url) == {}
    finally:
        shutil.rmtree(versions.parent)
        from flaskspark.core import modules

        modules.reset()


def test_revision_on_a_database_that_is_not_up_to_date_says_so(cfg, url, site):
    from flaskspark.core.db import migrations

    versions = site / "fsdemo" / "modules" / "beta" / "migrations" / "versions"
    try:
        with pytest.raises(migrations.MigrationError, match="run `fsdemo db upgrade` first"):
            migrations.revision(cfg, "beta", "beta tables", url=url)  # a new database: nothing upgraded yet
        assert not list(versions.glob("*.py"))
    finally:
        shutil.rmtree(versions.parent, ignore_errors=True)
        from flaskspark.core import modules

        modules.reset()


def test_a_database_of_an_earlier_history_is_refused_and_adopted(cfg, url):
    from flaskspark.core import db
    from flaskspark.core.db import migrations

    # the tables as an earlier single history left them, with its revision
    migrations.upgrade(cfg, url)
    con = sqlite3.connect(url.removeprefix("sqlite:///"))
    con.execute("DELETE FROM alembic_version")
    con.execute("INSERT INTO alembic_version VALUES ('0ldh15t0ry01')")
    con.execute("INSERT INTO alpha_item (text) VALUES ('kept')")
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'core_%'").fetchall():
        con.execute(f"DROP TABLE {table}")  # the earlier history had none of the core's tables
    con.commit()
    con.close()

    with pytest.raises(migrations.MigrationError, match="0ldh15t0ry01.*db adopt"):
        migrations.upgrade(cfg, url)
    report = migrations.adopt(cfg, url)
    assert report["dropped"] == ["0ldh15t0ry01"]
    assert report["stamped"] == {"alpha": ALPHA_REVISION}
    assert report["new"] == ["core"]
    assert report["backup"]
    assert _versions(url) == {ALPHA_REVISION}
    assert list(migrations.upgrade(cfg, url)["applied"]) == ["core"]
    assert migrations.differences(cfg, url) == {}
    con = sqlite3.connect(url.removeprefix("sqlite:///"))
    assert con.execute("SELECT text FROM alpha_item").fetchall() == [("kept",)]
    con.close()
    db.dispose()


def test_adopt_refuses_a_history_with_only_some_tables(cfg, url):
    from flaskspark.core.db import migrations

    migrations.upgrade(cfg, url)
    con = sqlite3.connect(url.removeprefix("sqlite:///"))
    con.execute("DELETE FROM alembic_version")
    con.execute("DROP TABLE core_user_role")
    con.commit()
    con.close()
    with pytest.raises(migrations.MigrationError, match="core: only"):
        migrations.adopt(cfg, url)
    assert _versions(url) == set()  # nothing changed


def test_adopt_takes_over_sign_in_tables_of_an_older_user_model(cfg, url):
    """Users and roles of an earlier history, without the columns FlaskSpark added later: adopt stamps the sign-in's
    first revision, the next one adds the missing columns and the users stay."""
    from flaskspark.core.config import Config
    from flaskspark.core.db import migrations

    with_sign_in = Config({**cfg.data, "auth": "oauth"})
    con = sqlite3.connect(url.removeprefix("sqlite:///"))
    con.executescript("""
        CREATE TABLE roles (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL UNIQUE);
        CREATE TABLE user (id INTEGER PRIMARY KEY, username VARCHAR(255) NOT NULL UNIQUE,
                           email VARCHAR(255) NOT NULL UNIQUE);
        CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);
        INSERT INTO roles (name) VALUES ('Users');
        INSERT INTO user (username, email) VALUES ('ada', 'ada@example.org');
        INSERT INTO alembic_version VALUES ('0ldh15t0ry01');
    """)
    con.commit()
    con.close()

    report = migrations.adopt(with_sign_in, url)
    assert report["stamped"] == {"signin": "8a41d6c2f0e7"}
    result = migrations.upgrade(with_sign_in, url)
    assert result["applied"]["signin"] == ["8a41d6c2f0e7", "29f594d439bf"]
    con = sqlite3.connect(url.removeprefix("sqlite:///"))
    user_columns = {r[1] for r in con.execute("PRAGMA table_info(user)")}
    role_columns = {r[1] for r in con.execute("PRAGMA table_info(roles)")}
    assert {"role_id", "first_name", "last_name", "admin"} <= user_columns
    assert {"is_admin", "rank"} <= role_columns
    assert con.execute("SELECT username, role_id FROM user").fetchall() == [("ada", None)]
    assert con.execute("SELECT name, is_admin, rank FROM roles").fetchall() == [("Users", 0, 0)]
    con.close()


def test_the_sign_in_history_on_a_new_database(cfg, url):
    from flaskspark.core.config import Config
    from flaskspark.core.db import migrations

    with_sign_in = Config({**cfg.data, "auth": "oauth"})
    assert migrations.upgrade(with_sign_in, url)["applied"]["signin"] == [None, "29f594d439bf"]
    assert migrations.state(with_sign_in, url).pending == []


def test_tables_without_a_revision_are_refused(cfg, url):
    from flaskspark.core.db import migrations

    migrations.upgrade(cfg, url)
    con = sqlite3.connect(url.removeprefix("sqlite:///"))
    con.execute("DELETE FROM alembic_version")
    con.commit()
    con.close()
    with pytest.raises(migrations.MigrationError, match="without a revision"):
        migrations.upgrade(cfg, url)


# --- the built-in web app, the command line ----------------------------------------------------------------------
def _environment(site: Path, tmp: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("APP_", "SQLALCHEMY_"))}
    project = tmp / "project"
    project.mkdir(exist_ok=True)
    env.update({
        "PYTHONPATH": os.pathsep.join([str(site), str(Path(__file__).resolve().parents[2])]),
        "APP_PROJECT_DIR": str(project),
        "APP_STATE_DIR": str(tmp / "state"),
        "APP_CONFIG_DIR": str(tmp / "conf"),
        "APP_NO_DOTENV": "1",
        "SECRET_KEY": "test",
        "NATS_URL": "nats://127.0.0.1:1",
    })
    return env


def _run(env: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *args], env=env, capture_output=True, text=True, timeout=120,
                          cwd=env["APP_PROJECT_DIR"])


def test_the_built_in_web_app_serves_the_installed_modules(site, tmp_path):
    env = _environment(site, tmp_path)
    # the web app refuses a database that is not migrated
    refused = _run(env, "-c", "import flaskspark.core.web.wsgi")
    assert refused.returncode != 0 and "db upgrade" in refused.stderr

    upgraded = _run(env, "-m", "flaskspark.core.cli", "db", "upgrade")
    assert upgraded.returncode == 0, upgraded.stderr
    assert "alpha" in upgraded.stdout and "core" in upgraded.stdout
    listed = _run(env, "-m", "flaskspark.core.cli", "modules")
    assert listed.returncode == 0, listed.stderr
    assert "theme: fsdemo" in listed.stdout and "needy        not loaded: needs missing" in listed.stdout
    current = _run(env, "-m", "flaskspark.core.cli", "db", "current")
    assert f"alpha        {ALPHA_REVISION}   (head)" in current.stdout

    script = textwrap.dedent("""
        import json
        from flaskspark.core import db, paths
        from flaskspark.core.web.wsgi import app
        from fsdemo.modules.alpha.models import Item

        with db.for_module("alpha").session() as s:
            s.add(Item(text="first item"))
        client = app.test_client()
        page = client.get("/alpha/items", headers={"Accept-Language": "en"})
        german = client.get("/alpha/items", headers={"Accept-Language": "de"})
        print(json.dumps({
            "app": paths.APP.name, "config": str(paths.CONFIG_FILE), "state": str(paths.STATE_DIR),
            "status": page.status_code, "page": page.get_data(as_text=True),
            "german": german.get_data(as_text=True),
            "needy": client.get("/needy").status_code,
            "theme": client.get("/theme/theme.css").status_code,
        }))
    """)
    done = _run(env, "-c", script)
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout.strip().splitlines()[-1])
    assert result["app"] == "fsdemo"
    assert result["config"] == str((site / "fsdemo" / "config.yaml").resolve())
    assert result["state"] == str(tmp_path / "state")
    assert result["status"] == 200
    assert "Alpha items" in result["page"] and "first item" in result["page"] and "gamma: no" in result["page"]
    assert "Alpha-Einträge" in result["german"]  # the module's catalogue
    assert "Alpha der App" in result["german"]  # the app's catalogue wins over the module's
    assert result["needy"] == 404  # not loaded: its web part is not registered
    assert result["theme"] == 200


def test_the_status_shows_the_modules_that_are_not_loaded(cfg):
    from flaskspark.core import status

    t = status.collect(cfg, shown=[status.ModulesTile()])[0]
    assert t["summary"] == "2 loaded" and ["Loaded", "beta, alpha"] in t["details"]
    assert ["needy", "not loaded: needs missing"] in t["details"]
    assert t["level"] in ("warning", "error")


def test_the_flask_command_line_finds_the_built_in_app(site, tmp_path):
    env = _environment(site, tmp_path)
    env["APP_SKIP_MIGRATION_CHECK"] = "1"
    done = _run(env, "-m", "flask", "--app", "flaskspark.core.web.app:create_app", "routes")
    assert done.returncode == 0, done.stderr
    assert "/alpha/items" in done.stdout and "/needy" not in done.stdout


def test_the_command_line_offers_the_modules_commands(site, tmp_path):
    """`<app> <command>` runs a module's Module.CLI command like `flask --app …:create_app <command>` does."""
    env = _environment(site, tmp_path)
    assert _run(env, "-m", "flaskspark.core.cli", "db", "upgrade").returncode == 0
    done = _run(env, "-m", "flaskspark.core.cli", "alpha", "count", "--label", "things")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip().endswith(": 0 things")
    assert _run(env, "-m", "flaskspark.core.cli", "alpha", "fail").returncode == 3
    group_help = _run(env, "-m", "flaskspark.core.cli", "alpha", "--help")
    assert group_help.returncode == 0 and "count" in group_help.stdout
    listed = _run(env, "-m", "flaskspark.core.cli", "--help")
    assert listed.returncode == 0 and "commands of the modules: alpha" in listed.stdout
    unknown = _run(env, "-m", "flaskspark.core.cli", "nowhere")
    assert unknown.returncode == 2 and "invalid choice" in unknown.stderr
    via_flask = _run(env, "-m", "flask", "--app", "flaskspark.core.web.app:create_app", "alpha", "count")
    assert via_flask.returncode == 0 and via_flask.stdout.strip().endswith(": 0 items")
