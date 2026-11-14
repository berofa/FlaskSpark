"""ui-richtext documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.richtext import PAGE


class RichtextDocsView(FlaskSparkMethodView):
    """Render the ui-richtext documentation page."""

    url = "/components/richtext"
    endpoint = "component_richtext"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
