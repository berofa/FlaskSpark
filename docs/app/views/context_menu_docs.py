"""ui-context-menu documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.context_menu import PAGE


class ContextMenuDocsView(FlaskSparkMethodView):
    """Render the ui-context-menu documentation page."""

    url = "/components/context-menu"
    endpoint = "component_context_menu"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
