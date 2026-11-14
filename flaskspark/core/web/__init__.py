"""Web base of flaskspark.core: what the web parts of the modules use from the web app.

Access of a view (class attribute `area`): an area key of a module (manifest AREAS), a dict per HTTP method, OPEN
(everyone who may use the application) or ADMIN (admin roles only). Without `area` a view is ADMIN. Which access
applies is the web app's choice (flaskspark.core.web.access, config.yaml `auth:`): OpenAccess (no sign-in, everyone
may do everything) or RoleAccess (sign-in, role x area), without touching the modules.

The start page («/»): the core's (the modules' tiles) unless a module or the app has a view on «/» of its own; config.yaml
`app.start` (a path or an endpoint) sends «/» there instead. start_url() is where «/» leads, start_endpoints() what
counts as the start page (a visitor who may not use it goes to the start page of the first area they may use).

Personal settings of the visitor (e.g. which columns a list shows): user_setting(key) / save_user_setting(key, value),
a dict per key (flaskspark.core.web.user_settings).
"""

from __future__ import annotations

OPEN = "open"
ADMIN = "admin"
EXTENSION = "flaskspark.core.access"  # app.extensions: the access of a web app

_access = None


def use(access) -> None:
    """The web app hands its access (flaskspark.core.web.access.Access) over at its start."""
    global _access
    _access = access


def get_access():
    """The access of the current web app (several apps in one process keep theirs), else the one handed over last."""
    from flask import current_app, has_app_context

    if has_app_context():
        found = current_app.extensions.get(EXTENSION)
        if found is not None:
            return found
    if _access is None:
        from .access import OpenAccess

        use(OpenAccess())
    return _access


def can(area: str) -> bool:
    """May the current visitor use `area` (an area key, OPEN or ADMIN)?"""
    return get_access().can(area)


def user_id() -> int:
    """The id of the signed-in user (0 without sign-in)."""
    return get_access().user_id()


def user_name() -> str:
    return get_access().user_name()


def roles_with(area: str) -> list[dict]:
    """The roles that may use `area`: [{id, name}] ([] without roles, OpenAccess)."""
    access = get_access()
    return access.roles_with(area) if hasattr(access, "roles_with") else []


def start_url() -> str | None:
    """Where the start page sends the visitor (config.yaml `app.start`: a path, or an endpoint of the web app); None:
    nowhere, «/» is the start page itself."""
    from flask import url_for

    from flaskspark.core import config

    start = str(config.load().section("app").get("start") or "").strip()
    if not start or start == "/":
        return None
    return start if start.startswith("/") else url_for(start)


def start_endpoints() -> set[str]:
    """The endpoints that are «the start page»: the view on «/» and the one config.yaml `app.start` names."""
    from flask import current_app

    from flaskspark.core import config

    adapter = current_app.url_map.bind("localhost")
    out = set()
    start = str(config.load().section("app").get("start") or "").strip()
    for path in ("/", start if start.startswith("/") else None):
        if path:
            try:
                out.add(adapter.match(path.split("?", 1)[0], method="GET")[0])
            except Exception:  # noqa: BLE001 - nothing (or a redirect) there
                pass
    if start and not start.startswith("/"):
        out.add(start)
    return out


def user_setting(key: str) -> dict:
    """A personal setting of the visitor, {} without one."""
    from .user_settings import load

    return load(key)


def save_user_setting(key: str, value: dict) -> dict:
    """Store a personal setting of the visitor (a dict, JSON)."""
    from .user_settings import save

    return save(key, value)
