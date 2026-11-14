"""ui-list-group (Bootstrap 6 list group)."""

from __future__ import annotations

from .common import THEMES, VARIANT_ATTRIBUTE, lines


def group(items: list[str], attributes: str = "") -> str:
    return lines(f"<ui-list-group{attributes}>", *(f"  {item}" for item in items), "</ui-list-group>")


def item(text: str, attributes: str = "") -> str:
    return f"<ui-list-group-item{attributes}>{text}</ui-list-group-item>"


BASIC = [item("An item"), item("A second item"), item("A third item"), item("A fourth item"), item("And a fifth one")]
THREE = [item("An item"), item("A second item"), item("A third item")]
CUSTOM = (
    '\n    <div class="ms-2 me-auto">\n      <div class="fw-bold">Subheading</div>\n      Content for list item\n    </div>'
    '\n    <ui-badge variant="primary" pill>14</ui-badge>\n  '
)

PAGE = {
    "title": "ui-list-group",
    "summary": "A flexible series of content: plain, link or button items, active and disabled states, theme "
    "colours, flush, numbered and (responsive) horizontal layouts.",
    "submodule": "ui-list-group",
    "entry": "modules/bootstrap/ui-list-group/ui-list-group.js",
    "sections": [
        {"id": "basic", "title": "Basic example", "html": group(BASIC)},
        {
            "id": "active",
            "title": "Active items",
            "intro": "<code>active</code> marks the current selection.",
            "html": group([item("An active item", " active"), *BASIC[1:]]),
        },
        {
            "id": "links",
            "title": "Links and buttons",
            "intro": "<code>href</code> makes a link item, <code>action</code> a button item, both with hover, "
            "active and disabled states. A click fires <code>ui-list-group:action</code>.",
            "html": lines(
                group([
                    item("The current link item", ' href="#" active'),
                    item("A second link item", ' href="#"'),
                    item("A third link item", ' href="#"'),
                    item("A fourth link item", ' href="#"'),
                    item("A disabled link item", ' href="#" disabled'),
                ]),
                group([
                    item("The current button", " action active"),
                    item("A second button item", " action"),
                    item("A third button item", " action"),
                    item("A fourth button item", " action"),
                    item("A disabled button item", " action disabled"),
                ], ' class="mt-4"'),
            ),
        },
        {
            "id": "flush",
            "title": "Flush",
            "intro": "<code>flush</code> removes the outer borders and radii, e.g. inside a card.",
            "html": group(BASIC, " flush"),
        },
        {
            "id": "numbered",
            "title": "Numbered",
            "intro": "<code>numbered</code> numbers the items (an <code>&lt;ol&gt;</code>, numbers by CSS counters).",
            "html": lines(
                group(THREE, " numbered"),
                group([item(CUSTOM, ' class="d-flex justify-content-between align-items-start"') for _ in range(3)],
                      ' numbered class="mt-4"'),
            ),
        },
        {
            "id": "horizontal", "stacked": True,
            "title": "Horizontal",
            "intro": "<code>horizontal</code> lays the items out in a row; with a breakpoint (<code>sm</code>, "
            "<code>md</code>, <code>lg</code>, <code>xl</code>, <code>2xl</code>) only from that width of the "
            "element on (a container query, so it reacts to the space it gets, not the viewport). "
            "<code>flex-fill</code> on the items gives equal widths.",
            "html": lines(
                group(THREE, " horizontal"),
                *(group(THREE, f' horizontal="{bp}" class="mt-3"') for bp in ["sm", "md", "lg", "xl", "2xl"]),
                group([item(text, ' class="flex-fill"') for text in ("An item", "A second item", "A third item")],
                      ' horizontal class="mt-3"'),
            ),
        },
        {
            "id": "variants",
            "title": "Variants",
            "intro": "<code>variant</code> on an item gives it a theme colour; on link and button items with hover "
            "and active states.",
            "html": lines(
                group([item("A simple default list group item")]
                      + [item(f"A simple {name} list group item", f' variant="{name}"') for name in THEMES]),
                group([item("A simple default list group item", ' href="#"')]
                      + [item(f"A simple {name} list group item", f' href="#" variant="{name}"') for name in THEMES],
                      ' class="mt-4"'),
            ),
        },
        {
            "id": "badges",
            "title": "With badges",
            "html": group([
                item(f'{text}\n    <ui-badge variant="primary" pill>{count}</ui-badge>\n  ',
                     ' class="d-flex justify-content-between align-items-center"')
                for text, count in (("A list item", 14), ("A second list item", 2), ("A third list item", 1))
            ]),
        },
        {
            "id": "custom-content",
            "title": "Custom content",
            "intro": "Any HTML, also in link items.",
            "html": group([
                item(
                    '\n    <div class="d-flex w-100 justify-content-between">\n      <h5 class="mb-1">List group item '
                    'heading</h5>\n      <small' + (' class="fg-2"' if index else "") + '>3 days ago</small>\n    </div>'
                    '\n    <p class="mb-1">Some placeholder content in a paragraph.</p>\n    <small'
                    + (' class="fg-2"' if index else "") + ">And some small print.</small>\n  ",
                    ' href="#"' + (" active" if index == 0 else ""),
                )
                for index in range(3)
            ]),
        },
        {
            "id": "checkboxes",
            "title": "Checkboxes and radios",
            "intro": "Form controls inside the items; <code>stretched-link</code> on the label makes the whole item "
            "clickable.",
            "html": lines(
                group([
                    item(f'<div class="form-field"><input type="checkbox" class="check" id="lgCheck{n}">'
                         f'<label for="lgCheck{n}">{label} checkbox</label></div>')
                    for n, label in enumerate(("First", "Second", "Third"))
                ]),
                group([
                    item(f'<div class="form-field"><input type="radio" class="radio" name="lgRadio" id="lgRadio{n}"'
                         f'{" checked" if n == 0 else ""}><label class="stretched-link" for="lgRadio{n}">{label} radio</label></div>')
                    for n, label in enumerate(("First", "Second", "Third"))
                ], ' class="mt-4"'),
            ),
        },
    ],
    "elements": [
        {
            "tag": "ui-list-group",
            "attributes": [
                ("flush", "boolean", "No outer borders and radii."),
                ("numbered", "boolean", "Numbers the items."),
                ("horizontal", "string", "Items in a row; with <code>sm</code>…<code>2xl</code> from that width of "
                 "the element on."),
                ("label", "string", "Accessible name of the list."),
            ],
            "slots": [("(items)", "<code>&lt;ui-list-group-item&gt;</code> children, each in its own slot.")],
            "parts": [
                ("list", "The <code>.list-group</code> element."),
                ("item", "Each <code>.list-group-item</code>; also <code>item-active</code>, <code>item-disabled</code>."),
            ],
            "events": [("ui-list-group:action", "A link or button item was clicked; <code>detail</code>: "
                        "<code>{ item, index }</code>.")],
            "methods": [("items", "The item elements in order (read only).")],
        },
        {
            "tag": "ui-list-group-item",
            "attributes": [
                ("href", "url", "Link item (with <code>target</code>, <code>rel</code>)."),
                ("action", "boolean", "Button item."),
                ("active", "boolean", "Current selection (<code>aria-current</code>)."),
                ("disabled", "boolean", "Inactive."),
                VARIANT_ATTRIBUTE,
            ],
            "slots": [("(default)", "Content of the item.")],
        },
    ],
    "notes": ["Tabbable list group panes (Bootstrap's Tab plugin) come with <code>ui-tabs</code>."],
    "tokens": {"host": "ui-list-group", "example_token": "--bs-list-group-active-bg", "example_value": "var(--bs-success-bg)"},
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["list_group"]
