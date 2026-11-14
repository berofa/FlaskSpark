"""Sharing of every module's items (flaskspark.core.shares), for <ui-share-dialog> and the modules' pages. Only with
sign-in (roles to share with); without it every request answers 404. An item of a Shareable with an AREA needs that
area; unknown items and items of others alike answer 404.

GET  /api/shares/<type>/<id>             the owner's dialog: {type, label, name, roles, shares: {role id: read|write},
                                         joins, members: [{username, status, permission}]}
POST /api/shares/<type>/<id>             {shares: {role id: read|write}} (none: shared with no one) -> the same and a
                                         message; the users concerned get the event "shares" (type, id)
GET  /api/shares/<type>                  {invitations: [{id, name, owner, status, permission}], notices: [text]} of
                                         the visitor (each notice only once)
POST /api/shares/<type>/<id>/join        join an item one is invited to (a kind that joins first)
POST /api/shares/<type>/<id>/leave       decline or leave it
"""

from __future__ import annotations

from flask import jsonify, request
from flask_babel import gettext
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core import events, shares
from flaskspark.core.web import OPEN, can, get_access, user_id


def _ok(data: dict):
    return jsonify(data)


def _fail(message: str, status: int = 400):
    return jsonify({"error": message}), status


def _message(error) -> str:
    template = getattr(error, "template", None)
    return gettext(template, **dict(error.params)) if template else str(error)


def _kind(object_type: str):
    """The Shareable, or the answer that ends the request (no sign-in, unknown, its area not allowed)."""
    if not get_access().signed_in or not user_id():
        return None, _fail(gettext("Sharing needs a sign-in."), 404)
    try:
        kind = shares.get(object_type)
    except shares.ShareError:
        return None, _fail(gettext("Not found."), 404)
    if kind.AREA and not can(kind.AREA):
        return None, _fail(gettext("Not found."), 404)
    return kind, None


def _dialog(kind, object_id: int) -> dict:
    data = shares.dialog(kind.TYPE, object_id, user_id())
    # data["label"]: shares.dialog() translated it already
    return data


class ShareApiView(FlaskSparkMethodView):
    url = "/api/shares/<object_type>/<int:object_id>"
    endpoint = "core_share"
    area = OPEN

    def get(self, object_type: str, object_id: int):
        kind, refused = _kind(object_type)
        if refused:
            return refused
        try:
            return _ok(_dialog(kind, object_id))
        except shares.ShareError:
            return _fail(gettext("Not found."), 404)

    def post(self, object_type: str, object_id: int):
        kind, refused = _kind(object_type)
        if refused:
            return refused
        wanted = (request.get_json(silent=True) or {}).get("shares") or {}
        if not isinstance(wanted, dict):
            return _fail(gettext("The shares are not readable."))
        try:
            concerned = shares.set_targets(kind.TYPE, object_id, user_id(), wanted)
            data = _dialog(kind, object_id)
        except shares.ShareError as error:
            return _fail(_message(error))
        events.emit_users("shares", concerned, type=kind.TYPE, id=object_id)
        text = gettext("Sharing saved.") if data["shares"] else gettext("Shared with no one.")
        return _ok({**data, "message": text})


class SharesOfTypeApiView(FlaskSparkMethodView):
    url = "/api/shares/<object_type>"
    endpoint = "core_shares_of_type"
    area = OPEN

    def get(self, object_type: str):
        kind, refused = _kind(object_type)
        if refused:
            return refused
        found = shares.invitations(user_id(), kind.TYPE)
        return _ok({"invitations": [{k: v for k, v in item.items() if k != "account_id"} for item in found],
                    "notices": shares.take_notices(user_id(), kind.TYPE)})


class ShareAnswerApiView(FlaskSparkMethodView):
    url = "/api/shares/<object_type>/<int:object_id>/<answer>"
    endpoint = "core_share_answer"
    area = OPEN

    def post(self, object_type: str, object_id: int, answer: str):
        kind, refused = _kind(object_type)
        if refused:
            return refused
        try:
            if answer == "join":
                shares.join(user_id(), kind.TYPE, object_id)
                text = gettext("Joined.")
            elif answer == "leave":
                shares.leave(user_id(), kind.TYPE, object_id)
                text = gettext("Left.")
            else:
                return _fail(gettext("Unknown action."), 404)
        except shares.ShareError as error:
            return _fail(_message(error), 404)
        events.emit_users("shares", {user_id()}, type=kind.TYPE, id=object_id)
        return _ok({"ok": True, "message": text})
