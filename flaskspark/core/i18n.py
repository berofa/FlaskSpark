"""Translations in Python code: the visitor's language in a request, the application's language elsewhere.

    from flaskspark.core.i18n import N_, ntr, tr

    tr("Saved")                                        # the visitor's language in a request, else the application's
    tr("%(n)s of %(total)s", n=3, total=7)             # %(name)s params; the text is positional-only
    ntr("%(num)s file", "%(num)s files", n)            # the plural for n (%(num)s is n)
    LABEL = N_("Notes")                                # only marks a text; translated where it is shown
    current_language()                                 # the language tr() translates into right now ("de")

Which language tr() uses, the first that applies:

1. `using(locale)` (a block of code in a chosen language; a service answering a request in the requester's language,
   see `with_request_language`),
2. inside a request the visitor's (Flask-Babel's locale: profile, cookie, browser, the app's default),
3. the application's language: config.yaml `notifications.language`, else the first of `app.locales` ("en" without).

The catalogues are the web app's (flaskspark.core.web.app.translation_directories): the core's, the loaded modules'
(<package>/locales), the application's own; a later one wins for every text it translates. They are loaded once per
process and language and loaded again when one of their .mo files changes (its mtime, looked at once a second).

Older API, still there: `gettext(text, locale=None, cfg=None, **params)` (the application's language unless `locale`
is given, also in a request), `language(cfg)` (the application's language), `translations(locale, cfg)`.

Services over NATS: the core's request client (flaskspark.core.events.request) sends the current language as the
header `Accept-Language`; a handler decorated with `with_request_language` (or `with using(language_of(msg))`)
translates its answer into it.
"""

from __future__ import annotations

import functools
import gettext as _gettext
import inspect
import logging
import os
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from .module import N_

log = logging.getLogger(__name__)

#: the NATS header that carries the requester's language (like HTTP's)
HEADER = "Accept-Language"
#: a short alternative a client may send instead
SHORT_HEADER = "lang"

_chosen: ContextVar[str | None] = ContextVar("flaskspark_i18n_language", default=None)
_lock = threading.Lock()
_dirs: tuple[str, ...] | None = None  # the process's catalogues (cfg None), found once
_catalogues: dict[tuple[str, tuple[str, ...]], tuple[tuple, object]] = {}  # (locale, dirs) -> (stamp, merged)
_files: dict[tuple[str, str], tuple[tuple, object]] = {}  # (directory, locale) -> (stamp, that directory's catalogue)
_checked: dict[tuple, float] = {}  # cache key -> when its .mo files were last looked at
#: seconds between two looks at the mtimes of a cached catalogue's .mo files
CHECK_INTERVAL = 1.0


def language(cfg=None) -> str:
    """The application's language for texts outside a request (current_language() is the one tr() uses)."""
    if cfg is None:
        from . import config

        try:
            cfg = config.load()
        except OSError:
            return "en"
    chosen = (cfg.section("notifications") or {}).get("language")
    if chosen:
        return str(chosen)
    locales = cfg.section("app").get("locales") or ["en"]
    return str(locales[0])


def app_language(cfg=None) -> str:
    """The application's language (the same as language(cfg))."""
    return language(cfg)


def locales(cfg=None) -> list[str]:
    """The languages of the application (config.yaml `app.locales`, ["en"] without)."""
    if cfg is None:
        from . import config

        try:
            cfg = config.load()
        except OSError:
            return ["en"]
    return [str(code) for code in (cfg.section("app").get("locales") or ["en"])]


def directories(cfg=None) -> list[Path]:
    """The catalogues in the order they are merged: the core's, the loaded modules', the application's."""
    from . import modules, paths
    from .web.app import CORE_LOCALES

    if cfg is None:
        from . import config

        cfg = config.load()
    out = [CORE_LOCALES, *modules.locale_dirs(cfg)]
    if paths.APP_DIR is not None:
        out.append(paths.APP_DIR / "locales")
    elif paths.WEB_DIR is not None and (paths.WEB_DIR / "app" / "locales").is_dir():
        out.append(paths.WEB_DIR / "app" / "locales")  # the classic layout's web/app
    return [d for d in out if d.is_dir()]


def _process_directories() -> tuple[str, ...]:
    """The catalogues of this process (its modules don't change while it runs): looked up once."""
    global _dirs
    if _dirs is None:
        try:
            found = tuple(str(d) for d in directories())
        except Exception as exc:  # noqa: BLE001 - no configuration (a process outside an application): source texts
            log.debug("translations: %s", exc)
            return ()
        _dirs = found
    return _dirs


def _stamp(locale: str, dirs: tuple[str, ...]) -> tuple:
    """The .mo files of `locale` in `dirs` with their mtimes: a catalogue is loaded again when this changes."""
    out = []
    for directory in dirs:
        for path in _gettext.find("messages", directory, [locale], all=True):
            try:
                out.append((path, os.stat(path).st_mtime_ns))
            except OSError:
                pass
    return tuple(out)


def _load(locale: str, dirs: tuple[str, ...]):
    from babel.support import NullTranslations, Translations

    merged = None
    for directory in dirs:
        found = Translations.load(directory, [locale])
        if isinstance(found, Translations):
            merged = found if merged is None else merged.merge(found)
    return merged or NullTranslations()


def _cached(locale: str, dirs: tuple[str, ...]):
    key = (locale, dirs)
    hit = _catalogues.get(key)
    now = time.monotonic()
    if hit is not None and now - _checked.get(key, 0.0) < CHECK_INTERVAL:
        return hit[1]
    stamp = _stamp(locale, dirs)
    if hit is not None and hit[0] == stamp:
        _checked[key] = now
        return hit[1]
    loaded = _load(locale, dirs)
    with _lock:
        _catalogues[key] = (stamp, loaded)
        _checked[key] = now
    return loaded


def translations(locale: str | None = None, cfg=None):
    """The merged catalogue of `locale` (default: language(cfg)), cached per process and language (loaded again when
    one of its .mo files changes)."""
    if cfg is None:
        dirs = _process_directories()
    else:
        try:
            dirs = tuple(str(d) for d in directories(cfg))
        except Exception as exc:  # noqa: BLE001 - no configuration: the source texts
            log.debug("translations: %s", exc)
            dirs = ()
    return _cached(locale or language(cfg), dirs)


def catalogue(directory: str | Path, locale: str):
    """The catalogue of one directory (e.g. a module's <package>/locales) in `locale`, cached like translations();
    None without a .mo file. Which texts a module has, e.g. for the browser's preloadCatalog()."""
    from babel.support import Translations

    directory = str(directory)
    key = (directory, locale)
    hit = _files.get(key)
    now = time.monotonic()
    if hit is not None and now - _checked.get(("file", *key), 0.0) < CHECK_INTERVAL:
        return hit[1]
    stamp = _stamp(locale, (directory,))
    if hit is not None and hit[0] == stamp:
        _checked[("file", *key)] = now
        return hit[1]
    found = Translations.load(directory, [locale]) if stamp else None
    found = found if isinstance(found, Translations) else None
    with _lock:
        _files[key] = (stamp, found)
        _checked[("file", *key)] = now
    return found


def gettext(text: str, locale: str | None = None, cfg=None, **params) -> str:
    """`text` (an English source text) in `locale` (default: the application's language), with %(name)s params."""
    if not text:
        return text
    translated = translations(locale, cfg).gettext(text)
    return translated % params if params else translated


# -- the current language: using() > the visitor's (in a request) > the application's ------------------------------


def _request_babel() -> bool:
    """Inside a request of an app with Flask-Babel?"""
    try:
        from flask import current_app, has_request_context
    except ImportError:  # pragma: no cover - a process without Flask
        return False
    return has_request_context() and "babel" in current_app.extensions


def current_language() -> str:
    """The language tr() translates into right now: using() > the visitor's (in a request) > the application's."""
    chosen = _chosen.get()
    if chosen:
        return chosen
    if _request_babel():
        from flask_babel import get_locale

        found = get_locale()
        if found is not None:
            return str(found)
    return language()


@contextmanager
def using(locale: str | None):
    """tr() and current_language() in `locale` inside the block (None or "": unchanged), e.g. a service answering a
    request in the requester's language. Per thread and per asyncio task (a context variable)."""
    token = _chosen.set(locale or _chosen.get())
    try:
        yield
    finally:
        _chosen.reset(token)


def tr(text: str, /, **params) -> str:
    """`text` (an English source text) in the current language (current_language()), with %(name)s params."""
    if not text:
        return text
    chosen = _chosen.get()
    if chosen is None and _request_babel():
        from flask_babel import gettext as babel_gettext

        return babel_gettext(text, **params)
    translated = translations(chosen or language()).gettext(text)
    return translated % params if params else translated


def ntr(singular: str, plural: str, n: int, /, **params) -> str:
    """The singular or the plural text for `n` in the current language (%(num)s is n)."""
    chosen = _chosen.get()
    if chosen is None and _request_babel():
        from flask_babel import ngettext as babel_ngettext

        return babel_ngettext(singular, plural, n, **params)
    translated = translations(chosen or language()).ngettext(singular, plural, n)
    return translated % {"num": n, **params}


# -- the requester's language over NATS -------------------------------------------------------------------------


def best_match(header: str | None, supported: list[str] | None = None) -> str | None:
    """The first language of an Accept-Language value ("de-CH,de;q=0.9,en;q=0.5", "de") the application supports
    (default its `app.locales`); None without one."""
    if not header:
        return None
    supported = supported if supported is not None else locales()
    weighted = []
    for position, part in enumerate(str(header).split(",")):
        code, _, rest = part.strip().partition(";")
        quality = 1.0
        rest = rest.strip()
        if rest.startswith("q="):
            try:
                quality = float(rest[2:])
            except ValueError:
                quality = 0.0
        if code.strip() and quality > 0:
            weighted.append((-quality, position, code.strip().replace("-", "_").lower()))
    by_lower = {code.lower(): code for code in supported}
    for _quality, _position, code in sorted(weighted):
        if code in by_lower:
            return by_lower[code]
        if code.split("_")[0] in by_lower:
            return by_lower[code.split("_")[0]]
    return None


def request_headers(headers: dict | None = None) -> dict:
    """NATS headers for a request to a service: `headers` with the current language as Accept-Language (unless they
    name one). flaskspark.core.events.request adds it by itself."""
    out = dict(headers or {})
    if HEADER not in out and SHORT_HEADER not in out:
        try:
            out[HEADER] = current_language()
        except Exception as exc:  # noqa: BLE001 - no configuration: no header, the service takes its own language
            log.debug("request_headers: %s", exc)
    return out


def language_of(msg_or_headers, supported: list[str] | None = None) -> str | None:
    """The requester's language of a NATS message (its header Accept-Language or lang) or of a dict of headers, when
    the application supports it; else None (tr() then takes the application's language)."""
    headers = getattr(msg_or_headers, "headers", msg_or_headers) or {}
    try:
        found = headers.get(HEADER) or headers.get(SHORT_HEADER)
    except AttributeError:
        return None
    return best_match(found, supported)


def with_request_language(handler):
    """A NATS message handler (`async def handler(msg)`, a method `handler(self, msg)`, or a synchronous one) that
    runs in the requester's language: tr() inside it answers in that language."""

    def message_of(args):
        return args[-1] if args else None

    if inspect.iscoroutinefunction(handler):
        @functools.wraps(handler)
        async def run_async(*args, **kwargs):
            with using(language_of(message_of(args))):
                return await handler(*args, **kwargs)
        return run_async

    @functools.wraps(handler)
    def run(*args, **kwargs):
        with using(language_of(message_of(args))):
            return handler(*args, **kwargs)
    return run


def reset() -> None:
    """Forget the loaded catalogues and where they are (tests)."""
    global _dirs
    with _lock:
        _dirs = None
        _catalogues.clear()
        _files.clear()
        _checked.clear()


__all__ = ["HEADER", "N_", "app_language", "best_match", "catalogue", "current_language", "directories", "gettext",
           "language", "language_of", "locales", "ntr", "request_headers", "reset", "tr", "translations", "using",
           "with_request_language"]
