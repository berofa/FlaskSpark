"""The asset pipeline of FlaskSpark apps: plain CSS and JS, no SCSS, no libsass, no Bootstrap 5."""

import importlib
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

VIEW = '''
from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView


class Home(FlaskSparkMethodView):
    url = "/"
    endpoint = "home"

    def get(self):
        return render_template("home.html")
'''


def _write(path, text=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def project(tmp_path, monkeypatch):
    """An app package «app» with a JS entry; libsass is not importable."""
    _write(tmp_path / ".env", "SECRET_KEY=test\n")
    _write(tmp_path / "app" / "__init__.py")
    _write(tmp_path / "app" / "views" / "__init__.py")
    _write(tmp_path / "app" / "views" / "home.py", VIEW)
    _write(tmp_path / "app" / "templates" / "home.html", '{% extends "layouts/framework.html" %}')
    _write(tmp_path / "app" / "static" / "js" / "app.js", "console.log('app');\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setitem(sys.modules, "sass", None)
    for name in ("ASSETS_ENABLE", "ASSETS_CSS_ENTRY", "ASSETS_CSS_FILTERS", "ENVIRONMENT"):
        monkeypatch.delenv(name, raising=False)
    yield tmp_path
    for name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[name]
    importlib.invalidate_caches()


def _app(project, **config):
    from flaskspark import FlaskSpark

    return FlaskSpark(app_module="app", dotenv_path=str(project / ".env"),
                      config={"ASSETS_BUILD_ON_START": True, **config}).app


def _built_css(project):
    return (project / "app" / "static" / "styles" / "app.min.css").read_text(encoding="utf-8")


def test_without_a_stylesheet_of_its_own_an_app_gets_flasksparks_plain_css(project):
    app = _app(project)

    assert app.config["ASSETS_CSS_ENTRY"] == "css/app.css"
    assert "css" in app.jinja_env.assets_environment and "scss" not in app.jinja_env.assets_environment
    css = _built_css(project)
    assert "@layer flaskspark" in css
    assert "light-dark(" in css and "color-mix(" in css


def test_the_production_build_minifies_with_rcssmin_and_keeps_nesting(project):
    _app(project, ENVIRONMENT="production", ASSETS_CACHE=False)

    css = _built_css(project)
    assert "/*" not in css  # minified: comments are gone
    assert "&.alert-success" in css or "&.alert-success" in css.replace(" ", "")


def test_an_apps_own_css_app_css_wins(project):
    _write(project / "app" / "static" / "css" / "app.css", ".mine { color: red; }\n")

    _app(project)

    css = _built_css(project)
    assert ".mine" in css and "@layer flaskspark" not in css


@pytest.mark.parametrize("setting", ["ASSETS_SCSS_ENTRY", "ASSETS_SCSS_FILTERS", "ASSETS_SCSS_OUTPUT",
                                     "ASSETS_SCSS_INCLUDE_PATHS", "VENDOR_INCLUDE_BOOTSTRAP", "LIBSASS_INCLUDES"])
def test_a_retired_scss_or_bootstrap5_setting_stops_the_start(project, capsys, setting):
    with pytest.raises(SystemExit):
        _app(project, **{setting: "something"})

    assert setting in capsys.readouterr().out


def test_a_retired_setting_in_the_environment_stops_the_start(project, capsys, monkeypatch):
    monkeypatch.setenv("VENDOR_INCLUDE_BOOTSTRAP", "true")

    with pytest.raises(SystemExit):
        _app(project)

    assert "VENDOR_INCLUDE_BOOTSTRAP" in capsys.readouterr().out


def test_an_extra_bundle_of_type_scss_stops_the_start(project, capsys):
    _write(project / "app" / "static" / "css" / "print.scss", "")

    with pytest.raises(SystemExit):
        _app(project, ASSETS_BUNDLES=[{"name": "print", "type": "scss", "entry": "css/print.scss",
                                       "output": "styles/print.min.css"}])

    assert "scss" in capsys.readouterr().out


def test_an_extra_css_bundle_is_built(project):
    _write(project / "app" / "static" / "css" / "print.css", "@media print { .no-print { display: none; } }\n")

    _app(project, ASSETS_BUNDLES=[{"name": "print", "type": "css", "entry": "css/print.css",
                                   "output": "styles/print.min.css"}])

    assert ".no-print" in (project / "app" / "static" / "styles" / "print.min.css").read_text(encoding="utf-8")


def test_no_scss_bootstrap5_or_libsass_left():
    scss = sorted(
        str(path.relative_to(ROOT))
        for folder in ("flaskspark", "webcomponents", "docs")
        for pattern in ("*.scss", "*.sass")
        for path in (ROOT / folder).rglob(pattern)
    )
    assert scss == []
    assert not (ROOT / "flaskspark" / "static" / "vendor" / "bootstrap").exists()
    assert not (ROOT / "webcomponents" / "build.py").exists()
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requirements = [*pyproject["project"]["dependencies"],
                    *(r for extra in pyproject["project"]["optional-dependencies"].values() for r in extra)]
    assert [r for r in requirements if "sass" in r.lower()] == []
