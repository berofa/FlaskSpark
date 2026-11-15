"""The profile of the signed-in user: the language (with more than one in `app.locales`; flaskspark.core.web.language),
the sections the modules add (Module.PAGE_SECTIONS["profile"], of the modules the visitor may use) and «Accounts»
(flaskspark.core.accounts). Only with sign-in (RoleAccess) and only when there is something to show: a section, or a
loaded module names account types (Module.ACCOUNT_TYPES); else the page answers 404 (the sidebar's language buttons
keep a signed-in user's language then), and the accounts' API whenever no type is offered. A type is offered to users
who may use one of the modules that name it (one of its areas, or it has none).

GET  /profile                     the page (<ui-user-accounts>)
GET  /api/accounts                {accounts, shared, types, providers, user}: the user's accounts (with the modules
                                  that use them), those shared with the user's role, the types offered (with their
                                  fields) and the presets
POST /api/accounts                {provider, name, username, password, types: {key: settings}} -> a new account, kept
                                  only if every type signs in
PUT  /api/accounts/<id>           {name?, password?, types?: {key: settings | null (remove)}}
POST /api/accounts/<id>           {action: test | activate | deactivate | delete}

Sharing an account: the generic /api/shares/account/<id> (flaskspark.core.web.views.shares).

The same API serves the application's accounts (Module.APP_ACCOUNT_TYPES) to the admins: /api/settings/accounts
(flaskspark.core.web.views.settings, AppAccounts: owner accounts.APP, no sharing, no presets with sso_user).
"""

from __future__ import annotations

from flask import abort, jsonify, render_template, request
from flask_babel import gettext
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core import accounts, config, db, shares
from flaskspark.core.accounts import store
from flaskspark.core.module import N_, page_sections
from flaskspark.core.secrets import SecretKeyError
from flaskspark.core.web import OPEN, can, get_access, user_id


def _ok(data: dict):
    return jsonify(data)


def _fail(message: str, status: int = 400):
    return jsonify({"error": message}), status


def _t(text: str) -> str:
    return gettext(text) if text else text


def message(error) -> str:
    """An AccountError in the visitor's language (its labels translated too)."""
    params = dict(getattr(error, "params", {}) or {})
    for key in ("label", "type"):
        if isinstance(params.get(key), str):
            params[key] = _t(params[key])
    template = getattr(error, "template", None)
    return gettext(template, **params) if template else str(error)


def _usable(manifest) -> bool:
    """May the visitor use the module (one of its areas, or it has none)?"""
    return not manifest.AREAS or any(can(area.key) for area in manifest.AREAS)


def offered(cfg=None) -> dict[str, list]:
    """The types offered to the visitor: key -> the manifests of the modules (usable by the visitor) that name it."""
    cfg = cfg or config.load()
    out = {}
    for key, manifests in accounts.used_types(cfg).items():
        usable = [m for m in manifests if _usable(m)]
        if usable:
            out[key] = usable
    return out


def sections(cfg=None) -> list[str]:
    """The templates the modules the visitor may use add to the profile (PAGE_SECTIONS["profile"])."""
    from flaskspark.core import modules

    return page_sections([m for m in modules.load(cfg or config.load()) if _usable(m)], "profile")


def _signed_in() -> bool:
    return bool(get_access().signed_in and user_id())


def accounts_available() -> bool:
    """The visitor has accounts: signed in, and some module they may use uses accounts."""
    return bool(_signed_in() and offered())


def languages(cfg=None) -> list[str]:
    """The languages a user may choose in the profile (config.yaml `app.locales`; none with a single language)."""
    found = list((cfg or config.load()).section("app").get("locales") or ["en"])
    return found if len(found) > 1 else []


def _without_sign_in() -> bool:
    """The app has no sign-in at all (auth: none, OpenAccess): everyone is the same visitor."""
    from ..access import OpenAccess

    return isinstance(get_access(), OpenAccess)


def available() -> bool:
    """The profile exists for the visitor: signed in, and a section or accounts to show (the language alone makes no
    profile: the sidebar's language buttons keep a signed-in user's choice too). In an app without sign-in (auth: none)
    it exists as soon as a module adds a section: settings of this workstation or browser (e.g. kept by an agent on
    it); accounts and the personal language need a sign-in."""
    if _signed_in():
        return bool(sections() or offered())
    return bool(_without_sign_in() and sections())


def _username() -> str:
    from flask_login import current_user

    return str(getattr(current_user, "username", "") or "")


class UserAccounts:
    """Whose accounts the API serves and which types it offers: the signed-in user's (the profile). AppAccounts
    (flaskspark.core.web.views.settings) serves the application's to the admins."""

    app = False

    def owner(self) -> int:
        return user_id()

    def available(self) -> bool:
        return accounts_available()

    def offered(self, cfg) -> dict[str, list]:
        return offered(cfg)

    def username(self) -> str:
        return _username()

    def unavailable(self):
        return _fail(gettext("Accounts need a sign-in."), 404)


def _data(s, cfg, scope: UserAccounts | None = None) -> dict:
    scope = scope or UserAccounts()
    uid = scope.owner()
    types = scope.offered(cfg)
    known = accounts.account_types()
    users_of = {key: [_t(m.LABEL) for m in manifests]
                for key, manifests in accounts.used_types(cfg, app=scope.app).items()}
    mine = []
    for account in store.of_user(s, uid):
        data = store.serialize(s, account, _t)
        data["modules"] = sorted({label for key in data["types"] for label in users_of.get(key, [])})
        data["shares"] = {} if scope.app else shares.targets(accounts.SHARE_TYPE, account.id, session=s)
        mine.append(data)
    shared = []
    granted = {} if scope.app else shares.shared_with(uid, accounts.SHARE_TYPE, session=s)
    if granted:
        from flaskspark.core.models import Account

        people = shares.users(s)
        for account in s.scalars(db.select(Account).where(Account.id.in_(list(granted))).order_by(Account.name)):
            rows = store.type_rows(s, account.id)
            shared.append({"id": account.id, "name": account.name, "username": account.username,
                           "owner": people.get(account.user_id, {}).get("username", "?"),
                           "permission": granted[account.id], "is_active": bool(account.is_active),
                           "types": [_t(known[k].LABEL) if k in known else k for k in rows]})
    presets = []
    for provider in accounts.providers(cfg).values():
        offers = {k: v for k, v in provider.settings.items() if k in types}
        if offers and not (scope.app and provider.sso_user):
            presets.append({"key": provider.key, "label": provider.label, "sso_user": provider.sso_user,
                            "types": offers})
    presets.append({"key": accounts.CUSTOM, "label": gettext("Own server"), "sso_user": False, "types": {}})

    def type_data(key: str) -> dict:
        data = known[key].as_dict()
        data["label"], data["secret_label"] = _t(data["label"]), _t(data["secret_label"])
        data["modules"] = [_t(m.LABEL) for m in types[key]]
        for f in data["fields"]:
            f["label"], f["help"] = _t(f["label"]), _t(f["help"])
            f["choices"] = [{**c, "label": _t(c["label"])} for c in f["choices"]]
        return data

    return {"accounts": mine, "shared": shared, "types": [type_data(k) for k in types], "providers": presets,
            "user": scope.username(), "app": scope.app,
            "roles": [] if scope.app else shares.roles(s, accounts.SHARE_TYPE)}


def _wanted(raw) -> dict:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise accounts.AccountError(N_("The services are not readable."))
    return raw


def _test(account_id: int, keys, cfg) -> tuple[list[str], list[str], set[str]]:
    """Each type signs in: (successes, errors, keys that failed), as texts for the user."""
    reader = accounts.for_module(db.CORE, cfg)
    ok, errors, failed = [], [], set()
    for key in keys:
        found = reader.get(account_id, key)
        if found is None:
            continue
        label = _t(accounts.get_type(key).LABEL)
        try:
            result = accounts.run_test(found, cfg)
            ok.append(f"{label}: {gettext(result.text, **dict(result.params or {}))}")
        except (accounts.AccountError, SecretKeyError) as error:
            errors.append(f"{label}: {message(error)}")
            failed.add(key)
    return ok, errors, failed


def _body() -> dict:
    return request.get_json(silent=True) or {}


class ProfilePageView(FlaskSparkMethodView):
    url = "/profile"
    endpoint = "core_profile"
    area = OPEN

    def get(self):
        if not available():
            abort(404)
        from .. import language

        locales = languages() if _signed_in() else []  # without sign-in the sidebar's buttons choose the language
        return render_template("flaskspark/profile.html", sections=sections(), accounts=accounts_available(),
                               languages=language.options(locales) if locales else [],
                               language_choice=language.choice(locales) if locales else "")


class AccountsApiView(FlaskSparkMethodView):
    url = "/api/accounts"
    endpoint = "core_accounts"
    area = OPEN
    scope = UserAccounts()

    def get(self):
        if not self.scope.available():
            return self.scope.unavailable()
        cfg = config.load()
        with db.session() as s:
            return _ok(_data(s, cfg, self.scope))

    def post(self):
        scope = self.scope
        if not scope.available():
            return scope.unavailable()
        cfg = config.load()
        body = _body()
        owner = scope.owner()
        try:
            with db.session() as s:
                account, keys = store.create(s, cfg, owner, scope.username(), str(body.get("provider") or ""),
                                             str(body.get("name") or ""), str(body.get("username") or ""),
                                             str(body.get("password") or ""), _wanted(body.get("types")),
                                             allowed=set(scope.offered(cfg)))
                account_id = account.id
        except (accounts.AccountError, SecretKeyError) as error:
            return _fail(message(error))
        ok, errors, _failed = _test(account_id, keys, cfg)
        if errors:
            with db.session() as s:  # a new account that can't sign in is not kept
                store.delete(s, account_id, owner, check=False)
            return _fail(gettext("Connection failed: %(errors)s", errors="; ".join(errors)))
        accounts.changed(accounts.AccountChange("connected", account_id, owner, tuple(keys)))
        with db.session() as s:
            return _ok({**_data(s, cfg, scope), "id": account_id,
                        "message": gettext("Account connected.") + (" " + ", ".join(ok) if ok else "")})


class AccountApiView(FlaskSparkMethodView):
    url = "/api/accounts/<int:account_id>"
    endpoint = "core_account"
    area = OPEN
    scope = UserAccounts()

    def put(self, account_id: int):
        scope = self.scope
        if not scope.available():
            return scope.unavailable()
        cfg = config.load()
        body = _body()
        owner = scope.owner()
        try:
            wanted = _wanted(body.get("types"))
            with db.session() as s:
                had = set(store.type_rows(s, store.get(s, account_id, owner).id))
                _account, keys = store.update(s, cfg, account_id, owner, name=body.get("name"),
                                              password=body.get("password") or None, wanted=wanted,
                                              allowed=set(scope.offered(cfg)) | had)
        except (accounts.AccountError, SecretKeyError) as error:
            return _fail(message(error))
        text = gettext("Account saved.")
        if keys:
            ok, errors, failed = _test(account_id, keys, cfg)
            new_failed = {k for k in failed if k not in had}
            if new_failed:  # a type just added that can't sign in is not kept
                with db.session() as s:
                    store.update(s, cfg, account_id, owner, wanted={k: None for k in new_failed}, check=False)
            if errors:
                text += " " + gettext("Connection failed: %(errors)s", errors="; ".join(errors))
                if new_failed:
                    text += " " + gettext("(not added)")
            if ok:
                text += " " + ", ".join(ok)
        with db.session() as s:
            now = set(store.type_rows(s, account_id))
        accounts.changed(accounts.AccountChange("changed", account_id, owner, tuple(sorted(had | now))))
        with db.session() as s:
            return _ok({**_data(s, cfg, scope), "message": text})

    def post(self, account_id: int):
        scope = self.scope
        if not scope.available():
            return scope.unavailable()
        cfg = config.load()
        action = _body().get("action")
        owner = scope.owner()
        try:
            with db.session() as s:
                keys = list(store.type_rows(s, store.get(s, account_id, owner).id))
                concerned = set() if scope.app else shares.audience(accounts.SHARE_TYPE, account_id, session=s)
                if action == "test":
                    pass
                elif action in ("activate", "deactivate"):
                    store.set_active(s, account_id, owner, action == "activate")
                    text = gettext("Account switched on.") if action == "activate" else gettext("Account switched off.")
                elif action == "delete":
                    store.delete(s, account_id, owner)
                    text = gettext("Account removed (the data on the servers stays).")
                else:
                    return _fail(gettext("Unknown action."))
        except (accounts.AccountError, SecretKeyError) as error:
            return _fail(message(error))
        if action == "test":
            ok, errors, _failed = _test(account_id, keys, cfg)
            if errors:
                with db.session() as s:
                    return _ok({**_data(s, cfg, scope), "ok": False,
                                "error": gettext("Connection failed: %(errors)s", errors="; ".join(errors))}), 400
            text = gettext("Connection works: %(results)s", results=", ".join(ok))
        else:
            change = {"activate": "activated", "deactivate": "deactivated", "delete": "removed"}[action]
            accounts.changed(accounts.AccountChange(change, account_id, owner, tuple(keys)), concerned)
        with db.session() as s:
            return _ok({**_data(s, cfg, scope), "message": text})
