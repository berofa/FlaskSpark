"""ui-grid-editor documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.grid_editor import PAGE


class GridEditorDocsView(FlaskSparkMethodView):
    """Render the ui-grid-editor documentation page."""

    url = "/components/grid-editor"
    endpoint = "component_grid_editor"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
