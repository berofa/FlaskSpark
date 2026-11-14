"""ui-combobox documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.combobox import PAGE


class ComboboxDocsView(FlaskSparkMethodView):
    """Render the ui-combobox documentation page."""

    url = "/components/combobox"
    endpoint = "component_combobox"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
