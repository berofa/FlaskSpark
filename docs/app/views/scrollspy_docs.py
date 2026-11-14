"""scrollspy documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.scrollspy import PAGE


class ScrollspyDocsView(FlaskSparkMethodView):
    """Render the scrollspy documentation page."""

    url = "/components/scrollspy"
    endpoint = "component_scrollspy"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
