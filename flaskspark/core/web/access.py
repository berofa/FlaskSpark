"""Access to the web app: who is the visitor, what may they use.

Access is abstract; the web app picks one at its start (config.yaml `auth:`):

- OpenAccess ("none", the default): no sign-in, everyone may use every area (the application runs in a trusted network
  only).
- RoleAccess ("oauth", also "sso"): sign-in over FlaskSpark's OAuth login provider (an identity provider, OAUTH_*
  in the environment; the provider maps the user's groups to a role). Every page needs a sign-in; the role decides
  the areas (role x area, table core_role_area, edited on «Settings › Access»; until then the manifests'
  Area.defaults), admin roles may use everything. An admin may set a user's role by hand on «Settings › Users»
  (table core_user_role): it wins over the sign-in's and is put back after every sign-in.

The views carry their area (flaskspark.core.web: an area key, OPEN, ADMIN or a dict per method); the navigation, the
tiles and the push service ask can() and user_id(), so the modules stay the same whichever access the app uses.
"""

from __future__ import annotations

import logging
import sys
from abc import ABC, abstractmethod

from flask import abort, g, has_request_context, request
from flaskspark.helpers.content_negotiation import wants_json

from flaskspark.core.module import N_

log = logging.getLogger(__name__)


def background() -> bool:
    """A fetch request or a JSON client: it gets status codes instead of redirects or pages."""
    return wants_json() or request.headers.get("Sec-Fetch-Mode", "navigate") != "navigate"


def areas(manifests) -> dict:
    """Every area of the core and the enabled modules: key -> Area, by Area.position (equal ones in the order of the
    modules)."""
    out = {}
    for module in manifests:
        for area in module.AREAS:
            out.setdefault(area.key, area)
    return dict(sorted(out.items(), key=lambda item: item[1].position))


def start_of(area_key: str, manifests) -> str | None:
    """The start page of an area: its Area.start, else its first navigation entry, else its first tile."""
    area = areas(manifests).get(area_key)
    if area is not None and area.start:
        return area.start
    entries = sorted((e for m in manifests for e in m.NAVIGATION if e.area == area_key), key=lambda e: e.position)
    if entries:
        return entries[0].href
    tiles = sorted((t for m in manifests for t in m.TILES if t.area == area_key), key=lambda t: t.position)
    return tiles[0].href if tiles else None


class Access(ABC):
    #: endpoints of the web app itself reachable without a session (static files, the sign-in flow)
    PUBLIC = frozenset({"static", "webcomponents.static", "theme.static", "theme.manifest", "flaskspark_i18n",
                        "flaskspark_core_i18n", "flaskspark_core_i18n_catalog", "set_language"})
    #: the FlaskSpark login provider this access needs (FlaskSpark(login_provider=...)), None: none
    LOGIN_PROVIDER: str | None = None
    #: is there a role x area matrix to edit («Settings › Access»)?
    HAS_MATRIX = False
    #: are there users whose role an admin may set by hand («Settings › Users»)?
    HAS_USERS = False

    manifests: tuple = ()

    @abstractmethod
    def can(self, area: str) -> bool:
        """May the current visitor use `area`?"""

    @abstractmethod
    def user_id(self) -> int:
        """The current user's id (0: anonymous)."""

    @abstractmethod
    def user_name(self) -> str:
        """The current user's name for the layout ("" for anonymous)."""

    @property
    def signed_in(self) -> bool:
        """Is there a sign-in at all (the layout shows the account buttons then)?"""
        return False

    @property
    def logout_url(self) -> str:
        """Where «Sign out» goes."""
        return "/"

    def init_app(self, flask_spark, manifests) -> None:
        """Once at the start of the web app (after FlaskSpark and its login provider are set up)."""
        self.manifests = tuple(manifests)

    def check(self, endpoint: str | None, view_class, method: str):
        """Before every request: None to go on, else a response (a redirect to the sign-in, 401/403)."""
        return None

    def permitted_areas(self) -> list[str]:
        """The areas the current visitor may use, in the order of the modules."""
        return [key for key in areas(self.manifests) if self.can(key)]

    def may_use_any(self) -> bool:
        """Is there anything for the visitor at all (False: the start page says they have no access)?"""
        return True

    def start_page(self) -> str | None:
        """The start page of the first area the visitor may use (None: none)."""
        for key in self.permitted_areas():
            start = start_of(key, self.manifests)
            if start:
                return start
        return None


class OpenAccess(Access):
    """No sign-in: everyone may use everything."""

    def can(self, area: str) -> bool:
        return True

    def user_id(self) -> int:
        return 0

    def user_name(self) -> str:
        return ""


class AccessError(ValueError):
    """A change of the matrix that is not possible (unknown role or area, an admin role). template and params: the
    English source text for gettext."""

    def __init__(self, template: str, **params):
        self.template, self.params = template, params
        super().__init__(template % params if params else template)


class RoleAccess(Access):
    """Sign-in over FlaskSpark's OAuth login provider; the role decides the areas.

    - Every endpoint but PUBLIC ones (static files, the sign-in flow, Module.PUBLIC_ENDPOINTS) needs a sign-in:
      a page goes to the sign-in (and back afterwards), a background request gets 401 (the page's script reloads it).
    - OPEN: every signed-in user. ADMIN: admin roles only (FlaskSpark's Role.is_admin, or the user's admin flag).
    - An area: admin roles always; other roles as the matrix says (core_role_area), a missing cell as the area's
      defaults (Area.defaults: role names). An area the user may not use is invisible (no navigation, no tile) and
      its pages and APIs answer 403.

    FlaskSpark's users and roles stay in its Flask-SQLAlchemy tables (user, roles); the matrix is a table of the core
    on the database API.
    """

    LOGIN_PROVIDER = "OAuth"
    HAS_MATRIX = True
    HAS_USERS = True
    PUBLIC = Access.PUBLIC | {"auth.login", "auth.callback", "auth.logout"}

    def init_app(self, flask_spark, manifests) -> None:
        super().init_app(flask_spark, manifests)
        self.login_manager = flask_spark.login_provider.login_manager
        self.login_manager.login_message = None  # no "Please log in" flash after the round trip
        from flask_login import user_logged_in

        user_logged_in.connect(self._signed_in, flask_spark.app, weak=False)
        if sys.argv[1:2] != ["db"]:
            with flask_spark.app.app_context():
                self.ensure_defaults()

    # --- who -----------------------------------------------------------------------------------------------------
    @staticmethod
    def _user():
        if not has_request_context():
            return None
        from flask_login import current_user

        return current_user if getattr(current_user, "is_authenticated", False) else None

    @property
    def signed_in(self) -> bool:
        return True

    @property
    def logout_url(self) -> str:
        from flask import url_for

        return url_for("auth.logout")

    def user_id(self) -> int:
        user = self._user()
        return int(user.id) if user is not None else 0

    def user_name(self) -> str:
        user = self._user()
        if user is None:
            return ""
        full = " ".join(p for p in (getattr(user, "first_name", None), getattr(user, "last_name", None)) if p)
        return full or user.username

    def is_admin(self) -> bool:
        user = self._user()
        return bool(user is not None and user.is_admin)

    # --- may they ------------------------------------------------------------------------------------------------
    def check(self, endpoint, view_class, method):
        if self._user() is not None:
            return None
        if background():
            abort(401)
        return self.login_manager.unauthorized()

    def can(self, area: str) -> bool:
        from . import ADMIN, OPEN

        user = self._user()
        if user is None:
            return False
        if area == OPEN or user.is_admin:
            return True
        known = areas(self.manifests)
        if area == ADMIN or area not in known:
            return False
        role = getattr(user, "role", None)
        if role is None:
            return False
        # The navigation asks for every area on each page: one query per request and role.
        cache = g.setdefault("_core_role_areas", {})
        if role.id not in cache:
            cache[role.id] = self._cells(role.id)
        cells = cache[role.id]
        return cells[area] if area in cells else role.name in known[area].defaults

    def may_use_any(self) -> bool:
        return self.is_admin() or not areas(self.manifests) or bool(self.permitted_areas())

    # --- the matrix (role x area) ----------------------------------------------------------------------------------
    @staticmethod
    def _cells(role_id: int | None = None) -> dict:
        from flaskspark.core import db
        from flaskspark.core.models import RoleArea

        query = db.select(RoleArea)
        if role_id is not None:
            query = query.where(RoleArea.role_id == role_id)
        with db.session() as s:
            rows = list(s.scalars(query))
        if role_id is not None:
            return {r.area: bool(r.allowed) for r in rows}
        return {(r.role_id, r.area): bool(r.allowed) for r in rows}

    @staticmethod
    def _roles():
        from flaskspark.models.role import Role

        return Role.query.order_by(Role.rank.desc(), Role.name).all()

    def ensure_defaults(self) -> None:
        """FlaskSpark's default roles, the missing cells of the matrix from the areas' defaults (cells set on the page
        stay), the cells of roles that are gone removed. Skipped while the tables are missing (before the migration)."""
        from flaskspark.core import db
        from flaskspark.core.models import RoleArea
        from flaskspark.models.role import Role

        try:
            Role.ensure_defaults()
            roles = self._roles()
            known = areas(self.manifests)
            with db.session() as s:
                rows = list(s.scalars(db.select(RoleArea)))
                have = {(r.role_id, r.area) for r in rows}
                ids = {role.id for role in roles}
                for row in rows:
                    if row.role_id not in ids:
                        s.delete(row)
                for role in roles:
                    for key, area in known.items():
                        if (role.id, key) not in have:
                            s.add(RoleArea(role_id=role.id, area=key,
                                           allowed=bool(role.is_admin) or role.name in area.defaults))
        except Exception as exc:  # noqa: BLE001 - no tables yet: the defaults apply until the migration
            log.warning("access: the role x area matrix is not ready (%s); run the migrations", exc)

    def matrix(self) -> dict:
        """Roles x areas for «Settings › Access»: {areas: [{key, label, description}], roles: [{id, name, admin,
        allowed: {key: bool}}]} (labels: the source texts)."""
        known = areas(self.manifests)
        cells = self._cells()
        return {
            "areas": [{"key": k, "label": a.label, "description": a.description} for k, a in known.items()],
            "roles": [{"id": r.id, "name": r.name, "admin": bool(r.is_admin),
                       "allowed": {k: bool(r.is_admin) or cells.get((r.id, k), r.name in a.defaults)
                                   for k, a in known.items()}}
                      for r in self._roles()],
        }

    def set_allowed(self, role_id: int, area: str, allowed: bool) -> None:
        """Switch one cell of the matrix; an admin role cannot be changed (it may always)."""
        from flaskspark import db as flask_db
        from flaskspark.core import db
        from flaskspark.core.models import RoleArea
        from flaskspark.models.role import Role

        role = flask_db.session.get(Role, role_id)
        if role is None or area not in areas(self.manifests):
            raise AccessError(N_("Unknown role or area."))
        if role.is_admin:
            raise AccessError(N_("Administrators may always use everything."))
        with db.session() as s:
            row = s.scalars(db.select(RoleArea).where(RoleArea.role_id == role.id, RoleArea.area == area)).first()
            if row is None:
                row = RoleArea(role_id=role.id, area=area)
                s.add(row)
            row.allowed = bool(allowed)
        if has_request_context():
            g.pop("_core_role_areas", None)

    def roles_with(self, area: str) -> list[dict]:
        """The roles that may use `area`: [{id, name}] (e.g. whom a module may share with)."""
        return [{"id": r["id"], "name": r["name"]} for r in self.matrix()["roles"] if r["allowed"].get(area)]

    # --- the role of a user set by hand (core_user_role) -----------------------------------------------------------
    def _signed_in(self, _sender, user=None, **_extra) -> None:
        """Flask-Login's user_logged_in: the sign-in just set the role (from the provider's groups)."""
        if user is None:
            return
        try:
            self.apply_override(user)
        except Exception:  # noqa: BLE001 - no table yet (before the migration): the sign-in's role applies
            log.exception("access: the role set by hand was not applied to user %s", getattr(user, "id", "?"))

    @staticmethod
    def _effective(user, role) -> None:
        """Give `user` the role `role` (FlaskSpark's user, in its session): its admin flag follows the role, and so
        does the signed-in session's copy of it."""
        from flask import session

        user.role = role
        if hasattr(user, "admin"):
            user.admin = bool(role is not None and role.is_admin)
        if has_request_context() and isinstance(session.get("user"), dict) and \
                session["user"].get("id") == user.id:
            session["user"] = {**session["user"], "role_id": role.id if role else None,
                               "role_name": role.name if role else None, "admin": bool(role and role.is_admin)}

    def apply_override(self, user) -> None:
        """After a sign-in (it just set the role): remember the sign-in's role and put the one set by hand back."""
        from flaskspark import db as flask_db
        from flaskspark.core import db
        from flaskspark.core.models import UserRole
        from flaskspark.models.role import Role

        with db.session() as s:
            row = s.get(UserRole, user.id)
            if row is None:
                row = UserRole(user_id=user.id)
                s.add(row)
            row.sso_role_id = user.role_id
            override = row.role_id
        if override is not None:
            role = flask_db.session.get(Role, override)
            if role is not None:
                self._effective(user, role)
        flask_db.session.commit()

    def users(self) -> list[dict]:
        """The users for «Settings › Users»: [{id, username, email, name, role_id, role, override, sso_role}]
        (override: the role set by hand or None; sso_role: the last role the sign-in gave). A user appears after
        their first sign-in."""
        from flaskspark.core import db
        from flaskspark.core.models import UserRole
        from flaskspark.models.user import User

        roles = {r.id: r.name for r in self._roles()}
        with db.session() as s:
            rows = {r.user_id: (r.role_id, r.sso_role_id) for r in s.scalars(db.select(UserRole))}
        out = []
        for u in User.query.order_by(User.username).all():
            override, sso = rows.get(u.id, (None, None))
            override = override if override in roles else None  # a role that is gone: the sign-in decides
            # without an override the current role is the sign-in's; with one, the last the sign-in gave (if known)
            sso_role = sso if sso else (u.role_id if override is None else None)
            name = " ".join(p for p in (getattr(u, "first_name", None), getattr(u, "last_name", None)) if p)
            out.append({"id": u.id, "username": u.username, "email": u.email, "name": name, "role_id": u.role_id,
                        "role": roles.get(u.role_id), "override": override, "sso_role": roles.get(sso_role)})
        return out

    def set_user_role(self, target_id: int, role_id: int | None, acting_id: int | None = None) -> None:
        """Set the role of a user by hand (role_id None: back to the sign-in's role). Applies at once and survives
        the next sign-ins. An admin can't change their own role (no lock-out)."""
        from flaskspark import db as flask_db
        from flaskspark.core import db
        from flaskspark.core.models import UserRole
        from flaskspark.models.role import Role
        from flaskspark.models.user import User

        acting_id = self.user_id() if acting_id is None else acting_id
        user = flask_db.session.get(User, target_id)
        if user is None:
            raise AccessError(N_("Unknown user."))
        if user.id == acting_id:
            raise AccessError(N_("You can't change your own role."))
        role = None
        if role_id is not None:
            role = flask_db.session.get(Role, role_id)
            if role is None:
                raise AccessError(N_("Unknown role."))
        with db.session() as s:  # the override first: should FlaskSpark's commit fail, the next sign-in applies it
            row = s.get(UserRole, user.id)
            if row is None:
                row = UserRole(user_id=user.id, sso_role_id=user.role_id)  # no override so far: the sign-in's role
                s.add(row)
            row.role_id = role_id
            sso_role_id = row.sso_role_id
        if role is None and sso_role_id is not None:
            role = flask_db.session.get(Role, sso_role_id)
        if role is not None:
            self._effective(user, role)
        flask_db.session.commit()
        if has_request_context():
            g.pop("_core_role_areas", None)


def area_of(view_class, method: str) -> str:
    """The area of a view for an HTTP method (its `area` attribute; ADMIN without one)."""
    from . import ADMIN

    area = getattr(view_class, "area", ADMIN)
    if isinstance(area, dict):
        return area.get(method.upper(), area.get("*", ADMIN))
    return area or ADMIN


ACCESS = {"none": OpenAccess, "oauth": RoleAccess, "sso": RoleAccess}


def access_class(name: str) -> type[Access]:
    try:
        return ACCESS[name]
    except KeyError:
        raise ValueError(f"unknown access {name!r} (config.yaml auth:, known: {', '.join(ACCESS)})") from None


def create(name: str) -> Access:
    return access_class(name)()
