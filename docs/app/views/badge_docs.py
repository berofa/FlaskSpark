"""ui-badge documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.badge import PAGE


class BadgeDocsView(FlaskSparkMethodView):
    """Render the ui-badge documentation page."""

    url = "/components/badge"
    endpoint = "component_badge"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
