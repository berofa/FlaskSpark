"""ui-kpi and ui-kpi-group (key figures as tiles)."""

from __future__ import annotations

from .common import VARIANT_ATTRIBUTE, lines

PAGE = {
    "title": "ui-kpi",
    "summary": "Key figures as small tiles: a label, the value, a line below and a trend arrow. "
    "ui-kpi-group lays them out in a responsive grid.",
    "submodule": "ui-kpi",
    "entry": "modules/bootstrap/ui-kpi/ui-kpi.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "<code>label</code>, <code>value</code> and <code>sub</code> as attributes; the group puts as many tiles "
            "in a row as fit (<code>--ui-kpi-group-min</code> wide at least).",
            "html": lines(
                "<ui-kpi-group>",
                '  <ui-kpi label="Revenue" value="CHF 12\'480" sub="last 30 days"></ui-kpi>',
                '  <ui-kpi label="Orders" value="318" sub="+12 % on the month before" trend="12" variant="success"></ui-kpi>',
                '  <ui-kpi label="Returns" value="4.1 %" trend="up" trend-inverse sub="costs rise"></ui-kpi>',
                '  <ui-kpi label="Open" value="27" trend="flat"></ui-kpi>',
                "</ui-kpi-group>",
            ),
        },
        {
            "id": "slots",
            "title": "Markup in the value",
            "intro": "The default slot takes the value as markup (e.g. a coloured amount with a unit), the slots "
            "<code>label</code> and <code>sub</code> the other lines (e.g. a label with a tooltip).",
            "html": lines(
                "<ui-kpi-group>",
                '  <ui-kpi size="lg">',
                '    <span slot="label"><ui-tooltip text="Revenue minus costs">Profit</ui-tooltip></span>',
                '    <span class="fg-success">+1\'240.50</span> <small class="fg-3">USD</small>',
                '    <span slot="sub">of which fees <strong>12.30</strong></span>',
                "  </ui-kpi>",
                '  <ui-kpi label="Stop" variant="danger" value="61\'200"></ui-kpi>',
                "</ui-kpi-group>",
            ),
        },
        {
            "id": "sizes",
            "title": "Sizes and compact groups",
            "intro": "<code>size=\"lg\"</code> emphasises a figure (a total), <code>size=\"sm\"</code> is compact. "
            "<code>compact</code> on the group makes every tile without a size of its own small and the grid tighter.",
            "html": lines(
                "<ui-kpi-group compact>",
                *[f'  <ui-kpi label="{label}" value="{value}"></ui-kpi>' for label, value in
                  (("Entry", "61\'950"), ("Size", "0.25"), ("Leverage", "5×"), ("Margin", "3\'097"), ("Fees", "18.60"))],
                "</ui-kpi-group>",
            ),
        },
        {
            "id": "tokens-example",
            "title": "Styling",
            "intro": "Tokens on the element or the group: background, border, radius, font sizes of label, value and "
            "the line below.",
            "html": lines(
                '<ui-kpi-group style="--ui-kpi-bg: var(--bs-primary-bg-subtle); --ui-kpi-border-width: 0; --ui-kpi-group-min: 12rem">',
                '  <ui-kpi label="Visitors" value="8\'204" sub="today"></ui-kpi>',
                '  <ui-kpi label="Sign-ups" value="96" sub="today"></ui-kpi>',
                "</ui-kpi-group>",
            ),
        },
    ],
    "tokens": {"host": "ui-kpi", "example_token": "--ui-kpi-radius", "example_value": "var(--bs-radius-3)"},
    "elements": [
        {
            "tag": "ui-kpi",
            "attributes": [
                ("label", "string", "The caption above the value."),
                ("value", "string", "The value as text (or the default slot)."),
                ("sub", "string", "A line below the value."),
                VARIANT_ATTRIBUTE,
                ("size", "string", "<code>sm</code> (compact) or <code>lg</code> (emphasised)."),
                ("trend", "string", "<code>up</code>, <code>down</code>, <code>flat</code> or a number (its sign): an arrow "
                 "in front of the value, green up and red down."),
                ("trend-inverse", "boolean", "Red up, green down (e.g. costs)."),
                ("trend-up-label / trend-down-label / trend-flat-label", "string",
                 "The arrow's text for screen readers (<code>Rising</code>, <code>Falling</code>, <code>Unchanged</code>)."),
            ],
            "slots": [("(default)", "The value as markup."), ("label", "The caption as markup."), ("sub", "The line below as markup.")],
            "parts": [("kpi", "The tile."), ("label, value, trend, sub", "Its lines and the arrow.")],
        },
        {
            "tag": "ui-kpi-group",
            "attributes": [("compact", "boolean", "Narrower tiles and gaps; tiles without a size become <code>sm</code>.")],
            "slots": [("(default)", "<code>&lt;ui-kpi&gt;</code> elements.")],
            "parts": [("group", "The grid.")],
        },
    ],
}
