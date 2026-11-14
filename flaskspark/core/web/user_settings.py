"""Personal settings of the visitor (e.g. the columns a list shows, a chart's layout): a dict per key.

- Signed in (RoleAccess): in the database (table core_user_settings), the same on every device of the user.
- Without sign-in (OpenAccess, user id 0): in the visitor's session, which lives on the server (Flask-Session): per
  browser, as long as the session (PERMANENT_SESSION_LIFETIME). There is no user to keep them for longer.
"""

from __future__ import annotations

import re

from flask import session

from flaskspark.core import db
from flaskspark.core.models import UserSetting

from . import user_id

SESSION_KEY = "core_user_settings"
KEY = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")


def check_key(key: str) -> str:
    if not isinstance(key, str) or not KEY.match(key):
        raise ValueError(f"invalid key for a user setting: {key!r}")
    return key


def load(key: str) -> dict:
    check_key(key)
    uid = user_id()
    if not uid:
        return dict((session.get(SESSION_KEY) or {}).get(key) or {})
    with db.session() as s:
        row = s.scalars(db.select(UserSetting).where(UserSetting.user_id == uid, UserSetting.key == key)).first()
        return dict(row.value) if row else {}


def save(key: str, value: dict) -> dict:
    check_key(key)
    if not isinstance(value, dict):
        raise ValueError("a user setting is a dict")
    uid = user_id()
    if not uid:
        stored = dict(session.get(SESSION_KEY) or {})
        stored[key] = value
        session[SESSION_KEY] = stored
        return value
    with db.session() as s:
        row = s.scalars(db.select(UserSetting).where(UserSetting.user_id == uid, UserSetting.key == key)).first()
        if row is None:
            s.add(UserSetting(user_id=uid, key=key, value=value))
        else:
            row.value = value
    return value
