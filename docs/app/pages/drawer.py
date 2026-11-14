"""ui-drawer (Bootstrap 6 drawer)."""

from __future__ import annotations

from .common import lines

BODY = "Content for the drawer goes here. You can place just about any Bootstrap component or custom elements here."


def drawer(drawer_id: str, title: str, attributes: str = "", body: str = BODY) -> str:
    return lines(f'<ui-drawer id="{drawer_id}" heading="{title}"{attributes}>', f"  <p>{body}</p>", "</ui-drawer>")


def trigger(drawer_id: str, label: str, extra: str = "") -> str:
    return f'<ui-button variant="primary" data-bs-toggle="drawer" data-bs-target="#{drawer_id}"{extra}>{label}</ui-button>'


PAGE = {
    "title": "ui-drawer",
    "summary": "Hidden sidebars from any edge of the viewport, on the native <dialog>: backdrop, focus trap, Escape, "
    "swipe to close, body scrolling, static backdrops, sheets, translucent panels and responsive drawers that sit "
    "in the layout from a breakpoint on.",
    "submodule": "ui-drawer",
    "entry": "modules/bootstrap/ui-drawer/ui-drawer.js",
    "sections": [
        {
            "id": "live-demo",
            "title": "Live demo",
            "intro": "A trigger with <code>data-bs-toggle=\"drawer\"</code>; the header's close button, the backdrop, "
            "Escape, a swipe towards the edge or <code>data-bs-dismiss=\"drawer\"</code> inside close it.",
            "html": lines(
                trigger("drawerExample", "Toggle drawer"),
                '<ui-drawer id="drawerExample" heading="Drawer">',
                "  <p>Some text as placeholder. In real life you can have the elements you have chosen.</p>",
                "  <ui-menu>",
                '    <ui-button variant="secondary" data-bs-toggle="menu">Menu button</ui-button>',
                '    <div class="menu"><a class="menu-item" href="#">Action</a><a class="menu-item" href="#">Another action</a></div>',
                "  </ui-menu>",
                "</ui-drawer>",
            ),
        },
        {
            "id": "body-scrolling",
            "title": "Body scrolling",
            "intro": "<code>scroll</code> keeps the page scrollable; with <code>backdrop=\"false\"</code> the drawer is "
            "non-modal (no focus trap). With a backdrop it stays modal.",
            "html": lines(
                trigger("drawerScrolling", "Enable body scrolling"),
                drawer("drawerScrolling", "Body scrolling", ' scroll backdrop="false"', "Try scrolling the rest of the page."),
                trigger("drawerBoth", "Enable both scrolling & backdrop"),
                drawer("drawerBoth", "Backdrop with scrolling", " scroll", "Try scrolling the rest of the page."),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "static-backdrop",
            "title": "Static backdrop",
            "intro": "<code>backdrop=\"static\"</code>: a click outside does not close it.",
            "html": lines(trigger("drawerStatic", "Toggle static drawer"),
                          drawer("drawerStatic", "Static", ' backdrop="static"', "I will not close if you click outside of me.")),
        },
        {
            "id": "instant",
            "title": "Instant drawer",
            "intro": "<code>animation=\"instant\"</code>: no slide.",
            "html": lines(trigger("drawerInstant", "Toggle instant drawer"), drawer("drawerInstant", "Instant drawer", ' animation="instant"')),
        },
        {
            "id": "dark",
            "title": "Dark drawer",
            "intro": "<code>data-bs-theme=\"dark\"</code>: the panel and everything in it in dark mode.",
            "html": lines(trigger("drawerDark", "Toggle dark drawer"), drawer("drawerDark", "Dark drawer", ' data-bs-theme="dark"')),
        },
        {
            "id": "translucent",
            "title": "Translucent drawer",
            "intro": "<code>translucent</code> blurs and saturates what lies behind the panel.",
            "html": lines(trigger("drawerTranslucent", "Toggle translucent drawer"),
                          drawer("drawerTranslucent", "Translucent drawer", " translucent")),
        },
        {
            "id": "sheet",
            "title": "Sheet",
            "intro": "<code>sheet</code>: flush with the edge, without inset, border, radius and shadow; best at the "
            "bottom.",
            "html": lines(trigger("drawerSheet", "Toggle sheet"), drawer("drawerSheet", "Sheet", ' placement="bottom" sheet')),
        },
        {
            "id": "responsive",
            "title": "Responsive",
            "intro": "<code>responsive</code> with a breakpoint: below it a drawer, from it on the content sits in "
            "the page (header hidden, body in a row) and the host has <code>docked</code>. Resize the window to see it.",
            "html": lines(
                trigger("drawerResponsive", "Toggle drawer", ' class="lg:d-none"'),
                '<ui-drawer id="drawerResponsive" heading="Responsive drawer" placement="end" responsive="lg">',
                '  <p class="mb-0">This is content within a <code>responsive="lg"</code> drawer.</p>',
                "</ui-drawer>",
            ),
        },
        {
            "id": "placement",
            "title": "Placement",
            "intro": "<code>placement</code>: <code>start</code> (default), <code>end</code>, <code>top</code>, "
            "<code>bottom</code> or <code>fullscreen</code>.",
            "html": lines(*(lines(trigger(f"drawer{p.title()}", f"Toggle {p} drawer"), drawer(f"drawer{p.title()}", f"Drawer {p}", f' placement="{p}"'))
                            for p in ("top", "end", "bottom", "fullscreen"))),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "footer",
            "title": "Footer",
            "intro": "The slot <code>footer</code> holds actions at the bottom.",
            "html": lines(
                trigger("drawerFooter", "Toggle drawer with footer"),
                '<ui-drawer id="drawerFooter" heading="Drawer with footer">',
                f"  <p>{BODY}</p>",
                '  <ui-button slot="footer" variant="secondary" data-bs-dismiss="drawer">Cancel</ui-button>',
                '  <ui-button slot="footer" variant="primary">Save</ui-button>',
                "</ui-drawer>",
            ),
        },
    ],
    "elements": [
        {
            "tag": "ui-drawer",
            "attributes": [
                ("open", "boolean", "Shown; reflected."),
                ("heading / no-close / close-label", "", "Title with close button, as on <code>ui-dialog</code>."),
                ("placement", "string", "<code>start</code>, <code>end</code>, <code>top</code>, <code>bottom</code>, <code>fullscreen</code>."),
                ("responsive", "string", "<code>sm</code> … <code>2xl</code>: in the layout from that breakpoint on."),
                ("backdrop", "string", "<code>static</code> or <code>false</code>."),
                ("keyboard", "string", "<code>false</code>: Escape does not close it."),
                ("scroll", "boolean", "The page stays scrollable (non-modal with backdrop false)."),
                ("animation", "string", "<code>instant</code>: no slide."),
                ("translucent / sheet", "boolean", "Translucent panel / flush with the edge."),
                ("docked", "boolean", "Set by the drawer while it is in the layout (read only)."),
            ],
            "slots": [("(default)", "The body."), ("heading", "The title."), ("footer", "Actions at the bottom.")],
            "parts": [("drawer", "The native <code>&lt;dialog class=\"drawer\"&gt;</code>."),
                      ("header, title, close, body, footer", "Its parts.")],
            "events": [
                ("ui-drawer:show / ui-drawer:hide", "Before opening / closing; cancelable."),
                ("ui-drawer:shown / ui-drawer:hidden", "After the slide."),
                ("ui-drawer:hide-prevented / ui-drawer:cancel", "As on <code>ui-dialog</code>."),
                ("ui-drawer:dock", "Entered or left the layout; <code>detail.docked</code>."),
            ],
            "methods": [("show(options) / hide() / toggle(options)", "Promises; options <code>{ backdrop, keyboard, scroll }</code>.")],
        }
    ],
    "notes": ["<code>ui-offcanvas</code> (Bootstrap 5) is replaced by <code>ui-drawer</code>; its <code>responsive</code> "
              "docking works the same way."],
    "tokens": {"host": "ui-drawer", "example_token": "--bs-drawer-width", "example_value": "320px"},
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["drawer"]
