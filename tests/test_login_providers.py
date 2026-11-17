"""Login providers of the classic FlaskSpark app: FlaskSpark brings «OAuth»; there is no built-in «Default» any more,
an app may still bring a provider of that name itself (<app>.helpers.login_provider_default)."""

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

OWN_PROVIDER = '''
from flaskspark.helpers.login_provider import AbstractLoginProvider


class DefaultLoginProvider(AbstractLoginProvider):
    requires_user_model = False

    def check_configuration(self, config):
        pass

    def configure(self):
        pass
'''


def _write(path, text=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def project(tmp_path, monkeypatch):
    """An app package «app» without views."""
    _write(tmp_path / ".env", "SECRET_KEY=test\n")
    _write(tmp_path / "app" / "__init__.py")
    _write(tmp_path / "app" / "views" / "__init__.py")
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    yield tmp_path
    for name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[name]
    importlib.invalidate_caches()


def _spark(project, **kwargs):
    from flaskspark import FlaskSpark

    return FlaskSpark(app_module="app", dotenv_path=str(project / ".env"), config={"ASSETS_ENABLE": False}, **kwargs)


def test_the_default_provider_stops_the_start_and_names_the_alternatives(project, capsys):
    with pytest.raises(SystemExit):
        _spark(project, login_provider="Default")

    out = capsys.readouterr().out
    assert "Default" in out and "OAuth" in out


def test_an_apps_own_default_provider_still_loads(project):
    _write(project / "app" / "helpers" / "__init__.py")
    _write(project / "app" / "helpers" / "login_provider_default.py", OWN_PROVIDER)
    spark = _spark(project)

    provider = spark._load_login_provider("Default")

    assert type(provider).__module__ == "app.helpers.login_provider_default"


def test_flaskspark_brings_no_default_provider_any_more():
    assert not (ROOT / "flaskspark" / "helpers" / "login_provider_default.py").exists()
    user = (ROOT / "flaskspark" / "models" / "user.py").read_text(encoding="utf-8")
    assert '"Default"' not in user and "password" not in user
