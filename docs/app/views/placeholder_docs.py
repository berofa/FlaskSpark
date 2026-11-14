"""ui-placeholder documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.placeholder import PAGE


class PlaceholderDocsView(FlaskSparkMethodView):
    """Render the ui-placeholder documentation page."""

    url = "/components/placeholder"
    endpoint = "component_placeholder"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
