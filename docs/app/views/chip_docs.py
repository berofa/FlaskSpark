"""ui-chip / ui-chip-input documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.chip import PAGE


class ChipDocsView(FlaskSparkMethodView):
    """Render the ui-chip documentation page."""

    url = "/components/chip"
    endpoint = "component_chip"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
