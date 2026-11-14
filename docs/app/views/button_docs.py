"""ui-button documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.button import PAGE


class ButtonDocsView(FlaskSparkMethodView):
    """Render the ui-button documentation page."""

    url = "/components/button"
    endpoint = "component_button"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
