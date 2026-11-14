"""ui-collapse (Bootstrap 6 collapse)."""

from __future__ import annotations

from .common import lines

TEXT = ("Some placeholder content for the collapse component. This panel is hidden by default but revealed when the "
        "user activates the relevant trigger.")

PAGE = {
    "title": "ui-collapse",
    "summary": "Show and hide content with an animated size (vertical or horizontal), from any number of triggers, for "
    "any number of targets — also Bootstrap's plain .collapse markup.",
    "submodule": "ui-collapse",
    "entry": "modules/bootstrap/ui-collapse/ui-collapse.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "A trigger with <code>data-bs-toggle=\"collapse\"</code> and <code>data-bs-target</code> (or a link's "
            "<code>href</code>); it gets <code>aria-expanded</code>. The size animates with "
            "<code>interpolate-size</code>; browsers without it switch at once.",
            "html": lines(
                '<p class="d-inline-flex gap-1">',
                '  <a class="btn-solid theme-primary" href="#collapseExample" role="button" data-bs-toggle="collapse">Link with href</a>',
                '  <ui-button variant="primary" data-bs-toggle="collapse" data-bs-target="#collapseExample">Button with data-bs-target</ui-button>',
                "</p>",
                '<ui-collapse id="collapseExample">',
                f'  <div class="card card-body">{TEXT}</div>',
                "</ui-collapse>",
            ),
        },
        {
            "id": "horizontal",
            "title": "Horizontal",
            "intro": "<code>horizontal</code> animates the width; give the content a width.",
            "html": lines(
                '<ui-button variant="primary" data-bs-toggle="collapse" data-bs-target="#collapseWidthExample">Toggle width collapse</ui-button>',
                '<div style="min-height: 120px;" class="mt-3">',
                '  <ui-collapse horizontal id="collapseWidthExample">',
                '    <div class="card card-body" style="width: 300px;">This is some placeholder content for a horizontal collapse.</div>',
                "  </ui-collapse>",
                "</div>",
            ),
        },
        {
            "id": "multiple",
            "title": "Multiple toggles and targets",
            "intro": "A selector may match several targets; several triggers may control the same target.",
            "html": lines(
                '<p class="d-inline-flex gap-1">',
                '  <ui-button variant="primary" data-bs-toggle="collapse" data-bs-target="#multiCollapse1">Toggle first</ui-button>',
                '  <ui-button variant="primary" data-bs-toggle="collapse" data-bs-target="#multiCollapse2">Toggle second</ui-button>',
                '  <ui-button variant="primary" data-bs-toggle="collapse" data-bs-target=".multi-collapse">Toggle both</ui-button>',
                "</p>",
                '<div class="row">',
                f'  <div class="col"><ui-collapse class="multi-collapse" id="multiCollapse1"><div class="card card-body">{TEXT}</div></ui-collapse></div>',
                f'  <div class="col"><ui-collapse class="multi-collapse" id="multiCollapse2"><div class="card card-body">{TEXT}</div></ui-collapse></div>',
                "</div>",
            ),
        },
        {
            "id": "plain-markup",
            "title": "Plain markup",
            "intro": "The data API also works on Bootstrap's own <code>.collapse</code> elements.",
            "html": lines(
                '<button class="btn-outline theme-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#plainCollapse">Toggle</button>',
                f'<div class="collapse mt-2" id="plainCollapse"><div class="card card-body">{TEXT}</div></div>',
            ),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines(
                'const panel = document.querySelector("#collapseExample");',
                'panel.addEventListener("ui-collapse:shown", () => console.log("open"));',
                "await panel.show();",
                "panel.toggle();",
            ),
        },
    ],
    "tokens": {"host": "ui-collapse", "example_token": "--bs-transition-collapse-duration", "example_value": "1s"},
    "elements": [
        {
            "tag": "ui-collapse",
            "attributes": [("open", "boolean", "Shown; reflected."), ("horizontal", "boolean", "Animates the width.")],
            "slots": [("(default)", "The content.")],
            "parts": [("collapse", "The <code>.collapse</code> element.")],
            "events": [("ui-collapse:show / ui-collapse:hide", "Before; cancelable (also on plain .collapse elements)."),
                       ("ui-collapse:shown / ui-collapse:hidden", "After the transition.")],
            "methods": [("show() / hide() / toggle()", "Promises."), ("shown", "Open (read only).")],
        }
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["collapse"]
