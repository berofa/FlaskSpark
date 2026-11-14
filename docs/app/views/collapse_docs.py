"""ui-collapse documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.collapse import PAGE


class CollapseDocsView(FlaskSparkMethodView):
    """Render the ui-collapse documentation page."""

    url = "/components/collapse"
    endpoint = "component_collapse"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
