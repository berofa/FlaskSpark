"""Navbar (Bootstrap 6 markup with a drawer; no element of its own)."""

from __future__ import annotations

from .common import lines

TOGGLER_ICON = '<span class="navbar-toggler-icon" aria-hidden="true"></span>'


def navbar(navbar_id: str, brand: str = "Navbar", expand: str = "md", extra: str = ' class="bg-1"', placement: str = "end",
           body: str = "") -> str:
    expand_class = f" {expand}:navbar-expand" if expand else ""
    nav_class = f"navbar{expand_class}"
    if 'class="' in extra:
        extra = extra.replace('class="', f'class="{nav_class} ', 1)
    else:
        extra = f' class="{nav_class}"{extra}'
    body = body or lines(
        '        <ul class="nav navbar-nav me-auto">',
        '          <li class="nav-item"><a class="nav-link active" aria-current="page" href="#">Home</a></li>',
        '          <li class="nav-item"><a class="nav-link" href="#">Link</a></li>',
        '          <li class="nav-item">',
        '            <button class="nav-link" type="button" data-bs-toggle="menu">Menu</button>',
        '            <div class="menu"><a class="menu-item" href="#">Action</a><a class="menu-item" href="#">Another action</a></div>',
        "          </li>",
        '          <li class="nav-item"><a class="nav-link disabled" aria-disabled="true">Disabled</a></li>',
        "        </ul>",
    )
    return lines(
        f"<nav{extra}>",
        '  <div class="container-fluid">',
        f'    <a class="navbar-brand" href="#">{brand}</a>',
        f'    <button class="btn-icon navbar-toggler" type="button" data-bs-toggle="drawer" data-bs-target="#{navbar_id}" '
        f'aria-controls="{navbar_id}" aria-expanded="false" aria-label="Toggle navigation">{TOGGLER_ICON}</button>',
        f'    <dialog class="drawer drawer-{placement}" tabindex="-1" id="{navbar_id}" aria-labelledby="{navbar_id}Label">',
        '      <div class="drawer-header">',
        f'        <h5 class="drawer-title" id="{navbar_id}Label">Menu</h5>',
        '        <button type="button" class="btn-close" data-bs-dismiss="drawer" aria-label="Close"></button>',
        "      </div>",
        '      <div class="drawer-body">',
        body,
        "      </div>",
        "    </dialog>",
        "  </div>",
        "</nav>",
    )


SEARCH = lines(
    '        <form class="hstack gap-2" role="search">',
    '          <input class="form-control" type="search" placeholder="Search" aria-label="Search">',
    '          <button class="btn-outline theme-success" type="submit">Search</button>',
    "        </form>",
)

DESCRIPTIONS = {
    "--bs-navbar-padding-x": "Horizontal padding.",
    "--bs-navbar-padding-y": "Vertical padding.",
    "--bs-navbar-min-height": "Minimum height.",
    "--bs-navbar-color": "Colour of nav links and text.",
    "--bs-navbar-hover-color": "Colour of hovered links.",
    "--bs-navbar-disabled-color": "Colour of disabled links.",
    "--bs-navbar-active-color": "Colour of the active link.",
    "--bs-navbar-brand-padding-y": "Vertical padding of the brand.",
    "--bs-navbar-brand-margin-end": "Space after the brand.",
    "--bs-navbar-brand-font-size": "Font size of the brand.",
    "--bs-navbar-brand-font-weight": "Font weight of the brand.",
    "--bs-navbar-brand-color": "Colour of the brand.",
    "--bs-navbar-brand-hover-color": "Colour of the hovered brand.",
    "--bs-navbar-nav-link-padding-x": "Horizontal padding of nav links when expanded.",
    "--bs-navbar-toggler-width": "Width of the toggler.",
    "--bs-navbar-toggler-padding-y": "Vertical padding of the toggler.",
    "--bs-navbar-toggler-padding-x": "Horizontal padding of the toggler.",
    "--bs-navbar-toggler-font-size": "Font size of the toggler.",
    "--bs-navbar-toggler-border-color": "Border colour of the toggler.",
    "--bs-navbar-toggler-border-radius": "Corner radius of the toggler.",
    "--bs-navbar-toggler-transition": "Transition of the toggler (focus ring).",
    "--bs-navbar-toggler-icon-size": "Size of the toggler icon.",
    "--bs-navbar-toggler-icon": "Mask image of the toggler icon.",
}

PAGE = {
    "title": "Navbar",
    "summary": "Bootstrap's navbar markup — brand, nav, forms, text, toggler — with a drawer for small screens. No element "
    "of its own: the page's Bootstrap CSS styles it, the drawer plugin (data-bs-toggle=\"drawer\" on the toggler and a "
    "plain <dialog class=\"drawer\">) and ui-menu add the behaviour.",
    "submodule": "",
    "entry": "",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "Below the <code>md</code> width of the navbar (a container query) the links sit in a drawer behind the "
            "toggler; from it on they are inline. Shrink the window to see the toggler.",
            "html": navbar(
                "navbarExample", body=lines(
                    '        <ul class="nav navbar-nav me-auto">',
                    '          <li class="nav-item"><a class="nav-link active" aria-current="page" href="#">Home</a></li>',
                    '          <li class="nav-item"><a class="nav-link" href="#">Link</a></li>',
                    '          <li class="nav-item">',
                    '            <button class="nav-link" type="button" data-bs-toggle="menu">Menu</button>',
                    '            <div class="menu"><a class="menu-item" href="#">Action</a><a class="menu-item" href="#">Another action</a></div>',
                    "          </li>",
                    '          <li class="nav-item"><a class="nav-link disabled" aria-disabled="true">Disabled</a></li>',
                    "        </ul>",
                    SEARCH,
                )),
            "stacked": True,
        },
        {
            "id": "brand-text",
            "title": "Brand and text",
            "intro": "<code>.navbar-brand</code> (text or image) and <code>.navbar-text</code>.",
            "html": lines(
                '<nav class="navbar bg-1"><div class="container-fluid"><a class="navbar-brand" href="#">Navbar</a></div></nav>',
                '<nav class="navbar bg-1 mt-2"><div class="container-fluid"><span class="navbar-text">Navbar text with an inline element</span></div></nav>',
            ),
            "stacked": True,
        },
        {
            "id": "color-schemes",
            "title": "Color schemes",
            "intro": "<code>data-bs-theme=\"dark\"</code> and background utilities.",
            "html": lines(navbar("navbarDark", "Dark", extra=' class="bg-inverse" data-bs-theme="dark"'),
                          navbar("navbarPrimary", "Primary", extra=' class="bg-primary mt-2" data-bs-theme="dark"')),
            "stacked": True,
        },
        {
            "id": "always-drawer",
            "title": "Always a drawer, other sides",
            "intro": "Without <code>{breakpoint}:navbar-expand</code> the links always sit in the drawer; "
            "<code>drawer-start</code>, <code>-top</code>, <code>-bottom</code> pick the side.",
            "html": lines(navbar("navbarStart", "Left drawer", expand="", placement="start"),
                          navbar("navbarTop", "Top drawer", expand="", placement="top", extra=' class="bg-1 mt-2"')),
            "stacked": True,
        },
        {
            "id": "placement",
            "title": "Placement",
            "intro": "Position utilities: <code>fixed-top</code>, <code>fixed-bottom</code>, <code>sticky-top</code>, "
            "<code>sticky-bottom</code> on the <code>&lt;nav&gt;</code>.",
            "html": '<nav class="navbar sticky-top bg-1"><div class="container-fluid"><a class="navbar-brand" href="#">Sticky top</a></div></nav>',
            "stacked": True,
        },
    ],
    "elements": [],
    "notes": [
        "The toggler's <code>aria-expanded</code> follows the drawer.",
        "<code>ui-navbar</code> (Bootstrap 5) is replaced by this markup.",
    ],
    "tokens": {
        "host": "",
        "selector": ".navbar",
        "example_token": "--bs-navbar-active-color",
        "example_value": "var(--bs-primary-fg)",
        "spec": {"sources": [{"selector": ".navbar", "prefix": "--bs-navbar-"}], "descriptions": DESCRIPTIONS},
    },
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["navbar"]
