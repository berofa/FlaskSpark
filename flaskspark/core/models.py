"""The core's own tables (manifest MODELS of flaskspark.core.core_module.Core), on the database API like every module's:

    core_settings       the settings of config.yaml the admins changed (flaskspark.core.settings)
    core_role_area      which role may use which area (flaskspark.core.web.access.RoleAccess)
    core_user_settings  personal settings of a user (flaskspark.core.web.user_setting)
    core_user_role      the role an admin set by hand for a user, over the one of the sign-in (RoleAccess)
    core_module_chains  the modules seen at the start: their history's revision and their tables, so FlaskSpark can
                        still name a module and its tables once the application no longer delivers it
                        (flaskspark.core.db.migrations, flaskspark.core.leftovers)
    core_accounts       the accounts of the users: one login at a provider (flaskspark.core.accounts)
    core_account_types  what an account offers: one row per account type (imap, caldav, …) with its settings and its
                        last connection test
    core_shares         a module's item shared with a role, read or write (flaskspark.core.shares)
    core_share_members  an invited user's answer for an item that is joined first: joined or declined
    core_share_notices  a message shown once to a user (a share ended, they were removed)
    core_attachments    files attached to an item of a module (flaskspark.core.attachments)

On the database API, not Flask-SQLAlchemy: the services read the settings too (config.load()) and load no Flask.
Role and user ids point at FlaskSpark's tables (roles, user) without a foreign key: those exist only in an application
with sign-in, the core's tables in every one. Rows of a role or user that is gone are ignored (and the matrix's are
tidied at the start, RoleAccess.ensure_defaults).
"""

from __future__ import annotations

import time

from .db import (JSON, BigInteger, Boolean, Float, Index, Integer, Mapped, Model, String, Text, UniqueConstraint,
                 mapped_column)

TABLES = ("core_settings", "core_role_area", "core_user_settings", "core_user_role", "core_module_chains",
          "core_accounts", "core_account_types", "core_shares", "core_share_members", "core_share_notices",
          "core_attachments")


class StoredSetting(Model):
    """A setting of config.yaml an admin changed: its path (e.g. "mail.interval") and the value as JSON."""

    __tablename__ = "core_settings"

    path: Mapped[str] = mapped_column(String(160), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    changed: Mapped[float] = mapped_column(Float, nullable=False, default=time.time)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # who changed it (0: no sign-in)


class RoleArea(Model):
    """Whether a role (FlaskSpark's roles.id) may use an area (Area.key). Admin roles may always."""

    __tablename__ = "core_role_area"
    __table_args__ = (UniqueConstraint("role_id", "area"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    area: Mapped[str] = mapped_column(String(64), nullable=False)
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class UserSetting(Model):
    """A personal setting of a user (FlaskSpark's user.id), one JSON value per key."""

    __tablename__ = "core_user_settings"
    __table_args__ = (UniqueConstraint("user_id", "key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated: Mapped[float] = mapped_column(Float, nullable=False, default=time.time, onupdate=time.time)


class UserRole(Model):
    """The role of a user (FlaskSpark's user.id) set by hand on «Settings › Users», over the one the sign-in gives
    (role_id; None: the sign-in decides). The sign-in sets the role at every login; sso_role_id keeps the last one it
    gave, so removing the override returns to it at once."""

    __tablename__ = "core_user_role"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    role_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sso_role_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ModuleChain(Model):
    """A module the application delivered at a start (written at every start, flaskspark.core.db.migrations.record):
    its migration history's revision in the database (None: it has none), its tables, its label, the version of the
    distribution that delivered it and when it was seen. The row of a module that is no longer delivered stays as it
    was last seen: it names the module of a revision no history knows any more, and its tables."""

    __tablename__ = "core_module_chains"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)  # the module's name = its history's branch label
    label: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    revision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tables: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    seen: Mapped[float] = mapped_column(Float, nullable=False, default=time.time)


# --- accounts (flaskspark.core.accounts) ------------------------------------------------------------------------------
class Account(Model):
    """One login of a user (FlaskSpark's user.id) at a provider: user name and password (encrypted,
    flaskspark.core.secrets). What it offers are its rows in core_account_types."""

    __tablename__ = "core_accounts"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="custom")
    username: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    password_enc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created: Mapped[float] = mapped_column(Float, nullable=False, default=time.time)


class AccountTypeRow(Model):
    """A type an account offers (AccountType.KEY, e.g. "imap") with its settings (JSON: host, port, …) and its last
    connection test: verified (it signed in), error, checked (when)."""

    __tablename__ = "core_account_types"

    account_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    type: Mapped[str] = mapped_column(String(32), primary_key=True)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked: Mapped[float | None] = mapped_column(Float, nullable=True)


# --- shares (flaskspark.core.shares) ----------------------------------------------------------------------------------
class Share(Model):
    """An item of a module (object_type: its Shareable.TYPE, object_id: its id) shared with a role (FlaskSpark's
    roles.id), read or write. No foreign key: the module forgets an item's rows when the item goes
    (shares.forget)."""

    __tablename__ = "core_shares"
    __table_args__ = (UniqueConstraint("object_type", "object_id", "role_id"),
                      Index("ix_core_shares_object", "object_type", "object_id"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String(5), nullable=False, default="write")  # read | write
    created: Mapped[float] = mapped_column(Float, nullable=False, default=time.time)


class ShareMember(Model):
    """An invited user's answer for an item that is joined first (Shareable.JOINS): joined (maybe with an account of
    theirs, e.g. where a copy lives) or declined."""

    __tablename__ = "core_share_members"
    __table_args__ = (UniqueConstraint("object_type", "object_id", "user_id"),
                      Index("ix_core_share_members_object", "object_type", "object_id"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False)  # joined | declined
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created: Mapped[float] = mapped_column(Float, nullable=False, default=time.time)


class ShareNotice(Model):
    """A message shown once to a user on the page of a type (a share ended, they were removed): the English source
    text and its parameters, translated when it is taken."""

    __tablename__ = "core_share_notices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created: Mapped[float] = mapped_column(Float, nullable=False, default=time.time)


# --- attachments (flaskspark.core.attachments) ------------------------------------------------------------------------
class Attachment(Model):
    """A file attached to an item of a module (owner_type: its AttachmentOwner.TYPE, owner_id: the item's id). The
    file lies below its store's directory (path, relative); kind: image, video or document."""

    __tablename__ = "core_attachments"
    __table_args__ = (Index("ix_core_attachments_owner", "owner_type", "owner_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_type: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    sorting: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded: Mapped[float] = mapped_column(Float, nullable=False, default=time.time)
