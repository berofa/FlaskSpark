"""What the layout gets from the manifests: the navigation (groups and entries), the start page's tiles, the sections
modules add to pages, the templates of every page, the theme and the languages."""

from __future__ import annotations

import logging

from flask import request
from flask_babel import gettext

from flaskspark.core import config as _config, web
from flaskspark.core.module import page_sections


def _translate(text: str) -> str:
    return gettext(text) if text else text


def navigation(manifests) -> list[dict]:
    """Groups in the order of their first entry (modules in config order), entries by position; only what the visitor
    may use. An entry a module names in Module.nav_disabled() is "disabled" (greyed out, not clickable)."""
    groups: list[dict] = []
    disabled = {href for module in manifests for href in module.nav_disabled()}
    for module in manifests:
        for entry in module.NAVIGATION:
            if not web.can(entry.area):
                continue
            label = _translate(entry.group)
            group = next((g for g in groups if g["key"] == entry.group), None)
            if group is None:
                group = {"key": entry.group, "label": label, "items": []}
                groups.append(group)
            group["items"].append({"label": _translate(entry.label), "href": entry.href, "icon": entry.icon,
                                   "position": entry.position, "badge": entry.badge,
                                   "disabled": entry.href in disabled})
    # counts of any module on an entry (Module.NAV_BADGES), each only for visitors with its own area
    extra = [b for module in manifests for b in module.NAV_BADGES if web.can(b.area)]
    for group in groups:
        group["items"].sort(key=lambda item: item["position"])
        for item in group["items"]:
            item["badges"] = [*([item["badge"]] if item["badge"] else []),
                              *(b.badge for b in extra if b.href == item["href"])]
    return groups


def active_href(groups: list[dict], path: str) -> str:
    """The entry of the current page: the longest href equal to the path or a prefix of it."""
    best = ""
    for group in groups:
        for item in group["items"]:
            href = item["href"]
            if (path == href or (href != "/" and path.startswith(href.rstrip("/") + "/"))) and len(href) > len(best):
                best = href
    return best


def tiles(manifests) -> list[dict]:
    out = []
    for module in manifests:
        for tile in module.TILES:
            if web.can(tile.area):
                out.append({"label": _translate(tile.label), "href": tile.href, "icon": tile.icon,
                            "description": _translate(tile.description), "position": tile.position,
                            "module": _translate(module.LABEL)})
    return sorted(out, key=lambda t: t["position"])


def current_language(locales: list[str]) -> str:
    """The page's language: the profile's (signed in), the cookie's, the browser's, the app's default."""
    from .language import select

    return select(locales)


def language_choice(locales: list[str]) -> str:
    """What the visitor chose (the profile's language, else the cookie's) or "system"."""
    from .language import choice

    return choice(locales)


def admin_links(manifests) -> list[dict]:
    """The admins' pages in the sidebar's footer: «Settings» (always: its tab «Data» shows what modules left behind);
    only with ADMIN."""
    if not web.can(web.ADMIN):
        return []
    return [{"label": gettext("Settings"), "href": "/settings", "icon": "gear"}]


def profile_link() -> str:
    """The signed-in user's profile («Accounts»), when it exists (sign-in, a module uses accounts)."""
    from .views.profile import available

    try:
        return "/profile" if available() else ""
    except Exception:  # noqa: BLE001 - the layout must render (e.g. the tables before the migration)
        return ""


def home_entry() -> bool:
    """Does the navigation start with «Home» («/»)? config.yaml `app.home_entry`: true or false; unset («auto»): only
    while «/» is the core's own start page (the modules' tiles), not when a module or the app answers «/» itself or
    `app.start` sends it elsewhere (then «Home» would only repeat an entry)."""
    from flaskspark.core import config

    setting = config.load().section("app").get("home_entry", "auto")
    if isinstance(setting, bool):
        return setting
    from flask import current_app

    from .views.home import HomeView

    if web.start_url():
        return False
    try:
        endpoint = current_app.url_map.bind("localhost").match("/", method="GET")[0]
    except Exception:  # noqa: BLE001 - nothing (or a redirect) on «/»
        return False
    return getattr(current_app.view_functions.get(endpoint), "view_class", None) is HomeView


def context(cfg, theme, manifests, locales: list[str]) -> dict:
    groups = navigation(manifests)
    return {
        "app_title": theme.title,
        "theme": theme,
        "navigation": groups,
        "nav_active": active_href(groups, request.path),
        "home_entry": home_entry(),
        "home_tiles": lambda: tiles(manifests),
        "module_layouts": [t for m in manifests for t in m.LAYOUT],
        "page_sections": lambda page: page_sections(manifests, page),
        # config.yaml app.home_title: false leaves the start page's title (the app's name) out
        "home_title": lambda: bool(_config.load().section("app").get("home_title", True)),
        "can": web.can,
        "admin_links": admin_links(manifests),
        "profile_link": profile_link(),
        "access": web.get_access(),
        "locales": locales,
        "language": current_language(locales),
        "language_cookie": language_choice(locales),  # the visitor's choice: a code or "system" (the sidebar)
        "modules_enabled": [m.NAME for m in manifests],
        # the catalogue of the page's module for flaskspark/i18n.js (a page may name others: {% set i18n_modules = [...] %})
        "i18n_page_parts": lambda: _i18n_page_parts(manifests),
        "i18n_catalogue": _i18n_catalogue,
    }


def _i18n_page_parts(manifests) -> list[str]:
    from .views.i18n import page_parts

    return page_parts(manifests)


def _i18n_catalogue(parts) -> dict:
    from .views.i18n import catalogue

    try:
        return catalogue(list(parts or ()))
    except Exception as exc:  # noqa: BLE001 - the page must render; the scripts ask the server instead
        logging.getLogger(__name__).warning("catalogue for the page: %s", exc)
        return {}
