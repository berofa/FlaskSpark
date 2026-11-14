"""ui-button-group documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.button_group import PAGE


class ButtonGroupDocsView(FlaskSparkMethodView):
    """Render the ui-button-group documentation page."""

    url = "/components/button-group"
    endpoint = "component_button_group"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
