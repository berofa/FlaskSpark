"""ui-datepicker documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.datepicker import PAGE


class DatepickerDocsView(FlaskSparkMethodView):
    """Render the ui-datepicker documentation page."""

    url = "/components/datepicker"
    endpoint = "component_datepicker"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
