"""ui-breadcrumb (Bootstrap 6 breadcrumb)."""

from __future__ import annotations

from .common import lines

DOTS = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" fill="currentcolor" '
    'aria-label="More"><circle cx="2" cy="8" r="2"/><circle cx="8" cy="8" r="2"/><circle cx="14" cy="8" r="2"/></svg>'
)
CHEVRONS = (
    '<svg slot="divider" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">'
    '<path fill-rule="evenodd" d="M3.646 1.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1 0 .708l-6 6a.5.5 0 0 1-.708-.708L9.293 8 '
    '3.646 2.354a.5.5 0 0 1 0-.708"/><path fill-rule="evenodd" d="M7.646 1.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1 0 .708l-6 '
    '6a.5.5 0 0 1-.708-.708L13.293 8 7.646 2.354a.5.5 0 0 1 0-.708"/></svg>'
)


def trail(*items: tuple[str, str], attributes: str = "", extra: str = "") -> str:
    """A breadcrumb; the last item is the current page."""
    rows = [f"<ui-breadcrumb{attributes}>"]
    if extra:
        rows.append(f"  {extra}")
    for index, (label, href) in enumerate(items):
        active = " active" if index == len(items) - 1 else ""
        rows.append(f'  <ui-breadcrumb-item href="{href}"{active}>{label}</ui-breadcrumb-item>')
    rows.append("</ui-breadcrumb>")
    return lines(*rows)


PAGE = {
    "title": "ui-breadcrumb",
    "summary": "The current page's location within a navigational hierarchy, with explicit dividers between the "
    "items: Bootstrap's chevron, text or your own SVG.",
    "submodule": "ui-breadcrumb",
    "entry": "modules/bootstrap/ui-breadcrumb/ui-breadcrumb.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "One <code>&lt;ui-breadcrumb-item&gt;</code> per page; <code>active</code> marks the current one "
            "(<code>aria-current=\"page\"</code>). Items may hold icons.",
            "html": lines(
                trail(("Home", "#"), ("Library", "#"), ("Data", "#")),
                trail(("Home", "#"), (DOTS, "#"), ("Documents", "#"), ("2026", "#")),
            ),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "default-divider",
            "title": "Default divider",
            "intro": "Without a divider, Bootstrap's chevron (a CSS mask in the divider colour). Change it with "
            "<code>--bs-breadcrumb-divider-icon</code>, <code>-width</code> and <code>-height</code>.",
            "html": trail(("Home", "#"), ("Library", "#")),
        },
        {
            "id": "svg-dividers",
            "title": "SVG dividers",
            "intro": "An element with <code>slot=\"divider\"</code> is repeated between the items; use "
            "<code>currentColor</code> so it takes the divider colour.",
            "html": trail(("Home", "#"), ("Library", "#"), extra=CHEVRONS),
        },
        {
            "id": "text-dividers",
            "title": "Text dividers",
            "intro": "<code>divider</code> sets a text divider.",
            "html": lines(
                trail(("Home", "#"), ("Library", "#"), ("Data", "#"), attributes=' divider="/"'),
                trail(("Home", "#"), ("Library", "#"), ("Data", "#"), attributes=' divider="›"'),
            ),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "accessibility",
            "title": "Accessibility",
            "intro": "The breadcrumb is a <code>&lt;nav&gt;</code> landmark labelled by <code>label</code> (default "
            "“Breadcrumb”); the current item has <code>aria-current=\"page\"</code>, dividers are hidden from "
            "assistive technology.",
            "html": trail(("Start", "#"), ("Settings", "#"), attributes=' label="You are here"'),
        },
    ],
    "elements": [
        {
            "tag": "ui-breadcrumb",
            "attributes": [
                ("label", "string", "Accessible name of the navigation (default <code>Breadcrumb</code>)."),
                ("divider", "string", "Text divider between the items."),
            ],
            "slots": [
                ("divider", "An element (e.g. SVG) repeated as the divider."),
                ("(items)", "<code>&lt;ui-breadcrumb-item&gt;</code> children, each in its own slot."),
            ],
            "parts": [
                ("nav", "The <code>&lt;nav&gt;</code> landmark."),
                ("list", "The <code>&lt;ol class=\"breadcrumb\"&gt;</code>."),
                ("item", "Each <code>.breadcrumb-item</code>."),
                ("link", "Each <code>.breadcrumb-link</code> (link or, without href, span)."),
                ("divider", "Each <code>.breadcrumb-divider</code>."),
            ],
        },
        {
            "tag": "ui-breadcrumb-item",
            "attributes": [
                ("href", "url", "Link of the page (with <code>target</code>, <code>rel</code>)."),
                ("active", "boolean", "The current page."),
            ],
            "slots": [("(default)", "Label or icon of the page.")],
        },
    ],
    "tokens": {"host": "ui-breadcrumb", "example_token": "--bs-breadcrumb-divider-color", "example_value": "var(--bs-primary-fg)"},
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["breadcrumb"]
