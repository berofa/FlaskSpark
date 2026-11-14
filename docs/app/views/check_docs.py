"""ui-check documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.check import PAGE


class CheckDocsView(FlaskSparkMethodView):
    """Render the ui-check documentation page."""

    url = "/components/check"
    endpoint = "component_check"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
