"""ui-menu (Bootstrap 6 menu: behaviour for Bootstrap's own markup)."""

from __future__ import annotations

from .common import THEMES, lines

ITEMS = ['<a class="menu-item" href="#">Menu item 1</a>', '<a class="menu-item" href="#">Menu item 2</a>',
         '<a class="menu-item" href="#">Menu item 3</a>']
CHECK = ('<svg class="menu-item-check" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" '
         'stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" viewBox="0 0 16 16">'
         '<path d="m2 7 4 5 8-8"/></svg>')
COPY = ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="menu-item-icon fg-3" '
        'viewBox="0 0 16 16"><path fill-rule="evenodd" d="M4 2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 '
        '1-2-2zm2-1a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1zM2 5a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h8a1 1 '
        '0 0 0 1-1v-1h1v1a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h1v1z"/></svg>')
TRASH = ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="menu-item-icon" '
         'viewBox="0 0 16 16"><path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 '
         '.5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/><path d="M14.5 3a1 1 0 0 1-1 '
         '1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 '
         '1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/></svg>')


def menu(toggle: str, items: list[str], attributes: str = "", menu_class: str = "menu", menu_attributes: str = "") -> str:
    return lines(
        f"<ui-menu{attributes}>",
        f"  {toggle}",
        f'  <div class="{menu_class}"{menu_attributes}>',
        *(f"    {item}" for item in items),
        "  </div>",
        "</ui-menu>",
    )


def toggle(label: str, variant: str = "secondary", extra: str = "") -> str:
    return f'<ui-button variant="{variant}" data-bs-toggle="menu"{extra}>{label}</ui-button>'


PAGE = {
    "title": "ui-menu",
    "summary": "Toggleable overlays with lists of links and more. <ui-menu> wraps Bootstrap's own menu markup (a "
    "data-bs-toggle=\"menu\" toggle and a .menu) and adds the behaviour: top layer, placement, auto close, keyboard "
    "and submenus. Every class of Bootstrap's docs works as written.",
    "submodule": "ui-menu",
    "entry": "modules/bootstrap/ui-menu/ui-menu.js",
    "sections": [
        {
            "id": "overview",
            "title": "Overview",
            "intro": "A toggle (button, <code>ui-button</code> or link with <code>role=\"button\"</code>) and the "
            "<code>.menu</code> after it. The menu opens in the top layer, so no container clips it.",
            "html": lines(
                menu(toggle("Toggle menu", "primary"), ITEMS),
                menu('<a class="btn-solid theme-primary" href="#" role="button" data-bs-toggle="menu">Link toggle</a>', ITEMS),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "split",
            "title": "Split button",
            "intro": "A button and a toggle in a <code>ui-button-group</code>, the menu after them.",
            "html": lines(
                "<ui-menu>",
                '  <ui-button-group label="Split button">',
                '    <ui-button variant="secondary">Split</ui-button>',
                '    <ui-button variant="secondary" data-bs-toggle="menu" label="Toggle menu">▾</ui-button>',
                "  </ui-button-group>",
                '  <div class="menu">',
                '    <a class="menu-item" href="#">Action</a>',
                '    <a class="menu-item" href="#">Another action</a>',
                '    <hr class="menu-divider">',
                '    <a class="menu-item" href="#">Separated link</a>',
                "  </div>",
                "</ui-menu>",
            ),
        },
        {
            "id": "dark",
            "title": "Dark and translucent menus",
            "intro": "<code>data-bs-theme=\"dark\"</code> on the <code>.menu</code>; <code>.menu-translucent</code> blurs "
            "what is behind it.",
            "html": lines(
                menu(toggle("Dark menu"), ITEMS, menu_attributes=' data-bs-theme="dark"'),
                menu(toggle("Translucent menu"), ITEMS, menu_class="menu menu-translucent"),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "placement",
            "title": "Placement",
            "intro": "<code>placement</code> (or <code>data-bs-placement</code> on the toggle): <code>top</code>, "
            "<code>bottom</code>, <code>left</code>, <code>right</code> or the logical <code>start</code> / "
            "<code>end</code>, each with <code>-start</code> / <code>-end</code> alignment. It flips when there is no "
            "room. Responsive: <code>\"bottom-start md:bottom-end lg:end-start\"</code>.",
            "html": lines(
                *(menu(toggle(p), ITEMS, f' placement="{p}"') for p in ("top", "bottom-end", "end-start", "start", "top-end")),
                menu(toggle("bottom-start md:bottom-end"), ITEMS, ' placement="bottom-start md:bottom-end"'),
                menu(toggle("bottom lg:right"), ITEMS, ' placement="bottom lg:right"'),
            ),
            "preview_class": "d-flex flex-wrap gap-2 py-5",
        },
        {
            "id": "items",
            "title": "Menu items",
            "intro": "<code>&lt;a&gt;</code> or <code>&lt;button&gt;</code> with <code>.menu-item</code>; "
            "<code>.menu-text</code> for non-interactive text, <code>.active</code> (with <code>aria-current</code>), "
            "<code>.disabled</code>, and <code>.theme-*</code> per item.",
            "html": lines(
                menu(toggle("Items"), [
                    '<button class="menu-item" type="button">Action</button>',
                    '<a class="menu-item active" href="#" aria-current="true">Active link</a>',
                    '<a class="menu-item disabled" aria-disabled="true">Disabled link</a>',
                    '<span class="menu-text">Menu item text</span>',
                ]),
                menu(toggle("Variants"), [f'<a class="menu-item theme-{name}" href="#">{name.title()}</a>' for name in THEMES]),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "icons-descriptions",
            "title": "Icons, descriptions and selected items",
            "intro": "<code>.menu-item-icon</code> on an SVG; <code>.menu-item-content</code> with "
            "<code>.menu-item-description</code>; <code>.selected</code> with a <code>.menu-item-check</code>.",
            "html": lines(
                menu(toggle("Icons"), [f'<button class="menu-item" type="button">{COPY} Copy</button>', '<hr class="menu-divider">',
                                       f'<button class="menu-item theme-danger" type="button">{TRASH} Delete</button>']),
                menu(toggle("Descriptions"), [
                    '<button class="menu-item" type="button"><span class="menu-item-content">Publish now'
                    '<small class="menu-item-description">Make this page visible immediately</small></span></button>',
                    '<button class="menu-item" type="button"><span class="menu-item-content">Schedule'
                    '<small class="menu-item-description">Set a future publish date</small></span></button>',
                ]),
                menu(toggle("Select status"), [
                    f'<button class="menu-item selected" type="button"><div class="menu-item-content">Selected menu item'
                    f'<small class="menu-item-description">Currently visible to users</small></div>{CHECK}</button>',
                    f'<button class="menu-item" type="button"><div class="menu-item-content">Default menu item'
                    f'<small class="menu-item-description">Not yet published</small></div>{CHECK}</button>',
                ]),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "content",
            "title": "Headers, dividers, text and forms",
            "html": lines(
                menu(toggle("Headers & dividers"), ['<h6 class="menu-header">Menu header</h6>', '<a class="menu-item" href="#">Action</a>',
                                                    '<a class="menu-item" href="#">Another action</a>', '<hr class="menu-divider">',
                                                    '<a class="menu-item" href="#">Separated link</a>']),
                menu(toggle("Text"), ['<p class="p-3 mb-0 fg-2">Some example text that’s free-flowing within the menu.</p>'],
                     menu_attributes=' style="--bs-menu-min-width: 15rem;"'),
                menu(toggle("Form"), [
                    '<form class="d-flex flex-column gap-3 p-3">',
                    '  <ui-input type="email" label="Email address" placeholder="email@example.com"></ui-input>',
                    '  <ui-input type="password" label="Password" placeholder="Password"></ui-input>',
                    '  <ui-check label="Remember me"></ui-check>',
                    '  <ui-button type="submit" variant="primary">Sign in</ui-button>',
                    "</form>",
                ], ' auto-close="outside"', menu_attributes=' style="--bs-menu-min-width: 300px;"'),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "scrollable",
            "title": "Scrollable menus",
            "intro": "<code>--bs-menu-max-height</code> and <code>--bs-menu-overflow-y</code>, or "
            "<code>.menu-scrollable</code> (80dvh).",
            "html": menu(toggle("Scrollable"), [f'<a class="menu-item" href="#">Item {n}</a>' for n in range(1, 13)],
                         menu_attributes=' style="--bs-menu-max-height: 145px; --bs-menu-overflow-y: auto;"'),
        },
        {
            "id": "submenus",
            "title": "Submenus",
            "intro": "A <code>.submenu</code> wraps a trigger <code>.menu-item</code> and a nested <code>.menu</code>; it "
            "opens on hover or click (→ with the keyboard), to the side, flipping when there is no room, nested to "
            "any depth. Below 576px submenus stack inside their menu.",
            "html": menu(toggle("Submenus"), [
                '<a class="menu-item" href="#">Action</a>',
                '<div class="submenu">',
                '      <button class="menu-item" type="button">More options</button>',
                '      <div class="menu">',
                '        <a class="menu-item" href="#">Sub-action A</a>',
                '        <div class="submenu">',
                '          <button class="menu-item" type="button">Even more</button>',
                '          <div class="menu"><a class="menu-item" href="#">Deep action 1</a><a class="menu-item" href="#">Deep action 2</a></div>',
                "        </div>",
                "      </div>",
                "    </div>",
                '<a class="menu-item" href="#">Another action</a>',
            ]),
        },
        {
            "id": "options",
            "title": "Offset, reference and auto close",
            "intro": "<code>offset=\"x,y\"</code> moves the menu; <code>reference=\"parent\"</code> places it at the "
            "toggle's parent. <code>auto-close</code>: <code>true</code> (default), <code>inside</code>, "
            "<code>outside</code>, <code>false</code>. Escape always closes and returns to the toggle.",
            "html": lines(
                menu(toggle("Offset 10,20"), ITEMS, ' offset="10,20"'),
                *(menu(toggle(title), ITEMS, f' auto-close="{value}"') for value, title in
                  (("true", "Default menu"), ("inside", "Clickable inside"), ("outside", "Clickable outside"), ("false", "Manual close"))),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "plain-markup",
            "title": "Plain markup",
            "intro": "Bootstrap's data API works without the wrapper: a <code>data-bs-toggle=\"menu\"</code> followed by "
            "a <code>.menu</code>, options as <code>data-bs-*</code>.",
            "html": lines(
                '<button class="btn-solid theme-secondary" type="button" data-bs-toggle="menu" data-bs-placement="bottom-end">Plain markup</button>',
                '<div class="menu">',
                *(f"  {item}" for item in ITEMS),
                "</div>",
            ),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines(
                'const menu = document.querySelector("ui-menu");',
                'menu.addEventListener("ui-menu:hide", (event) => {',
                "  // keep it open while a form inside is invalid",
                "  if (!form.checkValidity()) event.preventDefault();",
                "});",
                "menu.show();",
            ),
        },
    ],
    "elements": [
        {
            "tag": "ui-menu",
            "attributes": [
                ("placement", "string", "<code>bottom-start</code> (default) … with responsive prefixes."),
                ("offset", "string", "<code>\"x,y\"</code> in pixels (default <code>0,2</code>)."),
                ("reference", "string", "<code>toggle</code> (default), <code>parent</code> or a selector."),
                ("auto-close", "string", "<code>true</code>, <code>inside</code>, <code>outside</code>, <code>false</code>."),
                ("display", "string", "<code>static</code>: no positioning (e.g. in a navbar)."),
            ],
            "slots": [("(content)", "A <code>data-bs-toggle=\"menu\"</code> toggle and its <code>.menu</code> (Bootstrap's markup).")],
            "events": [
                ("ui-menu:show / ui-menu:hide", "Before opening / closing; cancelable (<code>detail.clickEvent</code> on hide)."),
                ("ui-menu:shown / ui-menu:hidden", "After the animation."),
            ],
            "methods": [("show(), hide(), toggle(), position()", "Open, close, toggle, re-place.")],
        }
    ],
    "notes": [
        "<code>ui-dropdown</code> (Bootstrap 5) is replaced by <code>ui-menu</code>.",
        "The toggle's options (<code>data-bs-placement</code>, <code>data-bs-offset</code>, <code>data-bs-reference</code>, "
        "<code>data-bs-auto-close</code>, <code>data-bs-display</code>) win over the attributes.",
    ],
    "tokens": {"host": "ui-menu", "selector": ".menu", "example_token": "--bs-menu-min-width", "example_value": "14rem"},
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["menu"]
