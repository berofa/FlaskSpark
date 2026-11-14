"""delivery: versioned static URLs cached for a year, and preload links for a page's module graph."""

from __future__ import annotations

import re
import time

from flask import Flask, url_for

from webcomponents import delivery


def make_app(tmp_path):
    static = tmp_path / "static"
    (static / "mod" / "a").mkdir(parents=True)
    (static / "mod" / "main.js").write_text('/**\n * e.g. new URL("./x.css", import.meta.url)\n * import { Y } from "./y.js";\n */\n'
                                            '// import "./z.js";\nimport { A } from "./a/a.js";\nimport "lib/b.js";\n')
    (static / "mod" / "a" / "a.js").write_text(
        'import { x } from "../c.js";\nexport class A { static stylesheet = new URL("./a.css", import.meta.url).href; }\n')
    (static / "mod" / "a" / "a.css").write_text("a{}")
    (static / "mod" / "c.js").write_text("export const x = 1;\n")
    (static / "lib").mkdir()
    (static / "lib" / "b.js").write_text('export * from "./d.js";\n')
    (static / "lib" / "d.js").write_text("export const d = 1;\n")
    app = Flask(__name__, static_folder=str(static))
    version = delivery.version_static(app, "static", static)
    delivery.install_preload(app, {"/static/": static})

    @app.route("/")
    def page():
        lib = url_for("static", filename="lib/x")[:-1]
        return (f'<html><head><script type="importmap">{{"imports": {{"lib/": "{lib}"}}}}</script></head><body>'
                f'<script type="module" src="{url_for("static", filename="mod/main.js")}"></script></body></html>')
    return app, version, static


def test_versioned_urls_are_cached_for_a_year(tmp_path):
    app, version, static = make_app(tmp_path)
    c = app.test_client()
    with app.test_request_context():
        url = url_for("static", filename="mod/c.js")
    assert url == f"/static/v-{version.get()}/mod/c.js"
    r = c.get(url)
    assert r.status_code == 200 and r.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    plain = c.get("/static/mod/c.js")
    assert plain.status_code == 200 and "immutable" not in (plain.headers.get("Cache-Control") or "")


def test_an_edited_file_gives_a_new_version(tmp_path, monkeypatch):
    app, version, static = make_app(tmp_path)
    monkeypatch.setattr(delivery, "VERSION_TTL", 0.0)
    before = version.get()
    time.sleep(0.01)
    (static / "mod" / "c.js").write_text("export const x = 2;\n")
    assert version.get() != before


def test_page_preloads_its_module_graph(tmp_path):
    app, version, static = make_app(tmp_path)
    html = app.test_client().get("/").get_data(as_text=True)
    v = f"/static/v-{version.get()}"
    head = html[: html.index("</head>")]
    preloads = re.findall(r'<link rel="modulepreload" href="([^"]+)">', head)
    assert preloads == [f"{v}/mod/main.js", f"{v}/mod/a/a.js", f"{v}/lib/b.js", f"{v}/mod/c.js", f"{v}/lib/d.js"]
    assert re.findall(r'<link rel="preload" as="fetch" crossorigin href="([^"]+)">', head) == [f"{v}/mod/a/a.css"]


def test_several_directories_under_one_prefix(tmp_path):
    """A module's static files in a directory of their own (FlaskSpark module packages): versioned and preloaded."""
    app_static, module_static = tmp_path / "app", tmp_path / "module"
    (app_static / "js").mkdir(parents=True)
    (module_static / "mod").mkdir(parents=True)
    (app_static / "js" / "page.js").write_text('import "../mod/m.js";\n')
    (module_static / "mod" / "m.js").write_text("export const m = 1;\n")
    app = Flask(__name__, static_folder=None)
    app.static_url_path = "/static"

    @app.route("/static/<path:filename>", endpoint="static")
    def static(filename):
        from flask import send_from_directory
        for d in (app_static, module_static):
            if (d / filename).is_file():
                return send_from_directory(d, filename)
        return "", 404

    version = delivery.version_static(app, "static", [app_static, module_static])
    delivery.install_preload(app, {"/static/": [app_static, module_static]})

    @app.route("/")
    def page():
        return f'<html><head></head><body><script type="module" src="{url_for("static", filename="js/page.js")}"></script></body></html>'

    before = version.get()
    html = app.test_client().get("/").get_data(as_text=True)
    assert re.search(r'<link rel="modulepreload" href="/static/v-[0-9a-f]{8}/mod/m\.js">', html), html
    time.sleep(0.01)
    (module_static / "mod" / "n.js").write_text("export const n = 1;\n")
    version.checked = 0.0
    assert version.get() != before  # a file in the module's directory changes the version too
