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


def test_enabled_loads_bootstrap6_and_the_module_from_the_snapshot(project):
    client = _app(project, VENDOR_INCLUDE_WEBCOMPONENTS=True).test_client()
    html = client.get("/").get_data(as_text=True)

    assert f'href="/static/vendor/webcomponents/{BOOTSTRAP_CSS}"' in html
    assert f'<script type="module" src="/static/vendor/webcomponents/{MODULE_ENTRY}"></script>' in html
    # The page CSS comes before the app's own stylesheet, so the app can override it.
    assert html.index(BOOTSTRAP_CSS) < html.index("styles/app.min.css")
    for filename in (BOOTSTRAP_CSS, MODULE_ENTRY, "modules/bootstrap/ui-alert/ui-alert.js"):
        assert client.get(f"/static/vendor/webcomponents/{filename}").status_code == 200, filename


def test_an_installed_webcomponents_blueprint_takes_precedence(project):
    app = _app(project, VENDOR_INCLUDE_WEBCOMPONENTS=True)
    app.register_blueprint(Blueprint("webcomponents", __name__, static_folder=str(project), static_url_path="/wc"))

    html = app.test_client().get("/").get_data(as_text=True)

    assert f'href="/wc/{BOOTSTRAP_CSS}"' in html
    assert f'src="/wc/{MODULE_ENTRY}"' in html


def test_cannot_be_combined_with_bootstrap5(project):
    with pytest.raises(SystemExit):
        _app(project, VENDOR_INCLUDE_WEBCOMPONENTS=True, VENDOR_INCLUDE_BOOTSTRAP=True)
