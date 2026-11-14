"""Flask settings from config.yaml (`flask:`) and values FlaskSpark reads from the environment, which may come from the
env files (CONFIG_DIR/app.env) loaded after FlaskSpark's import."""
from __future__ import annotations

import os

import pytest

from flaskspark.core import bus, config, paths, secrets


@pytest.fixture()
def conf_dir(monkeypatch, tmp_path):
    """An empty config directory; the variables its app.env brings are removed afterwards (env files never overwrite
    the environment, so monkeypatch can't restore them)."""
    monkeypatch.setattr(paths, "CONFIG_DIR", tmp_path)
    before = set(os.environ)
    config.reload()
    yield tmp_path
    for name in set(os.environ) - before:
        os.environ.pop(name, None)
    config.reload()


def test_the_flask_section_of_the_configuration(app):
    assert app.config["PERMANENT_SESSION_LIFETIME"] == 3600  # config.yaml flask:, not the core's week
    assert app.permanent_session_lifetime.total_seconds() == 3600


def test_role_defaults_in_every_form():
    from flaskspark.core.web.app import flask_settings

    def roles(value):
        return flask_settings(config.Config({"flask": {"ROLE_DEFAULTS": value}}))["ROLE_DEFAULTS"]

    assert roles("Owners:90:admin,Staff:10") == [("Owners", True, 90), ("Staff", False, 10)]
    assert roles(["Owners:90:admin", "Staff:10"]) == [("Owners", True, 90), ("Staff", False, 10)]
    assert roles([["Owners", True, 90]]) == [("Owners", True, 90)]
    assert flask_settings(config.Config({})) == {}


def test_flasksparks_settings_are_read_at_the_start_not_at_the_import(monkeypatch):
    from flaskspark import config as flaskspark_config

    monkeypatch.setenv("ROLE_DEFAULTS", "Late:5")
    assert flaskspark_config.from_environment().ROLE_DEFAULTS == [("Late", False, 5)]


def test_the_nats_env_file_may_be_named_in_app_env(conf_dir, monkeypatch):
    monkeypatch.delenv("NATS_ENV_FILE", raising=False)
    monkeypatch.delenv("NATS_REPLICAS", raising=False)
    nats_env = conf_dir / "nats.env"
    nats_env.write_text("NATS_REPLICAS=3\n")
    (conf_dir / "app.env").write_text(f"NATS_ENV_FILE={nats_env}\n")
    assert bus.env_file() == nats_env
    assert bus.replicas() == 3


def test_the_secret_keys_variable_may_be_named_in_app_env(conf_dir, monkeypatch):
    for name in ("APP_SECRET_KEY", "APP_SECRET_KEY_ENV", "OLD_KEY"):
        monkeypatch.delenv(name, raising=False)
    (conf_dir / "app.env").write_text("APP_SECRET_KEY_ENV=OLD_KEY\nOLD_KEY=from the env file\n")
    token = secrets.encrypt("x")
    assert secrets.env_key() == "OLD_KEY"
    assert secrets.decrypt(token, "from the env file") == "x"
