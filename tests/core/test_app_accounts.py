"""Accounts of the application (Module.APP_ACCOUNT_TYPES; the demo module names "gitlab"): kept by the admins in
«Settings» → «Accounts» (/api/settings/accounts), owner accounts.APP, read by a module with app()/app_account(),
never among a user's accounts, never shared. A login with an access token only (no user name)."""
from __future__ import annotations

import pytest

from tests.core.sso import client_for, sso_app

GITLAB = {"gitlab": {"url": "https://gitlab.example.com/"}}


@pytest.fixture(autouse=True)
def secret_key(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "a key for the tests")


@pytest.fixture(scope="module")
def sso(app):
    with sso_app() as found:
        yield found


@pytest.fixture()
def tests_pass(monkeypatch):
    from flaskspark.core import accounts

    calls = []

    def passed(self, account, timeout):
        calls.append((self.KEY, account.user_id, account.username, account.password))
        return accounts.Result("Connected as %(name)s", {"name": "Ann"})

    for kind in accounts.account_types().values():
        monkeypatch.setattr(type(kind), "test", passed)
    return calls


@pytest.fixture()
def clean_accounts():
    yield
    from flaskspark.core import db
    from flaskspark.core.models import Account, AccountTypeRow

    with db.session() as s:
        s.execute(db.delete(AccountTypeRow))
        s.execute(db.delete(Account))


def test_the_types_of_the_application_are_named_apart(app):
    from flaskspark.core import accounts, config

    cfg = config.load()
    assert set(accounts.used_types(cfg, app=True)) == {"gitlab"}
    assert "gitlab" not in accounts.used_types(cfg)  # the profile does not offer it
    assert accounts.declared(cfg, "demo", app=True) == ("gitlab",)


def test_admins_keep_the_applications_accounts(sso, clean_accounts, tests_pass):
    from flaskspark.core import accounts

    admin = client_for(sso, "admin")
    page = admin.get("/settings")
    assert page.status_code == 200 and b'src="/api/settings/accounts"' in page.data
    data = admin.get("/api/settings/accounts").get_json()
    assert data["app"] is True and data["roles"] == [] and data["user"] == ""
    (kind,) = data["types"]
    assert kind["key"] == "gitlab" and kind["username"] is False and kind["secret_label"] == "Access token"
    assert kind["modules"] == ["Demo"]

    # a token, no user name
    response = admin.post("/api/settings/accounts", json={"provider": "custom", "password": "glpat-1",
                                                          "types": GITLAB})
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    (account,) = data["accounts"]
    assert account["name"] == "gitlab.example.com" and account["username"] == ""
    assert account["types"]["gitlab"]["settings"] == {"url": "https://gitlab.example.com", "verify_tls": True}
    assert "Connected as Ann" in data["message"] and tests_pass == [("gitlab", accounts.APP, "", "glpat-1")]

    # not a user's account: not in anyone's profile, not in all()
    demo = accounts.for_module("demo")
    (found,) = demo.app("gitlab")
    assert found.is_app and found.password == "glpat-1" and found.id == data["id"]
    assert demo.app_account("gitlab").id == found.id
    assert demo.app_account("gitlab", name="elsewhere") is None
    assert demo.get(found.id, "gitlab").is_app
    assert demo.for_user(accounts.APP, "imap") == []

    # without a token: refused
    missing = admin.post("/api/settings/accounts", json={"name": "Other", "types": GITLAB})
    assert missing.status_code == 400 and missing.get_json()["error"] == "Access token is missing."

    # a new token, switched off, removed
    tests_pass.clear()
    assert admin.put(f"/api/settings/accounts/{found.id}", json={"password": "glpat-2"}).status_code == 200
    assert tests_pass == [("gitlab", accounts.APP, "", "glpat-2")]
    assert admin.post(f"/api/settings/accounts/{found.id}", json={"action": "deactivate"}).status_code == 200
    assert demo.app_account("gitlab") is None and len(demo.app("gitlab", active=False)) == 1
    assert admin.post(f"/api/settings/accounts/{found.id}", json={"action": "delete"}).get_json()["accounts"] == []


def test_only_admins_reach_the_applications_accounts(sso, clean_accounts, tests_pass):
    user = client_for(sso, "user")
    assert user.get("/api/settings/accounts").status_code in (403, 404)
    assert user.post("/api/settings/accounts", json={"password": "x", "types": GITLAB}).status_code in (403, 404)
    # the profile neither offers the type nor shows the application's accounts
    data = user.get("/api/accounts").get_json()
    assert "gitlab" not in [t["key"] for t in data["types"]] and data["app"] is False
    refused = user.post("/api/accounts", json={"password": "x", "types": GITLAB})
    assert refused.status_code == 400 and "not available" in refused.get_json()["error"]


def test_a_users_account_is_not_the_applications(sso, clean_accounts, tests_pass):
    from flaskspark.core import accounts

    admin, user = client_for(sso, "admin"), client_for(sso, "user")
    mine = user.post("/api/accounts", json={"username": "ann", "password": "pw",
                                            "types": {"imap": {"host": "imap.example.org"}}}).get_json()["id"]
    # the admins' API does not reach a user's account
    assert admin.post(f"/api/settings/accounts/{mine}", json={"action": "delete"}).status_code == 400
    demo = accounts.for_module("demo")
    assert [a.id for a in demo.all("imap")] == [mine]
    with pytest.raises(accounts.AccountAccessError):
        demo.app("imap")  # imap is not among the demo module's APP_ACCOUNT_TYPES
    with pytest.raises(accounts.AccountAccessError):
        demo.for_user(1, "gitlab")  # gitlab only as the application's


def test_without_sign_in_the_admins_are_everyone(client, clean_accounts, tests_pass):
    # OpenAccess: no profile, but the application's accounts in «Settings»
    assert client.get("/api/accounts").status_code == 404
    assert b'src="/api/settings/accounts"' in client.get("/settings").data
    response = client.post("/api/settings/accounts", json={"password": "glpat-1", "types": GITLAB})
    assert response.status_code == 200, response.get_json()


def test_no_tab_without_a_module_that_names_such_a_type(client, monkeypatch):
    from flaskspark.core import accounts

    real = accounts.used_types
    monkeypatch.setattr(accounts, "used_types", lambda cfg, app=False: {} if app else real(cfg))
    assert b"/api/settings/accounts" not in client.get("/settings").data
    assert client.get("/api/settings/accounts").status_code == 404


def test_a_preset_with_the_users_name_is_not_for_the_application(app, clean_accounts):
    from flaskspark.core import accounts, config, db
    from flaskspark.core.accounts import store

    provider = accounts.register_provider(accounts.Provider("sso-gitlab", "Company GitLab", {
        "gitlab": {"url": "https://gitlab.example.com", "verify_tls": True}}, sso_user=True))
    try:
        with db.session() as s, pytest.raises(accounts.AccountError, match="only for personal accounts"):
            store.create(s, config.load(), accounts.APP, "", provider.key, "", "", "glpat", {"gitlab": {}})
    finally:
        accounts._providers.pop(provider.key, None)


def test_changes_of_the_applications_accounts_reach_no_users_page(app, monkeypatch):
    from flaskspark.core import accounts, events

    sent = []
    monkeypatch.setattr(events, "emit", lambda topic, uid, **hints: sent.append(uid))
    accounts.changed(accounts.AccountChange("removed", 1, accounts.APP, ("gitlab",)))
    assert sent == []


def test_a_module_creates_an_application_account(app, clean_accounts, tests_pass):
    from flaskspark.core import accounts

    heard = []
    callback = accounts.listen(heard.append)
    try:
        tracker = accounts.for_module("demo")
        created = tracker.create_app_account("gitlab", "Company GitLab", url="https://gitlab.example.com/api/v4/",
                                             secret="token-1")
    finally:
        accounts._listeners.remove(callback)
    assert created.is_app and created.user_id == accounts.APP and created.name == "Company GitLab"
    assert created.settings["url"] == "https://gitlab.example.com" and created.password == "token-1"
    assert tracker.app_account("gitlab").id == created.id
    assert heard == [accounts.AccountChange("connected", created.id, accounts.APP, ("gitlab",))]
    assert not tests_pass  # no test unless asked

    with pytest.raises(accounts.AccountError):
        tracker.create_app_account("gitlab", "Company GitLab", url="https://other.example.com", secret="x")  # name taken
    with pytest.raises(accounts.AccountError):
        tracker.create_app_account("gitlab", "No address", secret="x")  # url is required
    with pytest.raises(accounts.AccountAccessError):
        tracker.create_app_account("imap", "Mail", settings={"host": "mail.example.com"}, username="u", secret="p")

    tested = tracker.create_app_account("gitlab", "Tested", settings={"url": "https://gitlab.example.com"},
                                        secret="token-2", test=True)
    assert tests_pass[-1][0] == "gitlab" and tracker.get(tested.id, "gitlab").verified


def test_a_failing_test_keeps_no_application_account(app, clean_accounts, monkeypatch):
    from flaskspark.core import accounts

    def failed(self, account, timeout):
        raise accounts.AccountTestError("refused")

    monkeypatch.setattr(type(accounts.get_type("gitlab")), "test", failed)
    tracker = accounts.for_module("demo")
    with pytest.raises(accounts.AccountTestError):
        tracker.create_app_account("gitlab", "Broken", url="https://gitlab.example.com", secret="x", test=True)
    assert tracker.app("gitlab", active=False) == []
