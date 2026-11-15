"""Pages for info screens (Module.SCREENS): a display on the wall that nobody operates.

GET /screen          the screens the visitor may use, with links (main layout)
GET /screen/<key>    the screen: layouts/screen.html with the sections the modules add (PAGE_SECTIONS["screen:<key>"]);
                     ?mode=light|dark|system fixes the colour mode for this browser's view, ?scale=<0.5…3> the size
                     (--app-screen-scale), both handy in the URL a screen is set up with

A screen the visitor may not use (its area) answers 403 with «no access», an unknown one 404. Screens of modules that
are not loaded do not exist; sections of modules that are not loaded are not there.
"""

from __future__ import annotations

from flask import abort, render_template, request
from flask_babel import gettext
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core import config, modules
from flaskspark.core.module import SCREEN_MODES, Screen, page_sections
from flaskspark.core.web import OPEN, can

SCALE_MIN, SCALE_MAX = 0.5, 3.0


def screens(manifests=None) -> list[Screen]:
    """Every screen of the loaded modules, by position (the first of a key wins)."""
    return [screen for screen, _module in declared(manifests)]


def declared(manifests=None) -> list[tuple[Screen, object]]:
    """Every screen of the loaded modules with the module that declares it, by position (the first of a key wins)."""
    found: dict[str, tuple[Screen, object]] = {}
    for module in manifests if manifests is not None else modules.load(config.load()):
        for screen in module.SCREENS:
            found.setdefault(screen.key, (screen, module))
    return sorted(found.values(), key=lambda pair: pair[0].position)


def find(key: str, manifests=None) -> Screen | None:
    return next((s for s in screens(manifests) if s.key == key), None)


def sections(screen: Screen, manifests=None) -> list[str]:
    """The templates the loaded modules add to the screen, in the order of the modules."""
    loaded = manifests if manifests is not None else modules.load(config.load())
    return page_sections(loaded, screen.page)


def colour_mode(screen: Screen, asked: str | None) -> str:
    """The fixed colour mode of the screen ("" follows the app): the URL's, else the screen's."""
    asked = (asked or "").strip().lower()
    return asked if asked in SCREEN_MODES and asked else screen.mode


def scale(asked: str | None) -> str:
    """The URL's size factor within SCALE_MIN … SCALE_MAX as text, "" when none or unreadable (the token's default)."""
    try:
        value = float(asked or "")
    except ValueError:
        return ""
    if value != value or value in (float("inf"), float("-inf")):  # NaN, infinite
        return ""
    return f"{min(max(value, SCALE_MIN), SCALE_MAX):g}"


class ScreensView(FlaskSparkMethodView):
    url = "/screen"
    endpoint = "flaskspark_screens"
    area = OPEN

    def get(self):
        usable = [{"key": s.key, "title": gettext(s.title), "description": gettext(s.description) if s.description else "",
                   "icon": s.icon} for s in screens() if can(s.area)]
        return render_template("flaskspark/screens.html", screens=usable)


class ScreenView(FlaskSparkMethodView):
    url = "/screen/<key>"
    endpoint = "flaskspark_screen"
    area = OPEN  # each screen has its own area (asked below)

    def get(self, key: str):
        screen = find(key)
        if screen is None:
            abort(404)
        if not can(screen.area):
            return render_template("flaskspark/no_access.html", denied=True), 403
        return render_template("flaskspark/screen.html", screen=screen, screen_title=gettext(screen.title),
                               screen_sections=sections(screen), screen_mode=colour_mode(screen, request.args.get("mode")),
                               screen_scale=scale(request.args.get("scale")))
