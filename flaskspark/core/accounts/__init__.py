"""Accounts of the users: a user connects an account once (one login at a provider: user name and password) and
switches on what it offers, e.g. mail (IMAP), sending (SMTP), calendars (CalDAV) and contacts (CardDAV) on one host.
The modules use them without asking the user again.

- Types (types.py): AccountType with its fields and its connection test; the core ships imap, smtp, caldav, carddav
  and gitlab (flaskspark.core.gitlab), a module registers more in Module.register() (register_type()).
- A module names the types it uses in its manifest: ACCOUNT_TYPES = ("imap", "smtp"). The profile («Accounts», for
  the signed-in user) offers only types a loaded module names, and only to users who may use that module (one of its
  areas, or it has none). Without sign-in (OpenAccess) there is no user: no profile, no accounts.
- Accounts of the application (APP_ACCOUNT_TYPES = ("gitlab",)): accounts that belong to no person but to the
  application (owner APP, i.e. user id 0), kept by the admins in «Settings» → «Accounts» (also without sign-in, where
  everyone is an admin), e.g. the token a service uses to read GitLab for everyone. A module reads them with
  for_module(...).app(type) / app_account(type); they are never shared and never among a user's accounts.
- Tables (flaskspark.core.models): core_accounts (the login; the password encrypted, flaskspark.core.secrets under
  the name "accounts": APP_SECRET_KEY, or APP_SECRET_KEY_ACCOUNTS when set) and core_account_types (one row per
  type: its settings as JSON, its last test).
- Presets (Provider): config.yaml accounts.providers or register_provider(): what a provider sets per type.
- Sharing: an account can be shared with roles (flaskspark.core.shares, type "account"): a module then also reads
  the accounts others shared with the user (for_user(..., shared=True)).

The API for a module, with the module's rights like the database's (only the types its manifest names; the core
reaches all):

    from flaskspark.core import accounts

    mail = accounts.for_module("mail")
    for account in mail.for_user(user_id, "imap"):     # AccountAccess: id, name, username, password, settings, …
        connect(account.settings["host"], account.username, account.password)
    mail.all("imap")                                   # every active user's account with IMAP (a service)
    mail.record_test(account_id, "imap", ok=False, error="refused")

    tracker = accounts.for_module("tracker")           # its manifest: APP_ACCOUNT_TYPES = ("gitlab",)
    account = tracker.app_account("gitlab")            # the application's first active GitLab account, or None

Changes (connected, changed, removed, switched on or off, shared) are told to listen() callbacks in the process and
as the event "accounts" to the user's pages (flaskspark.core.events: ev.user.<id>.accounts), once they are committed.
Before, a module may refuse one (veto): Module.account_change_veto(change) returns a reason (an English source text,
N_(); shown translated to the user) or None; add_veto() registers such a check without a manifest (the application).
The change is then not made (the profile shows the reason). E.g. a module that still uses an account for a running
job refuses its removal.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from .. import db
from .types import (  # noqa: F401 - part of the API
    BOOL,
    BUILTIN,
    CHOICE,
    HOST,
    INT,
    TEXT,
    URL,
    AccountError,
    AccountTestError,
    AccountType,
    Field,
    Provider,
    Result,
)

log = logging.getLogger(__name__)

CUSTOM = "custom"  # the provider of an account whose settings the user gave
SECRET_NAME = "accounts"  # flaskspark.core.secrets.for_module(): APP_SECRET_KEY_ACCOUNTS, else APP_SECRET_KEY
DEFAULT_TIMEOUT = 20.0  # seconds a connection test may take (config.yaml accounts.timeout)
OWNER = "owner"
APP = 0  # the owner (user id) of the application's accounts (Module.APP_ACCOUNT_TYPES); no user has the id 0

_types: dict[str, AccountType] = {t.KEY: t for t in BUILTIN}
_providers: dict[str, Provider] = {}
_listeners: list[Callable] = []
_vetoes: list[Callable] = []


class AccountAccessError(PermissionError):
    """A module asked for a type of account its manifest does not name (ACCOUNT_TYPES)."""


# --- types and providers ----------------------------------------------------------------------------------------------
def register_type(account_type: AccountType) -> AccountType:
    """Make a type of account known (a module's Module.register()). The same key again replaces it."""
    if not isinstance(account_type, AccountType) or not account_type.KEY or not account_type.LABEL:
        raise TypeError("register_type() needs an AccountType with KEY and LABEL")
    _types[account_type.KEY] = account_type
    return account_type


def account_types() -> dict[str, AccountType]:
    """Every known type: key -> AccountType. (Formerly types(), which hid the submodule accounts.types: calling the
    submodule still works, accounts.types() -> account_types(), deprecated.)"""
    return dict(_types)


def get_type(key: str) -> AccountType:
    if key not in _types:
        raise AccountError("Unknown type of account: %(key)s", key=key)
    return _types[key]


def register_provider(provider: Provider) -> Provider:
    """A preset of accounts (a module's Module.register(), or the application)."""
    _providers[provider.key] = provider
    return provider


def providers(cfg=None) -> dict[str, Provider]:
    """The presets: those registered, then config.yaml accounts.providers (key -> {label, sso_user, <type>: {…}})."""
    out = dict(_providers)
    section = ((cfg.section("accounts") if cfg is not None else None) or {}).get("providers") or {}
    for key, value in section.items():
        value = dict(value or {})
        label = str(value.pop("label", key))
        sso = bool(value.pop("sso_user", False))
        out[str(key)] = Provider(str(key), label, {k: dict(v or {}) for k, v in value.items()}, sso)
    return out


def timeout(cfg=None) -> float:
    try:
        return float(((cfg.section("accounts") if cfg is not None else None) or {}).get("timeout") or DEFAULT_TIMEOUT)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT


def _named(manifest, app: bool) -> tuple[str, ...]:
    return tuple((manifest.APP_ACCOUNT_TYPES if app else manifest.ACCOUNT_TYPES) or ())


def declared(cfg, module: str, app: bool = False) -> tuple[str, ...]:
    """The types a loaded module names (Module.ACCOUNT_TYPES; app: Module.APP_ACCOUNT_TYPES, the application's
    accounts); every known one for the core."""
    from .. import modules

    if module == db.CORE:
        return tuple(_types)
    manifest = modules.get(cfg, module)
    return _named(manifest, app) if manifest is not None else ()


def used_types(cfg, app: bool = False) -> dict[str, list]:
    """The types the loaded modules name: key -> [their manifests] (only known types, in the order of the modules).
    app: those they read as accounts of the application (APP_ACCOUNT_TYPES)."""
    from .. import modules

    out: dict[str, list] = {}
    for manifest in modules.load(cfg)[1:]:
        for key in _named(manifest, app):
            if key in _types:
                out.setdefault(key, []).append(manifest)
            else:
                log.warning("module %r names the account type %r, which no one registered", manifest.NAME, key)
    return out


# --- what a module reads --------------------------------------------------------------------------------------------
def _box():
    from .. import secrets

    return secrets.for_module(SECRET_NAME)


def encrypt(password: str) -> str:
    return _box().encrypt(password)


@dataclass(frozen=True)
class AccountAccess:
    """An account with one of its types, as a module uses it: the login (username, password decrypted on access),
    the type's settings and its last test. permission: "owner", or "read"/"write" for an account shared with the
    user. An account of the application (APP_ACCOUNT_TYPES) has the owner APP (user_id 0: is_app)."""

    id: int
    user_id: int
    name: str
    type: str
    provider: str
    username: str
    settings: dict
    is_active: bool
    verified: bool
    error: str | None
    checked: float | None
    permission: str = OWNER
    password_enc: str = field(default="", repr=False)

    @property
    def is_app(self) -> bool:
        """An account of the application (kept by the admins in «Settings»), not of a user."""
        return self.user_id == APP

    @property
    def password(self) -> str:
        """The password in plain text (flaskspark.core.secrets.SecretKeyError when the key changed)."""
        return _box().decrypt(self.password_enc) if self.password_enc else ""


def _access(account, row, permission: str = OWNER) -> AccountAccess:
    return AccountAccess(id=account.id, user_id=account.user_id, name=account.name, type=row.type,
                         provider=account.provider, username=account.username, settings=dict(row.settings or {}),
                         is_active=bool(account.is_active), verified=bool(row.verified), error=row.error,
                         checked=row.checked, permission=permission, password_enc=account.password_enc)


class ModuleAccounts:
    """The accounts as one module may read them: only the types its manifest names (ACCOUNT_TYPES for the users'
    accounts, APP_ACCOUNT_TYPES for the application's)."""

    def __init__(self, module: str, cfg=None):
        self.module, self._cfg = module, cfg

    @property
    def cfg(self):
        from .. import config

        return self._cfg if self._cfg is not None else config.load()

    def types(self) -> tuple[str, ...]:
        return declared(self.cfg, self.module)

    def app_types(self) -> tuple[str, ...]:
        return declared(self.cfg, self.module, app=True)

    def _check(self, type_key: str, app: bool | None = False) -> None:
        """app: False the users' accounts, True the application's, None either."""
        allowed = (self.types() if app is not True else ()) + (self.app_types() if app is not False else ())
        if type_key not in allowed:
            names = "APP_ACCOUNT_TYPES" if app else "ACCOUNT_TYPES"
            raise AccountAccessError(f"module {self.module!r} may not use accounts of type {type_key!r} (its manifest "
                                     "names only " + (", ".join(allowed) or "none") + f" in {names})")

    def _rows(self, s, type_key: str, *where):
        from ..models import Account, AccountTypeRow

        query = (db.select(Account, AccountTypeRow)
                 .join(AccountTypeRow, AccountTypeRow.account_id == Account.id)
                 .where(AccountTypeRow.type == type_key, *where).order_by(Account.id))
        return s.execute(query).all()

    def for_user(self, user_id: int, type_key: str, shared: bool = False, active: bool = True) -> list[AccountAccess]:
        """The user's accounts with the type (active ones only unless active=False); shared: also those other users
        shared with the user's role (permission "read" or "write")."""
        from ..models import Account
        from .. import shares

        self._check(type_key)
        if user_id == APP:  # no user: the application's accounts are read with app()
            return []
        where = [Account.user_id == user_id] + ([Account.is_active.is_(True)] if active else [])
        with db.session() as s:
            out = [_access(a, r) for a, r in self._rows(s, type_key, *where)]
            if shared and user_id:
                granted = shares.shared_with(user_id, SHARE_TYPE, session=s)
                if granted:
                    extra = [Account.id.in_(list(granted))] + ([Account.is_active.is_(True)] if active else [])
                    out += [_access(a, r, granted[a.id]) for a, r in self._rows(s, type_key, *extra)]
        return out

    def get(self, account_id: int, type_key: str) -> AccountAccess | None:
        """One account with the type (any user's: e.g. a service working for its owner; the application's when the
        manifest names the type in APP_ACCOUNT_TYPES), None without."""
        from ..models import Account

        self._check(type_key, app=None)
        with db.session() as s:
            rows = self._rows(s, type_key, Account.id == account_id)
            if not rows:
                return None
            found = _access(*rows[0])
        self._check(type_key, app=found.is_app)
        return found

    def all(self, type_key: str, active: bool = True) -> list[AccountAccess]:
        """Every user's account with the type (a service that works for every user; not the application's)."""
        from ..models import Account

        self._check(type_key)
        where = [Account.user_id != APP] + ([Account.is_active.is_(True)] if active else [])
        with db.session() as s:
            return [_access(a, r) for a, r in self._rows(s, type_key, *where)]

    def app(self, type_key: str, active: bool = True) -> list[AccountAccess]:
        """The application's accounts with the type (kept by the admins in «Settings» → «Accounts»; the manifest
        names the type in APP_ACCOUNT_TYPES), oldest first: e.g. a service that reads for everyone."""
        from ..models import Account

        self._check(type_key, app=True)
        where = [Account.user_id == APP] + ([Account.is_active.is_(True)] if active else [])
        with db.session() as s:
            return [_access(a, r) for a, r in self._rows(s, type_key, *where)]

    def app_account(self, type_key: str, name: str | None = None) -> AccountAccess | None:
        """The application's active account with the type (the one called `name`, else the first), None without."""
        found = [a for a in self.app(type_key) if name is None or a.name == name]
        return found[0] if found else None

    def create_app_account(self, type_key: str, name: str, *, secret: str = "", username: str = "",
                           settings: dict | None = None, test: bool = False, **fields) -> AccountAccess:
        """A new account of the application (owner APP, like one an admin adds in «Settings» → «Accounts») with the
        type `type_key` (the manifest names it in APP_ACCOUNT_TYPES), e.g. from an import:

            tracker.create_app_account("gitlab", "GitLab", url="https://gitlab.example.com", secret=token)

        `settings` and further keyword arguments (`url=…`) are the type's fields, checked like the form's (missing
        ones get their defaults); `secret` is the password or access token (stored encrypted), `username` the login
        (types with USERNAME = False need none). test: sign in first; a failing test removes the account again and
        raises AccountTestError. AccountError when a field does not fit or the name is taken; the modules' vetoes
        count (accounts.veto). The listeners hear «connected»."""
        from . import store

        self._check(type_key, app=True)
        wanted = {type_key: {**(settings or {}), **fields}}
        with db.session() as s:
            account, keys = store.create(s, self.cfg, APP, "", CUSTOM, name, username, secret, wanted,
                                         allowed={type_key})
            account_id = account.id
        if test:
            try:
                self.test(account_id, type_key)
            except Exception:
                with db.session() as s:
                    store.delete(s, account_id, APP, check=False)
                raise
        changed(AccountChange("connected", account_id, APP, tuple(keys)))
        return self.get(account_id, type_key)

    def record_test(self, account_id: int, type_key: str, ok: bool, error: str | None = None) -> None:
        """Keep the result of a sign-in the module made itself (e.g. its service's): verified, error, when."""
        self._check(type_key, app=None)
        record(account_id, type_key, ok, error)

    def test(self, account_id: int, type_key: str) -> Result:
        """Test the connection now (and keep the result); AccountTestError when it fails."""
        found = self.get(account_id, type_key)
        if found is None:
            raise AccountError("Account not found.")
        return run_test(found, self.cfg)


def for_module(module: str, cfg=None) -> ModuleAccounts:
    """The accounts as the module `module` (its manifest's ACCOUNT_TYPES) may read them."""
    return ModuleAccounts(module, cfg)


def record(account_id: int, type_key: str, ok: bool, error: str | None = None) -> None:
    from ..models import AccountTypeRow

    with db.session() as s:
        row = s.get(AccountTypeRow, (account_id, type_key))
        if row is not None:
            row.verified, row.error, row.checked = bool(ok), (None if ok else (error or "")[:500] or None), time.time()


def run_test(account: AccountAccess, cfg=None) -> Result:
    """The type's connection test for `account` (its result kept); AccountTestError when it fails."""
    kind = get_type(account.type)
    try:
        result = kind.test(account, timeout(cfg))
    except AccountError as exc:
        record(account.id, account.type, False, str(exc))
        raise
    except Exception as exc:  # noqa: BLE001 - a type's test: any failure is a message
        record(account.id, account.type, False, str(exc) or type(exc).__name__)
        raise AccountTestError("%(error)s", error=str(exc) or type(exc).__name__) from exc
    record(account.id, account.type, True)
    return result if isinstance(result, Result) else Result(str(result or "OK"))


# --- changes ----------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class AccountChange:
    """What happened to an account: action ("connected", "changed", "removed", "activated", "deactivated",
    "shared"), its id, its owner and its types (before and after)."""

    action: str
    account_id: int
    user_id: int
    types: tuple[str, ...] = ()


def listen(callback: Callable[[AccountChange], None]) -> Callable[[AccountChange], None]:
    """Call `callback(change)` after every change of an account in this process (e.g. a module forgets what it kept
    for a removed account). Errors of a callback are logged, never raised."""
    _listeners.append(callback)
    return callback


def add_veto(callback: Callable[[AccountChange], str | None]) -> Callable[[AccountChange], str | None]:
    """Ask `callback(change)` before every change of an account: a reason (an English source text) refuses it, None
    lets it happen. Like Module.account_change_veto, for an application without a manifest of its own."""
    _vetoes.append(callback)
    return callback


def veto(change: AccountChange, cfg=None) -> None:
    """Before a change of an account: ask the loaded modules (Module.account_change_veto) and add_veto()'s callbacks;
    the first reason refuses the change (AccountError with that reason). For a new account (connected) the account
    exists already in the open transaction: refusing rolls it back."""
    from .. import config, modules

    checks = [m.account_change_veto for m in modules.load(cfg if cfg is not None else config.load())]
    for check in checks + list(_vetoes):
        reason = check(change)
        if reason:
            raise AccountError(str(reason))


def changed(change: AccountChange, concerned=()) -> None:
    """Tell the listeners and the pages of the owner (and of `concerned` users) that an account changed."""
    for callback in list(_listeners):
        try:
            callback(change)
        except Exception:  # noqa: BLE001 - a module's callback must not break the profile
            log.exception("accounts: listener %r failed", callback)
    from .. import events

    events.emit_users("accounts", {change.user_id, *concerned} - {APP}, action=change.action,
                      account_id=change.account_id)


from .sharing import SHARE_TYPE  # noqa: E402 - after the API it uses
