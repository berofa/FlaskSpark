"""ui-list-group documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.list_group import PAGE


class ListGroupDocsView(FlaskSparkMethodView):
    """Render the ui-list-group documentation page."""

    url = "/components/list-group"
    endpoint = "component_list_group"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
