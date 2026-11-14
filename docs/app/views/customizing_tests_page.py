"""Browser checks of the customizing demos (tests/python/test_browser.py loads this page in headless Chromium).

Every demo is rendered twice: with its CSS class and without it. The page checks that the customized element looks
different, i.e. the documented tokens really reach the component.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

PAGES = Path(__file__).resolve().parent.parent / "pages"


def demos() -> list[dict]:
    result = []
    for path in sorted(PAGES.glob("*.py")):
        if path.stem in {"__init__", "common", "custom"}:
            continue
        page = importlib.import_module(f"app.pages.{path.stem}").PAGE
        custom = page.get("custom")
        if not custom:
            continue
        css = custom["css"]
        selector = re.match(r"\s*([^{]+?)\s*\{", css).group(1)
        name = re.match(r"\.([\w-]+)", selector).group(1)  # the demo's own class
        plain = re.sub(rf'(class="[^"]*?)\b{re.escape(name)}\b\s*', r"\1", custom["html"]).replace(' class=""', "")
        plain = re.sub(r'(id="|#)(\w+)"', r'\1\2Plain"', plain)
        tokens = " ".join(re.findall(r"(--[\w-]+)\s*:", css))
        result.append({"name": path.stem, "css": css, "selector": selector, "html": custom["html"], "plain": plain, "tokens": tokens})
    return result


class CustomizingTestsView(FlaskSparkMethodView):
    """Render the page that checks every customizing demo."""

    url = "/_tests/customizing"
    endpoint = "customizing_tests"

    def get(self):
        return render_template("tests/customizing.html", demos=demos())
