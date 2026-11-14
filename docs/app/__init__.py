"""Documentation app initialization."""

from __future__ import annotations

import os
from pathlib import Path

from flaskspark import FlaskSpark

from webcomponents.tokens import component_tokens, spec_tokens

DOCS_ROOT = Path(__file__).resolve().parent.parent

flask_spark_instance = FlaskSpark(
    app_module="app",
    config={
        "SECRET_KEY": os.environ.get("SECRET_KEY", "webcomponents-docs-secret"),
        "ASSETS_BUILD_ON_START": True,
        # Plain CSS, no SCSS: the bundle only minifies (FlaskSpark still names the setting "SCSS").
        "ASSETS_SCSS_ENTRY": "css/app.css",
        "ASSETS_SCSS_FILTERS": "rcssmin",
        # Bootstrap 6 page CSS and the "bootstrap" module; FlaskSpark registers the components' blueprint.
        "VENDOR_INCLUDE_WEBCOMPONENTS": True,
    },
    dotenv_path=str(DOCS_ROOT / ".env"),
)

app = flask_spark_instance.app
# CSS variables of a component (defaults from the vendored Bootstrap CSS, descriptions from submodule.json).
app.jinja_env.globals["component_tokens"] = component_tokens
app.jinja_env.globals["spec_tokens"] = spec_tokens


@app.context_processor
def _inject_navigation():
    return {
        "docs_navigation": [
            {"label": "Overview", "href": "/"},
            {"label": "ui-accordion", "href": "/components/accordion"},
            {"label": "ui-alert", "href": "/components/alert"},
            {"label": "ui-avatar", "href": "/components/avatar"},
            {"label": "ui-badge", "href": "/components/badge"},
            {"label": "ui-breadcrumb", "href": "/components/breadcrumb"},
            {"label": "ui-button", "href": "/components/button"},
            {"label": "ui-button-group", "href": "/components/button-group"},
            {"label": "ui-calendar", "href": "/components/calendar"},
            {"label": "ui-card", "href": "/components/card"},
            {"label": "ui-carousel", "href": "/components/carousel"},
            {"label": "ui-check", "href": "/components/check"},
            {"label": "ui-chip / chip-input", "href": "/components/chip"},
            {"label": "ui-close-button", "href": "/components/close-button"},
            {"label": "ui-collapse", "href": "/components/collapse"},
            {"label": "ui-combobox", "href": "/components/combobox"},
            {"label": "ui-context-menu", "href": "/components/context-menu"},
            {"label": "ui-datepicker", "href": "/components/datepicker"},
            {"label": "ui-dialog", "href": "/components/dialog"},
            {"label": "ui-drawer", "href": "/components/drawer"},
            {"label": "ui-dropzone", "href": "/components/dropzone"},
            {"label": "ui-emoji-picker", "href": "/components/emoji-picker"},
            {"label": "ui-gallery", "href": "/components/gallery"},
            {"label": "ui-grid", "href": "/components/grid"},
            {"label": "ui-grid-editor", "href": "/components/grid-editor"},
            {"label": "ui-input / select / textarea", "href": "/components/form-controls"},
            {"label": "ui-kpi / kpi-group", "href": "/components/kpi"},
            {"label": "ui-list-group", "href": "/components/list-group"},
            {"label": "ui-markdown-editor / markdown", "href": "/components/markdown"},
            {"label": "ui-menu", "href": "/components/menu"},
            {"label": "Nav (markup)", "href": "/components/nav"},
            {"label": "Navbar (markup)", "href": "/components/navbar"},
            {"label": "ui-otp", "href": "/components/otp"},
            {"label": "ui-pagination", "href": "/components/pagination"},
            {"label": "ui-placeholder", "href": "/components/placeholder"},
            {"label": "ui-popover", "href": "/components/popover"},
            {"label": "ui-progress", "href": "/components/progress"},
            {"label": "ui-range", "href": "/components/range"},
            {"label": "ui-richtext", "href": "/components/richtext"},
            {"label": "Scrollspy (data API)", "href": "/components/scrollspy"},
            {"label": "ui-spinner", "href": "/components/spinner"},
            {"label": "ui-stepper", "href": "/components/stepper"},
            {"label": "ui-table", "href": "/components/table"},
            {"label": "ui-tabs", "href": "/components/tabs"},
            {"label": "ui-toast", "href": "/components/toast"},
            {"label": "Toggler (data API)", "href": "/components/toggler"},
            {"label": "ui-tooltip", "href": "/components/tooltip"},
        ]
    }
