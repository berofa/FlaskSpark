"""ui-button (Bootstrap 6 button)."""

from __future__ import annotations

from .common import ICON_CHECK, ICON_STAR, THEMES, VARIANT_ATTRIBUTE, lines

APPEARANCES = ["solid", "outline", "subtle", "text"]

PAGE = {
    "title": "ui-button",
    "summary": "Buttons for actions in forms, dialogs and more: four appearances in every theme colour, link "
    "buttons, styled buttons, sizes, icon buttons, states, toggles and form submit/reset.",
    "submodule": "ui-button",
    "entry": "modules/bootstrap/ui-button/ui-button.js",
    "sections": [
        {
            "id": "base",
            "title": "Base class",
            "intro": "Without <code>variant</code> and <code>appearance</code> the button is Bootstrap's neutral "
            "<code>.btn</code>.",
            "html": "<ui-button>Base class</ui-button>",
        },
        {
            "id": "variants", "stacked": True,
            "title": "Variants",
            "intro": "<code>variant</code> picks the theme colour, <code>appearance</code> the style: "
            "<code>solid</code> (default with a variant), <code>outline</code>, <code>subtle</code> or <code>text</code>.",
            "html": lines(*(
                f'<ui-button variant="{name}" appearance="{appearance}">{name.title()}</ui-button>'
                for name in THEMES for appearance in APPEARANCES
            )),
            "preview_class": "docs-button-grid",
        },
        {
            "id": "link-buttons",
            "title": "Link buttons",
            "intro": "<code>appearance=\"link\"</code> looks like a link, optionally in a theme colour.",
            "html": lines(
                '<ui-button appearance="link">Link</ui-button>',
                *(f'<ui-button appearance="link" variant="{name}">{name.title()}</ui-button>' for name in THEMES),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "styled",
            "title": "Styled buttons",
            "intro": "<code>styled</code> adds a gradient and a shadow to solid buttons (tokens "
            "<code>--bs-btn-gradient-*</code>, <code>--bs-btn-border-*-mix-amount</code>, <code>--bs-btn-shadow</code>).",
            "html": lines(*(f'<ui-button variant="{name}" styled>{name.title()}</ui-button>' for name in THEMES)),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "tags",
            "title": "Button tags",
            "intro": "With <code>href</code> the button is a link (<code>target</code>, <code>rel</code>, "
            "<code>download</code>). <code>type=\"submit\"</code> and <code>type=\"reset\"</code> act on the "
            "surrounding form.",
            "html": lines(
                '<form class="d-flex flex-wrap gap-2" onsubmit="event.preventDefault(); this.querySelector(\'output\').value = \'Submitted\'">',
                '  <ui-button variant="primary" href="#">Link</ui-button>',
                '  <ui-button variant="primary" type="submit">Submit</ui-button>',
                '  <ui-button variant="primary" type="reset">Reset</ui-button>',
                '  <input class="form-control w-auto" name="demo" value="Change me">',
                "  <output></output>",
                "</form>",
            ),
        },
        {
            "id": "sizes",
            "title": "Sizes",
            "intro": "<code>size</code>: <code>lg</code>, <code>sm</code> or <code>xs</code>. Roll your own with the "
            "tokens on the element.",
            "html": lines(
                '<ui-button variant="primary" size="lg">Large button</ui-button>',
                '<ui-button variant="secondary" size="lg">Large button</ui-button>',
                '<ui-button variant="primary" size="sm">Small button</ui-button>',
                '<ui-button variant="secondary" size="sm">Small button</ui-button>',
                '<ui-button variant="primary" size="xs">Extra small button</ui-button>',
                '<ui-button variant="secondary" size="xs">Extra small button</ui-button>',
                '<ui-button variant="primary" style="--bs-btn-padding-y: .25rem; --bs-btn-padding-x: .5rem; '
                '--bs-btn-font-size: .75rem;">Custom button</ui-button>',
            ),
            "preview_class": "d-flex flex-wrap gap-2 align-items-center",
        },
        {
            "id": "icon-buttons",
            "title": "Icon buttons",
            "intro": "<code>icon</code> makes a square button for an icon only; always give it a <code>label</code>.",
            "html": lines(
                f'<ui-button icon label="Favourite">{ICON_STAR}</ui-button>',
                f'<ui-button icon variant="primary" label="Confirm">{ICON_CHECK}</ui-button>',
                f'<ui-button icon variant="secondary" appearance="outline" label="Favourite">{ICON_STAR}</ui-button>',
                f'<ui-button icon variant="warning" appearance="subtle" label="Favourite">{ICON_STAR}</ui-button>',
                f'<ui-button icon variant="primary" size="xs" label="Confirm">{ICON_CHECK}</ui-button>',
                f'<ui-button icon variant="primary" size="sm" label="Confirm">{ICON_CHECK}</ui-button>',
                f'<ui-button icon variant="primary" size="lg" label="Confirm">{ICON_CHECK}</ui-button>',
            ),
            "preview_class": "d-flex flex-wrap gap-2 align-items-center",
        },
        {
            "id": "disabled",
            "title": "Disabled state",
            "intro": "<code>disabled</code> on buttons and links (a link gets <code>.disabled</code>, "
            "<code>aria-disabled</code> and leaves the tab order). A disabled <code>&lt;fieldset&gt;</code> disables "
            "the buttons inside, too.",
            "html": lines(
                '<ui-button variant="primary" disabled>Primary button</ui-button>',
                '<ui-button variant="secondary" disabled>Button</ui-button>',
                '<ui-button variant="primary" appearance="outline" disabled>Primary button</ui-button>',
                '<ui-button variant="primary" href="#" disabled>Primary link</ui-button>',
                '<fieldset disabled class="d-inline-flex gap-2">',
                '  <ui-button variant="secondary">In a disabled fieldset</ui-button>',
                "</fieldset>",
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "block", "stacked": True,
            "title": "Block buttons",
            "intro": "In a <code>d-grid</code> the buttons fill the width; the responsive and column utilities work "
            "as in Bootstrap.",
            "html": lines(
                '<div class="d-grid gap-2">',
                '  <ui-button variant="primary">Button</ui-button>',
                '  <ui-button variant="primary">Button</ui-button>',
                "</div>",
                '<div class="d-grid gap-2 md:d-block mt-4">',
                '  <ui-button variant="primary">Button</ui-button>',
                '  <ui-button variant="primary">Button</ui-button>',
                "</div>",
                '<div class="d-grid gap-2 col-6 mx-auto mt-4">',
                '  <ui-button variant="primary">Button</ui-button>',
                '  <ui-button variant="primary">Button</ui-button>',
                "</div>",
                '<div class="d-grid gap-2 md:d-flex md:justify-content-end mt-4">',
                '  <ui-button variant="primary" class="md:me-2">Button</ui-button>',
                '  <ui-button variant="primary">Button</ui-button>',
                "</div>",
            ),
        },
        {
            "id": "toggle",
            "title": "Toggle buttons",
            "intro": "<code>toggle</code> works like Bootstrap's button plugin: a click switches <code>active</code>, "
            "exposed as <code>aria-pressed</code>, and fires <code>ui-button:toggle</code>.",
            "html": lines(
                '<ui-button variant="primary" toggle>Toggle button</ui-button>',
                '<ui-button variant="primary" toggle active>Active toggle button</ui-button>',
                '<ui-button variant="primary" toggle disabled>Disabled toggle button</ui-button>',
                '<ui-button variant="primary" toggle href="#">Toggle link</ui-button>',
                '<ui-button variant="primary" toggle active href="#">Active toggle link</ui-button>',
            ),
            "preview_class": "d-flex flex-wrap gap-2",
            "script": lines(
                'document.querySelectorAll("ui-button[toggle]").forEach((button) => {',
                '  button.addEventListener("ui-button:toggle", (event) => console.log(event.detail.active));',
                "});",
                "",
                "// switch all of them from code:",
                'document.querySelectorAll("ui-button[toggle]").forEach((button) => button.toggle());',
            ),
        },
    ],
    "elements": [
        {
            "tag": "ui-button",
            "attributes": [
                VARIANT_ATTRIBUTE,
                ("appearance", "string", "<code>solid</code> (default with a variant), <code>outline</code>, "
                 "<code>subtle</code>, <code>text</code> or <code>link</code>. Bootstrap 5: <code>outline</code> "
                 "(boolean), <code>variant=\"link\"</code>, <code>variant=\"ghost\"</code> (= text) still work."),
                ("styled", "boolean", "Gradient and shadow (<code>.btn-styled</code>)."),
                ("size", "string", "<code>xs</code>, <code>sm</code> or <code>lg</code>."),
                ("icon", "boolean", "Square icon-only button (<code>.btn-icon</code>); needs a <code>label</code>."),
                ("disabled", "boolean", "Inactive. Also inherited from a disabled <code>&lt;fieldset&gt;</code>."),
                ("active", "boolean", "Pressed / selected look."),
                ("toggle", "boolean", "On/off button: a click switches <code>active</code> (aria-pressed)."),
                ("block", "boolean", "Fills the width of its container."),
                ("type", "string", "<code>button</code> (default), <code>submit</code> or <code>reset</code> for the "
                 "surrounding form."),
                ("href", "url", "Renders a link (with <code>target</code>, <code>rel</code>, <code>download</code>)."),
                ("label", "string", "Accessible name (icon buttons)."),
                ("current", "string", "<code>aria-current</code> of a link (e.g. <code>page</code>)."),
                ("button-class", "string", "Further Bootstrap classes for the inner control."),
            ],
            "slots": [("(default)", "The label, icons, badges.")],
            "parts": [("button", "The inner <code>&lt;button&gt;</code> or <code>&lt;a&gt;</code>.")],
            "events": [
                ("click", "From the host; suppressed while disabled."),
                ("ui-button:toggle", "After a toggle switched; <code>detail.active</code> is the new state."),
            ],
            "methods": [
                ("toggle()", "Switches <code>active</code> and fires <code>ui-button:toggle</code>; returns the new state."),
                ("active / disabled", "The state as properties (reflected to the attributes)."),
                ("form", "The form the button belongs to."),
                ("focus(), click()", "Act on the inner control."),
            ],
        }
    ],
    "notes": [
        "Checkbox and radio toggle buttons (Bootstrap's <code>.btn-check</code>) are form controls and come with "
        "<code>ui-check</code>.",
        "Grouped buttons: <code>ui-button-group</code>.",
    ],
    "tokens": {"host": "ui-button", "example_token": "--bs-btn-border-radius", "example_value": "var(--bs-radius-pill)"},
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["button"]
