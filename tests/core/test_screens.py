"""Info screens (Module.SCREENS, flaskspark.core.web.views.screen, layouts/screen.html): the manifest's field, the
pages /screen and /screen/<key>, the layout without navigation, the access."""
from __future__ import annotations

import re

import pytest

from tests.core.sso import client_for


def test_a_screen_checks_its_fields():
    from flaskspark.core.module import Screen

    screen = Screen("wall-1", "Wall", "demo")
    assert screen.page == "screen:wall-1"
    assert screen.reload_at == "04:00" and screen.mode == ""
    for bad in ("", "a b", "a/b", "ä"):
        with pytest.raises(ValueError):
            Screen(bad, "Wall", "demo")
    with pytest.raises(ValueError):
        Screen("wall", "Wall", "demo", mode="sepia")
    with pytest.raises(ValueError):
        Screen("wall", "Wall", "demo", reload_at="25:00")
    assert Screen("wall", "Wall", "demo", reload_at="").reload_at == ""


def test_the_screens_of_the_modules_by_position(app):  # noqa: ARG001 - the demo app
    from flaskspark.core.web.views import screen

    assert [s.key for s in screen.screens()] == ["wall", "empty"]
    assert screen.find("nope") is None
    assert screen.sections(screen.find("wall")) == ["demo/screen.html"]
    assert screen.sections(screen.find("empty")) == []


def test_colour_mode_and_scale_from_the_url():
    from flaskspark.core.module import Screen
    from flaskspark.core.web.views.screen import colour_mode, scale

    wall = Screen("wall", "Wall", "demo", mode="dark")
    assert colour_mode(wall, None) == "dark"
    assert colour_mode(wall, "Light") == "light"
    assert colour_mode(wall, "sepia") == "dark"
    assert colour_mode(Screen("w", "W", "demo"), "") == ""
    assert scale("1.5") == "1.5"
    assert scale("9") == "3" and scale("0.1") == "0.5"
    assert scale("") == "" and scale("big") == "" and scale("nan") == "" and scale("inf") == ""


def test_a_screen_has_no_navigation_and_its_sections(client):
    response = client.get("/screen/wall")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert re.search(r'<html lang="en" data-screen="wall" data-theme-fixed="dark" data-screen-reload-at="04:00"', html)
    assert "app-screen-body" in html and "data-demo-screen" in html
    assert "app-sidebar" not in html and "app-nav" not in html and "app-topbar" not in html
    assert "flaskspark/js/screen.js" in html
    assert "<title>Wall · " in html  # the screen's title, then the app's
    assert "data-screen-clock" in html and "data-screen-live" in html


def test_the_url_sets_mode_and_scale(client):
    html = client.get("/screen/wall?mode=light&scale=1.6").get_data(as_text=True)
    assert 'data-theme-fixed="light"' in html and 'style="--app-screen-scale: 1.6"' in html
    plain = re.search(r"<html[^>]*>", client.get("/screen/empty").get_data(as_text=True)).group(0)
    assert plain == '<html lang="en" data-screen="empty">'


def test_the_title_beside_the_logo_or_only_for_screen_readers(client):
    assert '<h1 class="app-screen-title">Wall</h1>' in client.get("/screen/wall").get_data(as_text=True)
    assert '<h1 class="app-screen-title visually-hidden">Empty</h1>' in client.get("/screen/empty").get_data(as_text=True)


def test_an_empty_screen_says_so(client):
    html = client.get("/screen/empty").get_data(as_text=True)
    assert "Nothing on this dashboard yet." in html


def test_an_unknown_screen_is_not_found(client):
    assert client.get("/screen/nope").status_code == 404


def test_the_list_of_screens(client):
    html = client.get("/screen").get_data(as_text=True)
    assert 'href="/screen/wall"' in html and 'href="/screen/empty"' in html
    assert "Notes on the wall" in html


def test_a_screen_in_german(client):
    html = client.get("/screen/empty", headers={"Accept-Language": "de"}).get_data(as_text=True)
    assert "Auf diesem Dashboard ist noch nichts." in html


def test_ordinary_pages_are_no_screens(client):
    html = client.get("/demo/notes").get_data(as_text=True)
    assert "data-screen" not in html and "flaskspark/js/screen.js" not in html


def test_settings_list_the_screens(app):
    from flaskspark.core.web.views.settings import screen_items

    with app.test_request_context():
        items = screen_items()
    assert [i["key"] for i in items] == ["wall", "empty"]
    wall, empty = items
    assert wall["title"] == "Wall" and wall["description"] == "Notes on the wall" and wall["icon"] == "display"
    assert wall["module"] == "Demo" and wall["module_name"] == "demo"
    assert wall["area"] == "Demo" and wall["area_key"] == "demo"
    assert wall["mode"] == "dark" and wall["reload_at"] == "04:00" and wall["url"] == "/screen/wall"
    assert wall["sections"] == 1 and empty["sections"] == 0 and empty["reload_at"] == ""


def test_the_settings_tab_screens(client):
    html = client.get("/settings").get_data(as_text=True)
    assert 'name="screens"' in html and 'data-screen-row="wall"' in html and 'data-screen-row="empty"' in html
    assert 'href="/screen/wall" target="_blank"' in html and "Notes on the wall" in html
    row = html.split('data-screen-row="empty"')[1].split("</tr>")[0]
    assert "never" in row and "As in the app" in row and "No module adds anything to it yet." in row
    # the settings of the module that declares the dashboards: in this tab, below the list, not in a tab of their own
    panel = html.split('name="screens"')[1].split("</ui-tab-panel>")[0]
    assert 'data-settings-screen-module="demo"' in panel and 'action="/api/settings/config/demo"' in panel
    assert '<ui-tab-panel heading="Demo"' not in html


def test_the_settings_tab_screens_in_german(client):
    html = client.get("/settings", headers={"Accept-Language": "de"}).get_data(as_text=True)
    assert 'heading="Dashboards"' in html and "Tägliches Neuladen" in html and "Wie in der App" in html


@pytest.fixture(scope="module")
def sso(app):  # noqa: ARG001 - the demo app (its tables) first
    from tests.core.sso import sso_app

    with sso_app() as sso_web:
        yield sso_web


def test_a_screen_needs_its_area(sso):
    assert client_for(sso, "user").get("/screen/wall").status_code == 200
    denied = client_for(sso, "guest").get("/screen/wall")
    assert denied.status_code == 403 and "data-no-access" in denied.get_data(as_text=True)
    listed = client_for(sso, "guest").get("/screen").get_data(as_text=True)
    assert 'href="/screen/wall"' not in listed


def test_only_admins_see_the_screens_in_the_settings(sso):
    assert 'data-screen-row="wall"' in client_for(sso, "admin").get("/settings").get_data(as_text=True)
    assert client_for(sso, "user").get("/settings").status_code == 403
