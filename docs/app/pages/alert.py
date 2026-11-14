"""ui-alert (Bootstrap 6 alert)."""

from __future__ import annotations

from .common import ICON_WARNING, THEMES, VARIANT_ATTRIBUTE, lines

PAGE = {
    "title": "ui-alert",
    "summary": "Contextual feedback messages for typical user actions: theme colours, heading, icon and an optional "
    "close button that fades the alert out and removes it.",
    "submodule": "ui-alert",
    "entry": "modules/bootstrap/ui-alert/ui-alert.js",
    "sections": [
        {
            "id": "default",
            "title": "Default alert",
            "intro": "Alerts take any content. Without a theme colour they use neutral colours.",
            "html": "<ui-alert>\n  <p>A simple alert—check it out!</p>\n</ui-alert>",
        },
        {
            "id": "variants",
            "title": "Variants",
            "intro": "<code>variant</code> takes any theme colour; colours adapt to the colour mode. Don't rely on "
            "colour alone to convey meaning.",
            "html": lines(*(f'<ui-alert variant="{name}">\n  <p>A simple {name} alert—check it out!</p>\n</ui-alert>'
                            for name in THEMES)),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "live",
            "title": "Live example",
            "intro": "The button adds a dismissible alert; its close button fades it out and removes it.",
            "html": lines(
                '<div id="liveAlertPlaceholder"></div>',
                '<ui-button variant="primary" id="liveAlertBtn">Show live alert</ui-button>',
            ),
            "preview_class": "d-flex flex-column align-items-start gap-3",
            "script": lines(
                'const placeholder = document.getElementById("liveAlertPlaceholder");',
                "",
                'document.getElementById("liveAlertBtn").addEventListener("click", () => {',
                '  const alert = document.createElement("ui-alert");',
                '  alert.setAttribute("variant", "success");',
                '  alert.toggleAttribute("dismissible", true);',
                '  alert.innerHTML = "<p>Nice, you triggered this alert message!</p>";',
                "  placeholder.append(alert);",
                "});",
            ),
        },
        {
            "id": "link-color",
            "title": "Link color",
            "intro": "Give links in the body the page's <code>.alert-link</code> class for matching colours.",
            "html": lines(*(f'<ui-alert variant="{name}">\n  <p>A simple {name} alert with '
                            f'<a href="#" class="alert-link">an example link</a>. Give it a click if you like.</p>\n'
                            "</ui-alert>" for name in THEMES)),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "additional-content",
            "title": "Additional content",
            "intro": "Headings (slot <code>heading</code>), paragraphs and dividers; the <code>&lt;hr&gt;</code> "
            "takes the theme's border colour.",
            "html": lines(
                '<ui-alert variant="success">',
                '  <h4 slot="heading" class="alert-heading mb-2">Well done!</h4>',
                "  <p>Aww yeah, you successfully read this important alert message. This example text is going to run "
                "a bit longer so that you can see how spacing within an alert works with this kind of content.</p>",
                '  <hr class="my-3">',
                '  <p class="mb-0">Whenever you need to, be sure to use margin utilities to keep things nice and tidy.</p>',
                "</ui-alert>",
            ),
        },
        {
            "id": "icons",
            "title": "With icons",
            "intro": "Put an icon into the slot <code>icon</code>; it sits before the content, vertically centred.",
            "html": lines(
                '<ui-alert variant="primary">',
                "  " + ICON_WARNING.replace("<svg ", '<svg slot="icon" ', 1),
                "  <p>An example alert with an icon</p>",
                "</ui-alert>",
            ),
        },
        {
            "id": "dismiss",
            "title": "Dismiss",
            "intro": "<code>dismissible</code> adds a close button. Closing fades the alert out (the transition "
            "tokens tune it), fires <code>ui-alert:closed</code> and removes the element; <code>instant</code> "
            "removes it at once. Any element inside with <code>data-bs-dismiss=\"alert\"</code> closes it too. "
            "Move the focus somewhere sensible in a <code>ui-alert:closed</code> listener, as the close button "
            "disappears with the alert.",
            "html": lines(
                '<ui-alert variant="warning" dismissible>',
                "  <p>Something’s wrong, check the fields below and try again.</p>",
                "</ui-alert>",
                '<ui-alert variant="info" dismissible instant>',
                "  <p>This one is removed at once, without fading out.</p>",
                "</ui-alert>",
                '<ui-alert variant="secondary">',
                '  <p>Closed by a button of your own: <ui-button size="sm" appearance="outline" variant="secondary" '
                'data-bs-dismiss="alert">Got it</ui-button></p>',
                "</ui-alert>",
            ),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "methods",
            "title": "Close from JavaScript",
            "intro": "<code>close()</code> returns a promise that resolves once the alert is removed. Cancel the "
            "closing with <code>preventDefault()</code> on <code>ui-alert:close</code>.",
            "script": lines(
                'const alert = document.querySelector("#myAlert");',
                "",
                'alert.addEventListener("ui-alert:close", (event) => {',
                "  if (!confirmLeaving()) event.preventDefault();",
                "});",
                'alert.addEventListener("ui-alert:closed", () => {',
                '  document.getElementById("next-field").focus();',
                "});",
                "",
                "await alert.close();",
            ),
        },
    ],
    "elements": [
        {
            "tag": "ui-alert",
            "attributes": [
                VARIANT_ATTRIBUTE,
                ("dismissible", "boolean", "Renders a close button."),
                ("close-label", "string", "Accessible name of the close button (default <code>Close</code>)."),
                ("instant", "boolean", "Closes at once instead of fading out (<code>.alert-instant</code>)."),
            ],
            "slots": [
                ("(default)", "The body of the alert."),
                ("heading", "A heading above the body (<code>.alert-heading</code>)."),
                ("icon", "An icon before the content."),
            ],
            "parts": [
                ("alert", "The <code>.alert</code> element."),
                ("icon", "The wrapper of the icon slot."),
                ("content", "The wrapper of heading and body."),
                ("close", "The close button."),
            ],
            "events": [
                ("ui-alert:close", "Fires when <code>close()</code> is called (also by the close button); cancelable."),
                ("ui-alert:closed", "Fires after the fade-out, right before the element is removed (bubbles)."),
            ],
            "methods": [
                ("close()", "Fades the alert out and removes it. Returns a promise (<code>true</code> once removed, "
                 "<code>false</code> if cancelled)."),
                ("variant", "The resolved theme colour (read only)."),
            ],
        }
    ],
    "tokens": {"host": "ui-alert", "example_token": "--bs-alert-border-radius", "example_value": "0"},
    "page_script": lines(
        'const placeholder = document.getElementById("liveAlertPlaceholder");',
        'document.getElementById("liveAlertBtn")?.addEventListener("click", () => {',
        '  const alert = document.createElement("ui-alert");',
        '  alert.setAttribute("variant", "success");',
        '  alert.toggleAttribute("dismissible", true);',
        '  alert.innerHTML = "<p>Nice, you triggered this alert message!</p>";',
        "  placeholder.append(alert);",
        "});",
    ),
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["alert"]
