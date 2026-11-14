"""A small client for GitLab's REST API (v4), e.g. with an account of the type "gitlab" (flaskspark.core.accounts):

    from flaskspark.core import accounts
    from flaskspark.core.gitlab import GitLab, GitLabError

    account = accounts.for_module("tracker").app_account("gitlab")    # the application's account (admins keep it)
    with GitLab.from_account(account) as gitlab:
        me = gitlab.user()                                             # GET /api/v4/user
        issue = gitlab.get("/projects/42/issues/7")
        for issue in gitlab.pages("/issues", {"state": "opened", "scope": "all"}):
            ...                                                        # every page (X-Next-Page, else Link rel=next)

- The token goes only to the instance's own host (the scheme, host and port of its address): a redirect to another
  host is followed without it, and a next page that names another host (GitLab's external_url behind a proxy) is
  asked at the instance's own address instead.
- Every request has a timeout (default 20 s); every failure is a GitLabError (status: the HTTP status or None,
  timeout: True when the server did not answer in time). The texts are English (logs, services); a page translates
  its own message.
- verify_tls=False only for an instance of one's own with a self-signed certificate.

Paths are relative to /api/v4 ("/projects/42"); a project's path is encoded with project_path("group/project").
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any
from urllib.parse import quote, urljoin, urlsplit

import httpx

DEFAULT_TIMEOUT = 20.0
PER_PAGE = 100
MAX_REDIRECTS = 5
API = "/api/v4"
_LINK = re.compile(r'<([^>]+)>\s*;\s*rel="?([^";]+)"?')


class GitLabError(Exception):
    """A request to GitLab failed. status: the HTTP status (None: no answer), timeout: it did not answer in time."""

    def __init__(self, message: str, status: int | None = None, timeout: bool = False):
        super().__init__(message)
        self.status, self.timeout = status, timeout


def project_path(path: str) -> str:
    """A project's (or group's) full path as GitLab's API takes it in place of the id ("group/sub" -> "group%2Fsub")."""
    return quote(str(path).strip("/"), safe="")


def _origin(url: str) -> tuple[str, str, int | None]:
    parts = urlsplit(url)
    port = parts.port or {"http": 80, "https": 443}.get(parts.scheme)
    return parts.scheme, (parts.hostname or "").lower(), port


class GitLab:
    """A session with one GitLab instance. url: its address (https://gitlab.example.com, also with a path such as
    https://example.com/gitlab), token: an access token (sent as PRIVATE-TOKEN). transport: an httpx transport (tests:
    httpx.MockTransport)."""

    def __init__(self, url: str, token: str, verify_tls: bool = True, timeout: float = DEFAULT_TIMEOUT,
                 transport: httpx.BaseTransport | None = None):
        base = str(url or "").strip().rstrip("/")
        if base.endswith(API):
            base = base[: -len(API)]
        scheme, host, _port = _origin(base)
        if scheme not in ("http", "https") or not host:
            raise GitLabError(f"not an address of a GitLab instance: {url!r}")
        if not token:
            raise GitLabError("no access token")
        self.url, self._token = base, token
        self._client = httpx.Client(timeout=timeout, verify=verify_tls, follow_redirects=False, transport=transport,
                                    headers={"Accept": "application/json"})

    @classmethod
    def from_account(cls, account, timeout: float = DEFAULT_TIMEOUT,
                     transport: httpx.BaseTransport | None = None) -> "GitLab":
        """A session with an account of the type "gitlab" (flaskspark.core.accounts.AccountAccess: settings url and
        verify_tls, the token as its password)."""
        if account is None:
            raise GitLabError("no GitLab account")
        settings = dict(account.settings or {})
        return cls(settings.get("url", ""), account.password, verify_tls=bool(settings.get("verify_tls", True)),
                   timeout=timeout, transport=transport)

    def __repr__(self) -> str:  # never the token
        return f"GitLab({self.url!r})"

    # --- the session ----------------------------------------------------------------------------------------------
    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GitLab":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def api_url(self, path: str) -> str:
        """The full address of an API path ("/projects/42" -> <url>/api/v4/projects/42); a full address of the own
        host stays as it is."""
        if path.startswith(("http://", "https://")):
            return self._own(path)
        return f"{self.url}{API}/{path.lstrip('/')}"

    def _own(self, url: str) -> str:
        """`url` on the instance's own scheme, host and port (GitLab may name its external_url in links)."""
        if _origin(url) == _origin(self.url):
            return url
        parts, base = urlsplit(url), urlsplit(self.url)
        return parts._replace(scheme=base.scheme, netloc=base.netloc).geturl()

    def _trusted(self, url: str) -> bool:
        """May the token go to `url`? Only to the instance's host and port, never from https down to http."""
        scheme, host, port = _origin(url)
        own_scheme, own_host, own_port = _origin(self.url)
        if host != own_host or scheme not in ("http", "https") or (own_scheme == "https" and scheme == "http"):
            return False
        return port == own_port or (own_scheme == "http" and scheme == "https")

    def request(self, method: str, path: str, params: dict | None = None, json: Any = None) -> httpx.Response:
        """One request (redirects followed; the token only to the own host); GitLabError unless it answers 2xx."""
        url = self.api_url(path)
        for _ in range(MAX_REDIRECTS + 1):
            headers = {"PRIVATE-TOKEN": self._token} if self._trusted(url) else {}
            try:
                response = self._client.request(method, url, params=params, json=json, headers=headers)
            except httpx.TimeoutException as exc:
                raise GitLabError(f"{self.url} did not answer in time", timeout=True) from exc
            except httpx.HTTPError as exc:
                raise GitLabError(f"{self.url} not reachable: {exc or type(exc).__name__}") from exc
            if response.is_redirect and response.headers.get("location"):
                url = urljoin(str(response.url), response.headers["location"])
                params = None  # the location names the whole address
                if response.status_code in (301, 302, 303) and method.upper() != "GET":
                    method, json = "GET", None
                continue
            if response.is_success:
                return response
            raise GitLabError(self._message(response), status=response.status_code)
        raise GitLabError(f"{self.url}: too many redirects")

    @staticmethod
    def _message(response: httpx.Response) -> str:
        detail = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                detail = body.get("message") or body.get("error_description") or body.get("error") or ""
        except ValueError:
            pass
        text = f"HTTP {response.status_code}"
        return f"{text}: {str(detail)[:300]}" if detail else text

    @staticmethod
    def _json(response: httpx.Response) -> Any:
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise GitLabError(f"not a JSON answer from {response.url}", status=response.status_code) from exc

    # --- reading and writing ----------------------------------------------------------------------------------------
    def get(self, path: str, params: dict | None = None) -> Any:
        return self._json(self.request("GET", path, params=params))

    def post(self, path: str, json: Any = None, params: dict | None = None) -> Any:
        return self._json(self.request("POST", path, params=params, json=json))

    def put(self, path: str, json: Any = None, params: dict | None = None) -> Any:
        return self._json(self.request("PUT", path, params=params, json=json))

    def delete(self, path: str, params: dict | None = None) -> Any:
        return self._json(self.request("DELETE", path, params=params))

    def pages(self, path: str, params: dict | None = None, per_page: int = PER_PAGE,
              limit: int | None = None) -> Iterator[Any]:
        """Every item of a list, page by page (X-Next-Page, else the Link header's rel="next", e.g. keyset
        pagination); limit: at most that many items."""
        query = {**(params or {}), "per_page": per_page}
        url: str = self.api_url(path)
        count = 0
        while True:
            response = self.request("GET", url, params=query)
            items = self._json(response) or []
            if not isinstance(items, list):
                raise GitLabError(f"not a list: {path}", status=response.status_code)
            for item in items:
                yield item
                count += 1
                if limit is not None and count >= limit:
                    return
            following = (response.headers.get("x-next-page") or "").strip()
            if following:
                query = {**query, "page": following}
                continue
            link = self._next_link(response.headers.get("link", ""))
            if not link or not items:
                return
            url, query = self._own(link), None

    @staticmethod
    def _next_link(header: str) -> str:
        for target, rel in _LINK.findall(header or ""):
            if "next" in rel.split():
                return target
        return ""

    def user(self) -> dict:
        """The user the token belongs to (GET /user)."""
        return self.get("/user")
