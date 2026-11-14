"""FlaskSpark's users and roles as targets of foreign keys (flaskspark.core.db.USER, ROLES): a module's table points at
a user without importing FlaskSpark, and the sign-in tables stay out of the modules' metadata."""
from __future__ import annotations

import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

from flaskspark.core import db


class Base(DeclarativeBase):
    """A metadata of the test's own (like Model, without adding a table to the application's)."""


class Ticket(Base):
    __tablename__ = "test_ticket"

    id: db.Mapped[int] = db.mapped_column(db.Integer, primary_key=True)
    owner_id: db.Mapped[int | None] = db.mapped_column(db.Integer, db.ForeignKey(db.USER.c.id, ondelete="SET NULL"))
    role_id: db.Mapped[int | None] = db.mapped_column(db.Integer, db.ForeignKey(db.ROLES.c.id))


def test_the_sign_in_tables_are_not_the_modules():
    assert db.USER.metadata is not db.Model.metadata
    assert "user" not in db.load_models() and "roles" not in db.load_models()
    assert db.USER.c.role_id.references(db.ROLES.c.id)


def test_a_module_table_points_at_a_user(tmp_path):
    path = tmp_path / "fk.db"
    eng = create_engine(f"sqlite:///{path}")
    db.signin.METADATA.create_all(eng)
    Base.metadata.create_all(eng)
    eng.dispose()
    con = sqlite3.connect(path)
    keys = {(r[2], r[3], r[4]) for r in con.execute("PRAGMA foreign_key_list(test_ticket)")}
    con.close()
    assert keys == {("user", "owner_id", "id"), ("roles", "role_id", "id")}
