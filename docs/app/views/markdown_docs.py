"""ui-markdown-editor and ui-markdown documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.markdown import PAGE


class MarkdownDocsView(FlaskSparkMethodView):
    """Render the ui-markdown-editor / ui-markdown documentation page."""

    url = "/components/markdown"
    endpoint = "component_markdown"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
