"""ui-toast documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.toast import PAGE


class ToastDocsView(FlaskSparkMethodView):
    """Render the ui-toast documentation page."""

    url = "/components/toast"
    endpoint = "component_toast"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
