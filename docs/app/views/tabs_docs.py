"""ui-tabs documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.tabs import PAGE


class TabsDocsView(FlaskSparkMethodView):
    """Render the ui-tabs documentation page."""

    url = "/components/tabs"
    endpoint = "component_tabs"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
