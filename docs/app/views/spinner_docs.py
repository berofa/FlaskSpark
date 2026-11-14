"""ui-spinner documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.spinner import PAGE


class SpinnerDocsView(FlaskSparkMethodView):
    """Render the ui-spinner documentation page."""

    url = "/components/spinner"
    endpoint = "component_spinner"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
