"""ui-dialog documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.dialog import PAGE


class DialogDocsView(FlaskSparkMethodView):
    """Render the ui-dialog documentation page."""

    url = "/components/dialog"
    endpoint = "component_dialog"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
