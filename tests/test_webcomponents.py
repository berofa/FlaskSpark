"""VENDOR_INCLUDE_WEBCOMPONENTS: web components with Bootstrap 6 in layouts/framework.html."""

import importlib
import sys

import pytest
from flask import Blueprint

VIEW = '''
from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView


class Home(FlaskSparkMethodView):
    url = "/"
    endpoint = "home"

    def get(self):
        return render_template("home.html")
'''

BOOTSTRAP_CSS = "vendor/bootstrap6/css/bootstrap.min.css"
MODULE_ENTRY = "modules/bootstrap/bootstrap.js"


def _write(path, text=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def project(tmp_path, monkeypatch):
    """An app package «app» whose page extends the framework layout."""
    _write(tmp_path / ".env", "SECRET_KEY=test\nASSETS_ENABLE=false\n")
    _write(tmp_path / "app" / "__init__.py")
    _write(tmp_path / "app" / "views" / "__init__.py")
    _write(tmp_path / "app" / "views" / "home.py", VIEW)
    _write(tmp_path / "app" / "templates" / "home.html", '{% extends "layouts/framework.html" %}')
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("ASSETS_ENABLE", "false")
    yield tmp_path
    for name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[name]
    importlib.invalidate_caches()


def _app(project, **config):
    from flaskspark import FlaskSpark

    return FlaskSpark(app_module="app", dotenv_path=str(project / ".env"), config={"ASSETS_ENABLE": False, **config}).app


def test_disabled_by_default(project):
    html = _app(project).test_client().get("/").get_data(as_text=True)

    assert "bootstrap6" not in html
    assert MODULE_ENTRY not in html


def test_enabled_serves_bootstrap6_and_the_module_from_the_package(project):
    client = _app(project, VENDOR_INCLUDE_WEBCOMPONENTS=True).test_client()
    html = client.get("/").get_data(as_text=True)

    assert BOOTSTRAP_CSS in html and "/webcomponents/" in html
    assert f"/{MODULE_ENTRY}" in html
    # The page CSS comes before the app's own stylesheet, so the app can override it.
    assert html.index(BOOTSTRAP_CSS) < html.index("styles/app.min.css")
    for filename in (BOOTSTRAP_CSS, MODULE_ENTRY, "modules/bootstrap/ui-alert/ui-alert.js"):
        assert client.get(f"/webcomponents/{filename}").status_code == 200, filename


def test_the_snapshot_is_gone(project):
    from pathlib import Path

    import flaskspark

    assert not (Path(flaskspark.__file__).parent / "static" / "vendor" / "webcomponents").exists()
