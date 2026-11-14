"""ui-popover (Bootstrap 6 popover)."""

from __future__ import annotations

from .common import lines

PAGE = {
    "title": "ui-popover",
    "summary": "Popovers with title and body in the top layer: click (default), hover or focus triggers, responsive "
    "placements, rich content, dismiss on next click, and Bootstrap's data API on plain markup.",
    "submodule": "ui-popover",
    "entry": "modules/bootstrap/ui-popover/ui-popover.js",
    "sections": [
        {
            "id": "live-demo",
            "title": "Live demo",
            "intro": "A click toggles it; Escape or a click outside closes it. Only one popover is open at a time.",
            "html": '<ui-popover heading="Popover title" text="And here’s some amazing content. It’s very engaging. Right?">'
                    '<ui-button variant="danger" size="lg">Click to toggle popover</ui-button></ui-popover>',
        },
        {
            "id": "placement",
            "title": "Placement",
            "intro": "<code>placement</code>: <code>right</code> (default), <code>top</code>, <code>bottom</code>, "
            "<code>left</code>, responsive.",
            "html": lines(*(f'<ui-popover text="{p.title()} popover" placement="{p}"><ui-button variant="secondary">Popover on {p}</ui-button></ui-popover>'
                            for p in ("top", "right", "bottom", "left"))),
            "preview_class": "d-flex flex-wrap gap-2 py-5",
        },
        {
            "id": "rich",
            "title": "Rich content",
            "intro": "Slots <code>heading</code> and <code>content</code> take markup (lists, tables, links).",
            "html": lines(
                "<ui-popover>",
                '  <ui-button variant="secondary">Rich popover</ui-button>',
                '  <strong slot="heading">Order 1042</strong>',
                '  <div slot="content"><ul class="mb-0 ps-3"><li>3 items</li><li>CHF 129.00</li></ul><a href="#">Open order</a></div>',
                "</ui-popover>",
            ),
        },
        {
            "id": "custom",
            "title": "Custom popovers",
            "intro": "Variables on the element (or <code>custom-class</code>).",
            "html": '<ui-popover heading="Custom popover" text="This popover is themed via CSS variables." '
                    'style="--bs-popover-header-bg: var(--bs-primary-bg); --bs-popover-header-color: var(--bs-white); --bs-popover-max-width: 200px;">'
                    '<ui-button variant="secondary">Custom popover</ui-button></ui-popover>',
        },
        {
            "id": "hover",
            "title": "Hover and focus",
            "intro": "<code>trigger=\"hover focus\"</code>; <code>focus</code> alone dismisses it on the next click elsewhere.",
            "html": lines(
                '<ui-popover heading="Hover" text="Opens on hover and focus." trigger="hover focus"><ui-button variant="secondary">Hover me</ui-button></ui-popover>',
                '<ui-popover heading="Dismissible popover" text="Closes on the next click." trigger="focus"><ui-button variant="danger">Dismissible popover</ui-button></ui-popover>',
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "plain-markup",
            "title": "Plain markup",
            "html": '<button type="button" class="btn-outline theme-secondary" data-bs-toggle="popover" data-bs-title="Plain" '
                    'data-bs-content="Plain markup popover" data-bs-placement="bottom">Plain markup</button>',
        },
    ],
    "elements": [
        {
            "tag": "ui-popover",
            "attributes": [
                ("heading", "string", "Title (or slot <code>heading</code>); without one no header."),
                ("text", "string", "Body (or slot <code>content</code>); <code>html</code>: sanitized HTML."),
                ("placement / trigger / delay / offset / custom-class / animation / disabled", "", "As on <code>ui-tooltip</code> (defaults: right, click, 0,8)."),
                ("anchor", "string", "Selector of an ancestor the box is placed at."),
            ],
            "slots": [("(default)", "The trigger."), ("heading / content", "Rich title and body.")],
            "parts": [("trigger, popover, arrow, header, body", "Trigger wrapper and the box parts.")],
            "events": [("ui-popover:show / hide / shown / hidden / inserted", "As on <code>ui-tooltip</code>.")],
            "methods": [("show(), hide(), toggle(), update(), enable(), disable(), setContent({ title, content })", "Control.")],
        }
    ],
    "tokens": {"host": "ui-popover", "example_token": "--bs-popover-max-width", "example_value": "360px"},
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["popover"]
