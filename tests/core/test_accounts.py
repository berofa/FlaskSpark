"""Accounts (flaskspark.core.accounts): the types and their fields, the connection tests (the network mocked), the
encryption, a module's rights (only the types its manifest names: the demo module names imap, smtp and carddav),
the profile's API with sign-in, and no accounts without sign-in."""
from __future__ import annotations

import pytest

from tests.core.sso import client_for, sso_app


@pytest.fixture(autouse=True)
def secret_key(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "a key for the tests")


@pytest.fixture(scope="module")
def sso(app):
    with sso_app() as found:
        yield found


@pytest.fixture()
def tests_pass(monkeypatch):
    """Every type's connection test passes, without the network; the calls are recorded."""
    from flaskspark.core import accounts

    calls = []

    def passed(self, account, timeout):
        calls.append((self.KEY, account.username, account.password, account.settings))
        return accounts.Result("Signed in")

    for kind in accounts.account_types().values():
        monkeypatch.setattr(type(kind), "test", passed)
    return calls


@pytest.fixture()
def clean_accounts():
    yield
    from flaskspark.core import db
    from flaskspark.core.models import Account, AccountTypeRow, Share

    with db.session() as s:
        s.execute(db.delete(AccountTypeRow))
        s.execute(db.delete(Account))
        s.execute(db.delete(Share).where(Share.object_type == "account"))


# --- types and fields -----------------------------------------------------------------------------------------------
def test_the_core_ships_four_types():
    from flaskspark.core import accounts

    assert {"imap", "smtp", "caldav", "carddav"} <= set(accounts.account_types())
    assert [f.key for f in accounts.get_type("imap").FIELDS] == ["host", "port", "security"]


def test_fields_check_their_values():
    from flaskspark.core.accounts import AccountError, Field

    assert Field("port", "Port", "int", default=993, min=1, max=65535).clean("") == 993
    assert Field("port", "Port", "int", min=1, max=65535).clean("587") == 587
    with pytest.raises(AccountError, match="between"):
        Field("port", "Port", "int", min=1, max=65535).clean("70000")
    with pytest.raises(AccountError, match="whole number"):
        Field("port", "Port", "int").clean("abc")
    assert Field("host", "Server", "host").clean(" Mail.Example.ORG ") == "mail.example.org"
    with pytest.raises(AccountError, match="not a valid server"):
        Field("host", "Server", "host").clean("mail example/org")
    with pytest.raises(AccountError, match="https://"):
        Field("url", "Address", "url").clean("ftp://dav.example.org")
    with pytest.raises(AccountError, match="missing"):
        Field("url", "Address", "url").clean("")
    assert Field("verify", "Verify", "bool", default=True).clean(None) is True
    assert Field("verify", "Verify", "bool", default=True).clean(False) is False
    with pytest.raises(AccountError, match="unknown choice"):
        Field("security", "Encryption", "choice", choices=(("ssl", "SSL"),)).clean("rot13")


def test_a_type_cleans_with_the_stored_settings_and_a_preset():
    from flaskspark.core import accounts

    imap = accounts.get_type("imap")
    assert imap.clean({"host": "imap.example.org"}) == {"host": "imap.example.org", "port": 993, "security": "ssl"}
    previous = {"host": "imap.example.org", "port": 143, "security": "starttls"}
    assert imap.clean({}, previous=previous) == previous
    preset = {"host": "mail.provider.example", "port": 993, "security": "ssl"}
    assert imap.clean({"host": "evil.example"}, preset=preset) == preset


def test_a_module_registers_a_type_of_its_own():
    from flaskspark.core import accounts

    class Tracker(accounts.AccountType):
        KEY, LABEL = "tracker-test", "Tracker"
        FIELDS = (accounts.Field("url", "Address", "url"),)

        def test(self, account, timeout):
            return accounts.Result("Signed in")

    try:
        accounts.register_type(Tracker())
        assert accounts.get_type("tracker-test").describe({"url": "https://t.example"}) == "https://t.example"
        with pytest.raises(TypeError):
            accounts.register_type(object())
    finally:
        accounts._types.pop("tracker-test", None)


# --- connection tests (the network mocked) -----------------------------------------------------------------------------
def _account(type_key: str, settings: dict, password: str = "secret"):
    from flaskspark.core import accounts

    return accounts.AccountAccess(id=1, user_id=1, name="Test", type=type_key, provider="custom", username="ann",
                                  settings=settings, is_active=True, verified=False, error=None, checked=None,
                                  password_enc=accounts.encrypt(password))


def test_imap_signs_in_and_counts_the_folders(monkeypatch):
    import imaplib

    from flaskspark.core import accounts

    seen = {}

    class FakeImap:
        def __init__(self, host, port, ssl_context=None, timeout=None):
            seen.update(host=host, port=port, timeout=timeout)

        def login(self, user, password):
            if password != "secret":
                raise imaplib.IMAP4.error(b"[AUTHENTICATIONFAILED] Invalid credentials")
            seen["login"] = (user, password)

        def list(self):
            return "OK", [b'(\\HasNoChildren) "/" INBOX', b'(\\HasNoChildren) "/" Sent']

        def logout(self):
            seen["logout"] = True

    monkeypatch.setattr(imaplib, "IMAP4_SSL", FakeImap)
    imap = accounts.get_type("imap")
    result = imap.test(_account("imap", {"host": "imap.example.org", "port": 993, "security": "ssl"}), 5)
    assert result == accounts.Result("%(n)s folders", {"n": 2})
    assert seen == {"host": "imap.example.org", "port": 993, "timeout": 5, "login": ("ann", "secret"), "logout": True}
    with pytest.raises(accounts.AccountTestError, match="Sign-in refused"):
        imap.test(_account("imap", {"host": "imap.example.org", "port": 993, "security": "ssl"}, "wrong"), 5)


def test_imap_reports_a_server_that_is_not_there(monkeypatch):
    import imaplib
    import socket

    from flaskspark.core import accounts

    def unreachable(*args, **kwargs):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(imaplib, "IMAP4_SSL", unreachable)
    with pytest.raises(accounts.AccountTestError, match="Server not found"):
        accounts.get_type("imap").test(_account("imap", {"host": "nowhere.example", "port": 993, "security": "ssl"}), 5)


def test_smtp_with_starttls(monkeypatch):
    import smtplib

    from flaskspark.core import accounts

    steps = []

    class FakeSmtp:
        def __init__(self, host, port, timeout=None):
            steps.append(("connect", host, port))

        def starttls(self, context=None):
            steps.append("starttls")

        def login(self, user, password):
            if password != "secret":
                raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Authentication failed")
            steps.append("login")

        def quit(self):
            steps.append("quit")

    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)
    smtp = accounts.get_type("smtp")
    settings = {"host": "smtp.example.org", "port": 587, "security": "starttls"}
    assert smtp.test(_account("smtp", settings), 5) == accounts.Result("Signed in")
    assert steps == [("connect", "smtp.example.org", 587), "starttls", "login", "quit"]
    with pytest.raises(accounts.AccountTestError, match="Authentication failed"):
        smtp.test(_account("smtp", settings, "wrong"), 5)


@pytest.mark.parametrize("status, expected", [(207, None), (401, "Sign-in refused"), (404, "Nothing found"),
                                              (200, "not as a CardDAV server")])
def test_dav_asks_the_address_with_propfind(monkeypatch, status, expected):
    import httpx

    from flaskspark.core import accounts

    asked = {}

    def fake_request(method, url, **kwargs):
        asked.update(method=method, url=url, auth=kwargs.get("auth"), verify=kwargs.get("verify"),
                     depth=kwargs["headers"]["Depth"])
        return httpx.Response(status)

    monkeypatch.setattr(httpx, "request", fake_request)
    carddav = accounts.get_type("carddav")
    account = _account("carddav", {"url": "https://dav.example.org/", "verify_tls": False})
    if expected is None:
        assert carddav.test(account, 5) == accounts.Result("Signed in")
    else:
        with pytest.raises(accounts.AccountTestError, match=expected):
            carddav.test(account, 5)
    assert asked == {"method": "PROPFIND", "url": "https://dav.example.org/", "auth": ("ann", "secret"),
                     "verify": False, "depth": "0"}


# --- storage, encryption and a module's rights -------------------------------------------------------------------------
def _create(user_id: int, wanted: dict, name: str = "", password: str = "pw-1"):
    from flaskspark.core import config, db
    from flaskspark.core.accounts import store

    with db.session() as s:
        account, keys = store.create(s, config.load(), user_id, "ann", "custom", name, "ann@example.org", password,
                                     wanted)
        return account.id, keys


def test_the_password_is_stored_encrypted(app, clean_accounts):
    from flaskspark.core import accounts, db
    from flaskspark.core.models import Account

    account_id, keys = _create(41, {"imap": {"host": "imap.example.org"}}, password="very secret")
    assert keys == ["imap"]
    with db.session() as s:
        stored = s.get(Account, account_id)
        assert stored.password_enc and "very secret" not in stored.password_enc
        assert stored.name == "imap.example.org"  # an own server's account is named after its host
    found = accounts.for_module("demo").get(account_id, "imap")
    assert found.password == "very secret" and found.settings["port"] == 993
    assert "very secret" not in repr(found)


def test_a_module_reads_only_the_types_its_manifest_names(app, clean_accounts):
    from flaskspark.core import accounts

    account_id, _ = _create(42, {"imap": {"host": "imap.example.org"}, "caldav": {"url": "https://dav.example.org/"}})
    demo = accounts.for_module("demo")
    assert [a.id for a in demo.for_user(42, "imap")] == [account_id]
    assert demo.for_user(43, "imap") == []
    with pytest.raises(accounts.AccountAccessError, match="caldav"):
        demo.for_user(42, "caldav")
    with pytest.raises(accounts.AccountAccessError):
        accounts.for_module("nowhere").all("imap")
    assert [a.type for a in accounts.for_module("core").for_user(42, "caldav")] == ["caldav"]
    assert [a.id for a in demo.all("imap")] == [account_id]


def test_a_test_result_is_kept(app, clean_accounts, tests_pass):
    from flaskspark.core import accounts

    account_id, _ = _create(44, {"smtp": {"host": "smtp.example.org"}})
    demo = accounts.for_module("demo")
    assert demo.test(account_id, "smtp") == accounts.Result("Signed in")
    assert demo.get(account_id, "smtp").verified
    demo.record_test(account_id, "smtp", ok=False, error="refused")
    found = demo.get(account_id, "smtp")
    assert not found.verified and found.error == "refused" and found.checked


def test_listeners_hear_of_changes(app):
    from flaskspark.core import accounts

    heard = []
    callback = accounts.listen(heard.append)
    try:
        accounts.changed(accounts.AccountChange("removed", 1, 2, ("imap",)))
    finally:
        accounts._listeners.remove(callback)
    assert heard == [accounts.AccountChange("removed", 1, 2, ("imap",))]


# --- the profile ----------------------------------------------------------------------------------------------------
def test_without_sign_in_there_is_no_profile(client):
    assert client.get("/profile").status_code == 404
    assert client.get("/api/accounts").status_code == 404
    assert b"data-profile-link" not in client.get("/").data


def test_the_profile_offers_the_types_the_modules_use(sso, clean_accounts):
    user = client_for(sso, "user")
    page = user.get("/profile")
    assert page.status_code == 200 and b"<ui-user-accounts" in page.data and b"data-profile-link" in page.data
    assert b"data-demo-profile" in page.data  # the module's section (PAGE_SECTIONS["profile"])
    data = user.get("/api/accounts").get_json()
    assert [t["key"] for t in data["types"]] == ["imap", "smtp", "carddav"]  # the demo module's, not caldav
    assert data["types"][0]["modules"] == ["Demo"] and data["types"][0]["fields"][0]["key"] == "host"
    assert data["accounts"] == [] and data["user"] == "user.demo"
    assert [p["key"] for p in data["providers"]] == ["custom"]
    # a guest may not use the demo module: nothing to offer, no profile
    guest = client_for(sso, "guest")
    assert guest.get("/api/accounts").status_code == 404 and guest.get("/profile").status_code == 404


def test_the_profile_shows_the_modules_sections_without_accounts(sso, monkeypatch):
    from flaskspark.core import accounts

    monkeypatch.setattr(accounts, "used_types", lambda cfg: {})  # no module uses accounts
    user = client_for(sso, "user")
    page = user.get("/profile")
    assert page.status_code == 200 and b"data-demo-profile" in page.data and b"<ui-user-accounts" not in page.data
    assert user.get("/api/accounts").status_code == 404


def test_connect_change_and_remove_an_account(sso, clean_accounts, tests_pass):
    from flaskspark.core import accounts

    user = client_for(sso, "user")
    uid = sso.test_users["user"]
    response = user.post("/api/accounts", json={
        "provider": "custom", "name": "Mail", "username": "ann", "password": "pw-1",
        "types": {"imap": {"host": "imap.example.org"}, "smtp": {"host": "smtp.example.org", "port": 587,
                                                                 "security": "starttls"}}})
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    account_id = data["id"]
    assert "Account connected." in data["message"]
    (account,) = data["accounts"]
    assert set(account["types"]) == {"imap", "smtp"} and account["modules"] == ["Demo"]
    assert account["types"]["imap"]["verified"] and "password" not in str(account)
    assert {c[0] for c in tests_pass} == {"imap", "smtp"} and all(c[2] == "pw-1" for c in tests_pass)

    # caldav: no loaded module names it
    refused = user.post("/api/accounts", json={"name": "Cal", "username": "ann", "password": "pw",
                                               "types": {"caldav": {"url": "https://dav.example.org/"}}})
    assert refused.status_code == 400 and "not available" in refused.get_json()["error"]
    # the same name twice
    assert user.post("/api/accounts", json={"name": "Mail", "username": "x", "password": "y",
                                            "types": {"imap": {"host": "a.example"}}}).status_code == 400

    # a new password: every type is tested again
    tests_pass.clear()
    assert user.put(f"/api/accounts/{account_id}", json={"password": "pw-2"}).status_code == 200
    assert sorted(c[0] for c in tests_pass) == ["imap", "smtp"] and all(c[2] == "pw-2" for c in tests_pass)
    assert accounts.for_module("demo").get(account_id, "imap").password == "pw-2"

    # remove a type, but never the last one
    assert user.put(f"/api/accounts/{account_id}", json={"types": {"smtp": None}}).status_code == 200
    assert [a.id for a in accounts.for_module("demo").for_user(uid, "smtp")] == []
    last = user.put(f"/api/accounts/{account_id}", json={"types": {"imap": None}})
    assert last.status_code == 400 and "At least one" in last.get_json()["error"]

    # another user can't touch it
    assert client_for(sso, "other").post(f"/api/accounts/{account_id}", json={"action": "delete"}).status_code == 400

    # switched off: a module no longer reads it (unless it asks for inactive ones)
    assert user.post(f"/api/accounts/{account_id}", json={"action": "deactivate"}).status_code == 200
    assert accounts.for_module("demo").for_user(uid, "imap") == []
    assert len(accounts.for_module("demo").for_user(uid, "imap", active=False)) == 1
    assert user.post(f"/api/accounts/{account_id}", json={"action": "test"}).get_json()["message"].startswith(
        "Connection works")
    assert user.post(f"/api/accounts/{account_id}", json={"action": "delete"}).get_json()["accounts"] == []
    assert accounts.for_module("demo").for_user(uid, "imap", active=False) == []


def test_an_account_that_can_not_sign_in_is_not_kept(sso, clean_accounts, monkeypatch):
    from flaskspark.core import accounts

    def refused(self, account, timeout):
        raise accounts.AccountTestError("Sign-in refused: %(error)s", error="wrong password")

    monkeypatch.setattr(type(accounts.get_type("imap")), "test", refused)
    user = client_for(sso, "user")
    response = user.post("/api/accounts", json={"name": "Mail", "username": "ann", "password": "pw",
                                                "types": {"imap": {"host": "imap.example.org"}}})
    assert response.status_code == 400
    assert response.get_json()["error"] == "Connection failed: Mail (IMAP): Sign-in refused: wrong password"
    assert user.get("/api/accounts").get_json()["accounts"] == []


def test_a_type_added_later_that_fails_is_not_added(sso, clean_accounts, tests_pass, monkeypatch):
    from flaskspark.core import accounts

    user = client_for(sso, "user")
    account_id = user.post("/api/accounts", json={"name": "Mail", "username": "ann", "password": "pw",
                                                  "types": {"imap": {"host": "imap.example.org"}}}).get_json()["id"]

    def refused(self, account, timeout):
        raise accounts.AccountTestError("Server not found.")

    monkeypatch.setattr(type(accounts.get_type("smtp")), "test", refused)
    data = user.put(f"/api/accounts/{account_id}", json={"types": {"smtp": {"host": "smtp.example.org"}}}).get_json()
    assert "(not added)" in data["message"]
    assert set(data["accounts"][0]["types"]) == {"imap"}


def test_a_shared_account_is_read_by_the_users_of_the_role(sso, clean_accounts, tests_pass):
    from flaskspark.core import accounts

    user, other = client_for(sso, "user"), client_for(sso, "other")
    account_id = user.post("/api/accounts", json={"name": "Team mail", "username": "team", "password": "pw",
                                                  "types": {"imap": {"host": "imap.example.org"}}}).get_json()["id"]
    role = sso.test_roles["Users"]
    assert user.post(f"/api/shares/account/{account_id}", json={"shares": {str(role): "read"}}).status_code == 200
    (shared,) = other.get("/api/accounts").get_json()["shared"]
    assert shared["name"] == "Team mail" and shared["owner"] == "user.demo" and shared["permission"] == "read"
    demo = accounts.for_module("demo")
    assert demo.for_user(sso.test_users["other"], "imap") == []
    (found,) = demo.for_user(sso.test_users["other"], "imap", shared=True)
    assert found.id == account_id and found.permission == "read" and found.password == "pw"
    # removing the account ends its shares
    user.post(f"/api/accounts/{account_id}", json={"action": "delete"})
    assert other.get("/api/accounts").get_json()["shared"] == []


def test_sharing_an_account_is_a_change_of_it(sso, clean_accounts, tests_pass):
    from flaskspark.core import accounts

    user = client_for(sso, "user")
    account_id = user.post("/api/accounts", json={"name": "Team mail", "username": "team", "password": "pw",
                                                  "types": {"imap": {"host": "imap.example.org"}}}).get_json()["id"]
    heard = []
    callback = accounts.listen(heard.append)
    try:
        role = sso.test_roles["Users"]
        assert user.post(f"/api/shares/account/{account_id}", json={"shares": {str(role): "read"}}).status_code == 200
        assert user.post(f"/api/shares/account/{account_id}", json={"shares": {}}).status_code == 200
    finally:
        accounts._listeners.remove(callback)
    change = accounts.AccountChange("shared", account_id, sso.test_users["user"], ("imap",))
    assert heard == [change, change]


def test_a_module_may_veto_a_change_of_an_account(sso, clean_accounts, tests_pass, monkeypatch):
    from flaskspark.core import accounts, config, modules

    user, other = client_for(sso, "user"), client_for(sso, "other")
    account_id = user.post("/api/accounts", json={"name": "Mail", "username": "ann", "password": "pw",
                                                  "types": {"imap": {"host": "imap.example.org"}}}).get_json()["id"]
    asked = []

    def busy(self, change):
        asked.append(change.action)
        return "A job still uses this account." if change.action in ("removed", "deactivated", "shared") else None

    monkeypatch.setattr(type(modules.get(config.load(), "demo")), "account_change_veto", busy)
    refused = user.post(f"/api/accounts/{account_id}", json={"action": "delete"})
    assert refused.status_code == 400 and refused.get_json()["error"] == "A job still uses this account."
    assert user.post(f"/api/accounts/{account_id}", json={"action": "deactivate"}).status_code == 400
    role = sso.test_roles["Users"]
    shared = user.post(f"/api/shares/account/{account_id}", json={"shares": {str(role): "read"}})
    assert shared.status_code == 400 and shared.get_json()["error"] == "A job still uses this account."
    assert other.get("/api/accounts").get_json()["shared"] == []
    assert user.put(f"/api/accounts/{account_id}", json={"name": "Mail 2"}).status_code == 200  # not refused
    (kept,) = user.get("/api/accounts").get_json()["accounts"]
    assert kept["name"] == "Mail 2" and kept["is_active"]
    assert asked == ["removed", "deactivated", "shared", "changed"]

    # a check of the application (add_veto): a new account is refused and not kept
    check = accounts.add_veto(lambda change: "No new accounts." if change.action == "connected" else None)
    try:
        response = user.post("/api/accounts", json={"name": "Other", "username": "ann", "password": "pw",
                                                    "types": {"imap": {"host": "imap.example.org"}}})
    finally:
        accounts._vetoes.remove(check)
    assert response.status_code == 400 and response.get_json()["error"] == "No new accounts."
    assert [a["name"] for a in user.get("/api/accounts").get_json()["accounts"]] == ["Mail 2"]


def test_presets_of_config(app):
    from flaskspark.core import accounts
    from flaskspark.core.config import Config

    cfg = Config({"accounts": {"providers": {"example": {"label": "Example Mail", "sso_user": True,
                                                         "imap": {"host": "imap.example.org", "port": 993,
                                                                  "security": "ssl"}}}}})
    found = accounts.providers(cfg)["example"]
    assert found.label == "Example Mail" and found.sso_user and found.offers("imap") and not found.offers("smtp")


def test_the_profile_script_is_served(client):
    response = client.get("/static/flaskspark/js/ui-user-accounts.js")
    assert response.status_code == 200 and b'registerComponent("ui-user-accounts"' in response.data


def test_the_types_function_no_longer_hides_the_submodule():
    import types as python_types

    from flaskspark.core import accounts

    assert isinstance(accounts.types, python_types.ModuleType) and accounts.types.AccountType is accounts.AccountType
    with pytest.warns(DeprecationWarning, match="account_types"):
        assert accounts.types() == accounts.account_types()
