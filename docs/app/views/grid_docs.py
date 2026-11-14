"""ui-grid documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.grid import PAGE


class GridDocsView(FlaskSparkMethodView):
    """Render the ui-grid documentation page."""

    url = "/components/grid"
    endpoint = "component_grid"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
