"""ui-table documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.table import PAGE


class TableDocsView(FlaskSparkMethodView):
    """Render the ui-table documentation page."""

    url = "/components/table"
    endpoint = "component_table"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
