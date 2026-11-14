"""ui-menu documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.menu import PAGE


class MenuDocsView(FlaskSparkMethodView):
    """Render the ui-menu documentation page."""

    url = "/components/menu"
    endpoint = "component_menu"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
