"""ui-close-button documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.close_button import PAGE


class CloseButtonDocsView(FlaskSparkMethodView):
    """Render the ui-close-button documentation page."""

    url = "/components/close-button"
    endpoint = "component_close_button"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
