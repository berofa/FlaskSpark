"""Module packages (FlaskSpark(modules=[...])) and STRICT_IMPORTS."""

import importlib
import sys
import textwrap

import pytest

VIEW = textwrap.dedent('''
    from flask import render_template
    from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView


    class {name}(FlaskSparkMethodView):
        url = "{url}"
        endpoint = "{endpoint}"

        def get(self):
            return render_template("{template}")
''')


def _write(path, text=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def project(tmp_path, monkeypatch):
    """An app package «app» with one view and a module package «mods.demo.web» with its views, templates and
    static files, in a fresh directory (FlaskSpark looks for the app below the working directory)."""
    _write(tmp_path / ".env", "SECRET_KEY=test\nASSETS_ENABLE=false\n")
    _write(tmp_path / "app" / "__init__.py")
    _write(tmp_path / "app" / "views" / "__init__.py")
    _write(tmp_path / "app" / "views" / "home.py", VIEW.format(name="Home", url="/", endpoint="home", template="home.html"))
    _write(tmp_path / "app" / "templates" / "home.html", "app home")
    _write(tmp_path / "app" / "static" / "app.txt", "app static")
    web = tmp_path / "mods" / "demo" / "web"
    for init in (tmp_path / "mods", tmp_path / "mods" / "demo", web, web / "views"):
        _write(init / "__init__.py")
    _write(web / "views" / "page.py", VIEW.format(name="Demo", url="/demo", endpoint="demo", template="demo/page.html"))
    _write(web / "templates" / "demo" / "page.html", "demo page")
    _write(web / "static" / "demo" / "demo.js", "export const demo = 1;")
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("ASSETS_ENABLE", "false")
    yield tmp_path
    for name in [m for m in sys.modules if m == "app" or m.startswith(("app.", "mods"))]:
        del sys.modules[name]
    importlib.invalidate_caches()


def _app(project, **kwargs):
    from flaskspark import FlaskSpark

    return FlaskSpark(app_module="app", dotenv_path=str(project / ".env"), config={"ASSETS_ENABLE": False}, **kwargs).app


def test_without_modules_nothing_changes(project):
    app = _app(project)
    endpoints = {r.endpoint for r in app.url_map.iter_rules()}
    assert "home" in endpoints and "demo" not in endpoints


def test_module_views_templates_and_static(project):
    app = _app(project, modules=["mods.demo.web"])
    client = app.test_client()
    assert client.get("/").get_data(as_text=True) == "app home"
    assert client.get("/demo").get_data(as_text=True) == "demo page"
    assert client.get("/static/demo/demo.js").status_code == 200
    assert client.get("/static/app.txt").get_data(as_text=True) == "app static"


def test_a_fallback_view_gives_way_to_another_view_on_its_url(project):
    _write(project / "mods" / "demo" / "web" / "views" / "default.py", textwrap.dedent('''
        from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView


        class DefaultHome(FlaskSparkMethodView):
            url = "/"
            endpoint = "default_home"
            fallback = True

            def get(self):
                return "default home"


        class DefaultOther(FlaskSparkMethodView):
            url = "/other"
            endpoint = "default_other"
            fallback = True

            def get(self):
                return "default other"
    '''))
    app = _app(project, modules=["mods.demo.web"])
    endpoints = {r.endpoint for r in app.url_map.iter_rules()}
    assert "default_home" not in endpoints and "default_other" in endpoints
    client = app.test_client()
    assert client.get("/").get_data(as_text=True) == "app home"
    assert client.get("/other").get_data(as_text=True) == "default other"


def test_app_static_wins_over_module_static(project):
    _write(project / "app" / "static" / "demo" / "demo.js", "app wins")
    app = _app(project, modules=["mods.demo.web"])
    assert app.test_client().get("/static/demo/demo.js").get_data(as_text=True) == "app wins"


def test_unknown_module_package_stops_the_start(project):
    with pytest.raises(SystemExit):
        _app(project, modules=["mods.missing"])


def test_broken_view_is_skipped_without_strict_imports(project):
    _write(project / "mods" / "demo" / "web" / "views" / "broken.py", "import does_not_exist\n")
    app = _app(project, modules=["mods.demo.web"])
    assert "demo" in {r.endpoint for r in app.url_map.iter_rules()}


def test_broken_view_stops_the_start_with_strict_imports(project, monkeypatch):
    _write(project / "mods" / "demo" / "web" / "views" / "broken.py", "import does_not_exist\n")
    from flaskspark import FlaskSpark

    with pytest.raises(SystemExit):
        FlaskSpark(app_module="app", dotenv_path=str(project / ".env"),
                   config={"ASSETS_ENABLE": False, "STRICT_IMPORTS": True}, modules=["mods.demo.web"])


def test_imported_base_class_gets_no_route(project):
    app = _app(project, modules=["mods.demo.web"])
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/app.views.home" not in rules and "/mods.demo.web.views.page" not in rules
