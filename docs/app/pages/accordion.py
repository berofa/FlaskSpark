"""ui-accordion (Bootstrap 6 accordion)."""

from __future__ import annotations

from .common import THEMES, VARIANT_ATTRIBUTE, lines

BODY = "<strong>This is the {n} item’s accordion body.</strong> Style it with the CSS variables below."
ICON = ('<svg class="accordion-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none" stroke="currentColor" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m2 5 6 6 6-6"/></svg>')
ORDINALS = ["first", "second", "third"]


def items(open_first: bool = True, heading: str = "Accordion Item #{n}", indent: str = "  ") -> list[str]:
    """Three items like the ones in Bootstrap's docs."""
    result = []
    for index, ordinal in enumerate(ORDINALS):
        attributes = f' heading="{heading.format(n=index + 1)}"' + (" open" if open_first and index == 0 else "")
        result.append(f"{indent}<ui-accordion-item{attributes}>{BODY.format(n=ordinal)}</ui-accordion-item>")
    return result


PAGE = {
    "title": "ui-accordion",
    "summary": "Vertically collapsing sections on native details elements: one open at a time or "
    "always open, theme colours, a small size, flush and gap layouts, custom icons.",
    "submodule": "ui-accordion",
    "entry": "modules/bootstrap/ui-accordion/ui-accordion.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "Each <code>&lt;ui-accordion-item&gt;</code> becomes a <code>&lt;details&gt;</code>; the items share a "
            "<code>name</code>, so opening one closes the others (native exclusive accordion). The panel height "
            "animates with <code>interpolate-size</code>; browsers without it switch at once.",
            "html": lines("<ui-accordion>", *items(), "</ui-accordion>"),
        },
        {
            "id": "variants",
            "title": "Theme variants",
            "intro": "<code>variant</code> colours the open item with a theme colour: "
            + ", ".join(f"<code>{name}</code>" for name in THEMES) + ".",
            "html": lines('<ui-accordion variant="primary">', *items(), "</ui-accordion>"),
        },
        {
            "id": "small",
            "title": "Small",
            "intro": "<code>sm</code> reduces the padding, the font size and the radius.",
            "html": lines("<ui-accordion sm>", *items(), "</ui-accordion>"),
        },
        {
            "id": "flush",
            "title": "Flush",
            "intro": "<code>flush</code> removes the outer borders and the radii, to render edge-to-edge in a parent.",
            "html": lines("<ui-accordion flush>", *items(open_first=False), "</ui-accordion>"),
        },
        {
            "id": "gap",
            "title": "Gap",
            "intro": "<code>gap</code> separates the items, each with its own border and radius "
            "(<code>--bs-accordion-gap</code>).",
            "html": lines("<ui-accordion gap>", *items(), "</ui-accordion>"),
        },
        {
            "id": "always-open",
            "title": "Always open",
            "intro": "<code>always-open</code> drops the shared name: items open independently.",
            "html": lines("<ui-accordion always-open>", *items(), "</ui-accordion>"),
        },
        {
            "id": "expand-all",
            "title": "Expand and collapse all",
            "intro": "<code>openAll()</code> and <code>closeAll()</code> open or close every item that is not disabled. "
            "Opening all needs several open items, so <code>openAll()</code> sets <code>always-open</code>.",
            "html": lines(
                '<div class="d-flex gap-2 mb-3">',
                '  <ui-button size="sm" variant="secondary" appearance="outline" onclick="document.querySelector(\'#accordionAll\').openAll()">Expand all</ui-button>',
                '  <ui-button size="sm" variant="secondary" appearance="outline" onclick="document.querySelector(\'#accordionAll\').closeAll()">Collapse all</ui-button>',
                "</div>",
                '<ui-accordion id="accordionAll" always-open>',
                *items(open_first=False),
                "</ui-accordion>",
            ),
        },
        {
            "id": "rich-heading",
            "title": "Rich headings, disabled items",
            "intro": "A child with <code>slot=\"heading\"</code> replaces the <code>heading</code> text. "
            "<code>disabled</code> items do not open.",
            "html": lines(
                "<ui-accordion>",
                "  <ui-accordion-item open>",
                '    <span slot="heading" class="d-flex gap-2 align-items-center">Rich heading <ui-badge variant="primary">New</ui-badge></span>',
                "    Content of the item with a rich heading.",
                "  </ui-accordion-item>",
                '  <ui-accordion-item heading="Disabled item" disabled>Not reachable.</ui-accordion-item>',
                '  <ui-accordion-item heading="Third item">Content of the third item.</ui-accordion-item>',
                "</ui-accordion>",
            ),
        },
        {
            "id": "custom-icon",
            "title": "Custom icon",
            "intro": "A child with <code>slot=\"icon\"</code> replaces the chevron of every item; it turns by "
            "<code>--bs-accordion-btn-icon-transform</code> when an item opens.",
            "html": lines(
                '<ui-accordion style="--bs-accordion-btn-icon-transform: rotate(45deg);">',
                '  <svg slot="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none" stroke="currentColor" '
                'stroke-width="1.5" stroke-linecap="round" aria-hidden="true"><path d="M8 2v12M2 8h12"/></svg>',
                *items(),
                "</ui-accordion>",
            ),
        },
        {
            "id": "nested",
            "title": "Nested",
            "intro": "Accordions can be nested; each keeps its own group.",
            "html": lines(
                "<ui-accordion>",
                '  <ui-accordion-item heading="Outer item" open>',
                "    <ui-accordion sm>",
                '      <ui-accordion-item heading="Inner item #1" open>Inner content one.</ui-accordion-item>',
                '      <ui-accordion-item heading="Inner item #2">Inner content two.</ui-accordion-item>',
                "    </ui-accordion>",
                "  </ui-accordion-item>",
                '  <ui-accordion-item heading="Another outer item">Outer content.</ui-accordion-item>',
                "</ui-accordion>",
            ),
        },
        {
            "id": "plain-markup",
            "title": "Plain markup",
            "intro": "Bootstrap's own accordion markup needs no JavaScript (the shared <code>name</code> makes it "
            "exclusive).",
            "html": lines(
                '<div class="accordion">',
                '  <details class="accordion-item" name="plainAccordion" open>',
                f'    <summary class="accordion-header">Plain item #1{ICON}</summary>',
                '    <div class="accordion-body">Content of the first item.</div>',
                "  </details>",
                '  <details class="accordion-item" name="plainAccordion">',
                f'    <summary class="accordion-header">Plain item #2{ICON}</summary>',
                '    <div class="accordion-body">Content of the second item.</div>',
                "  </details>",
                "</div>",
            ),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines(
                'const accordion = document.querySelector("ui-accordion");',
                'accordion.addEventListener("ui-accordion-item:toggle", (event) => {',
                "  console.log(event.target.getAttribute(\"heading\"), event.detail.open);",
                "});",
                "accordion.items[1].open = true;",
                "accordion.closeAll();",
            ),
        },
    ],
    "tokens": {"host": "ui-accordion", "example_token": "--bs-accordion-active-bg", "example_value": "var(--bs-primary-bg-subtle)"},
    "elements": [
        {
            "tag": "ui-accordion",
            "attributes": [
                ("always-open", "boolean", "Items open independently (no shared name)."),
                VARIANT_ATTRIBUTE,
                ("sm", "boolean", "Small size."),
                ("flush", "boolean", "No outer borders and radii."),
                ("gap", "boolean", "Separated items."),
            ],
            "slots": [("(items)", "<code>&lt;ui-accordion-item&gt;</code> children."),
                      ("icon", "Replaces the chevron of every item (copied into each header).")],
            "parts": [("accordion", "The <code>.accordion</code> element."), ("item", "Each <code>&lt;details&gt;</code>."),
                      ("header", "Each <code>&lt;summary&gt;</code>."), ("icon", "Each icon."), ("body", "Each body.")],
            "events": [("ui-accordion-item:toggle", "On the item (bubbles) after each toggle; <code>detail.open</code>.")],
            "methods": [("openAll() / closeAll()", "Open (sets <code>always-open</code>) or close every enabled item."),
                        ("items", "The item elements (read only).")],
        },
        {
            "tag": "ui-accordion-item",
            "attributes": [
                ("heading", "string", "Header text."),
                ("open", "boolean", "Open; reflected."),
                ("disabled", "boolean", "Cannot be opened."),
            ],
            "slots": [("(default)", "The body."), ("heading", "Rich header content (replaces <code>heading</code>).")],
            "methods": [("open", "Property for the <code>open</code> attribute.")],
        },
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["accordion"]
