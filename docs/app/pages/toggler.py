"""Toggler (Bootstrap 6 data API, new in v6): toggle classes or attributes without own JavaScript."""

from __future__ import annotations

from .common import lines

PAGE = {
    "title": "Toggler (data API)",
    "summary": "Toggle a class or an attribute on click with data attributes only — new in Bootstrap 6. No element of "
    "its own: it works on any markup, also on the components.",
    "entry": "modules/bootstrap/toggler.js",
    "sections": [
        {
            "id": "class",
            "title": "Toggle class",
            "intro": "<code>data-bs-toggle=\"toggler\"</code> on the element, <code>data-bs-value</code> names the class "
            "(<code>data-bs-attribute</code> defaults to <code>class</code>).",
            "html": lines('<div class="w-100 p-3 rounded-5 border" data-bs-toggle="toggler" data-bs-value="fg-danger">',
                          "  Click to toggle <code>fg-danger</code>", "</div>"),
        },
        {
            "id": "remove",
            "title": "Remove existing",
            "intro": "A class the element already has is removed by the first click.",
            "html": lines('<div class="w-100 p-3 rounded-5 border bg-subtle-info" data-bs-toggle="toggler" data-bs-value="bg-subtle-info">',
                          "  Starts with <code>bg-subtle-info</code>. Click to remove it.", "</div>"),
        },
        {
            "id": "target",
            "title": "Target elements",
            "intro": "With <code>data-bs-target</code> the trigger toggles other elements — all a selector matches; each "
            "element names its own attribute and value. Components can be triggers.",
            "html": lines(
                '<ui-button variant="primary" data-bs-toggle="toggler" data-bs-target=".togglerTargets">Toggle both</ui-button>',
                '<div class="vstack gap-2 mt-2">',
                '  <div class="p-3 rounded-5 border togglerTargets" data-bs-value="bg-subtle-info">Toggles <code>bg-subtle-info</code></div>',
                '  <div class="p-3 rounded-5 border togglerTargets" data-bs-value="bg-subtle-warning">Toggles <code>bg-subtle-warning</code></div>',
                "</div>",
            ),
        },
        {
            "id": "attribute",
            "title": "Toggle attribute",
            "intro": "<code>data-bs-attribute</code> toggles an attribute instead: set to <code>data-bs-value</code>, removed "
            "when it has that value. Here <code>disabled</code> of a fieldset disables all its controls.",
            "html": lines(
                '<ui-button variant="secondary" data-bs-toggle="toggler" data-bs-target="#togglerFieldset">Toggle disabled</ui-button>',
                '<fieldset id="togglerFieldset" class="mt-2" data-bs-attribute="disabled" data-bs-value="">',
                '  <ui-input label="Name" placeholder="Disabled with the fieldset"></ui-input>',
                "</fieldset>",
            ),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines(
                'import { toggleToggler } from "…/modules/bootstrap/bootstrap.js";',
                'element.addEventListener("ui-toggler:toggle", (event) => { if (locked) event.preventDefault(); });',
                'element.addEventListener("ui-toggler:toggled", () => console.log(element.className));',
                "toggleToggler(element); // as a click would",
            ),
        },
    ],
    "elements": [
        {
            "tag": "[data-bs-toggle=\"toggler\"]",
            "attributes": [
                ("data-bs-toggle=\"toggler\"", "string", "On the trigger."),
                ("data-bs-target", "string", "Optional selector: the toggled elements (default: the trigger)."),
                ("data-bs-attribute", "string", "On the toggled element: the attribute (default <code>class</code>; never <code>id</code>)."),
                ("data-bs-value", "string", "On the toggled element: the class, or the attribute's value."),
            ],
            "events": [("ui-toggler:toggle", "Before; cancelable (on the toggled element)."), ("ui-toggler:toggled", "After.")],
            "methods": [("toggleToggler(element)", "Exported by the module: toggles like a click.")],
        }
    ],
}
