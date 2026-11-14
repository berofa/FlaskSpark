"""The visitor's language in the built-in web app, the first that applies:

1. the signed-in user's choice in the profile (the personal setting `core.language`, table core_user_settings: the
   same on every device),
2. the cookie `lang` (the sidebar's buttons; also without sign-in),
3. the browser's Accept-Language,
4. the application's default (the first of `app.locales`).

Without sign-in (OpenAccess) only 2 to 4 apply, as before. A signed-in user who picks a language in the sidebar or in
the profile changes the profile's choice (and the cookie); «browser default» removes both.
"""

from __future__ import annotations

import logging

from flask import request

log = logging.getLogger(__name__)

#: the personal setting that keeps the profile's language: {"code": "de"}
SETTING = "core.language"
#: the cookie of the sidebar's language buttons
COOKIE = "lang"
SYSTEM = "system"


def _signed_in_user() -> int:
    from . import get_access, user_id

    try:
        access = get_access()
        return int(user_id()) if access.signed_in else 0
    except Exception:  # noqa: BLE001 - no access yet (an error page early in a request)
        return 0


def profile_language(locales: list[str]) -> str | None:
    """The signed-in user's language from the profile, if it is one of `locales`; None without sign-in or choice."""
    if not _signed_in_user():
        return None
    from flask import g

    if not hasattr(g, "_core_profile_language"):  # once per request (the locale, the layout)
        from .user_settings import load

        try:
            g._core_profile_language = load(SETTING).get("code")
        except Exception as exc:  # noqa: BLE001 - e.g. the table before the migration: the next source decides
            log.debug("profile language: %s", exc)
            g._core_profile_language = None
    code = g._core_profile_language
    return code if code in locales else None


def cookie_language(locales: list[str]) -> str | None:
    code = request.cookies.get(COOKIE)
    return code if code in locales else None


def choice(locales: list[str]) -> str:
    """What the visitor chose: a code of `locales` (the profile's, else the cookie's) or "system" (the browser's)."""
    return profile_language(locales) or cookie_language(locales) or SYSTEM


def select(locales: list[str]) -> str:
    """The language of the page: profile > cookie > browser > the application's default."""
    return (profile_language(locales) or cookie_language(locales)
            or request.accept_languages.best_match(locales) or locales[0])


def remember(code: str, locales: list[str]) -> bool:
    """Keep the signed-in user's choice in the profile (a code of `locales`, or "system": none). False without
    sign-in (then only the cookie counts)."""
    if not _signed_in_user():
        return False
    from flask import g

    from .user_settings import save

    save(SETTING, {"code": code} if code in locales else {})
    g.pop("_core_profile_language", None)
    return True


def options(locales: list[str]) -> list[dict]:
    """The choices for a selection: "system" and every language with its name in the page's language."""
    from babel import Locale
    from flask_babel import get_locale, gettext

    shown_in = get_locale() or Locale.parse(locales[0])
    out = [{"code": SYSTEM, "label": gettext("Browser default")}]
    for code in locales:
        try:
            name = Locale.parse(code).get_display_name(shown_in) or code
        except Exception:  # noqa: BLE001 - a code Babel doesn't know
            name = code
        out.append({"code": code, "label": name[:1].upper() + name[1:]})
    return out


__all__ = ["COOKIE", "SETTING", "SYSTEM", "choice", "cookie_language", "options", "profile_language", "remember",
           "select"]
