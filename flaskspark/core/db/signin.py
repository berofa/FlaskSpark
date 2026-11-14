"""FlaskSpark's users and roles (the sign-in, flaskspark.models, kept in Flask-SQLAlchemy) as targets of foreign keys:
the tables «user» and «roles» described here in a MetaData of their own, so a module's table can point at a user or a
role without importing FlaskSpark and without these tables becoming part of the modules' metadata (their history is
the core's «signin», flaskspark.core.db.migrations).

    owner_id: Mapped[int | None] = mapped_column(Integer, ForeignKey(db.USER.c.id, ondelete="SET NULL"))

The description follows the sign-in history's head (versions_signin). Reading users through it (e.g. their names)
needs the table in the module's SHARED_TABLES like every other table it does not own.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, MetaData, String, Table

METADATA = MetaData()

ROLES = Table(
    "roles", METADATA,
    Column("id", Integer, primary_key=True),
    Column("name", String(255), nullable=False, unique=True),
    Column("is_admin", Boolean, nullable=False, default=False),
    Column("rank", Integer, nullable=False, default=0),
)

USER = Table(
    "user", METADATA,
    Column("id", Integer, primary_key=True),
    Column("username", String(255), nullable=False, unique=True),
    Column("email", String(255), nullable=False, unique=True),
    Column("role_id", Integer, ForeignKey("roles.id"), nullable=True),
    Column("first_name", String(255), nullable=True),
    Column("last_name", String(255), nullable=True),
    Column("admin", Boolean, nullable=True),
)

__all__ = ["METADATA", "ROLES", "USER"]
