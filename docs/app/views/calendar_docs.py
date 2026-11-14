"""ui-calendar documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.calendar import PAGE


class CalendarDocsView(FlaskSparkMethodView):
    """Render the ui-calendar documentation page."""

    url = "/components/calendar"
    endpoint = "component_calendar"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
