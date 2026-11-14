"""ui-popover documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.popover import PAGE


class PopoverDocsView(FlaskSparkMethodView):
    """Render the ui-popover documentation page."""

    url = "/components/popover"
    endpoint = "component_popover"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
