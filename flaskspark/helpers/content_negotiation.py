"""
Content negotiation helpers for FlaskSpark.

Decide whether a request wants JSON instead of HTML and convert view data into
JSON-serialisable structures.
"""

from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import PurePath
from uuid import UUID

from flask import request


def wants_json():
    """
    Determine whether the current request expects a JSON response.

    Precedence:
        1. Query parameter `?format=json` (or `?format=html` to force HTML).
        2. The Accept header, if it prefers `application/json` over `text/html`.
        3. A JSON request body (`Content-Type: application/json`) as a fallback.

    A wildcard Accept header (`*/*`, e.g. curl's default) resolves to HTML.

    Args:
        None

    Returns:
        bool: True if the response should be JSON.
    """
    fmt = (request.args.get("format") or "").lower()
    if fmt in ("json", "html"):
        return fmt == "json"

    accepted = request.accept_mimetypes
    if accepted.best_match(["text/html", "application/json"]) == "application/json":
        return True

    return request.is_json


def to_jsonable(value):
    """
    Recursively convert a value into JSON-serialisable types.

    Handles dicts, lists/tuples/sets, datetime/date/time (ISO 8601), timedelta
    (seconds), Decimal, UUID, Enum, paths, dataclasses and objects that provide
    a `to_dict()` method.

    Args:
        value (Any): The value to convert.

    Returns:
        Any: A structure that `json.dumps` can serialise.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return to_jsonable(value.value)
    if isinstance(value, (UUID, PurePath)):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(asdict(value))
    if callable(getattr(value, "to_dict", None)):
        return to_jsonable(value.to_dict())
    return str(value)
