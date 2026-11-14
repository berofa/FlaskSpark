"""The accounts of one user for the profile page (or of the application, user_id APP, for «Settings» → «Accounts»):
connect, change, test, switch on or off, remove.

The profile changes only the signed-in user's own accounts. A new account is kept only if every type it was given
signed in (the view tests them, then calls delete() otherwise); a type added to an account that fails its test is
taken off again. A new password clears the test of every type until it signed in again.
"""

from __future__ import annotations

import time

from .. import db
from ..module import N_
from . import APP, CUSTOM, AccountChange, AccountError, encrypt, get_type, providers, account_types as known_types, veto

NAME_MAX = 60


def of_user(s, user_id: int) -> list:
    from ..models import Account

    return list(s.scalars(db.select(Account).filter_by(user_id=user_id).order_by(Account.id)))


def get(s, account_id: int, user_id: int):
    """The user's own account (AccountError for another user's or a missing one)."""
    from ..models import Account

    account = s.get(Account, account_id)
    if account is None or account.user_id != user_id:
        raise AccountError(N_("Account not found."))
    return account


def type_rows(s, account_id: int) -> dict:
    """type key -> its row (AccountTypeRow) of the account."""
    from ..models import AccountTypeRow

    rows = s.scalars(db.select(AccountTypeRow).filter_by(account_id=account_id).order_by(AccountTypeRow.type))
    return {row.type: row for row in rows}


def _name_free(s, user_id: int, name: str, account_id: int | None = None) -> None:
    from ..models import Account

    other = s.scalars(db.select(Account).filter_by(user_id=user_id, name=name)).first()
    if other is not None and other.id != account_id:
        raise AccountError(N_("There is an account «%(name)s» already."), name=name)


def _provider(cfg, key: str):
    if key == CUSTOM:
        return None
    found = providers(cfg).get(key)
    if found is None:
        raise AccountError(N_("Unknown provider."))
    return found


def _preset(provider, type_key: str) -> dict | None:
    """The provider's settings of a type ({} for an own server); AccountError when the provider does not offer it."""
    if provider is None:
        return {}
    if not provider.offers(type_key):
        raise AccountError(N_("%(provider)s does not offer %(type)s."), provider=provider.label,
                           type=get_type(type_key).LABEL)
    return provider.settings[type_key]


def _host_of(settings: list[dict]) -> str:
    """The server an own account names first (an address, a host): its default name."""
    for data in settings:
        url = str(data.get("url") or "")
        host = url.split("/")[2] if url.count("/") >= 2 else str(data.get("host") or "")
        if host.strip():
            return host.strip().lower()[:NAME_MAX]
    return ""


def _check_types(wanted: dict, allowed) -> None:
    unknown = set(wanted) - set(known_types())
    if unknown:
        raise AccountError(N_("Unknown type of account."))
    if allowed is not None and set(wanted) - set(allowed):
        raise AccountError(N_("This type of account is not available to you."))


def create(s, cfg, user_id: int, user_name: str, provider: str, name: str, username: str, password: str,
           wanted: dict, allowed=None) -> tuple:
    """A new account with its types (key -> settings from the browser); returns it and the keys to test. allowed:
    the types the user may connect (None: all)."""
    from ..models import Account, AccountTypeRow

    found = _provider(cfg, provider or CUSTOM)
    wanted = {k: v for k, v in (wanted or {}).items() if v is not None}
    if not wanted:
        raise AccountError(N_("Choose at least one service of the account."))
    _check_types(wanted, allowed)
    if found is not None and found.sso_user:
        if user_id == APP:
            raise AccountError(N_("This provider is only for personal accounts."))
        username = user_name
    username = (username or "").strip()
    logins = [get_type(k) for k in wanted if get_type(k).LOGIN]
    if any(kind.USERNAME for kind in logins) and (not username or not password):
        raise AccountError(N_("User name and password are needed."))
    if logins and not password:
        raise AccountError(N_("%(label)s is missing."), label=logins[0].SECRET_LABEL)
    settings = {key: get_type(key).clean(data if isinstance(data, dict) else {}, preset=_preset(found, key))
                for key, data in wanted.items()}
    name = (name or "").strip()[:NAME_MAX] or (found.label if found is not None else
                                               _host_of(list(settings.values())) or username or "Account")[:NAME_MAX]
    _name_free(s, user_id, name)
    account = Account(user_id=user_id, name=name, provider=found.key if found else CUSTOM, username=username,
                      password_enc=encrypt(password) if password else "", is_active=True, created=time.time())
    s.add(account)
    s.flush()
    for key, value in settings.items():
        s.add(AccountTypeRow(account_id=account.id, type=key, settings=value, verified=False))
    s.flush()
    veto(AccountChange("connected", account.id, user_id, tuple(settings)), cfg)
    return account, list(settings)


def update(s, cfg, account_id: int, user_id: int, name: str | None = None, password: str | None = None,
           wanted: dict | None = None, allowed=None, check: bool = True) -> tuple:
    """Name, password and the types (key -> settings to add or change, None to remove; at least one stays); returns
    the account and the keys to test (all after a new password). check: ask the modules' vetoes (accounts.veto; False
    only to undo what just failed its test)."""
    from ..models import AccountTypeRow

    account = get(s, account_id, user_id)
    had = set(type_rows(s, account.id))
    retest: list[str] = []
    if name is not None and name.strip() and name.strip()[:NAME_MAX] != account.name:
        _name_free(s, user_id, name.strip()[:NAME_MAX], account.id)
        account.name = name.strip()[:NAME_MAX]
    if wanted:
        _check_types({k: v for k, v in wanted.items()}, allowed)
        have = type_rows(s, account.id)
        removed = {k for k, v in wanted.items() if v is None}
        if not (set(have) - removed) | (set(wanted) - removed):
            raise AccountError(N_("At least one service must stay (else remove the account)."))
        found = _provider(cfg, account.provider) if account.provider != CUSTOM else None
        for key, data in wanted.items():
            row = have.get(key)
            if data is None:
                if row is not None:
                    s.delete(row)
                continue
            kind = get_type(key)
            value = kind.clean(data if isinstance(data, dict) else {}, previous=row.settings if row else None,
                               preset=_preset(found, key))
            if row is None:
                s.add(AccountTypeRow(account_id=account.id, type=key, settings=value, verified=False))
                retest.append(key)
            elif kind.reconnect(dict(row.settings or {}), value):
                row.settings, row.verified, row.error = value, False, None
                retest.append(key)
    if password:
        account.password_enc = encrypt(password)
        s.flush()
        for key, row in type_rows(s, account.id).items():
            row.verified = False
            if key not in retest:
                retest.append(key)
    s.flush()
    keys = set(type_rows(s, account.id)) | set(had)
    if check:
        veto(AccountChange("changed", account.id, user_id, tuple(sorted(keys))), cfg)
    return account, retest


def set_active(s, account_id: int, user_id: int, active: bool):
    account = get(s, account_id, user_id)
    if bool(account.is_active) != bool(active):
        veto(AccountChange("activated" if active else "deactivated", account.id, user_id,
                           tuple(type_rows(s, account.id))))
    account.is_active = bool(active)
    return account


def delete(s, account_id: int, user_id: int, check: bool = True) -> list[str]:
    """The account with its types and its shares (the data on the servers stays); returns its types. check: ask the
    modules' vetoes (accounts.veto; False only to drop a new account that failed its test)."""
    from ..models import AccountTypeRow
    from .. import shares
    from .sharing import SHARE_TYPE

    account = get(s, account_id, user_id)
    keys = list(type_rows(s, account.id))
    if check:
        veto(AccountChange("removed", account.id, user_id, tuple(keys)))
    s.execute(db.delete(AccountTypeRow).where(AccountTypeRow.account_id == account.id))
    shares.forget(SHARE_TYPE, account.id, session=s)
    s.delete(account)
    s.flush()
    return keys


def serialize(s, account, translate=lambda text: text) -> dict:
    """An own account for the browser: its login (never the password) and its types with their settings and their
    last test."""
    known = known_types()
    out = {}
    for key, row in type_rows(s, account.id).items():
        kind = known.get(key)
        out[key] = {"settings": dict(row.settings or {}), "verified": bool(row.verified), "error": row.error,
                    "checked": row.checked, "label": translate(kind.LABEL) if kind else key,
                    "icon": kind.ICON if kind else "plug", "describe": kind.describe(row.settings or {}) if kind else ""}
    return {"id": account.id, "name": account.name, "provider": account.provider, "username": account.username,
            "is_active": bool(account.is_active), "created": account.created, "types": out}
