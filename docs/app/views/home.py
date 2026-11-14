"""Documentation landing page: the concept (shadow DOM, what a component brings, styling)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.home import PAGE


class HomeView(FlaskSparkMethodView):
    """Render the overview page."""

    url = "/"
    endpoint = "home"

    def get(self):
        return render_template("home.html", page=PAGE)
