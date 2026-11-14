"""flaskspark.core with the demo application of conftest.py: layout, navigation, theme, access, database rights,
push session, translations for scripts, sessions on the server, router routes, supervisor."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from flaskspark.core import config, db, modules, paths, theme
from flaskspark.core.module import Module, NavItem
from flaskspark.core.services.router.service import Router, Target, targets
from flaskspark.core.services.push.service import allowed

CORE = Path(__file__).resolve().parents[2] / "flaskspark" / "core"


def test_project_dir_and_config():
    from tests.core.conftest import ROOT

    assert paths.PROJECT_DIR == ROOT.resolve()
    assert config.load().app_name == "demo-app"
    assert config.load().modules == ("demo",)


def test_home_lists_the_module_in_navigation_and_tiles(client):
    html = client.get("/").get_data(as_text=True)
    assert "app-sidebar" in html
    assert 'href="/demo/notes"' in html
    assert "Short notes" in html
    assert "/theme/theme.css" in html


def test_module_page_renders_with_the_layout(client):
    response = client.get("/demo/notes")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "<h1>Notes</h1>" in html
    assert 'aria-current="page"' in html


def test_builtin_default_theme(client):
    t = theme.load(config.load())
    assert t.name == "default" and t.directory.is_relative_to(CORE)
    assert client.get("/theme/theme.css").status_code == 200
    assert client.get("/theme/images/logo.svg").status_code == 200
    assert client.get("/theme/theme.yaml").status_code == 404


def test_layout_import_map_and_icon_sprite(client):
    import re

    html = client.get("/").get_data(as_text=True)
    assert re.search(r'"app/": "/static/(v-\w+/)?app/"', html)  # the app's own JS (its package's static/app/)
    assert re.search(r'"modules/": "/static/(v-\w+/)?public/"', html)
    assert re.search(r'<meta name="ui-icon-sprite" content="/static/(v-\w+/)?flaskspark/vendor/bootstrap-icons/bootstrap-icons.svg"', html)
    assert 'rel="apple-touch-icon"' not in html and 'rel="manifest"' not in html  # the default theme has none
    assert client.get("/theme/manifest.webmanifest").status_code == 404


def test_theme_home_screen_icons_and_manifest_file(tmp_path):
    (tmp_path / "brand").mkdir()
    (tmp_path / "brand" / "theme.yaml").write_text("title: Brand\napple_touch_icon: touch.png\nmanifest: site.webmanifest\n")
    t = theme.DirectoryThemes(tmp_path, installed={}).get("brand")
    assert t.apple_touch_icon == "touch.png" and t.manifest_file == "site.webmanifest"
    assert "manifest" not in t.extra and "apple_touch_icon" not in t.extra


def test_theme_manifest_fields(tmp_path):
    (tmp_path / "brand").mkdir()
    (tmp_path / "brand" / "theme.yaml").write_text(
        "title: Brand App\nshort_name: Brand\ntheme_color: '#ffffff'\ntheme_color_dark: '#111111'\ndefault_mode: dark\n"
        "apple_touch_icon: touch.png\n"
        "manifest:\n  display: minimal-ui\n  icons:\n    - {src: icon-192.png, sizes: 192x192, type: image/png}\n"
        "    - {src: /elsewhere/icon.svg}\n")
    t = theme.DirectoryThemes(tmp_path, installed={}).get("brand")
    assert t.manifest_file == ""
    data = theme.manifest_data(t, "/theme/images/")
    assert data["name"] == "Brand App" and data["short_name"] == "Brand" and data["display"] == "minimal-ui"
    assert data["start_url"] == "/" and data["theme_color"] == "#111111" and data["background_color"] == "#111111"
    assert [i["src"] for i in data["icons"]] == ["/theme/images/icon-192.png", "/elsewhere/icon.svg"]
    # manifest: true: the defaults, the touch icon as its icon
    (tmp_path / "brand" / "theme.yaml").write_text("title: Brand\napple_touch_icon: touch.png\nmanifest: true\n")
    t = theme.DirectoryThemes(tmp_path, installed={}).get("brand")
    data = theme.manifest_data(t, "/theme/images/")
    assert data["icons"] == [{"src": "/theme/images/touch.png", "sizes": "180x180", "type": "image/png"}]
    assert data["theme_color"] == "#ffffff"
    (tmp_path / "brand" / "theme.yaml").write_text("title: Brand\nmanifest: 3\n")
    with pytest.raises(ValueError):
        theme.DirectoryThemes(tmp_path, installed={}).get("brand")


def test_the_layout_links_the_generated_manifest(app):
    from dataclasses import replace

    from flask import Flask, render_template

    from flaskspark.core.web import app as web_app
    from flaskspark.core.web.access import Access

    t = replace(theme.load(config.load()), apple_touch_icon="touch.png", manifest={"display": "standalone"})
    own = Flask(__name__)
    own.register_blueprint(web_app._theme_blueprint(t))
    answer = own.test_client().get("/theme/manifest.webmanifest")
    assert answer.status_code == 200 and answer.mimetype == "application/manifest+json"
    assert answer.get_json()["name"] == t.title and answer.get_json()["icons"][0]["src"] == "/theme/images/touch.png"
    assert "theme.manifest" in Access.PUBLIC
    with app.test_request_context("/"):
        html = render_template("layouts/main.html", theme=t)
    assert '<link rel="apple-touch-icon" href="/theme/images/touch.png">' in html
    assert '<link rel="manifest" href="/theme/manifest.webmanifest">' in html
    with app.test_request_context("/"):
        html = render_template("layouts/main.html", theme=replace(t, manifest="site.webmanifest"))
    assert '<link rel="manifest" href="/theme/images/site.webmanifest">' in html


def test_frame_css_top_level_rules_are_whole():
    """Every top-level rule of the layout's CSS starts with a selector or an at-rule (a nested `&…` rule at the top
    level means a block was cut, and the browser drops the rules after it), and the sidebar's inner column is defined
    once at the top level."""
    import re

    css = re.sub(r"/\*.*?\*/", "", (CORE / "web" / "static" / "flaskspark" / "css" / "frame.css").read_text(), flags=re.S)
    depth, start, preludes = 0, 0, []
    for index, char in enumerate(css):
        if char == "{":
            if depth == 0:
                preludes.append(css[start:index].strip())
            depth += 1
        elif char == "}":
            depth -= 1
            assert depth >= 0
            if depth == 0:
                start = index + 1
        elif char == ";" and depth == 0:
            start = index + 1
    assert depth == 0
    assert not [p for p in preludes if p.startswith(("&", ">", "+", "~"))], preludes
    assert preludes.count(".app-sidebar-inner") == 1 and preludes.count(".app-sidebar") == 1


def test_a_theme_of_the_app_wins(tmp_path):
    (tmp_path / "default").mkdir()
    (tmp_path / "default" / "theme.yaml").write_text("title: Mine\n")
    assert theme.DirectoryThemes(tmp_path).get("default").title == "Mine"
    with pytest.raises(KeyError):
        theme.DirectoryThemes(tmp_path).get("missing")


def test_webcomponents_come_with_flaskspark(client):
    html = client.get("/").get_data(as_text=True)
    assert "/webcomponents/" in html and "bootstrap.js" in html


def test_push_session_names_the_module_topics(client):
    data = client.get("/api/push/session").get_json()
    assert data["user"] == 0
    assert {"ev.all.>", "ev.user.0.>", "demo.state"} <= set(data["topics"])


def test_translations_for_scripts_take_commas(client):
    data = client.post("/api/i18n", json={"keys": ["Home", "One, two"]}).get_json()
    assert data == {"Home": "Home", "One, two": "One, two"}
    assert client.post("/api/i18n", json={"keys": "Home"}).status_code == 400


def test_the_core_brings_its_own_catalogue(client):
    """A German visitor gets the core's texts in German (flaskspark/core/locales), without a word of them in the app's
    catalogue; the scripts' translations come from the same catalogue."""
    client.environ_base["HTTP_ACCEPT_LANGUAGE"] = "de"
    page = client.get("/").get_data(as_text=True)
    assert "Start" in page and "Farbmodus" in page and "Sprache" in page
    assert "Colour mode" not in page
    data = client.post("/api/i18n", json={"keys": ["Saved", "Status of the services"]}).get_json()
    assert data == {"Saved": "Gespeichert", "Status of the services": "Status der Dienste"}
    client.environ_base["HTTP_ACCEPT_LANGUAGE"] = "en"
    assert "Colour mode" in client.get("/").get_data(as_text=True)


def test_the_apps_catalogue_wins_over_the_cores(app, client):
    from flaskspark.core.web.app import CORE_LOCALES, translation_directories

    directories = app.extensions["babel"].translation_directories
    assert directories[0] == str(CORE_LOCALES) and directories[-1].endswith("locales")  # later ones override
    assert translation_directories(f"x;{CORE_LOCALES}") == f"{CORE_LOCALES};x"
    client.environ_base["HTTP_ACCEPT_LANGUAGE"] = "de"
    page = client.get("/").get_data(as_text=True)
    assert 'title="Wie im Browser"' in page and 'title="Browser-Standard"' not in page  # the app translates it itself
    assert "Notizen" in page  # a text of the app's module
    assert "Farbmodus" in page  # the core's texts stay


def test_language_cookie_and_safe_redirect(client):
    response = client.get("/language/de?next=/demo/notes")
    assert "lang=de" in response.headers["Set-Cookie"]
    assert response.headers["Location"].endswith("/demo/notes")
    assert client.get("/language/de?next=//evil.example").headers["Location"].endswith("/")


def test_sessions_live_on_the_server(app):
    from flask import session

    assert type(app.session_interface).__module__.startswith("flask_session")
    with app.test_request_context("/"):
        session["secret"] = "not-in-the-cookie"
        response = app.make_response("ok")
        app.session_interface.save_session(app, session, response)
    assert "not-in-the-cookie" not in response.headers.get("Set-Cookie", "")


def test_module_reaches_only_its_tables(app):
    assert db.rights("demo") == frozenset({"demo_note"})
    assert db.rights("unknown") == frozenset()
    from modules.demo.models import Note

    with db.for_module("demo").session() as s:
        s.add(Note(text="hello"))
    with db.for_module("unknown").session() as s:
        with pytest.raises(db.DatabaseAccessError):
            s.scalars(db.select(Note)).all()


def test_manifest_needs_name_and_label():
    with pytest.raises(TypeError):
        type("Broken", (Module,), {"NAME": "x"})
    assert NavItem("G", "L", "/x", "open").position == 100


def test_push_topics_come_once(app, monkeypatch):
    from flaskspark.core.module import PushTopic
    from flaskspark.core.web.views import push

    class Twice(Module):
        NAME, LABEL = "twice", "Twice"
        PUSH_TOPICS = (PushTopic("shared.state", "open"), PushTopic("shared.state", "open"))

    class Again(Module):
        NAME, LABEL = "again", "Again"
        PUSH_TOPICS = (PushTopic("shared.state", "open"), PushTopic("own.{uid}", "open"))

    monkeypatch.setattr(modules, "load", lambda cfg: [Twice(), Again()])
    with app.test_request_context("/"):
        assert push.topics(7) == ["ev.all.>", "ev.user.7.>", "shared.state", "own.7"]


def test_push_topic_patterns():
    assert allowed("demo.state", ["demo.>"])
    assert allowed("ev.user.3.x", ["ev.user.3.>"])
    assert not allowed("ev.user.4.x", ["ev.user.3.>"])
    assert not allowed("demo", ["demo.>"])


def test_router_routes():
    router = Router([Target("/events", 1), Target("/ws/x", 2)], web_port=9)
    assert [router.port_for(p) for p in ("/events", "/events/sub", "/eventsx", "/ws/x", "/")] == [1, 1, 9, 2, 9]
    assert any(t.prefix == "/events" for t in targets(modules.load(config.load())))


def test_supervisor_starts_every_service_and_the_router(monkeypatch):
    from flaskspark.core import supervisor

    children = supervisor.children(config.load())
    assert [c.name for c in children] == ["flaskspark-web", "flaskspark-push", "flaskspark-router"]
    # the short name inside; the router through its ServiceInfo like the others
    assert [c.args[-2:] for c in children] == [["service", "web"], ["service", "push"], ["service", "router"]]


def test_the_router_stays_last_after_the_optional_services(monkeypatch):
    from flaskspark.core import supervisor
    from flaskspark.core.config import Config

    monkeypatch.setenv("NATS_EMBEDDED", "1")
    monkeypatch.setenv("NATS_SERVER", "/bin/true")
    monkeypatch.setenv("NATS_URL", "nats://127.0.0.1:1")  # children() sets it for an embedded node otherwise
    cfg = Config({**config.load().data, "notifications": {"enabled": True}, "guardian": {"enabled": True}})
    modules.reset()
    try:
        names = [c.name for c in supervisor.children(cfg)]
    finally:
        modules.reset()
    assert names[0] == "flaskspark-nats" and names[-1] == "flaskspark-router"
    assert "flaskspark-guardian" in names and names.count("flaskspark-router") == 1


def test_the_router_counts_what_it_carries():
    router = Router([Target("/events", 1)], web_port=9)
    router._requests.extend([0.0, 100.0, 130.0])
    router._failures.append(130.0)
    router.open, router.websockets = 2, 1
    assert router.details(now=150.0) == {"routes": 1, "open": 2, "websockets": 1, "requests_per_minute": 2,
                                          "upstream_failures": 1}


def test_the_router_passes_a_refused_websocket_on_and_counts_only_what_does_not_answer():
    """A service that refuses a WebSocket (no such path: 404) answers the browser through the router as it is and is
    no upstream failure; only a service that is not there counts (502). An accepted one carries messages both ways."""
    import asyncio
    import socket

    import aiohttp
    from aiohttp import web

    def free_port() -> int:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    async def echo(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for msg in ws:
            await ws.send_str("echo " + msg.data)
        return ws

    async def main():
        upstream = web.Application()
        upstream.router.add_get("/ws/ok", echo)
        up = web.AppRunner(upstream)
        await up.setup()
        web_port, port = free_port(), free_port()
        await web.TCPSite(up, "127.0.0.1", web_port).start()
        router = Router([Target("/ws/away", free_port(), websocket=True)], web_port=web_port)
        runner = await router.start("127.0.0.1", port)
        try:
            async with aiohttp.ClientSession() as http:
                async with http.ws_connect(f"http://127.0.0.1:{port}/ws/ok") as ws:
                    await ws.send_str("hi")
                    assert (await ws.receive()).data == "echo hi"
                with pytest.raises(aiohttp.WSServerHandshakeError) as refused:
                    await http.ws_connect(f"http://127.0.0.1:{port}/ws/gone")
                assert refused.value.status == 404
                assert router.details()["upstream_failures"] == 0
                with pytest.raises(aiohttp.WSServerHandshakeError) as away:
                    await http.ws_connect(f"http://127.0.0.1:{port}/ws/away")
                assert away.value.status == 502
                assert router.details()["upstream_failures"] == 1
        finally:
            await runner.cleanup()
            await router.close()
            await up.cleanup()

    asyncio.run(main())


def test_core_imports_no_application_code():
    for path in CORE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module and node.level == 0 else [])
            assert not [n for n in names if n.split(".")[0] in ("modules", "app")], path


def test_sqlalchemy_only_inside_the_database_api():
    for path in CORE.rglob("*.py"):
        if path.is_relative_to(CORE / "db"):
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                assert not [n for n in names if n.split(".")[0] == "sqlalchemy"], path


def test_html_lang_follows_the_language(client):
    assert '<html lang="de">' in client.get("/", headers={"Accept-Language": "de"}).get_data(as_text=True)
    assert '<html lang="en">' in client.get("/").get_data(as_text=True)


def test_nats_url_defaults_to_the_local_node_on_nats_port(monkeypatch):
    from flaskspark.core import bus

    monkeypatch.delenv("NATS_URL", raising=False)
    monkeypatch.setenv("NATS_PORT", "4299")
    assert bus.credentials("web")["servers"] == ["nats://127.0.0.1:4299"]
