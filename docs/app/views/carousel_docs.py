"""ui-carousel documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.carousel import PAGE


class CarouselDocsView(FlaskSparkMethodView):
    """Render the ui-carousel documentation page."""

    url = "/components/carousel"
    endpoint = "component_carousel"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
