"""The database API: the only place that works with SQLAlchemy and the database itself.

Every database function of the core and of every module goes through this API; none opens a connection, a session or
writes plain SQL itself. What the API gives:

- for_module(name) -> the module's access (ModuleDatabase): session() / transaction() as one unit of work (commits at
  the end, rolls back on an error), with the module's rights (access.py: its own tables, manifest TABLES, and the
  shared ones it names, SHARED_TABLES; the core reaches all).
- Model: the base of every table; the building blocks of tables and queries (sql.py: column types, select, update, …)
  handed through from SQLAlchemy. Modules import them from here, never sqlalchemy.
- The database systems behind it (databases.py): an abstract Database, today SqliteDatabase (PostgreSQL later),
  chosen by the URL.
- load_models(): every table of the enabled modules (manifest MODELS), for the migrations.
- USER and ROLES: FlaskSpark's users and roles as targets of foreign keys (ForeignKey(db.USER.c.id)), in a MetaData of
  their own (signin.py).

The web app, the services and the CLI open the same database (SQLite: WAL and a busy timeout let them write
concurrently; the file lies on a local disk, never on NFS). SQLALCHEMY_DATABASE_URI overrides the location for every
process (tests, a container). FlaskSpark keeps Flask-SQLAlchemy inside for its own tables (users and roles, once
sign-in comes), on the URL given here (the only exception).
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .. import paths
from . import access
from .access import DatabaseAccessError, as_core  # noqa: F401 - part of the API
from .databases import Database, database_for  # noqa: F401 - part of the API
from .signin import ROLES, USER  # noqa: F401 - part of the API: targets of foreign keys
from .sql import *  # noqa: F401,F403 - the building blocks are part of the API

CORE = "core"  # the core's name (its manifest): reaches every table

_engines: dict[str, Engine] = {}
_factories: dict[str, sessionmaker] = {}
_rights: dict[str, frozenset | None] = {}


def default_url() -> str:
    """SQLALCHEMY_DATABASE_URI, else the database in the state directory (read at every call: tests set it late)."""
    return os.environ.get("SQLALCHEMY_DATABASE_URI") or f"sqlite:///{paths.DATABASE}"


class Model(DeclarativeBase):
    """The base of every table of the application's modules."""


def engine(url: str | None = None) -> Engine:
    url = url or default_url()
    if url not in _engines:
        database = database_for(url)
        database.prepare(url)
        eng = create_engine(url)
        database.configure(eng)
        _engines[url] = eng
        _factories[url] = sessionmaker(eng, expire_on_commit=False)
    return _engines[url]


def dispose() -> None:
    """Close every engine (tests that switch databases)."""
    for eng in _engines.values():
        eng.dispose()
    _engines.clear()
    _factories.clear()
    _rights.clear()


class ModuleDatabase:
    """The database of one module: its sessions carry its rights."""

    def __init__(self, module: str, url: str | None = None):
        self.module, self._url = module, url

    @property
    def url(self) -> str:
        return self._url or default_url()

    def session(self):
        return session(self)

    transaction = session  # the same unit of work; the name says it where all or nothing matters

    def __repr__(self) -> str:
        return f"<database of {self.module}>"


def for_module(module: str, url: str | None = None) -> ModuleDatabase:
    """The access of a module (e.g. "notes") to the database."""
    return ModuleDatabase(module, url)


def rights(module: str) -> frozenset | None:
    """The tables a module's sessions may touch: its TABLES and SHARED_TABLES (manifest); None (all) only for the core.
    Fail-closed: a module that names none, or that is not enabled here, reaches nothing."""
    if module == CORE:
        return None
    if module not in _rights:
        from .. import config, modules

        manifest = modules.get(config.load(), module)
        if manifest is None:
            _rights[module] = frozenset()
        else:
            _rights[module] = frozenset(set(manifest.TABLES or ()) | set(manifest.SHARED_TABLES or ()))
    return _rights[module]


@contextmanager
def session(target: ModuleDatabase | None = None) -> Iterator[Session]:
    """A unit of work: commits on success, rolls back on errors. target: the module's access (for_module), None: the
    core's (all tables)."""
    url = target.url if target is not None else default_url()
    engine(url)
    s: Session = _factories[url]()
    if target is not None:
        s.info[access.NAME_KEY] = target.module
        s.info[access.INFO_KEY] = rights(target.module)
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def after_commit(s: Session, callback) -> None:
    """Call `callback()` once after the session's transaction is committed, never after a rollback (e.g. remove the
    files of deleted rows only when their rows are gone for good)."""
    from sqlalchemy import event

    event.listen(s, "after_commit", lambda _session: callback(), once=True)


def after_rollback(s: Session, callback) -> None:
    """Call `callback()` if the session's transaction is rolled back (e.g. remove a file written for a row that never
    came); never once it is committed."""
    from sqlalchemy import event

    settled = []

    def rolled_back(_session):
        if not settled:
            settled.append(True)
            callback()

    event.listen(s, "after_rollback", rolled_back)
    event.listen(s, "after_commit", lambda _session: settled.append(True))


def has_table(s: Session, name: str) -> bool:
    """The table exists in the database (asked of the database, not of the loaded models)."""
    return inspect(s.connection()).has_table(name)


def load_models(cfg=None):
    """Every table of the enabled modules (their manifests' MODELS imported): Model.metadata, e.g. for the migrations."""
    from .. import config, modules

    for manifest in modules.load(cfg or config.load()):
        for name in manifest.MODELS:
            importlib.import_module(name)
    return Model.metadata


# --- copies of the whole database (the backup, the restore scripts): through its Database, never a file copy ---------
def database(url: str | None = None) -> Database:
    """The database system of `url` (default: the application's database)."""
    return database_for(url or default_url())


def location(url: str | None = None) -> str:
    """Where the database is (for messages and scripts)."""
    url = url or default_url()
    return database_for(url).location(url)


def copy(target, url: str | None = None) -> None:
    """A consistent copy of the live database into the file `target` (also while the services write)."""
    from pathlib import Path

    url = url or default_url()
    database_for(url).copy(url, Path(target))


def check(path, url: str | None = None) -> str:
    """Check a copy: "ok" or what is wrong."""
    from pathlib import Path

    return database(url).check(Path(path))


def counts(path, url: str | None = None) -> dict[str, int]:
    """Rows per table of a copy."""
    from pathlib import Path

    return database(url).counts(Path(path))


# --- whole tables (the clean-up of what a module left behind, flaskspark.core.leftovers) ------------------------------
def table_names(url: str | None = None) -> list[str]:
    """The tables in the database (asked of the database, not of the models)."""
    url = url or default_url()
    return database_for(url).table_names(engine(url))


def row_count(table: str, url: str | None = None) -> int:
    """The rows of one table."""
    url = url or default_url()
    return database_for(url).row_count(engine(url), table)


def drop_tables(tables: list[str], url: str | None = None) -> list[str]:
    """Drop tables with their data (only the core: a module no longer delivered left them); returns the dropped ones."""
    url = url or default_url()
    return database_for(url).drop_tables(engine(url), list(tables))


def restore(source, url: str | None = None) -> None:
    """Put the copy `source` in place of the live database (the services are stopped); the engines are closed first."""
    from pathlib import Path

    url = url or default_url()
    dispose()
    database_for(url).restore(url, Path(source))
