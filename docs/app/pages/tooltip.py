"""ui-tooltip (Bootstrap 6 tooltip)."""

from __future__ import annotations

from .common import lines

PAGE = {
    "title": "ui-tooltip",
    "summary": "Tooltips in the top layer: never clipped, flipping when there is no room, responsive placements, "
    "triggers, delays, HTML (sanitized) and Bootstrap's data API on plain markup.",
    "submodule": "ui-tooltip",
    "entry": "modules/bootstrap/ui-tooltip/ui-tooltip.js",
    "sections": [
        {
            "id": "links",
            "title": "Tooltips on links",
            "intro": "Wrap the trigger; plain text gets <code>tabindex=\"0\"</code> so it is reachable by keyboard.",
            "html": '<p class="mb-0">Placeholder text to demonstrate some <ui-tooltip text="Default tooltip"><a href="#">inline links</a></ui-tooltip> '
                    'with tooltips. This is now just filler, no killer. Content placed here just to mimic the presence of '
                    '<ui-tooltip text="Another tooltip">real text</ui-tooltip>.</p>',
        },
        {
            "id": "placement",
            "title": "Placement",
            "intro": "<code>placement</code>: <code>top</code> (default), <code>right</code>, <code>bottom</code>, "
            "<code>left</code>; responsive like <code>\"top md:right lg:bottom\"</code>.",
            "html": lines(*(f'<ui-tooltip text="Tooltip on {p}" placement="{p}"><ui-button variant="secondary">Tooltip on {p}</ui-button></ui-tooltip>'
                            for p in ("top", "right", "bottom", "left")),
                          '<ui-tooltip text="Top, right from md, bottom from lg" placement="top md:right lg:bottom"><ui-button variant="secondary">Responsive</ui-button></ui-tooltip>'),
            "preview_class": "d-flex flex-wrap gap-2 py-4",
        },
        {
            "id": "custom-html",
            "title": "Custom HTML and rich content",
            "intro": "<code>html</code> renders the text as sanitized HTML; the slot <code>content</code> takes markup directly.",
            "html": lines(
                '<ui-tooltip html text="<em>Tooltip</em> <u>with</u> <b>HTML</b>"><ui-button variant="secondary">Tooltip with HTML</ui-button></ui-tooltip>',
                '<ui-tooltip><ui-button variant="secondary">Slotted content</ui-button><span slot="content">Rich <strong>content</strong></span></ui-tooltip>',
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "custom",
            "title": "Custom tooltips",
            "intro": "<code>custom-class</code> adds classes to the box; the variables theme it.",
            "html": lines(
                '<ui-tooltip text="This top tooltip is themed via CSS variables." custom-class="custom-tooltip"',
                '  style="--bs-tooltip-bg: var(--bs-primary-bg); --bs-tooltip-color: var(--bs-white);">',
                '  <ui-button variant="secondary">Custom tooltip</ui-button>',
                "</ui-tooltip>",
            ),
        },
        {
            "id": "triggers",
            "title": "Triggers, delay, offset",
            "intro": "<code>trigger</code>: <code>hover focus</code> (default), <code>click</code>, <code>manual</code>; "
            "<code>delay</code> in ms or <code>{\"show\":500,\"hide\":100}</code>; <code>offset=\"x,y\"</code>; "
            "<code>animation=\"false\"</code>; <code>disabled</code>.",
            "html": lines(
                '<ui-tooltip text="Click again to close" trigger="click"><ui-button variant="secondary">Click</ui-button></ui-tooltip>',
                '<ui-tooltip text="After 500 ms" delay=\'{"show":500,"hide":100}\'><ui-button variant="secondary">Delayed</ui-button></ui-tooltip>',
                '<ui-tooltip text="Further away" offset="0,16"><ui-button variant="secondary">Offset</ui-button></ui-tooltip>',
                '<ui-tooltip text="No fade" animation="false"><ui-button variant="secondary">Instant</ui-button></ui-tooltip>',
                '<ui-tooltip text="Never shown" disabled><ui-button variant="secondary">Disabled tooltip</ui-button></ui-tooltip>',
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "disabled-elements",
            "title": "Disabled elements",
            "intro": "A disabled button gets no pointer events; the wrapper still shows the tooltip.",
            "html": '<ui-tooltip text="Disabled tooltip"><ui-button variant="primary" disabled>Disabled button</ui-button></ui-tooltip>',
        },
        {
            "id": "plain-markup",
            "title": "Plain markup",
            "intro": "Bootstrap's data API on any element: <code>data-bs-toggle=\"tooltip\"</code>, "
            "<code>data-bs-title</code> (or <code>title</code>) and the other options as <code>data-bs-*</code>.",
            "html": '<button type="button" class="btn-outline theme-secondary" data-bs-toggle="tooltip" data-bs-placement="bottom" '
                    'data-bs-title="Plain markup tooltip">Plain markup</button>',
        },
    ],
    "elements": [
        {
            "tag": "ui-tooltip",
            "attributes": [
                ("text", "string", "The tooltip (or slot <code>content</code>)."),
                ("html", "boolean", "The text is HTML (sanitized: Bootstrap's allow list)."),
                ("placement", "string", "<code>top</code>, <code>right</code>, <code>bottom</code>, <code>left</code>, responsive."),
                ("trigger", "string", "<code>hover focus</code>, <code>click</code>, <code>manual</code>."),
                ("delay / offset", "string", "Show/hide delay; <code>x,y</code> offset."),
                ("custom-class", "string", "Classes for the box."),
                ("animation", "string", "<code>false</code>: no fade."),
                ("disabled", "boolean", "Not shown."),
            ],
            "slots": [("(default)", "The trigger."), ("content", "Rich tooltip content.")],
            "parts": [("trigger, tooltip, arrow, inner", "Trigger wrapper and the box parts.")],
            "events": [("ui-tooltip:show / ui-tooltip:hide", "Before; cancelable."), ("ui-tooltip:shown / ui-tooltip:hidden", "After the fade."),
                       ("ui-tooltip:inserted", "The box was added.")],
            "methods": [("show(), hide(), toggle(), update()", "Promises / re-place."), ("enable(), disable(), setContent({ title })", "Control.")],
        }
    ],
    "tokens": {"host": "ui-tooltip", "example_token": "--bs-tooltip-bg", "example_value": "var(--bs-primary-bg)"},
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["tooltip"]
