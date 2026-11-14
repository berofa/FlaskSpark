"""The rights of the modules in the database: a module's session reaches its own tables (manifest TABLES) and
the shared ones it names (SHARED_TABLES), nothing else; the core reaches all. A module that names no tables reaches
none (fail-closed).

Checked in the session, before anything reaches the database: every statement it executes (queries, also lazy
loads and session.get) and every object it writes on a flush. Plain SQL (text) has no tables to check: refused for a
checked module (plain SQL belongs into the API).
"""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import TextClause, event, inspect
from sqlalchemy.orm import Session
from sqlalchemy.sql import visitors
from sqlalchemy.sql.schema import Table
from sqlalchemy.sql.selectable import TableClause

INFO_KEY = "app_allowed"  # session.info: the tables the session may touch (None or missing: all)
NAME_KEY = "app_module"


class DatabaseAccessError(PermissionError):
    """A module reached for a table that is not its own (nor one of its shared ones)."""


def _tables(statement) -> set[str]:
    out = set()
    for element in visitors.iterate(statement):
        if isinstance(element, (Table, TableClause)):
            out.add(element.name)
    return out


def _check(session: Session, tables: set[str]) -> None:
    allowed = session.info.get(INFO_KEY)
    if allowed is None:
        return
    foreign = tables - allowed
    if foreign:
        raise DatabaseAccessError(f"module {session.info.get(NAME_KEY)!r} may not use {', '.join(sorted(foreign))} "
                                  "(only its own tables and the shared ones its manifest names)")


@contextmanager
def as_core(session: Session):
    """The core's own work inside a module's session (e.g. accounts: does the account still have a capability in
    another module's table): every table for the block, the module's rights again after it."""
    allowed = session.info.get(INFO_KEY)
    session.info[INFO_KEY] = None
    try:
        yield session
    finally:
        session.info[INFO_KEY] = allowed


@event.listens_for(Session, "do_orm_execute")
def _on_execute(state) -> None:
    session = state.session
    if session.info.get(INFO_KEY) is None:
        return
    if isinstance(state.statement, TextClause):
        raise DatabaseAccessError(f"module {session.info.get(NAME_KEY)!r}: plain SQL only inside the database API")
    _check(session, _tables(state.statement))


@event.listens_for(Session, "before_flush")
def _on_flush(session: Session, _context, _instances) -> None:
    if session.info.get(INFO_KEY) is None:
        return
    tables = set()
    for obj in (*session.new, *session.dirty, *session.deleted):
        # every table of its mapper: a model over a join (e.g. a model over two tables)
        tables |= {t.name for t in inspect(obj).mapper.tables}
    _check(session, tables)
