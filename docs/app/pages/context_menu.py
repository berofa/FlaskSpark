"""ui-context-menu (Bootstrap 6 menu as a context menu)."""

from __future__ import annotations

from .common import lines

PAGE = {
    "title": "ui-context-menu",
    "summary": "The actions of an element on a right click, a long press on touch screens or the context menu key "
    "(Shift+F10): Bootstrap's own menu markup with icons, dividers, headers and danger items, opened at the pointer "
    "in the top layer.",
    "submodule": "ui-context-menu",
    "entry": "modules/bootstrap/ui-context-menu/ui-context-menu.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "Right click a row (or rest a finger on it). <code>UiContextMenu.attach(root, {selector, items, "
            "enabled})</code> gives the elements matching <code>selector</code> inside <code>root</code> their menu; "
            "<code>items(target, event)</code> returns the items (falsy ones are left out), <code>null</code> or "
            "<code>[]</code> keeps the browser's own menu.",
            "html": lines(
                '<ul class="list-group" id="contextDemo">',
                '  <li class="list-group-item" data-name="Anna">Anna Muster</li>',
                '  <li class="list-group-item" data-name="Bruno">Bruno Beispiel</li>',
                "</ul>",
                '<p class="small fg-3 mt-2 mb-0" id="contextDemoOut">Nothing chosen yet.</p>',
            ),
        },
    ],
    "page_script": lines(
        'import { UiContextMenu } from "webcomponents/modules/bootstrap/ui-context-menu/ui-context-menu.js";',
        'const icon = (d) => `<svg viewBox="0 0 16 16"><path d="${d}"/></svg>`;',
        'const out = document.getElementById("contextDemoOut");',
        'UiContextMenu.attach(document.getElementById("contextDemo"), {',
        '  selector: "[data-name]",',
        "  items: (row) => [",
        '    { header: row.dataset.name },',
        '    { label: "Edit", icon: icon("M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168z"), action: () => { out.textContent = `Edit ${row.dataset.name}`; } },',
        '    { label: "Copy name", description: "To the clipboard", action: () => { out.textContent = `Copied ${row.dataset.name}`; } },',
        "    { divider: true },",
        '    { label: "Delete", danger: true, action: () => { out.textContent = `Delete ${row.dataset.name}`; } },',
        "  ],",
        "});",
    ),
    "elements": [
        {
            "tag": "ui-context-menu",
            "attributes": [],
            "slots": [],
            "events": [
                ("ui-context-menu:show", "On the element, before opening; cancelable (<code>detail.items</code>)."),
                ("ui-context-menu:hidden", "On the element, after closing."),
            ],
            "methods": [
                ("UiContextMenu.attach(root, {selector, items, enabled})", "Context menus for elements inside root; returns the function that removes them."),
                ("UiContextMenu.instance.open(items, {target, event, x, y})", "Open it at a point (viewport pixels)."),
                ("UiContextMenu.instance.hide()", "Close it."),
            ],
        }
    ],
    "notes": [
        "An item: <code>label</code>, <code>icon</code> (SVG markup), <code>description</code>, <code>danger</code>, "
        "<code>disabled</code>, <code>action(target, event)</code>; or <code>{divider: true}</code>, <code>{header}</code>.",
        "Touch: a finger resting 500 ms opens it (moving more than 10 px scrolls instead); the click after it is "
        "swallowed. Give the elements <code>-webkit-touch-callout: none</code> where iOS would show its own callout.",
        "One element per page, added on first use. Keyboard: ↓ ↑ Home End, Enter or Space, Esc, Tab.",
    ],
}
