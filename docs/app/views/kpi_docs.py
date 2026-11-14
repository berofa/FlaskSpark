"""ui-kpi documentation view."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.kpi import PAGE


class KpiDocsView(FlaskSparkMethodView):
    """Render the ui-kpi documentation page."""

    url = "/components/kpi"
    endpoint = "component_kpi"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
