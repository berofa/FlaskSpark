"""ui-alert documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.alert import PAGE


class AlertDocsView(FlaskSparkMethodView):
    """Render the ui-alert documentation page."""

    url = "/components/alert"
    endpoint = "component_alert"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
