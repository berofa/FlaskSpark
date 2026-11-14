"""ui-stepper documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.stepper import PAGE


class StepperDocsView(FlaskSparkMethodView):
    """Render the ui-stepper documentation page."""

    url = "/components/stepper"
    endpoint = "component_stepper"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
