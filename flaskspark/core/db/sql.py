"""The building blocks of the database API the application's code may use: what a table is made of and how a query is
written. They come from SQLAlchemy, handed through unchanged (no own query language); outside flaskspark.core.db nothing
imports sqlalchemy itself. Sessions, transactions, plain SQL and the rights stay in the API (flaskspark.core.db: for_module,
session); a building block that is missing here comes here, it is not imported directly.
"""

from __future__ import annotations

from sqlalchemy import (  # noqa: F401 - handed through
    JSON,
    BigInteger,
    Date,
    DateTime,
    Numeric,
    asc,
    case,
    desc,
    distinct,
    exists,
    literal,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Table,
    Text,
    UniqueConstraint,
    and_,
    column,
    delete,
    func,
    insert,
    join,
    not_,
    or_,
    select,
    table,
    type_coerce,
    update,
)
from sqlalchemy.exc import IntegrityError, OperationalError  # noqa: F401
from sqlalchemy.orm import (  # noqa: F401
    Mapped,
    Session,  # only as a type (a parameter «s: Session»); a session is opened by the API
    column_property,
    mapped_column,
    object_session,
    joinedload,
    relationship,
    selectinload,
)
from sqlalchemy.types import TypeDecorator  # noqa: F401 - own column types (e.g. JSON as text)

__all__ = [
    "JSON", "BigInteger", "Date", "DateTime", "Numeric", "asc", "case", "desc", "distinct", "exists",
    "literal", "Boolean", "Float", "ForeignKey", "Index", "Integer", "LargeBinary", "String", "Table", "Text",
    "UniqueConstraint", "and_", "column", "delete", "func", "insert", "join", "not_", "or_", "select", "table", "type_coerce",
    "update", "IntegrityError", "OperationalError", "Mapped", "Session", "column_property", "mapped_column",
    "object_session", "joinedload", "relationship", "selectinload", "TypeDecorator",
]
