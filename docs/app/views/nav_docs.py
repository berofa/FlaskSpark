"""Nav documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.nav import PAGE


class NavDocsView(FlaskSparkMethodView):
    """Render the Nav documentation page."""

    url = "/components/nav"
    endpoint = "component_nav"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
