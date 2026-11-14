"""ui-avatar documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.avatar import PAGE


class AvatarDocsView(FlaskSparkMethodView):
    """Render the ui-avatar documentation page."""

    url = "/components/avatar"
    endpoint = "component_avatar"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
