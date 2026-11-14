"""Nav (Bootstrap 6 markup: base nav, tabs, pills, underline; no element of its own)."""

from __future__ import annotations

from .common import lines

LINKS = lines(
    '  <li class="nav-item"><a class="nav-link active" aria-current="page" href="#">Active</a></li>',
    '  <li class="nav-item"><a class="nav-link" href="#">Link</a></li>',
    '  <li class="nav-item"><a class="nav-link" href="#">Link</a></li>',
    '  <li class="nav-item"><a class="nav-link disabled" aria-disabled="true">Disabled</a></li>',
)


def nav(classes: str, items: str = LINKS) -> str:
    return lines(f'<ul class="{classes}">', items, "</ul>")


NAV_DESCRIPTIONS = {
    "--bs-nav-gap": "Space between the links.",
    "--bs-nav-link-gap": "Space between icon and text of a link.",
    "--bs-nav-link-align": "Vertical alignment inside a link.",
    "--bs-nav-link-justify": "Horizontal alignment inside a link.",
    "--bs-nav-link-padding-x": "Horizontal padding of a link.",
    "--bs-nav-link-padding-y": "Vertical padding of a link.",
    "--bs-nav-link-color": "Text colour of a link.",
    "--bs-nav-link-hover-color": "Text colour of a hovered link.",
    "--bs-nav-link-hover-bg": "Background of a hovered link.",
    "--bs-nav-link-active-color": "Text colour of the active link.",
    "--bs-nav-link-active-bg": "Background of the active link.",
    "--bs-nav-link-disabled-color": "Text colour of a disabled link.",
    "--bs-nav-link-border-width": "Border width of links (tabs, underline).",
    "--bs-nav-link-transition-property": "Properties animated on hover and activation.",
    "--bs-nav-link-transition-duration": "Duration of that transition.",
    "--bs-nav-link-transition-timing": "Timing function of that transition.",
}

OV_PILLS = ['<div class="docs-resizable">', '  <div class="nav-overflow" data-bs-toggle="nav-overflow">', '    <ul class="nav nav-pills">', '      <li class="nav-item"><a class="nav-link active" aria-current="page" href="#">Home</a></li>', '      <li class="nav-item"><a class="nav-link" href="#">Products</a></li>', '      <li class="nav-item"><a class="nav-link" href="#">Features</a></li>', '      <li class="nav-item"><a class="nav-link" href="#">Pricing</a></li>', '      <li class="nav-item"><a class="nav-link disabled" href="#">Docs</a></li>', '      <li class="nav-item"><a class="nav-link" href="#">Blog</a></li>', '      <li class="nav-item"><a class="nav-link" href="#">Support</a></li>', '      <li class="nav-item"><a class="nav-link" href="#">Contact</a></li>', '    </ul>', '  </div>', '</div>']
OV_TABS = ['<div class="docs-resizable">', '  <div class="nav-overflow" data-bs-toggle="nav-overflow" data-bs-threshold="2" data-bs-collapse-below="sm" data-bs-more-text="Menu" data-bs-icon-placement="end">', '    <ul class="nav nav-tabs">', '      <li class="nav-item nav-overflow-keep"><a class="nav-link active" aria-current="page" href="#">Home</a></li>', '      <li class="nav-item"><a class="nav-link" href="#">Products</a></li>', '      <li class="nav-item"><a class="nav-link" href="#">Features</a></li>', '      <li class="nav-item"><a class="nav-link" href="#">Pricing</a></li>', '      <li class="nav-item"><a class="nav-link" href="#">Docs</a></li>', '      <li class="nav-item"><a class="nav-link" href="#">Blog</a></li>', '      <li class="nav-item"><a class="nav-link" href="#">Support</a></li>', '      <li class="nav-item"><a class="nav-link" href="#">Contact</a></li>', '    </ul>', '  </div>', '</div>']

PAGE = {
    "title": "Nav",
    "summary": "Navigation with Bootstrap's own markup (.nav, .nav-tabs, .nav-pills, .nav-underline) — plain CSS, no "
    "element of its own. Menus in a nav come from ui-menu; switching panes is ui-tabs (or the tab data API).",
    "submodule": "",
    "entry": "",
    "sections": [
        {
            "id": "base",
            "title": "Base nav",
            "intro": "A <code>.nav</code> of <code>.nav-link</code>s, as a list or as plain links.",
            "html": lines(nav("nav"), '<nav class="nav mt-3">', '  <a class="nav-link active" aria-current="page" href="#">Active</a>',
                          '  <a class="nav-link" href="#">Link</a>', '  <a class="nav-link disabled" aria-disabled="true">Disabled</a>', "</nav>"),
        },
        {"id": "tabs", "title": "Tabs", "html": nav("nav nav-tabs")},
        {"id": "pills", "title": "Pills", "html": nav("nav nav-pills")},
        {"id": "underline", "title": "Underline", "html": nav("nav nav-underline")},
        {
            "id": "alignment",
            "title": "Alignment, vertical, fill and justify",
            "intro": "Flex utilities align the nav; <code>flex-column</code> stacks it; <code>.nav-fill</code> and "
            "<code>.nav-justified</code> fill the width.",
            "html": lines(nav("nav justify-content-center"), nav("nav justify-content-end mt-3"), nav("nav flex-column mt-3"),
                          nav("nav nav-pills nav-fill mt-3"), nav("nav nav-pills nav-justified mt-3")),
        },
        {
            "id": "menus",
            "title": "Using menus",
            "intro": "A menu in a nav item: <code>ui-menu</code> (or the menu data API) on Bootstrap's markup.",
            "html": lines(
                '<ul class="nav nav-tabs">',
                '  <li class="nav-item"><a class="nav-link active" aria-current="page" href="#">Active</a></li>',
                '  <li class="nav-item">',
                '    <button class="nav-link" type="button" data-bs-toggle="menu">Menu</button>',
                '    <div class="menu"><a class="menu-item" href="#">Action</a><a class="menu-item" href="#">Another action</a></div>',
                "  </li>",
                '  <li class="nav-item"><a class="nav-link" href="#">Link</a></li>',
                "</ul>",
            ),
        },
        {
            "id": "overflow",
            "title": "Overflow (Priority+)",
            "intro": "New in Bootstrap 6: wrap the nav in <code>.nav-overflow[data-bs-toggle=\"nav-overflow\"]</code> and the "
            "items that do not fit move into a «More» menu. It follows the wrapper's width, not the viewport's — drag the "
            "right edge of the box. Works with every nav style; active and disabled states are kept.",
            "html": lines(*OV_PILLS),
        },
        {
            "id": "overflow-options",
            "title": "Overflow: keep, threshold, collapse below, text",
            "intro": "<code>.nav-overflow-keep</code> items never move; <code>data-bs-threshold</code> keeps that many visible; "
            "<code>data-bs-collapse-below=\"md\"</code> (or pixels) moves everything below that width; "
            "<code>data-bs-more-text</code> (<code>false</code>: icon only), <code>data-bs-icon-placement=\"end\"</code>, "
            "an element with <code>data-bs-overflow-icon</code> as the icon. Events: <code>ui-nav-overflow:overflow</code>, "
            "<code>ui-nav-overflow:update</code>.",
            "html": lines(*OV_TABS),
        },
        {
            "id": "overflow-menus",
            "title": "Overflow with menus",
            "intro": "An item with its own menu becomes a submenu of the «More» menu (the menu itself moves, nested submenus stay).",
            "html": lines(
                '<div class="docs-resizable">',
                '  <div class="nav-overflow" data-bs-toggle="nav-overflow">',
                '    <ul class="nav nav-underline">',
                '      <li class="nav-item"><a class="nav-link active" aria-current="page" href="#">Overview</a></li>',
                '      <li class="nav-item">',
                '        <button class="nav-link" type="button" data-bs-toggle="menu">Products</button>',
                '        <div class="menu"><a class="menu-item" href="#">Laptops</a><a class="menu-item" href="#">Tablets</a></div>',
                "      </li>",
                '      <li class="nav-item">',
                '        <button class="nav-link" type="button" data-bs-toggle="menu">Company</button>',
                '        <div class="menu"><a class="menu-item" href="#">About</a><a class="menu-item" href="#">Careers</a></div>',
                "      </li>",
                *[f'      <li class="nav-item"><a class="nav-link" href="#">{n}</a></li>' for n in ["Support", "Partners", "Investors"]],
                "    </ul>",
                "  </div>",
                "</div>",
            ),
        },
    ],
    "elements": [],
    "notes": [
        "The nav is page markup styled by the page's Bootstrap CSS; <code>ui-tabs</code> renders the same classes "
        "inside its shadow tree and takes the same variables on <code>&lt;ui-tabs&gt;</code>.",
    ],
    "tokens": {
        "host": "",
        "selector": ".nav",
        "example_token": "--bs-nav-link-color",
        "example_value": "var(--bs-primary-fg)",
        "spec": {"sources": [{"selector": ".nav", "prefix": "--bs-nav-"}], "descriptions": NAV_DESCRIPTIONS},
    },
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["nav"]
