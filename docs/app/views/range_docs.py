"""ui-range documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.range_ import PAGE


class RangeDocsView(FlaskSparkMethodView):
    """Render the ui-range documentation page."""

    url = "/components/range"
    endpoint = "component_range"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
