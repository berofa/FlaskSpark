"""Sharing: one mechanism for every item a module lets its users share (a list, a folder, an account, …).

- Shared with roles (FlaskSpark's roles), never with single users; per role read or write. Only the owner of an item
  changes its shares; a user whose role changes takes the access along.
- Joining: an item that should not appear by itself (Shareable.JOINS) is joined first; an invited user may decline,
  leave and join again. Without JOINS, shared means usable at once.
- A share that ends (the owner shares with no one, removes the item) ends for everyone: who had joined gets a notice
  once (take_notices()).
- AREA: an item of a module's area is shared only with roles that may use that area, and only their users get access.

A module describes its kind of item with a Shareable (who owns an item, its name) and names it in its manifest:

    SHAREABLES = ("modules.notes.sharing:NoteShareable",)

    class NoteShareable(shares.Shareable):
        TYPE, AREA, LABEL = "note", "notes", N_("Note")

        def owner_of(self, s, object_id):
            note = s.get(Note, object_id)
            return note.owner_id if note else None

        def name_of(self, s, object_id):
            note = s.get(Note, object_id)
            return note.title if note else "?"

Then everywhere (the web app, the services):

    shares.access(user_id, "note", 7)          # "owner", "write", "read" or None
    shares.can_write(user_id, "note", 7)
    shares.shared_with(user_id, "note")        # {note id: permission} of others' notes the user may use
    shares.grant("note", 7, role_id, "read", owner_id=user_id) / shares.revoke(...)
    shares.forget("note", 7)                   # the note is deleted: its shares go

Every function takes an optional session (`session=`): a session of the module (db.for_module(<module>)) joins the
module's own work in one transaction; without one a session of the Shareable's module is opened. The Shareable's
methods run with the module's rights; the core's tables (core_shares, core_share_members, core_share_notices) and
FlaskSpark's users and roles are read with the core's (db.as_core).

The owner's dialog (the web component <ui-share-dialog>) talks to /api/shares/<type>/<id> (flaskspark.core.web.views
.shares). Without sign-in (OpenAccess) there are no roles: nothing can be shared.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager

from . import db
from .i18n import tr
from .module import N_

log = logging.getLogger(__name__)

READ, WRITE = "read", "write"
PERMISSIONS = (READ, WRITE)
JOINED, DECLINED, INVITED = "joined", "declined", "invited"
OWNER = "owner"

#: the notices to who had joined (English source texts, translated when taken)
REMOVED = N_("You are no longer part of «%(name)s» (shared by %(owner)s).")
ENDED = N_("«%(name)s» is no longer shared by %(owner)s.")


class ShareError(ValueError):
    """A change that is not possible (not the owner, unknown role, …). template and params: the English source text."""

    def __init__(self, template: str, **params):
        self.template, self.params = template, params
        super().__init__(template % params if params else template)


class Shareable(ABC):
    """A kind of item a module shares. TYPE: the key of its rows (unique in the application, e.g. "note"), JOINS:
    an invited user joins first, AREA: the area whose roles it may be shared with ("": any role), LABEL: what an item
    is called (for the dialog). MODULE is set by the core: the module whose manifest names it."""

    TYPE: str = ""
    JOINS: bool = False
    AREA: str = ""
    LABEL: str = ""
    MODULE: str = ""

    @abstractmethod
    def owner_of(self, s, object_id: int) -> int | None:
        """The owner's user id, None if the item does not exist."""

    @abstractmethod
    def name_of(self, s, object_id: int) -> str:
        """Its name for the user (notices, invitations)."""

    def eligible(self, s, user_id: int) -> bool:
        """May the user be invited at all (beyond their role)? E.g. needs an account of a type."""
        return True

    def check_change(self, s, object_id: int, owner_id: int, wanted: dict[int, str]) -> None:
        """Before the shares of an item change (set_targets, grant, revoke; wanted: {role id: permission}, {}: shared
        with no one): raise ShareError to refuse the change."""

    def shares_changed(self, object_id: int, owner_id: int, concerned: set[int]) -> None:
        """After a change of the item's shares is committed (concerned: the users before and after, and the owner).
        Errors are logged, never raised."""


# --- the registry -------------------------------------------------------------------------------------------------
_registered: dict[str, Shareable] = {}  # register(): apps and tests
_cache: dict[tuple, dict[str, Shareable]] = {}


def register(shareable: Shareable, module: str = db.CORE) -> Shareable:
    """Make a kind of item shareable without a manifest entry (e.g. an application's own); `module`: whose rights its
    methods run with."""
    if not shareable.TYPE:
        raise TypeError(f"{type(shareable).__name__}: TYPE is required")
    shareable.MODULE = shareable.MODULE or module
    _registered[shareable.TYPE] = shareable
    _cache.clear()
    return shareable


def registry(cfg=None) -> dict[str, Shareable]:
    """Every shareable kind: the manifests' SHAREABLES (of the core and the loaded modules) and register()'s."""
    from . import config, modules

    cfg = cfg if cfg is not None else config.load()
    manifests = modules.load(cfg)
    key = tuple(m.NAME for m in manifests)
    if key not in _cache:
        found: dict[str, Shareable] = {}
        for manifest in manifests:
            for spec in manifest.SHAREABLES or ():
                shareable = modules.resolve(spec)()
                if not shareable.TYPE:
                    raise TypeError(f"{spec}: TYPE is required")
                if shareable.TYPE in found:
                    raise TypeError(f"{spec}: the share type {shareable.TYPE!r} exists already "
                                    f"(module {found[shareable.TYPE].MODULE!r})")
                shareable.MODULE = manifest.NAME
                found[shareable.TYPE] = shareable
        _cache[key] = {**found, **_registered}
    return _cache[key]


def get(object_type: str) -> Shareable:
    found = registry().get(object_type)
    if found is None:
        raise ShareError(N_("Unknown kind of item to share."))
    return found


@contextmanager
def _session(kind: Shareable, session=None):
    if session is not None:
        yield session
    else:
        with db.for_module(kind.MODULE or db.CORE).session() as s:
            yield s


# --- users and roles (FlaskSpark's tables "user" and "roles", only with sign-in) ---------------------------------------
USERS = db.table("user", db.column("id"), db.column("username"), db.column("role_id"))
ROLES = db.table("roles", db.column("id"), db.column("name"), db.column("rank"), db.column("is_admin"))


def _signin_tables(s) -> bool:
    return db.has_table(s, "user") and db.has_table(s, "roles")


def users(s) -> dict[int, dict]:
    """{id: {id, username, role_id}} of every user ({} without sign-in)."""
    with db.as_core(s):
        if not _signin_tables(s):
            return {}
        rows = s.execute(db.select(USERS.c.id, USERS.c.username, USERS.c.role_id)).all()
    return {r.id: {"id": r.id, "username": r.username, "role_id": r.role_id} for r in rows}


def _role_of(s, user_id: int) -> int | None:
    with db.as_core(s):
        if not _signin_tables(s):
            return None
        return s.execute(db.select(USERS.c.role_id).where(USERS.c.id == user_id)).scalar()


def _area_allowed(s, area: str) -> set[int] | None:
    """The roles that may use `area` (admin roles always; the matrix core_role_area, else the area's defaults);
    None: no restriction (no area)."""
    if not area:
        return None
    from . import config, modules
    from .models import RoleArea
    from .web.access import areas

    known = areas(modules.load(config.load()))
    with db.as_core(s):
        rows = s.execute(db.select(ROLES.c.id, ROLES.c.name, ROLES.c.is_admin)).all()
        cells = {r.role_id: bool(r.allowed) for r in s.scalars(db.select(RoleArea).where(RoleArea.area == area))}
    out = set()
    for role in rows:
        if role.is_admin:
            out.add(role.id)
        elif area in known:
            if cells.get(role.id, role.name in known[area].defaults):
                out.add(role.id)
    return out


def roles(s, object_type: str | None = None) -> list[dict]:
    """The roles an item can be shared with, highest rank first: [{id, name}] (those of its AREA; [] without
    sign-in)."""
    with db.as_core(s):
        if not _signin_tables(s):
            return []
        rows = s.execute(db.select(ROLES.c.id, ROLES.c.name).order_by(ROLES.c.rank.desc(), ROLES.c.id)).all()
    allowed = _area_allowed(s, get(object_type).AREA) if object_type else None
    return [{"id": r.id, "name": r.name} for r in rows if allowed is None or r.id in allowed]


# --- what is shared ---------------------------------------------------------------------------------------------------
def _targets(s, object_type: str, object_id: int) -> dict[int, str]:
    from .models import Share

    with db.as_core(s):
        rows = s.scalars(db.select(Share).filter_by(object_type=object_type, object_id=object_id)).all()
    return {row.role_id: row.permission for row in rows}


def targets(object_type: str, object_id: int, session=None) -> dict[int, str]:
    """role id -> permission of an item."""
    with _session(get(object_type), session) as s:
        return _targets(s, object_type, object_id)


def _invited(s, kind: Shareable, object_id: int) -> dict[int, str]:
    by_role = _targets(s, kind.TYPE, object_id)
    if not by_role:
        return {}
    allowed = _area_allowed(s, kind.AREA)
    if allowed is not None:
        by_role = {k: v for k, v in by_role.items() if k in allowed}
    owner = kind.owner_of(s, object_id)
    return {u["id"]: by_role[u["role_id"]] for u in users(s).values()
            if u["role_id"] in by_role and u["id"] != owner and kind.eligible(s, u["id"])}


def invited(object_type: str, object_id: int, session=None) -> dict[int, str]:
    """The users invited now: user id -> permission (of their role); never the owner, only eligible users."""
    kind = get(object_type)
    with _session(kind, session) as s:
        return _invited(s, kind, object_id)


def _members(s, object_type: str, object_id: int) -> list:
    from .models import ShareMember

    with db.as_core(s):
        return list(s.scalars(db.select(ShareMember).filter_by(object_type=object_type, object_id=object_id)
                              .order_by(ShareMember.id)))


def members(object_type: str, object_id: int, session=None) -> list:
    """The answers of the invited users (ShareMember rows: user_id, status, account_id)."""
    with _session(get(object_type), session) as s:
        return _members(s, object_type, object_id)


def _member(s, object_type: str, object_id: int, user_id: int):
    from .models import ShareMember

    with db.as_core(s):
        return s.scalars(db.select(ShareMember).filter_by(object_type=object_type, object_id=object_id,
                                                          user_id=user_id)).first()


def _access(s, kind: Shareable, object_id: int, user_id: int) -> str | None:
    owner = kind.owner_of(s, object_id)
    if owner is None:
        return None
    if owner == user_id:
        return OWNER
    permission = _invited(s, kind, object_id).get(user_id)
    if permission and kind.JOINS:
        member = _member(s, kind.TYPE, object_id, user_id)
        return permission if member is not None and member.status == JOINED else None
    return permission


def access(user_id: int, object_type: str, object_id: int, session=None) -> str | None:
    """What the user may do with the item: "owner", "write", "read" or None (a joined kind: only after joining)."""
    kind = get(object_type)
    with _session(kind, session) as s:
        return _access(s, kind, object_id, user_id)


def can_read(user_id: int, object_type: str, object_id: int, session=None) -> bool:
    return access(user_id, object_type, object_id, session) is not None


def can_write(user_id: int, object_type: str, object_id: int, session=None) -> bool:
    return access(user_id, object_type, object_id, session) in (OWNER, WRITE)


def shared_with(user_id: int, object_type: str, session=None) -> dict[int, str]:
    """The items of others the user may use now: item id -> permission (a joined kind: those joined)."""
    from .models import Share

    kind = get(object_type)
    with _session(kind, session) as s:
        role = _role_of(s, user_id)
        if role is None:
            return {}
        allowed = _area_allowed(s, kind.AREA)
        if allowed is not None and role not in allowed:
            return {}
        if not kind.eligible(s, user_id):
            return {}
        with db.as_core(s):
            rows = s.scalars(db.select(Share).filter_by(object_type=object_type, role_id=role)).all()
        out = {}
        for row in rows:
            if kind.owner_of(s, row.object_id) in (None, user_id):
                continue
            if kind.JOINS:
                member = _member(s, object_type, row.object_id, user_id)
                if member is None or member.status != JOINED:
                    continue
            out[row.object_id] = row.permission
        return out


def audience(object_type: str, object_id: int, session=None) -> set[int]:
    """Who uses the item now: its owner and every user with access (a joined kind: who joined). E.g. whose pages to
    tell after a change."""
    kind = get(object_type)
    with _session(kind, session) as s:
        owner = kind.owner_of(s, object_id)
        if owner is None:
            return set()
        now = _invited(s, kind, object_id)
        if kind.JOINS:
            now = {m.user_id: 1 for m in _members(s, object_type, object_id) if m.status == JOINED and m.user_id in now}
        return {owner, *now}


def invitations(user_id: int, object_type: str, session=None) -> list[dict]:
    """The items shared with the user: [{id, name, owner, status: invited|joined|declined, permission, account_id}],
    by name (for a joined kind, the list to join or leave)."""
    from .models import Share

    kind = get(object_type)
    with _session(kind, session) as s:
        role = _role_of(s, user_id)
        allowed = _area_allowed(s, kind.AREA)
        if role is None or (allowed is not None and role not in allowed) or not kind.eligible(s, user_id):
            return []
        people = users(s)
        with db.as_core(s):
            rows = s.scalars(db.select(Share).filter_by(object_type=object_type, role_id=role)).all()
        out = []
        for row in rows:
            owner = kind.owner_of(s, row.object_id)
            if owner in (None, user_id):
                continue
            member = _member(s, object_type, row.object_id, user_id)
            out.append({"id": row.object_id, "name": kind.name_of(s, row.object_id),
                        "owner": people.get(owner, {}).get("username", "?"),
                        "status": member.status if member else INVITED, "permission": row.permission,
                        "account_id": member.account_id if member else None})
        return sorted(out, key=lambda x: (x["name"].lower(), x["id"]))


def _owned(s, kind: Shareable, object_id: int, owner_id: int) -> None:
    if kind.owner_of(s, object_id) != owner_id:
        raise ShareError(N_("Only the owner can share this."))


def dialog(object_type: str, object_id: int, owner_id: int, session=None) -> dict:
    """For the owner's dialog: {type, label (LABEL in the visitor's language), roles, shares: {role id: permission}, joins, members: [{username,
    status, permission}] (those invited now)}."""
    kind = get(object_type)
    with _session(kind, session) as s:
        _owned(s, kind, object_id, owner_id)
        people = users(s)
        answers = {m.user_id: m.status for m in _members(s, object_type, object_id)}
        now = _invited(s, kind, object_id)
        return {
            "type": object_type, "label": tr(kind.LABEL) if kind.LABEL else "", "name": kind.name_of(s, object_id),
            "roles": roles(s, object_type),
            "shares": {str(k): v for k, v in _targets(s, object_type, object_id).items()},
            "joins": kind.JOINS,
            "members": [{"username": people[i]["username"], "permission": p,
                         "status": answers.get(i, INVITED) if kind.JOINS else JOINED}
                        for i, p in sorted(now.items(), key=lambda kv: people[kv[0]]["username"].lower())],
        }


# --- changing -----------------------------------------------------------------------------------------------------------
def notice(s, user_id: int, object_type: str, text: str, **params) -> None:
    """A message shown once to the user (an English source text with %(name)s parameters)."""
    from .models import ShareNotice

    with db.as_core(s):
        s.add(ShareNotice(user_id=user_id, object_type=object_type, text=text, params=params, created=time.time()))
        s.flush()  # within the core's rights (a module's session commits with its own)


def take_notices(user_id: int, object_type: str, session=None) -> list[str]:
    """The user's notices of a kind, each only once (translated within a request of the web app)."""
    from .models import ShareNotice

    with _session(get(object_type), session) as s, db.as_core(s):
        rows = list(s.scalars(db.select(ShareNotice).filter_by(user_id=user_id, object_type=object_type)
                              .order_by(ShareNotice.id)))
        for row in rows:
            s.delete(row)
        s.flush()
        return [_translate(row.text, row.params or {}) for row in rows]


def _translate(text: str, params: dict) -> str:
    try:
        from flask import has_request_context
        from flask_babel import gettext

        if has_request_context():
            return gettext(text, **params)
    except ImportError:  # pragma: no cover - a service without Flask
        pass
    return text % params if params else text


def _owner_name(s, owner_id: int) -> str:
    return users(s).get(owner_id, {}).get("username") or str(owner_id)


def set_targets(object_type: str, object_id: int, owner_id: int, wanted, session=None) -> set[int]:
    """Share the item with exactly these roles ({role id: "read"|"write"}; empty: the share ends, a notice to who had
    joined). Members no longer invited leave (a notice to who had joined). Returns everyone concerned (before and
    after, and the owner), whose pages should reload."""
    from .models import Share

    kind = get(object_type)
    try:
        wanted = {int(k): str(v) for k, v in (wanted or {}).items()}
    except (TypeError, ValueError, AttributeError):
        raise ShareError(N_("The shares are not readable.")) from None
    with _session(kind, session) as s:
        _owned(s, kind, object_id, owner_id)
        if set(wanted) - {r["id"] for r in roles(s, object_type)}:
            raise ShareError(N_("Unknown role (or it may not use this)."))
        if set(wanted.values()) - set(PERMISSIONS):
            raise ShareError(N_("Unknown permission (read or write)."))
        kind.check_change(s, object_id, owner_id, dict(wanted))
        name, owner = kind.name_of(s, object_id), _owner_name(s, owner_id)
        before = set(_invited(s, kind, object_id))
        if not wanted:
            _end(s, kind, object_id, name, owner)
            return _changed(s, kind, object_id, owner_id, before | {owner_id})
        with db.as_core(s):
            have = {row.role_id: row for row in s.scalars(db.select(Share).filter_by(object_type=object_type,
                                                                                     object_id=object_id))}
            for role_id, row in have.items():
                if role_id not in wanted:
                    s.delete(row)
                else:
                    row.permission = wanted[role_id]
            for role_id, permission in wanted.items():
                if role_id not in have:
                    s.add(Share(object_type=object_type, object_id=object_id, role_id=role_id, permission=permission,
                                created=time.time()))
            s.flush()
        after = set(_invited(s, kind, object_id))
        for member in _members(s, object_type, object_id):
            if member.user_id not in after:
                if member.status == JOINED:
                    notice(s, member.user_id, object_type, REMOVED, name=name, owner=owner)
                with db.as_core(s):
                    s.delete(member)
        with db.as_core(s):
            s.flush()
        return _changed(s, kind, object_id, owner_id, before | after | {owner_id})


def _changed(s, kind: Shareable, object_id: int, owner_id: int, concerned: set[int]) -> set[int]:
    """Tell the Shareable once the change is committed (Shareable.shares_changed); returns `concerned`."""

    def tell():
        try:
            kind.shares_changed(object_id, owner_id, set(concerned))
        except Exception:  # noqa: BLE001 - a module's hook must not break the sharing
            log.exception("shares: shares_changed of %s %s failed", kind.TYPE, object_id)

    db.after_commit(s, tell)
    return concerned


def grant(object_type: str, object_id: int, role_id: int, permission: str, owner_id: int, session=None) -> set[int]:
    """Share the item with one more role (or change that role's permission); the others stay."""
    with _session(get(object_type), session) as s:
        wanted = {**_targets(s, object_type, object_id), int(role_id): permission}
        return set_targets(object_type, object_id, owner_id, wanted, session=s)


def revoke(object_type: str, object_id: int, role_id: int, owner_id: int, session=None) -> set[int]:
    """Share the item with one role less."""
    with _session(get(object_type), session) as s:
        wanted = {k: v for k, v in _targets(s, object_type, object_id).items() if k != int(role_id)}
        return set_targets(object_type, object_id, owner_id, wanted, session=s)


def _invitation(s, kind: Shareable, object_id: int, user_id: int) -> None:
    if not kind.JOINS or user_id not in _invited(s, kind, object_id):
        raise ShareError(N_("Invitation not found."))


def join(user_id: int, object_type: str, object_id: int, account_id: int | None = None, session=None):
    """Join an item one is invited to (with an account of one's own where the kind needs one)."""
    from .models import ShareMember

    kind = get(object_type)
    with _session(kind, session) as s:
        _invitation(s, kind, object_id, user_id)
        member = _member(s, object_type, object_id, user_id)
        with db.as_core(s):
            if member is None:
                member = ShareMember(object_type=object_type, object_id=object_id, user_id=user_id, status=JOINED,
                                     account_id=account_id, created=time.time())
                s.add(member)
            elif member.status == JOINED and member.account_id not in (None, account_id):
                raise ShareError(N_("Joined already (leave first to join with another account)."))
            member.status, member.account_id = JOINED, account_id
            s.flush()
        return member


def decline(user_id: int, object_type: str, object_id: int, session=None) -> None:
    """Decline the invitation, or leave (may join again while invited)."""
    from .models import ShareMember

    kind = get(object_type)
    with _session(kind, session) as s:
        _invitation(s, kind, object_id, user_id)
        member = _member(s, object_type, object_id, user_id)
        with db.as_core(s):
            if member is None:
                s.add(ShareMember(object_type=object_type, object_id=object_id, user_id=user_id, status=DECLINED,
                                  created=time.time()))
            else:
                member.status, member.account_id = DECLINED, None
            s.flush()


leave = decline


def _end(s, kind: Shareable, object_id: int, name: str, owner: str, tell: bool = True) -> set[int]:
    still = set(_invited(s, kind, object_id))
    joined = {m.user_id for m in _members(s, kind.TYPE, object_id) if m.status == JOINED and m.user_id in still}
    if tell:
        for user_id in joined:
            notice(s, user_id, kind.TYPE, ENDED, name=name, owner=owner)
    _forget(s, kind.TYPE, object_id)
    return joined


def end(object_type: str, object_id: int, session=None, tell: bool = True) -> set[int]:
    """The share ends for everyone (the item stays); who had joined gets a notice once (tell). Returns them."""
    kind = get(object_type)
    with _session(kind, session) as s:
        owner_id = kind.owner_of(s, object_id)
        return _end(s, kind, object_id, kind.name_of(s, object_id), _owner_name(s, owner_id), tell)


def _forget(s, object_type: str, object_id: int) -> None:
    from .models import Share, ShareMember

    with db.as_core(s):
        s.execute(db.delete(Share).where(Share.object_type == object_type, Share.object_id == object_id))
        s.execute(db.delete(ShareMember).where(ShareMember.object_type == object_type,
                                               ShareMember.object_id == object_id))
        s.flush()


def forget(object_type: str, object_id: int, session=None) -> None:
    """The item is gone: its shares and answers go, without notices (a module calls it when it deletes an item)."""
    with _session(get(object_type), session) as s:
        _forget(s, object_type, object_id)


def reset() -> None:
    """Forget the registry (tests)."""
    _registered.clear()
    _cache.clear()
