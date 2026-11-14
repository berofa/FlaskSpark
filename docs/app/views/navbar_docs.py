"""Navbar documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.navbar import PAGE


class NavbarDocsView(FlaskSparkMethodView):
    """Render the Navbar documentation page."""

    url = "/components/navbar"
    endpoint = "component_navbar"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
