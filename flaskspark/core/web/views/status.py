"""Status of the application's services for the tiles in the sidebar (flaskspark.core.status: the tiles of the core and
the modules), admins only.

GET /api/status/services -> {services: [{key, name, service, level, summary, details, instances}], ts}
"""

from __future__ import annotations

import time

from flask import jsonify
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core import config, status
from flaskspark.core.web import ADMIN


class ServicesStatusView(FlaskSparkMethodView):
    url = "/api/status/services"
    endpoint = "api_status_services"
    area = ADMIN

    def get(self):
        return jsonify({"services": status.collect(config.load()), "ts": time.time()})
