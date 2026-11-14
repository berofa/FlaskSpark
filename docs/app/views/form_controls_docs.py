"""ui-input, ui-select and ui-textarea documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.form_controls import PAGE


class FormControlsDocsView(FlaskSparkMethodView):
    """Render the ui-input, ui-select and ui-textarea documentation page."""

    url = "/components/form-controls"
    endpoint = "component_form_controls"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
