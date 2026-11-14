"""ui-toast (Bootstrap 6 toasts)."""

from __future__ import annotations

from .common import THEMES, lines

PAGE = {
    "title": "ui-toast",
    "summary": "Short messages that do not move the page: header with time and close button, theme colours, "
    "translucent and dark toasts, autohide with pause on hover, and a container per corner. showToast() for code.",
    "submodule": "ui-toast",
    "entry": "modules/bootstrap/ui-toast/ui-toast.js",
    "sections": [
        {
            "id": "basic",
            "title": "Basic",
            "intro": "<code>heading</code> and <code>meta</code> build the header with a close button. A toast shows itself "
            "when added and hides after <code>delay</code> (5 s; <code>autohide=\"false\"</code> keeps it).",
            "html": '<ui-toast heading="Bootstrap" meta="11 mins ago" autohide="false" keep>Hello, world! This is a toast message.</ui-toast>',
        },
        {
            "id": "live",
            "title": "Live example",
            "html": '<ui-button variant="primary" id="liveToastBtn">Show live toast</ui-button>',
            "script": lines(
                'import { showToast } from "webcomponents/modules/bootstrap/ui-toast/ui-toast.js";  // or bootstrap.js',
                'showToast("Hello, world! This is a toast message.", { heading: "Bootstrap", meta: "just now" });',
            ),
        },
        {
            "id": "translucent",
            "title": "Translucent and dark",
            "html": lines(
                '<div class="docs-translucent-backdrop p-4 d-grid gap-3">',
                '  <ui-toast heading="Bootstrap" meta="11 mins ago" translucent autohide="false" keep>Translucent toast.</ui-toast>',
                '  <ui-toast heading="Bootstrap" meta="11 mins ago" data-bs-theme="dark" autohide="false" keep>Dark toast.</ui-toast>',
                "</div>",
            ),
        },
        {
            "id": "variants",
            "title": "Variants",
            "html": lines(*(f'<ui-toast variant="{name}" heading="{name.title()}" autohide="false" keep>A {name} toast.</ui-toast>' for name in THEMES)),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "custom",
            "title": "Custom content",
            "intro": "Without heading the close button is up to you: <code>data-bs-dismiss=\"toast\"</code>.",
            "html": lines(
                '<ui-toast autohide="false" keep>',
                '  <div class="d-flex align-items-center gap-2">Hello, world! This is a toast message.'
                '<ui-close-button class="ms-auto" data-bs-dismiss="toast"></ui-close-button></div>',
                '  <div class="mt-2 pt-2 border-top d-flex gap-2"><ui-button size="sm" variant="primary">Take action</ui-button>'
                '<ui-button size="sm" variant="secondary" data-bs-dismiss="toast">Close</ui-button></div>',
                "</ui-toast>",
            ),
        },
        {
            "id": "instant",
            "title": "Instant",
            "html": '<ui-toast heading="Instant" instant autohide="false" keep>No fade in and out.</ui-toast>',
        },
        {
            "id": "placement",
            "title": "Placement",
            "intro": "<code>&lt;ui-toast-container placement&gt;</code>: <code>top-</code>, <code>middle-</code> or "
            "<code>bottom-</code> with <code>-start</code>, <code>-center</code>, <code>-end</code> (default "
            "<code>top-end</code>), fixed in the window; toasts stack.",
            "html": lines(
                '<ui-toast-container placement="bottom-start">',
                '  <ui-toast heading="Bottom start" autohide="false" keep>Stacked at the bottom left.</ui-toast>',
                '  <ui-toast heading="Second" autohide="false" keep>See? Just like this.</ui-toast>',
                "</ui-toast-container>",
            ),
        },
    ],
    "elements": [
        {
            "tag": "ui-toast",
            "attributes": [
                ("heading / meta", "string", "Header title (or slot <code>heading</code>) and small text."),
                ("variant", "string", "Theme colour."),
                ("translucent / instant", "boolean", "Blurred background / no fade."),
                ("autohide / delay", "string", "<code>false</code> / ms (default 5000; 0 keeps it)."),
                ("keep", "boolean", "Stays in the DOM when hidden."),
                ("static", "boolean", "Not shown on connect."),
            ],
            "slots": [("(default)", "The body."), ("heading", "Rich header title.")],
            "parts": [("toast, header, body, close", "Its parts.")],
            "events": [("ui-toast:show / ui-toast:hide", "Before; cancelable."), ("ui-toast:shown / ui-toast:hidden", "After the fade.")],
            "methods": [("show(), hide() / close()", "Promises."), ("showToast(message, options)", "Module function: a toast in the corner's container.")],
        },
        {"tag": "ui-toast-container", "attributes": [("placement", "string", "Corner or edge of the window.")]},
    ],
    "tokens": {"host": "ui-toast", "example_token": "--bs-toast-max-width", "example_value": "420px"},
    "page_script": lines(
        'document.getElementById("liveToastBtn")?.addEventListener("click", () => {',
        '  let stack = document.querySelector("ui-toast-container[placement=top-end]");',
        "  if (!stack) {",
        '    stack = document.createElement("ui-toast-container");',
        '    stack.setAttribute("placement", "top-end");',
        "    document.body.append(stack);",
        "  }",
        '  const toast = document.createElement("ui-toast");',
        '  toast.setAttribute("heading", "Bootstrap");',
        '  toast.setAttribute("meta", "just now");',
        '  toast.textContent = "Hello, world! This is a toast message.";',
        "  stack.prepend(toast);",
        "});",
    ),
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["toast"]
