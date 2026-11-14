"""ui-breadcrumb documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.breadcrumb import PAGE


class BreadcrumbDocsView(FlaskSparkMethodView):
    """Render the ui-breadcrumb documentation page."""

    url = "/components/breadcrumb"
    endpoint = "component_breadcrumb"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
