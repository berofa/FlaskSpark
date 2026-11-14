"""Browser checks of the components (tests/python/test_browser.py loads this page in headless Chromium)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView


class ComponentTestsView(FlaskSparkMethodView):
    """Render the page that checks the components in a real browser and reports JSON."""

    url = "/_tests/components"
    endpoint = "component_tests"

    def get(self):
        return render_template("tests/components.html")
