"""ui-tooltip documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.tooltip import PAGE


class TooltipDocsView(FlaskSparkMethodView):
    """Render the ui-tooltip documentation page."""

    url = "/components/tooltip"
    endpoint = "component_tooltip"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
