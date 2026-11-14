"""ui-dropzone documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.dropzone import PAGE


class DropzoneDocsView(FlaskSparkMethodView):
    """Render the ui-dropzone documentation page."""

    url = "/components/dropzone"
    endpoint = "component_dropzone"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
