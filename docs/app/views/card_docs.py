"""ui-card documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.card import PAGE


class CardDocsView(FlaskSparkMethodView):
    """Render the ui-card documentation page."""

    url = "/components/card"
    endpoint = "component_card"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
