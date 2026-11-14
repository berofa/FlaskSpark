"""ui-gallery documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.gallery import PAGE


class GalleryDocsView(FlaskSparkMethodView):
    """Render the ui-gallery documentation page."""

    url = "/components/gallery"
    endpoint = "component_gallery"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
