"""Personal settings of the visitor for scripts (flaskspark.core.web.user_settings):

GET /api/user-settings/<key>         {key, value}: the stored dict ({} without one)
PUT /api/user-settings/<key>         {value: {...}} -> {key, value} (also POST)
"""

from __future__ import annotations

import json

from flask import jsonify, request
from flask_babel import gettext
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core.web import OPEN, save_user_setting, user_setting
from flaskspark.core.web.user_settings import KEY


def _ok(data: dict):
    """An API answer: always JSON (also without an Accept header)."""
    return jsonify(data)


def _fail(message: str, status: int = 400):
    return jsonify({"error": message}), status


MAX_BYTES = 64 * 1024


class UserSettingApiView(FlaskSparkMethodView):
    url = "/api/user-settings/<key>"
    endpoint = "core_user_setting"
    area = OPEN

    def get(self, key: str):
        if not KEY.match(key):
            return _fail(gettext("Invalid key."), status=404)
        return _ok({"key": key, "value": user_setting(key)})

    def put(self, key: str):
        if not KEY.match(key):
            return _fail(gettext("Invalid key."), status=404)
        value = (request.get_json(silent=True) or {}).get("value")
        if not isinstance(value, dict):
            return _fail(gettext("The value must be an object."))
        if len(json.dumps(value)) > MAX_BYTES:
            return _fail(gettext("The value is too large."))
        return _ok({"key": key, "value": save_user_setting(key, value)})

    post = put
