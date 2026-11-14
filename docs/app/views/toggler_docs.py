"""toggler documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.toggler import PAGE


class TogglerDocsView(FlaskSparkMethodView):
    """Render the toggler documentation page."""

    url = "/components/toggler"
    endpoint = "component_toggler"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
