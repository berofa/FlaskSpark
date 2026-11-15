"""Status of the application's services for the tiles in the sidebar (flaskspark.core.status: the tiles of the core and
the modules): admins only, or everyone who may use the app with config.yaml `status.everyone: true` (everybody sees
when something does not run).

GET /api/status/services -> {services: [{key, name, service, level, summary, details, instances}], ts}
"""

from __future__ import annotations

import time

from flask import jsonify
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core import config, status
from flask import abort

from flaskspark.core.web import ADMIN, OPEN, can


def everyone() -> bool:
    """config.yaml `status.everyone`: the services' status for everyone, not only the admins."""
    return bool(config.load().section("status").get("everyone", False))


class ServicesStatusView(FlaskSparkMethodView):
    url = "/api/status/services"
    endpoint = "api_status_services"
    area = OPEN  # admins, or everyone with status.everyone (below)

    def get(self):
        if not can(ADMIN) and not everyone():
            abort(403)
        return jsonify({"services": status.collect(config.load()), "ts": time.time()})
