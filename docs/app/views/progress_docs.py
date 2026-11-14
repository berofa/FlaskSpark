"""ui-progress documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.progress import PAGE


class ProgressDocsView(FlaskSparkMethodView):
    """Render the ui-progress documentation page."""

    url = "/components/progress"
    endpoint = "component_progress"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
