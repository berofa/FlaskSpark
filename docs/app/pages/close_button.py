"""ui-close-button (Bootstrap 6 close button)."""

from __future__ import annotations

from .common import lines

PAGE = {
    "title": "ui-close-button",
    "summary": "A generic close button for dismissing content like alerts and dialogs. The icon is a CSS mask in the "
    "current text colour, so it follows the colour mode without an extra variant.",
    "submodule": "ui-close-button",
    "entry": "modules/bootstrap/ui-close-button/ui-close-button.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "Give it a <code>label</code> when “Close” does not describe what it closes.",
            "html": '<ui-close-button></ui-close-button>\n<ui-close-button label="Close the message"></ui-close-button>',
            "preview_class": "d-flex gap-3",
        },
        {
            "id": "disabled",
            "title": "Disabled state",
            "intro": "Disabled close buttons are fainter and ignore pointer and keyboard.",
            "html": "<ui-close-button disabled></ui-close-button>",
        },
        {
            "id": "dark",
            "title": "Dark variant",
            "intro": "The icon takes the text colour, so it follows <code>data-bs-theme=\"dark\"</code> on any ancestor "
            "(or the dark colour mode of the page) together with the text: here <code>fg-body</code> resolves the "
            "text colour in the dark scheme.",
            "html": lines(
                '<div class="bg-inverse p-3 rounded">',
                '  <div data-bs-theme="dark" class="fg-body d-flex gap-3">',
                "    <ui-close-button></ui-close-button>",
                "    <ui-close-button disabled></ui-close-button>",
                "  </div>",
                "</div>",
            ),
        },
        {
            "id": "dismiss",
            "title": "Dismiss an ancestor",
            "intro": "<code>dismiss</code> takes a selector; a click calls <code>close()</code> of the closest ancestor "
            "that matches.",
            "html": lines(
                '<ui-alert variant="info">',
                '  <p class="d-flex align-items-center gap-2">A notice with its own close button '
                '<ui-close-button dismiss="ui-alert" class="ms-auto"></ui-close-button></p>',
                "</ui-alert>",
            ),
        },
    ],
    "elements": [
        {
            "tag": "ui-close-button",
            "attributes": [
                ("label", "string", "Accessible name (default <code>Close</code>)."),
                ("disabled", "boolean", "Inactive: fainter, no clicks, not focusable."),
                ("dismiss", "selector", "Closes the closest ancestor matching the selector (its <code>close()</code>)."),
            ],
            "parts": [("button", "The inner <code>&lt;button class=\"btn-close\"&gt;</code>.")],
            "events": [("click", "From the host, never while disabled.")],
            "methods": [("focus()", "Focuses the inner button.")],
        }
    ],
    "tokens": {"host": "ui-close-button", "example_token": "--bs-btn-close-size", "example_value": "1rem"},
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["close_button"]
