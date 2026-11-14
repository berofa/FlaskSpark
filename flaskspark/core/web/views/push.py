"""Sign-in of the push service.

GET /api/push/session -> {user, topics}: who the browser's session belongs to and which topics of the live channel they
may subscribe to (NATS patterns). The push service asks this with the cookie the browser sent along when it opens the
channel and every few minutes after. The topics: the events for everyone (ev.all.>), the visitor's own events
(ev.user.<id>.>) and the topics of the modules (manifest PUSH_TOPICS) whose area the visitor may use.
"""

from __future__ import annotations

from flask import jsonify
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core import config, modules
from flaskspark.core.web import OPEN, can, user_id


def topics(uid: int) -> list[str]:
    """The patterns the visitor may subscribe to, each once (in the order of the modules)."""
    out = ["ev.all.>", f"ev.user.{uid}.>"]
    for module in modules.load(config.load()):
        out += [t.pattern.format(uid=uid) for t in module.PUSH_TOPICS if can(t.area)]
    return list(dict.fromkeys(out))


class PushSessionView(FlaskSparkMethodView):
    url = "/api/push/session"
    endpoint = "api_push_session"
    area = OPEN

    def get(self):
        uid = user_id()
        return jsonify({"user": uid, "topics": topics(uid)})
