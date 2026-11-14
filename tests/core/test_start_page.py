"""The start page («/»): the core's unless a module or the app has a view there; config.yaml `app.start` sends «/»
elsewhere; the access gate treats what «/» leads to as the start page."""
from __future__ import annotations

import os
import sys

import pytest

from tests.core.conftest import ROOT
from tests.core.sso import client_for


@pytest.fixture(scope="module")
def sso(app):  # noqa: ARG001 - the demo app (its tables) first
    from tests.core.sso import sso_app

    with sso_app() as sso_web:
        yield sso_web


@pytest.fixture()
def start(monkeypatch):
    """Set config.yaml `app.start` for one test."""
    from flaskspark.core import config

    load = config.load

    def with_start(value):
        def patched(path=None):
            cfg = load(path)
            return config.Config({**cfg.data, "app": {**cfg.section("app"), "start": value}}, cfg.defaults)

        monkeypatch.setattr(config, "load", patched)

    return with_start


def test_the_cores_start_page_serves_without_a_view_of_its_own(app, client):
    assert "index" in {r.endpoint for r in app.url_map.iter_rules()}
    assert client.get("/").status_code == 200


def test_a_view_of_the_app_on_the_root_replaces_the_cores(app):
    from flaskspark.core.web import start_endpoints
    from flaskspark.core.web.app import create
    from flaskspark.core.web.navigation import home_entry

    cwd = os.getcwd()
    os.chdir(ROOT / "web")
    sys.path.insert(0, str(ROOT / "web"))
    try:
        _, own = create("app_home")
    finally:
        os.chdir(cwd)
        sys.path.remove(str(ROOT / "web"))
        for name in [m for m in sys.modules if m == "app_home" or m.startswith("app_home.")]:
            del sys.modules[name]
    own.config.update(TESTING=True)
    endpoints = {r.endpoint for r in own.url_map.iter_rules()}
    assert "own_start" in endpoints and "index" not in endpoints
    assert own.test_client().get("/").get_data(as_text=True) == "the app's own start page"
    with own.test_request_context("/"):
        assert start_endpoints() == {"own_start"}
        assert home_entry() is False  # «/» is the app's: no «Home» in the navigation


@pytest.fixture()
def app_setting(monkeypatch):
    """Set a key of config.yaml `app:` for one test."""
    from flaskspark.core import config

    load = config.load

    def with_setting(key, value):
        def patched(path=None):
            cfg = load(path)
            return config.Config({**cfg.data, "app": {**cfg.section("app"), key: value}}, cfg.defaults)

        monkeypatch.setattr(config, "load", patched)

    return with_setting


HOME_LINK = '<i class="bi bi-house" aria-hidden="true"></i>'


def test_home_entry_while_the_cores_start_page_answers(client):
    assert HOME_LINK in client.get("/demo/notes").get_data(as_text=True)


def test_no_home_entry_when_the_start_page_leads_elsewhere(client, start):
    start("/demo/notes")
    assert HOME_LINK not in client.get("/demo/notes").get_data(as_text=True)


@pytest.mark.parametrize("value, shown", [(False, False), (True, True)])
def test_home_entry_by_config(client, start, app_setting, value, shown):
    app_setting("home_entry", value)
    assert (HOME_LINK in client.get("/demo/notes").get_data(as_text=True)) is shown


@pytest.mark.parametrize("value", ["/demo/notes", "demo_notes"])
def test_the_configured_start_page(client, start, value):
    start(value)
    answer = client.get("/")
    assert answer.status_code == 302 and answer.headers["Location"].endswith("/demo/notes")


def test_the_gate_sends_a_visitor_who_may_not_use_the_start_page_elsewhere(sso, start, monkeypatch):
    from flaskspark.core.web import EXTENSION

    guest = client_for(sso, "guest")  # Guests may not use the area «demo»
    assert guest.get("/demo/notes").status_code == 403  # an ordinary page: «no access»
    start("demo_notes")
    monkeypatch.setattr(sso.extensions[EXTENSION], "start_page", lambda: "/elsewhere")
    assert guest.get("/").headers["Location"].endswith("/demo/notes")
    answer = guest.get("/demo/notes")  # the start page: the first area the visitor may use instead
    assert answer.status_code == 302 and answer.headers["Location"].endswith("/elsewhere")
