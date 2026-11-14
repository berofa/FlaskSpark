"""ui-pagination documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.pagination import PAGE


class PaginationDocsView(FlaskSparkMethodView):
    """Render the ui-pagination documentation page."""

    url = "/components/pagination"
    endpoint = "component_pagination"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
