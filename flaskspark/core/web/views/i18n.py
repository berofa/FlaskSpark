"""Translations for scripts (flaskspark/i18n.js):

POST /api/i18n            {"keys": [...]} -> {key: translation}
GET  /api/i18n/catalog    ?modules=notes,core,app -> the whole catalogue of those parts (see catalogue())
POST /api/i18n/catalog    {"keys": [...], "plurals": [[singular, plural], ...], "modules": [...]} -> the same format,
                          also for single texts and plurals

A JSON list instead of FlaskSpark's comma separated GET parameter: source texts may contain commas.

The catalogue format: {"language": "de", "nplurals": 2, "plural": "(n != 1)", "texts": {source: translation},
"plurals": {singular: [form, ...]}}. The translations are the page's (the core's, the modules' and the app's catalogue
merged, a later one wins); the texts are those the named parts' own catalogues have.
"""

from __future__ import annotations

from pathlib import Path

from flask import jsonify, request
from flask_babel import get_locale, get_translations, gettext
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core.web import OPEN

MAX_KEYS = 500
MAX_MODULES = 20
#: the parts that are no module: the core's catalogue and the application's own
CORE, APP = "core", "app"


def _plural_rule(locale: str) -> tuple[int, str]:
    from babel.messages.plurals import get_plural

    try:
        found = get_plural(locale)
        return found.num_plurals, found.plural_expr
    except Exception:  # noqa: BLE001 - a locale Babel doesn't know: English's rule
        return 2, "(n != 1)"


def _directory(name: str):
    """The catalogue directory of a part: "core", "app" or a loaded module's name (None if unknown)."""
    from flaskspark.core import config, modules, paths
    from flaskspark.core.web.app import CORE_LOCALES

    if name == CORE:
        return CORE_LOCALES
    if name == APP:
        from flask import current_app

        own = current_app.config.get("APP_LOCALES_DIR")
        if own:
            return Path(own)
        return paths.APP_DIR / "locales" if paths.APP_DIR is not None else None
    module = modules.get(config.load(), name)
    if module is None or not module.PACKAGE:
        return None
    found = modules.directory(module)
    return found / "locales" if found is not None else None


def catalogue(names, keys=(), plurals=()) -> dict:
    """The translations in the page's language for scripts: every text of the catalogues of the parts `names` (module
    names, "core", "app"), plus the single `keys` and `plurals` ([singular, plural] pairs)."""
    from flaskspark.core import i18n

    locale = get_locale()
    language = str(locale) if locale is not None else "en"
    nplurals, rule = _plural_rule(language)
    out = {"language": language, "nplurals": nplurals, "plural": rule, "texts": {}, "plurals": {}}
    merged = get_translations()
    entries = getattr(merged, "_catalog", None) or {}

    def forms_of(singular: str, plural: str = "", own=None) -> list[str]:
        for source in (entries, getattr(own, "_catalog", None) or {}):  # the page's, else the part's own
            found = [source.get((singular, index)) for index in range(nplurals)]
            if all(found):
                return found
        return [singular] + [plural or singular] * (nplurals - 1)  # not translated: the source texts

    for name in list(dict.fromkeys(names))[:MAX_MODULES]:
        directory = _directory(str(name))
        own = i18n.catalogue(directory, language) if directory is not None else None
        for key in getattr(own, "_catalog", None) or {}:
            if isinstance(key, tuple):
                singular, index = key
                if index == 0 and singular and "\x04" not in singular:
                    out["plurals"][singular] = forms_of(singular, own=own)
            elif key and "\x04" not in key:
                translated = merged.gettext(key)
                out["texts"][key] = own.gettext(key) if translated == key else translated
    for key in list(keys)[:MAX_KEYS]:
        if isinstance(key, str) and key:
            out["texts"][key] = gettext(key)
    for pair in list(plurals)[:MAX_KEYS]:
        if isinstance(pair, (list, tuple)) and len(pair) == 2 and all(isinstance(p, str) and p for p in pair):
            out["plurals"][pair[0]] = forms_of(pair[0], pair[1])
    return out


def page_parts(manifests) -> list[str]:
    """The parts whose catalogue a page gets in the browser: the module (or the app) that owns the request's view."""
    from flask import current_app

    view = current_app.view_functions.get(request.endpoint or "")
    owner = getattr(getattr(view, "view_class", None), "__module__", None) or getattr(view, "__module__", "") or ""
    for module in manifests:
        if module.PACKAGE and (owner == module.PACKAGE or owner.startswith(module.PACKAGE + ".")):
            return [module.NAME]
    if owner and not owner.startswith("flaskspark"):
        return [APP]
    return []


class I18nView(FlaskSparkMethodView):
    url = "/api/i18n"
    endpoint = "flaskspark_core_i18n"
    area = OPEN

    def post(self):
        keys = (request.get_json(silent=True) or {}).get("keys") or []
        if not isinstance(keys, list):
            return jsonify({"error": "keys must be a list"}), 400
        return jsonify({key: gettext(key) for key in keys[:MAX_KEYS] if isinstance(key, str) and key})


class I18nCatalogueView(FlaskSparkMethodView):
    url = "/api/i18n/catalog"
    endpoint = "flaskspark_core_i18n_catalog"
    area = OPEN

    def get(self):
        names = [n.strip() for n in (request.args.get("modules") or "").split(",") if n.strip()]
        return jsonify(catalogue(names))

    def post(self):
        body = request.get_json(silent=True) or {}
        keys, plurals, names = body.get("keys") or [], body.get("plurals") or [], body.get("modules") or []
        if not all(isinstance(v, list) for v in (keys, plurals, names)):
            return jsonify({"error": "keys, plurals and modules must be lists"}), 400
        return jsonify(catalogue([str(n) for n in names], keys, plurals))
