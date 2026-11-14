"""«Settings» (admins only): the access (role x area, with sign-in), the users' roles (with sign-in), the info screens
of the modules (Module.SCREENS, a list with links; when there are any) and a tab per
module with its own sections (Module.SETTINGS: templates of the module) and its settings of config.yaml (Module.CONFIG,
flaskspark.core.settings). With OpenAccess everyone is an admin (a trusted network).

GET  /settings                        the page (tabs; /settings#access, /settings#<module> open one)
GET  /api/settings/access             {areas, roles}: the matrix (RoleAccess only, else 404)
POST /api/settings/access             one cell: {role_id, area, allowed} -> the matrix and a message
GET  /api/settings/users              {users: [{id, username, email, name, role_id, role, override, sso_role}], roles}
                                      (RoleAccess only, else 404)
POST /api/settings/users              {user_id, role_id} (role_id null: the sign-in's role again) -> the same and a
                                      message; not one's own role
GET  /api/settings/config/<module>    {settings: [{path, label, kind, …, default, value}]}
POST /api/settings/config/<module>    {values: {path: value}} (null or "": the default again) -> the same with
                                      changed (paths), restart ([{name, label}]: services that read them at their start)
                                      and a message; one value that does not fit stores none (400)
GET  /api/settings/accounts           the application's accounts (Module.APP_ACCOUNT_TYPES; the tab «Accounts»): the
                                      same API as the profile's /api/accounts (flaskspark.core.web.views.profile) with
POST /api/settings/accounts           the owner accounts.APP, without sharing; 404 when no loaded module names such a
PUT  /api/settings/accounts/<id>      type
POST /api/settings/accounts/<id>
GET  /api/settings/data               {items: [{id, kind, name, label, title, deletes, ...}]}: what modules no longer
                                      delivered and the core left behind (flaskspark.core.leftovers)
POST /api/settings/data               {items: [id, …] or ["all"]} -> removes them after a backup: {removed, backup: {db,
                                      state}, message, items (what is left)}; an id that names nothing left over
                                      removes nothing (400)
"""

from __future__ import annotations

import json
import logging

from flask import jsonify, request
from flask_babel import gettext
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core import accounts, config, leftovers, modules, settings
from flaskspark.core.web import ADMIN, get_access, user_id
from flaskspark.core.web.access import AccessError
from flaskspark.core.web.views.profile import AccountApiView, AccountsApiView, UserAccounts

log = logging.getLogger(__name__)


def _ok(data: dict):
    """An API answer: always JSON (also without an Accept header)."""
    return jsonify(data)


def _fail(message: str, status: int = 400):
    return jsonify({"error": message}), status


def _t(text: str) -> str:
    return gettext(text) if text else text


def _error(error) -> str:
    """The message of a SettingError / AccessError in the visitor's language (its label translated too)."""
    params = dict(error.params)
    if "label" in params:
        params["label"] = _t(params["label"])
    return gettext(error.template, **params)


def _shown(value, kind: str = "") -> str:
    """A value as the form shows it (a list comma separated, a structure as JSON)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if kind == "json" or isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _module(name: str):
    return next((m for m in modules.load(config.load()) if m.NAME == name and m.CONFIG), None)


def fields(module) -> list[dict]:
    """The settings of a module for the form and the API: translated, with their default and their stored value."""
    out = []
    for item in settings.view(tuple(module.CONFIG), config.load().defaults):
        effective = item["default"] if item["value"] is None else item["value"]
        out.append({
            **item,
            "label": _t(item["label"]),
            "help": _t(item["help"]),
            "group": _t(item["group"]),
            "unit": _t(item["unit"]),
            "choices": [{**c, "label": _t(c["label"])} for c in item["choices"]],
            "shown": _shown(item["value"], item["kind"]),
            "default_shown": _shown(item["default"], item["kind"]),
            "effective": effective,
            "changed": item["value"] is not None,
        })
    return out


def grouped(items: list[dict]) -> list[dict]:
    """The fields by their group, in the order of their first field: [{label, fields}]."""
    groups: list[dict] = []
    for item in items:
        group = next((g for g in groups if g["label"] == item["group"]), None)
        if group is None:
            group = {"label": item["group"], "fields": []}
            groups.append(group)
        group["fields"].append(item)
    return groups


def matrix(access) -> dict:
    data = access.matrix()
    return {
        "areas": [{**a, "label": _t(a["label"]), "description": _t(a["description"])} for a in data["areas"]],
        "roles": data["roles"],
    }


def _services(names) -> list[dict]:
    known = {s.name: s for s in modules.services(config.load())}
    return [{"name": n, "label": _t(known[n].label)} for n in sorted(set(names)) if n in known]


def _size(size: int) -> str:
    for unit in ("B", "kB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return str(size)


def _rows(n: int) -> str:
    return gettext("1 row") if n == 1 else gettext("%(n)s rows", n=n)


def data_items() -> list[dict]:
    """What is left over (flaskspark.core.leftovers.find), each with its title, its kind's label and what removing it
    deletes (deletes: lines for the confirmation), translated."""
    kinds = {
        "module": gettext("Module no longer delivered"),
        "table": gettext("Table no module describes"),
        "revision": gettext("Unknown migration revision"),
        "setting": gettext("Setting no module defines"),
        "area": gettext("Access of an area that is gone"),
        "user-setting": gettext("Personal settings of a module that is gone"),
        "state": gettext("State directory of a module that is gone"),
    }
    out = []
    for item in leftovers.find(config.load()):
        kind = item["kind"]
        deletes: list[str] = []
        detail = ""
        if kind == "module":
            for table in item["tables"]:
                deletes.append(gettext("table %(name)s (%(rows)s)", name=table["name"], rows=_rows(table["rows"])))
            for rev in item["revisions"]:
                deletes.append(gettext("migration revision %(rev)s", rev=rev))
            deletes.append(gettext("FlaskSpark's record of the module (when it comes back, it starts afresh)"))
            detail = (", ".join(f"{t['name']} ({_rows(t['rows'])})" for t in item["tables"])
                      or gettext("no tables left"))
            if item.get("version"):
                detail += " · " + gettext("last seen in version %(version)s", version=item["version"])
        elif kind == "table":
            deletes.append(gettext("table %(name)s (%(rows)s)", name=item["name"], rows=_rows(item["rows"])))
            detail = _rows(item["rows"])
        elif kind == "revision":
            deletes.append(gettext("migration revision %(rev)s", rev=item["name"]))
        elif kind == "setting":
            deletes.append(gettext("stored setting %(path)s", path=item["name"]))
            detail = json.dumps(item["value"], ensure_ascii=False)
        elif kind == "area":
            deletes.append(gettext("access of the area %(area)s for every role (%(rows)s)", area=item["name"],
                                   rows=_rows(item["rows"])))
            detail = _rows(item["rows"])
        elif kind == "user-setting":
            deletes.append(gettext("personal setting %(key)s of every user (%(rows)s)", key=item["name"],
                                   rows=_rows(item["rows"])))
            detail = gettext("module %(module)s", module=item["module"]) + " · " + _rows(item["rows"])
        elif kind == "state":
            deletes.append(gettext("directory %(path)s with everything in it (%(size)s)", path=item["path"],
                                   size=_size(item["size"])))
            detail = _size(item["size"])
        title = item["name"] if kind != "module" or item["label"] == item["name"] else f"{item['label']} ({item['name']})"
        out.append({**item, "title": title, "kind_label": kinds[kind], "detail": detail, "deletes": deletes})
    return out


def _cleaned_message(result: dict) -> str:
    made = [p for p in (result["backup"]["db"], result["backup"]["state"]) if p]
    removed = len(result["removed"])
    text = gettext("1 item removed.") if removed == 1 else gettext("%(n)s items removed.", n=removed)
    if made:
        text += " " + gettext("Backup: %(files)s", files=", ".join(made))
    return text


def screen_items(manifests=None) -> list[dict]:
    """The info screens of the loaded modules (Module.SCREENS) for the tab «Screens»: key, title, description, icon,
    module (its label), area (its label), mode, reload_at and url, translated, by position."""
    from flask import url_for

    from flaskspark.core.web.access import areas
    from flaskspark.core.web.views import screen as screens

    loaded = manifests if manifests is not None else modules.load(config.load())
    known = areas(loaded)
    out = []
    for item, module in screens.declared(loaded):
        area = known.get(item.area)
        out.append({
            "key": item.key,
            "title": _t(item.title),
            "description": _t(item.description),
            "icon": item.icon or "display",
            "module": _t(module.LABEL) or module.NAME,
            "module_name": module.NAME,
            "area": _t(area.label) if area is not None else item.area,
            "area_key": item.area,
            "mode": item.mode,
            "reload_at": item.reload_at,
            "url": url_for("flaskspark_screen", key=item.key),
            "sections": len(screens.sections(item, loaded)),
        })
    return out


def app_offered(cfg=None) -> dict[str, list]:
    """The types of the application's accounts: key -> the manifests of the loaded modules that name it
    (APP_ACCOUNT_TYPES). Admins may use every module."""
    return accounts.used_types(cfg or config.load(), app=True)


class AppAccounts(UserAccounts):
    """The application's accounts (owner accounts.APP) for the admins: no sharing, no presets with sso_user."""

    app = True

    def owner(self) -> int:
        return accounts.APP

    def available(self) -> bool:
        return bool(app_offered())

    def offered(self, cfg) -> dict[str, list]:
        return app_offered(cfg)

    def username(self) -> str:
        return ""

    def unavailable(self):
        return _fail(gettext("No module uses accounts of the application."), status=404)


class AppAccountsApiView(AccountsApiView):
    url = "/api/settings/accounts"
    endpoint = "core_settings_accounts"
    area = ADMIN
    scope = AppAccounts()


class AppAccountApiView(AccountApiView):
    url = "/api/settings/accounts/<int:account_id>"
    endpoint = "core_settings_account"
    area = ADMIN
    scope = AppAccounts()


class SettingsView(FlaskSparkMethodView):
    url = "/settings"
    endpoint = "core_settings"
    area = ADMIN

    def get(self):
        from flask import render_template

        access = get_access()
        tabs = [{"name": m.NAME, "label": _t(m.LABEL), "sections": tuple(m.SETTINGS),
                 "groups": grouped(fields(m)) if m.CONFIG else []}
                for m in modules.load(config.load()) if m.CONFIG or m.SETTINGS]
        return render_template("flaskspark/settings.html", tabs=tabs,
                               matrix=matrix(access) if access.HAS_MATRIX else None,
                               users=access.users() if access.HAS_USERS else None, me=user_id(),
                               app_accounts=bool(app_offered()), screens=screen_items(), leftovers=data_items())


class AccessApiView(FlaskSparkMethodView):
    url = "/api/settings/access"
    endpoint = "core_settings_access"
    area = ADMIN

    def get(self):
        access = get_access()
        if not access.HAS_MATRIX:
            return _fail(gettext("No sign-in: everyone may use everything."), status=404)
        return _ok(matrix(access))

    def post(self):
        access = get_access()
        if not access.HAS_MATRIX:
            return _fail(gettext("No sign-in: everyone may use everything."), status=404)
        body = request.get_json(silent=True) or {}
        allowed = body.get("allowed")
        if isinstance(allowed, str):
            allowed = allowed.lower() in settings.TRUE
        try:
            access.set_allowed(int(body.get("role_id") or 0), str(body.get("area") or ""), bool(allowed))
        except AccessError as error:
            return _fail(_error(error))
        except (TypeError, ValueError):
            return _fail(gettext("Unknown role or area."))
        return _ok({**matrix(access), "message": gettext("Saved.")})


def _users(access) -> dict:
    return {"users": access.users(), "roles": [{"id": r["id"], "name": r["name"]} for r in access.matrix()["roles"]]}


class UsersApiView(FlaskSparkMethodView):
    url = "/api/settings/users"
    endpoint = "core_settings_users"
    area = ADMIN

    def get(self):
        access = get_access()
        if not access.HAS_USERS:
            return _fail(gettext("No sign-in: everyone may use everything."), status=404)
        return _ok(_users(access))

    def post(self):
        access = get_access()
        if not access.HAS_USERS:
            return _fail(gettext("No sign-in: everyone may use everything."), status=404)
        body = request.get_json(silent=True) or {}
        try:
            role_id = int(body["role_id"]) if body.get("role_id") not in (None, "") else None
            access.set_user_role(int(body.get("user_id") or 0), role_id)
        except AccessError as error:
            return _fail(_error(error))
        except (TypeError, ValueError):
            return _fail(gettext("Unknown user."))
        return _ok({**_users(access), "message": gettext("Saved.")})


class ConfigApiView(FlaskSparkMethodView):
    url = "/api/settings/config/<name>"
    endpoint = "core_settings_config"
    area = ADMIN

    def get(self, name: str):
        module = _module(name)
        if module is None:
            return _fail(gettext("No settings."), status=404)
        return _ok({"settings": fields(module)})

    def post(self, name: str):
        module = _module(name)
        if module is None:
            return _fail(gettext("No settings."), status=404)
        values = (request.get_json(silent=True) or {}).get("values")
        if not isinstance(values, dict):
            return _fail(gettext("No values."))
        try:
            changed = settings.save(tuple(module.CONFIG), values, user_id())
        except settings.SettingError as error:
            return _fail(_error(error))
        by_path = {s.path: s for s in module.CONFIG}
        restart = _services(n for p in changed for n in by_path[p].services)
        if not changed:
            message = gettext("Nothing changed.")
        elif restart:
            message = gettext("Saved. Takes effect after a restart of: %(services)s",
                              services=", ".join(s["label"] for s in restart))
        else:
            message = gettext("Saved, takes effect now.")
        return _ok({"settings": fields(module), "changed": changed, "restart": restart,
                                     "message": message})


class DataApiView(FlaskSparkMethodView):
    url = "/api/settings/data"
    endpoint = "core_settings_data"
    area = ADMIN

    def get(self):
        return _ok({"items": data_items()})

    def post(self):
        items = (request.get_json(silent=True) or {}).get("items")
        if not isinstance(items, list) or not items or not all(isinstance(i, str) for i in items):
            return _fail(gettext("Nothing chosen."))
        try:
            result = leftovers.clean(config.load(), items)
        except leftovers.LeftoverError:
            return _fail(gettext("Not left over (any more): reload the page."))
        except Exception as error:  # noqa: BLE001 - e.g. a table another one still refers to: said, not hidden
            log.exception("clean-up of %s failed", ", ".join(items))
            return _fail(gettext("Clean-up failed: %(error)s", error=str(error)), status=500)
        return _ok({**result, "message": _cleaned_message(result), "items": data_items()})
