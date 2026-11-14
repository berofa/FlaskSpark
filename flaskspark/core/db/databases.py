"""The database systems behind the database API: an abstract Database, one subclass per system (today SQLite,
PostgreSQL later), chosen by the scheme of the URL. What differs between them: setting up a connection, a consistent
copy for the backup and its check, and the few operations on whole tables the core needs (the tables there, their rows,
dropping tables a module left behind). Everything else goes through SQLAlchemy and stays portable."""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path

from sqlalchemy import MetaData, event, func, inspect, select
from sqlalchemy import table as sa_table
from sqlalchemy.engine import Engine


class Database(ABC):
    """One database system, chosen by the scheme of the URL (database_for)."""

    scheme: str = ""

    @abstractmethod
    def prepare(self, url: str) -> None:
        """Before the first connection (e.g. create the directory of a database file)."""

    @abstractmethod
    def configure(self, engine: Engine) -> None:
        """Settings of every new connection."""

    @abstractmethod
    def copy(self, url: str, target: Path) -> None:
        """A consistent copy of the live database into the file `target` (also while the services write)."""

    @abstractmethod
    def restore(self, url: str, source: Path) -> None:
        """Put the copy `source` in place of the live database (the services are stopped)."""

    @abstractmethod
    def location(self, url: str) -> str:
        """Where the database is (for messages and the scripts)."""

    @abstractmethod
    def check(self, path: Path) -> str:
        """Check a copy: "ok" or what is wrong."""

    @abstractmethod
    def counts(self, path: Path) -> dict[str, int]:
        """Rows per table of a copy."""

    @abstractmethod
    def table_names(self, engine: Engine) -> list[str]:
        """The tables of the live database (without the system's own)."""

    @abstractmethod
    def row_count(self, engine: Engine, table: str) -> int:
        """The rows of one table of the live database."""

    @abstractmethod
    def drop_tables(self, engine: Engine, tables: list[str]) -> list[str]:
        """Drop tables of the live database with everything on them (indexes, data), the ones that refer to others
        first; returns the dropped ones (a name that is not there is skipped)."""


class SqliteDatabase(Database):
    """SQLite on the local disk (never NFS): WAL, no lost commits on power loss, a busy timeout for the several
    processes that write, foreign keys; copies with the SQLite backup API."""

    scheme = "sqlite"

    @staticmethod
    def path(url: str) -> Path:
        if not url.startswith("sqlite:///"):
            raise ValueError(f"not a SQLite file: {url}")
        return Path(url.removeprefix("sqlite:///"))

    def prepare(self, url: str) -> None:
        if url.startswith("sqlite:///"):
            self.path(url).parent.mkdir(parents=True, exist_ok=True)

    def configure(self, engine: Engine) -> None:
        event.listen(engine, "connect", _sqlite_pragmas)

    def copy(self, url: str, target: Path) -> None:
        source = self.path(url)
        if not source.is_file():
            raise FileNotFoundError(source)
        src = sqlite3.connect(source, timeout=30)
        dst = sqlite3.connect(target)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

    def restore(self, url: str, source: Path) -> None:
        live = self.path(url)
        for extra in (live.with_name(live.name + "-wal"), live.with_name(live.name + "-shm")):
            extra.unlink(missing_ok=True)
        Path(source).replace(live)

    def location(self, url: str) -> str:
        return str(self.path(url))

    def check(self, path: Path) -> str:
        con = sqlite3.connect(path)
        try:
            return con.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            con.close()

    def counts(self, path: Path) -> dict[str, int]:
        con = sqlite3.connect(path)
        try:
            tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            return {t: con.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tables}
        finally:
            con.close()


    def table_names(self, engine: Engine) -> list[str]:
        return sorted(t for t in inspect(engine).get_table_names() if not t.startswith("sqlite_"))

    def row_count(self, engine: Engine, table: str) -> int:
        with engine.connect() as connection:
            return int(connection.execute(select(func.count()).select_from(sa_table(table))).scalar_one())

    def drop_tables(self, engine: Engine, tables: list[str]) -> list[str]:
        present = set(self.table_names(engine))
        wanted = [t for t in dict.fromkeys(tables) if t in present]
        if not wanted:
            return []
        metadata = MetaData()
        metadata.reflect(engine, only=wanted, resolve_fks=False)
        # the ones that refer to others first; only the wanted ones (never a table they refer to)
        order = [t for t in reversed(metadata.sorted_tables) if t.name in wanted]
        with engine.begin() as connection:
            for table in order:
                table.drop(connection)
        return [t.name for t in order]


def _sqlite_pragmas(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=FULL")  # in WAL mode: no lost commits on power loss
    cursor.execute("PRAGMA busy_timeout=10000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


DATABASES: dict[str, Database] = {d.scheme: d for d in (SqliteDatabase(),)}


def database_for(url: str) -> Database:
    scheme = url.split(":", 1)[0].split("+", 1)[0]
    if scheme not in DATABASES:
        raise ValueError(f"no database system for {scheme}")
    return DATABASES[scheme]
