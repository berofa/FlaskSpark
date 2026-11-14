"""The GitLab client (flaskspark.core.gitlab) and the account type "gitlab": no network, the HTTP answers come from an
httpx.MockTransport. The token goes only to the instance's own host; pages are followed; failures are GitLabError."""
from __future__ import annotations

import httpx
import pytest

from flaskspark.core.gitlab import GitLab, GitLabError, project_path

TOKEN = "glpat-test-token"


class Fake:
    """A GitLab answering from `routes` (method, URL without the query -> a function of the request or a Response);
    every request is recorded with the token it carried."""

    def __init__(self, routes: dict):
        self.routes, self.seen = routes, []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.seen.append((request.method, str(request.url), request.headers.get("PRIVATE-TOKEN")))
        url = str(request.url).split("?")[0]
        answer = self.routes.get((request.method, url))
        if answer is None:
            return httpx.Response(404, json={"message": "404 Not Found"})
        return answer(request) if callable(answer) else answer

    def client(self, url: str = "https://gitlab.example.com", **kwargs) -> GitLab:
        return GitLab(url, TOKEN, transport=httpx.MockTransport(self), **kwargs)


def test_get_sends_the_token_to_the_api():
    fake = Fake({("GET", "https://gitlab.example.com/api/v4/user"): httpx.Response(200, json={"name": "Ann"})})
    with fake.client("https://gitlab.example.com/api/v4/") as gitlab:  # a trailing /api/v4 is dropped
        assert gitlab.url == "https://gitlab.example.com"
        assert gitlab.user() == {"name": "Ann"}
        assert TOKEN not in repr(gitlab)
    assert fake.seen == [("GET", "https://gitlab.example.com/api/v4/user", TOKEN)]


def test_an_instance_under_a_path():
    fake = Fake({("GET", "https://example.com/gitlab/api/v4/projects/group%2Fsub"):
                 httpx.Response(200, json={"id": 7})})
    with fake.client("https://example.com/gitlab") as gitlab:
        assert gitlab.get(f"/projects/{project_path('group/sub')}") == {"id": 7}


def test_pages_follow_x_next_page():
    def issues(request):
        page = request.url.params.get("page", "1")
        assert request.url.params["per_page"] == "2" and request.url.params["state"] == "opened"
        items = {"1": [{"iid": 1}, {"iid": 2}], "2": [{"iid": 3}]}[page]
        return httpx.Response(200, json=items, headers={"X-Next-Page": "2" if page == "1" else ""})

    fake = Fake({("GET", "https://gitlab.example.com/api/v4/issues"): issues})
    with fake.client() as gitlab:
        assert [i["iid"] for i in gitlab.pages("/issues", {"state": "opened"}, per_page=2)] == [1, 2, 3]
        assert [i["iid"] for i in gitlab.pages("/issues", {"state": "opened"}, per_page=2, limit=1)] == [1]


def test_pages_follow_the_link_header_on_the_own_host():
    # keyset pagination: only a Link header; GitLab names its external_url (here http, another port) in it
    def first(request):
        return httpx.Response(200, json=[{"id": 1}], headers={
            "Link": '<http://gitlab.example.com:8080/api/v4/projects?id_after=1&per_page=100>; rel="next"'})

    def second(request):
        assert request.url.params["id_after"] == "1"
        return httpx.Response(200, json=[{"id": 2}])

    fake = Fake({("GET", "https://gitlab.example.com/api/v4/projects"): lambda r: (
        second(r) if "id_after" in r.url.params else first(r))})
    with fake.client() as gitlab:
        assert [p["id"] for p in gitlab.pages("/projects")] == [1, 2]
    assert all(url.startswith("https://gitlab.example.com/") and token == TOKEN for _m, url, token in fake.seen)


def test_the_token_never_goes_to_another_host():
    fake = Fake({
        ("GET", "https://gitlab.example.com/api/v4/projects/1/repository/archive"):
            httpx.Response(302, headers={"Location": "https://storage.example.net/blob?sig=abc"}),
        ("GET", "https://storage.example.net/blob"): httpx.Response(200, json={"ok": True}),
        ("GET", "https://gitlab.example.com/api/v4/moved"):
            httpx.Response(301, headers={"Location": "/api/v4/here"}),
        ("GET", "https://gitlab.example.com/api/v4/here"): httpx.Response(200, json={"here": True}),
    })
    with fake.client() as gitlab:
        assert gitlab.get("/projects/1/repository/archive") == {"ok": True}
        assert gitlab.get("/moved") == {"here": True}
    tokens = {url.split("?")[0]: token for _m, url, token in fake.seen}
    assert tokens["https://storage.example.net/blob"] is None
    assert tokens["https://gitlab.example.com/api/v4/here"] == TOKEN


def test_the_token_is_not_sent_from_https_down_to_http():
    fake = Fake({
        ("GET", "https://gitlab.example.com/api/v4/user"):
            httpx.Response(302, headers={"Location": "http://gitlab.example.com/api/v4/user"}),
        ("GET", "http://gitlab.example.com/api/v4/user"): httpx.Response(401, json={"message": "401 Unauthorized"}),
    })
    with fake.client() as gitlab, pytest.raises(GitLabError) as caught:
        gitlab.user()
    assert caught.value.status == 401
    assert fake.seen[-1] == ("GET", "http://gitlab.example.com/api/v4/user", None)


@pytest.mark.parametrize("answer, status, text", [
    (httpx.Response(401, json={"message": "401 Unauthorized"}), 401, "HTTP 401: 401 Unauthorized"),
    (httpx.Response(403, json={"error": "insufficient_scope"}), 403, "HTTP 403: insufficient_scope"),
    (httpx.Response(500, text="boom"), 500, "HTTP 500"),
    (httpx.Response(200, text="<html>"), 200, "not a JSON answer"),
])
def test_failures_are_gitlab_errors(answer, status, text):
    fake = Fake({("GET", "https://gitlab.example.com/api/v4/user"): answer})
    with fake.client() as gitlab, pytest.raises(GitLabError, match=text) as caught:
        gitlab.user()
    assert caught.value.status == status and not caught.value.timeout


def test_a_timeout_and_an_unreachable_server():
    def slow(request):
        raise httpx.ReadTimeout("slow", request=request)

    def gone(request):
        raise httpx.ConnectError("refused", request=request)

    with GitLab("https://gitlab.example.com", TOKEN, transport=httpx.MockTransport(slow)) as gitlab:
        with pytest.raises(GitLabError) as caught:
            gitlab.user()
    assert caught.value.timeout and caught.value.status is None
    with GitLab("https://gitlab.example.com", TOKEN, transport=httpx.MockTransport(gone)) as gitlab:
        with pytest.raises(GitLabError, match="not reachable"):
            gitlab.user()


def test_too_many_redirects():
    loop = httpx.Response(302, headers={"Location": "/api/v4/user"})
    fake = Fake({("GET", "https://gitlab.example.com/api/v4/user"): loop})
    with fake.client() as gitlab, pytest.raises(GitLabError, match="too many redirects"):
        gitlab.user()


def test_writing_and_an_empty_answer():
    fake = Fake({
        ("POST", "https://gitlab.example.com/api/v4/projects/1/issues"):
            lambda r: httpx.Response(201, json={"title": __import__("json").loads(r.content)["title"]}),
        ("DELETE", "https://gitlab.example.com/api/v4/projects/1/issues/2"): httpx.Response(204),
    })
    with fake.client() as gitlab:
        assert gitlab.post("/projects/1/issues", json={"title": "Hello"}) == {"title": "Hello"}
        assert gitlab.delete("/projects/1/issues/2") is None


def test_an_address_and_a_token_are_needed():
    with pytest.raises(GitLabError):
        GitLab("gitlab.example.com", TOKEN)
    with pytest.raises(GitLabError):
        GitLab("https://gitlab.example.com", "")
    with pytest.raises(GitLabError):
        GitLab.from_account(None)


# --- the account type ---------------------------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def secret_key(monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "a key for the tests")


def _account(settings: dict, token: str = TOKEN):
    from flaskspark.core import accounts

    return accounts.AccountAccess(id=1, user_id=accounts.APP, name="GitLab", type="gitlab", provider="custom",
                                  username="", settings=settings, is_active=True, verified=False, error=None,
                                  checked=None, password_enc=accounts.encrypt(token))


def test_the_gitlab_type_has_an_address_and_a_token():
    from flaskspark.core import accounts

    gitlab = accounts.get_type("gitlab")
    assert [f.key for f in gitlab.FIELDS] == ["url", "verify_tls"]
    assert gitlab.as_dict()["username"] is False and gitlab.as_dict()["secret_label"] == "Access token"
    assert gitlab.clean({"url": "https://gitlab.example.com/api/v4/"}) == {
        "url": "https://gitlab.example.com", "verify_tls": True}
    with pytest.raises(accounts.AccountError, match="https://"):
        gitlab.clean({"url": "gitlab.example.com"})


@pytest.mark.parametrize("answer, expected", [
    (httpx.Response(200, json={"name": "Ann Example", "username": "ann"}), None),
    (httpx.Response(401, json={"message": "401 Unauthorized"}), "access token is wrong"),
    (httpx.Response(403, json={"error": "insufficient_scope"}), "read_api"),
    (httpx.Response(404, text="nothing"), "No GitLab API"),
])
def test_the_gitlab_test_asks_who_the_token_is(monkeypatch, answer, expected):
    from flaskspark.core import accounts, gitlab as gitlab_module

    fake = Fake({("GET", "https://gitlab.example.com/api/v4/user"): answer})
    original = gitlab_module.GitLab.from_account.__func__
    monkeypatch.setattr(gitlab_module.GitLab, "from_account", classmethod(
        lambda cls, account, timeout=20.0, transport=None: original(cls, account, timeout,
                                                                    httpx.MockTransport(fake))))
    kind = accounts.get_type("gitlab")
    account = _account({"url": "https://gitlab.example.com", "verify_tls": True})
    if expected is None:
        assert kind.test(account, 5) == accounts.Result("Connected as %(name)s", {"name": "Ann Example"})
    else:
        with pytest.raises(accounts.AccountTestError, match=expected):
            kind.test(account, 5)
    assert fake.seen == [("GET", "https://gitlab.example.com/api/v4/user", TOKEN)]
