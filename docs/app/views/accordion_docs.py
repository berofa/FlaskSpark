"""ui-accordion documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.accordion import PAGE


class AccordionDocsView(FlaskSparkMethodView):
    """Render the ui-accordion documentation page."""

    url = "/components/accordion"
    endpoint = "component_accordion"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
