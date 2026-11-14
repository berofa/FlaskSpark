"""Account types: what a login at a provider can offer (mail over IMAP, sending over SMTP, calendars over CalDAV, address
books over CardDAV, …). One account (user name and password at a provider) may offer several types at once.

AccountType is the abstract part: its key and label, its fields (host, port, TLS, URL, …) with kinds and defaults, how
its settings are checked (clean), how a connection is tested (test) and how it is shown (describe). The core ships
imap, smtp, caldav, carddav and gitlab (only offered when a loaded module names it); a module registers further types in
Module.register():

    from flaskspark.core import accounts

    class TrackerAccount(accounts.AccountType):
        KEY, LABEL, ICON = "tracker", N_("Issue tracker"), "bug"
        FIELDS = (accounts.Field("url", N_("Address"), "url"),)

        def test(self, account, timeout):
            ...  # sign in with account.username / account.password at account.settings["url"]
            return accounts.Result(N_("Signed in"))

    accounts.register_type(TrackerAccount())

Texts (labels, results, errors) are English source texts; the web app translates them (gettext).
"""

from __future__ import annotations

import re
import sys as _sys
from abc import ABC, abstractmethod
from types import ModuleType as _ModuleType
from dataclasses import dataclass, field
from typing import Any, NamedTuple
from urllib.parse import urlparse

from ..module import N_

#: Field.kind
TEXT, INT, BOOL, CHOICE, URL, HOST = "text", "int", "bool", "choice", "url", "host"
KINDS = (TEXT, INT, BOOL, CHOICE, URL, HOST)
HOSTNAME = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9.-]{0,253}[A-Za-z0-9])?$|^\[?[0-9A-Fa-f:.]+\]?$")


class AccountError(ValueError):
    """Settings or a change of an account that do not fit. template and params: the English source text for gettext."""

    def __init__(self, template: str, **params):
        self.template, self.params = template, params
        super().__init__(template % params if params else template)


class AccountTestError(AccountError):
    """A connection test failed (the message names why: refused sign-in, server not reachable, …)."""


class Result(NamedTuple):
    """The result of a successful test for the user: an English source text and its parameters (e.g.
    Result(N_("%(n)s folders"), {"n": 12}))."""

    text: str
    params: dict = {}


@dataclass(frozen=True)
class Field:
    """A setting of an account type. kind: text, int, bool, choice (choices: (value, label) pairs), url (http or
    https) or host (a host name or an address). required: an empty value is refused (bool never)."""

    key: str
    label: str
    kind: str = TEXT
    default: Any = None
    required: bool = True
    choices: tuple[tuple[str, str], ...] = ()
    help: str = ""
    min: int | None = None
    max: int | None = None
    placeholder: str = ""

    def __post_init__(self):
        if self.kind not in KINDS:
            raise TypeError(f"field {self.key!r}: kind must be one of {', '.join(KINDS)}")

    def clean(self, value) -> Any:
        """The value from the browser as stored, or AccountError."""
        if self.kind == BOOL:
            if isinstance(value, str):
                return value.strip().lower() in ("1", "true", "on", "yes")
            return bool(self.default if value is None else value)
        if value is None or (isinstance(value, str) and not value.strip()):
            if self.default is not None:
                return self.default
            if self.required:
                raise AccountError(N_("%(label)s is missing."), label=self.label)
            return None
        if self.kind == INT:
            try:
                number = int(str(value).strip())
            except ValueError:
                raise AccountError(N_("%(label)s must be a whole number."), label=self.label) from None
            if (self.min is not None and number < self.min) or (self.max is not None and number > self.max):
                raise AccountError(N_("%(label)s must be between %(min)s and %(max)s."), label=self.label,
                                   min=self.min if self.min is not None else "…",
                                   max=self.max if self.max is not None else "…")
            return number
        text = str(value).strip()
        if len(text) > 500:
            raise AccountError(N_("%(label)s is too long."), label=self.label)
        if self.kind == CHOICE:
            if text not in {c[0] for c in self.choices}:
                raise AccountError(N_("%(label)s: unknown choice."), label=self.label)
        elif self.kind == URL:
            parsed = urlparse(text)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise AccountError(N_("%(label)s must be an address starting with https:// (or http://)."),
                                   label=self.label)
        elif self.kind == HOST:
            text = text.lower()
            if not HOSTNAME.match(text):
                raise AccountError(N_("%(label)s is not a valid server name."), label=self.label)
        return text

    def as_dict(self) -> dict:
        """For the browser's form (labels as source texts; the view translates them)."""
        return {"key": self.key, "label": self.label, "kind": self.kind, "default": self.default,
                "required": self.required and self.kind != BOOL, "help": self.help, "min": self.min, "max": self.max,
                "placeholder": self.placeholder, "choices": [{"value": v, "label": label} for v, label in self.choices]}


class AccountType(ABC):
    """A type of account (what a login offers). KEY: its key (stored with the account, named in Module.ACCOUNT_TYPES
    or Module.APP_ACCOUNT_TYPES), LABEL: for the user, ICON: a Bootstrap Icon, FIELDS: its settings. LOGIN: it signs in
    with the account's user name and password (False: e.g. a public calendar URL, the account's login stays unused).
    USERNAME: its login has a user name (False: only a secret, e.g. an access token kept as the account's password).
    SECRET_LABEL: what the form calls the password (e.g. "Access token")."""

    KEY: str = ""
    LABEL: str = ""
    ICON: str = "plug"
    FIELDS: tuple[Field, ...] = ()
    LOGIN: bool = True
    USERNAME: bool = True
    SECRET_LABEL: str = N_("Password")

    def clean(self, data: dict, previous: dict | None = None, preset: dict | None = None) -> dict:
        """The settings from the browser (data), checked: every field, a missing one from `previous` (the stored
        settings when an account is changed), else its default; `preset` (a provider's settings) wins over all.
        AccountError when one does not fit."""
        data = dict(data or {})
        previous = dict(previous or {})
        preset = dict(preset or {})
        out = {}
        for f in self.FIELDS:
            if f.key in preset:
                out[f.key] = preset[f.key]
                continue
            value = data.get(f.key)
            if (value is None or value == "") and f.key in previous:
                value = previous[f.key]
            out[f.key] = f.clean(value)
        return out

    def reconnect(self, old: dict, new: dict) -> bool:
        """Whether changed settings need a new connection test (default: any change)."""
        return old != new

    @abstractmethod
    def test(self, account, timeout: float) -> Result:
        """Sign in with `account` (flaskspark.core.accounts.AccountAccess: username, password, settings) within
        `timeout` seconds: a Result on success, AccountTestError (or any exception: its text is shown) on failure."""

    def describe(self, settings: dict) -> str:
        """A short line for the user, e.g. "mail.example.org:993"."""
        if settings.get("url"):
            return str(settings["url"])
        if settings.get("host"):
            return f"{settings['host']}:{settings['port']}" if settings.get("port") else str(settings["host"])
        return ""

    def as_dict(self) -> dict:
        return {"key": self.KEY, "label": self.LABEL, "icon": self.ICON, "login": self.LOGIN,
                "username": self.LOGIN and self.USERNAME, "secret_label": self.SECRET_LABEL,
                "fields": [f.as_dict() for f in self.FIELDS]}


# --- the core's types -------------------------------------------------------------------------------------------------
SSL, STARTTLS, PLAIN = "ssl", "starttls", "none"
SECURITY = ((SSL, N_("SSL/TLS")), (STARTTLS, N_("STARTTLS")), (PLAIN, N_("None (unencrypted)")))


def _tls_context():
    import ssl

    return ssl.create_default_context()


def _refused(exc: Exception) -> AccountTestError:
    """A refused sign-in or an unreachable server as a message for the user."""
    import socket
    import ssl

    if isinstance(exc, AccountTestError):
        return exc
    if isinstance(exc, socket.timeout | TimeoutError):
        return AccountTestError(N_("The server did not answer in time."))
    if isinstance(exc, ssl.SSLError):
        return AccountTestError(N_("Secure connection failed: %(error)s"), error=str(exc))
    if isinstance(exc, socket.gaierror):
        return AccountTestError(N_("Server not found."))
    if isinstance(exc, ConnectionError | OSError):
        return AccountTestError(N_("Server not reachable: %(error)s"), error=str(exc) or type(exc).__name__)
    return AccountTestError(N_("Sign-in failed: %(error)s"), error=str(exc) or type(exc).__name__)


class ImapType(AccountType):
    """Mail over IMAP: the test signs in and counts the folders."""

    KEY, LABEL, ICON = "imap", N_("Mail (IMAP)"), "envelope"
    FIELDS = (
        Field("host", N_("Server (IMAP)"), HOST, placeholder="imap.example.org"),
        Field("port", N_("Port"), INT, default=993, min=1, max=65535),
        Field("security", N_("Encryption"), CHOICE, default=SSL, choices=SECURITY),
    )

    def test(self, account, timeout: float) -> Result:
        import imaplib

        s = account.settings
        try:
            if s.get("security", SSL) == SSL:
                conn = imaplib.IMAP4_SSL(s["host"], int(s["port"]), ssl_context=_tls_context(), timeout=timeout)
            else:
                conn = imaplib.IMAP4(s["host"], int(s["port"]), timeout=timeout)
                if s.get("security") == STARTTLS:
                    conn.starttls(ssl_context=_tls_context())
        except Exception as exc:  # noqa: BLE001 - the user's server: every failure is a message
            raise _refused(exc) from exc
        try:
            try:
                conn.login(account.username, account.password)
            except imaplib.IMAP4.error as exc:
                raise AccountTestError(N_("Sign-in refused: %(error)s"), error=_text(exc)) from exc
            status, folders = conn.list()
            count = len(folders or []) if status == "OK" else 0
            return Result(N_("%(n)s folders"), {"n": count})
        except AccountTestError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _refused(exc) from exc
        finally:
            try:
                conn.logout()
            except Exception:  # noqa: BLE001 - closing only
                pass


class SmtpType(AccountType):
    """Sending mail over SMTP: the test signs in."""

    KEY, LABEL, ICON = "smtp", N_("Sending (SMTP)"), "send"
    FIELDS = (
        Field("host", N_("Server (SMTP)"), HOST, placeholder="smtp.example.org"),
        Field("port", N_("Port"), INT, default=465, min=1, max=65535),
        Field("security", N_("Encryption"), CHOICE, default=SSL, choices=SECURITY),
    )

    def test(self, account, timeout: float) -> Result:
        import smtplib

        s = account.settings
        try:
            if s.get("security", SSL) == SSL:
                conn = smtplib.SMTP_SSL(s["host"], int(s["port"]), timeout=timeout, context=_tls_context())
            else:
                conn = smtplib.SMTP(s["host"], int(s["port"]), timeout=timeout)
                if s.get("security") == STARTTLS:
                    conn.starttls(context=_tls_context())
        except Exception as exc:  # noqa: BLE001
            raise _refused(exc) from exc
        try:
            try:
                conn.login(account.username, account.password)
            except smtplib.SMTPAuthenticationError as exc:
                raise AccountTestError(N_("Sign-in refused: %(error)s"), error=_text(exc.smtp_error)) from exc
            return Result(N_("Signed in"))
        except AccountTestError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _refused(exc) from exc
        finally:
            try:
                conn.quit()
            except Exception:  # noqa: BLE001 - closing only
                pass


PROPFIND = ('<?xml version="1.0" encoding="utf-8"?>'
            '<d:propfind xmlns:d="DAV:"><d:prop><d:current-user-principal/><d:resourcetype/></d:prop></d:propfind>')


class DavType(AccountType):
    """A WebDAV service (CalDAV, CardDAV): the test asks the address for its properties with the account's login
    (PROPFIND, depth 0) and expects a multi-status answer."""

    ICON = "globe"
    SERVICE = "WebDAV"
    FIELDS = (
        Field("url", N_("Address"), URL, placeholder="https://dav.example.org/"),
        Field("verify_tls", N_("Check the certificate"), BOOL, default=True,
              help=N_("Switch off only for a server of your own with a self-signed certificate.")),
    )

    def test(self, account, timeout: float) -> Result:
        import httpx

        s = account.settings
        try:
            response = httpx.request("PROPFIND", s["url"], content=PROPFIND, timeout=timeout,
                                     auth=(account.username, account.password) if self.LOGIN else None,
                                     verify=bool(s.get("verify_tls", True)), follow_redirects=True,
                                     headers={"Depth": "0", "Content-Type": "application/xml; charset=utf-8"})
        except httpx.TimeoutException as exc:
            raise AccountTestError(N_("The server did not answer in time.")) from exc
        except httpx.HTTPError as exc:
            raise _refused(exc) from exc
        if response.status_code in (401, 403):
            raise AccountTestError(N_("Sign-in refused (user name or password wrong)."))
        if response.status_code == 404:
            raise AccountTestError(N_("Nothing found at this address."))
        if response.status_code != 207:
            raise AccountTestError(N_("The server answered %(status)s, not as a %(service)s server."),
                                   status=response.status_code, service=self.SERVICE)
        return Result(N_("Signed in"))


class CalDavType(DavType):
    KEY, LABEL, ICON, SERVICE = "caldav", N_("Calendars (CalDAV)"), "calendar-week", "CalDAV"


class CardDavType(DavType):
    KEY, LABEL, ICON, SERVICE = "carddav", N_("Contacts (CardDAV)"), "person-lines-fill", "CardDAV"


class GitLabType(AccountType):
    """GitLab (its REST API, flaskspark.core.gitlab): the address of the instance and a personal, group or project
    access token (kept encrypted as the account's password, no user name). The test asks GET /api/v4/user with the
    token and names who it signed in as."""

    KEY, LABEL, ICON = "gitlab", N_("GitLab"), "gitlab"
    USERNAME = False
    SECRET_LABEL = N_("Access token")
    FIELDS = (
        Field("url", N_("Address"), URL, placeholder="https://gitlab.example.com",
              help=N_("The address of the GitLab instance, without /api/v4.")),
        Field("verify_tls", N_("Check the certificate"), BOOL, default=True,
              help=N_("Switch off only for a server of your own with a self-signed certificate.")),
    )

    def clean(self, data: dict, previous: dict | None = None, preset: dict | None = None) -> dict:
        out = super().clean(data, previous, preset)
        out["url"] = str(out["url"]).rstrip("/")
        if out["url"].endswith("/api/v4"):
            out["url"] = out["url"][: -len("/api/v4")]
        return out

    def test(self, account, timeout: float) -> Result:
        from ..gitlab import GitLab, GitLabError

        try:
            with GitLab.from_account(account, timeout=timeout) as gitlab:
                me = gitlab.user()
        except GitLabError as exc:
            if exc.status == 401:
                raise AccountTestError(N_("Sign-in refused (the access token is wrong, expired or revoked).")) from exc
            if exc.status == 403:
                raise AccountTestError(N_("The access token may not read the API (scope read_api or api).")) from exc
            if exc.status == 404:
                raise AccountTestError(N_("No GitLab API at this address.")) from exc
            if exc.timeout:
                raise AccountTestError(N_("The server did not answer in time.")) from exc
            raise AccountTestError(N_("GitLab: %(error)s"), error=str(exc)) from exc
        name = str(me.get("name") or me.get("username") or "?") if isinstance(me, dict) else "?"
        return Result(N_("Connected as %(name)s"), {"name": name})


def _text(value) -> str:
    """A server's answer (bytes or a tuple of them) as text."""
    if isinstance(value, tuple | list):
        value = b" ".join(v if isinstance(v, bytes) else str(v).encode() for v in value)
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    return str(value)[:300]


BUILTIN: tuple[AccountType, ...] = (ImapType(), SmtpType(), CalDavType(), CardDavType(), GitLabType())


@dataclass(frozen=True)
class Provider:
    """A preset of accounts (config.yaml accounts.providers or accounts.register_provider()): what a provider sets per
    type, so the user only gives what is left. sso_user: the user name is the signed-in user's name (only the
    password is asked)."""

    key: str
    label: str
    settings: dict = field(default_factory=dict)  # type key -> {field key: value}
    sso_user: bool = False

    def offers(self, type_key: str) -> bool:
        return type_key in self.settings


class _CallableModule(_ModuleType):
    """accounts.types() was a function before it was renamed to accounts.account_types(): calling the submodule still
    gives every known type (deprecated)."""

    def __call__(self):
        import warnings

        warnings.warn("accounts.types() is deprecated: use accounts.account_types()", DeprecationWarning, stacklevel=2)
        from . import account_types

        return account_types()


_sys.modules[__name__].__class__ = _CallableModule
