"""ui-drawer documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.drawer import PAGE


class DrawerDocsView(FlaskSparkMethodView):
    """Render the ui-drawer documentation page."""

    url = "/components/drawer"
    endpoint = "component_drawer"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
