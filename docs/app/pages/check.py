"""ui-check (Bootstrap 6 checkbox, radio, switch and toggle button)."""

from __future__ import annotations

from .common import THEMES, VARIANT_ATTRIBUTE, lines

PAGE = {
    "title": "ui-check",
    "summary": "Checkboxes, radios and switches with labels and descriptions, theme colours, sizes, an indeterminate "
    "state and validation, and toggle buttons. Form-associated: they submit under their name like native ones.",
    "submodule": "ui-check",
    "entry": "modules/bootstrap/ui-check/ui-check.js",
    "sections": [
        {
            "id": "checkbox",
            "title": "Checkbox",
            "intro": "Without a label it is the box alone (give it an <code>aria-label</code>).",
            "html": '<ui-check checked aria-label="Example checkbox"></ui-check>',
        },
        {
            "id": "indeterminate",
            "title": "Indeterminate",
            "intro": "<code>indeterminate</code> (also a property): neither checked nor unchecked, e.g. for “some of "
            "them”. A click clears it.",
            "html": '<ui-check indeterminate label="Some selected"></ui-check>',
        },
        {
            "id": "with-label",
            "title": "With label and description",
            "intro": "<code>label</code> (or the content) beside the box, <code>description</code> (or the slot "
            "<code>description</code>) below it.",
            "html": lines(
                '<ui-check label="Example new checkbox"></ui-check>',
                '<ui-check label="Example new checkbox" description="Supporting description for the above label."></ui-check>',
                "<ui-check>Label with <strong>markup</strong>",
                '  <span slot="description">A description with <a href="#">a link</a>.</span>',
                "</ui-check>",
            ),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "theme-colors",
            "title": "Theme colors",
            "intro": "<code>variant</code> colours the checked state.",
            "html": lines(*(f'<ui-check checked variant="{name}" label="Example {name} checkbox"></ui-check>' for name in THEMES)),
            "preview_class": "d-grid gap-2",
        },
        {
            "id": "disabled",
            "title": "Disabled",
            "intro": "The label follows with a lighter colour. A disabled <code>&lt;fieldset&gt;</code> disables the "
            "checks inside, too.",
            "html": lines(
                '<ui-check disabled label="Disabled checkbox"></ui-check>',
                '<ui-check disabled checked label="Disabled checked checkbox"></ui-check>',
                '<ui-check type="radio" disabled label="Disabled radio"></ui-check>',
                '<ui-check switch disabled checked label="Disabled checked switch"></ui-check>',
            ),
            "preview_class": "d-grid gap-2",
        },
        {
            "id": "sizes",
            "title": "Sizes",
            "intro": "<code>size</code>: <code>sm</code> or <code>lg</code>, for checkboxes, radios and switches.",
            "html": lines(
                *(f'<ui-check checked{f" size={chr(34)}{s}{chr(34)}" if s else ""} label="{title} checkbox"></ui-check>'
                  for s, title in (("sm", "Small"), ("", "Default"), ("lg", "Large"))),
                *(f'<ui-check type="radio" name="sizes" checked{f" size={chr(34)}{s}{chr(34)}" if s else ""} label="{title} radio"></ui-check>'
                  for s, title in (("sm", "Small"), ("", "Default"), ("lg", "Large"))),
                *(f'<ui-check switch{f" size={chr(34)}{s}{chr(34)}" if s else ""} label="{title} switch"></ui-check>'
                  for s, title in (("sm", "Small"), ("", "Default"), ("lg", "Large"))),
            ),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "radio",
            "title": "Radio",
            "intro": "<code>type=\"radio\"</code>. Radios with the same <code>name</code> (in the same form) are a "
            "group: one at a time, arrow keys move between them, and <code>required</code> is met by any of them.",
            "html": lines(
                '<ui-check type="radio" name="radios" value="1" label="First example radio"></ui-check>',
                '<ui-check type="radio" name="radios" value="2" label="Second example radio" checked></ui-check>',
                '<ui-check type="radio" name="radios" value="3" label="Example new radio" '
                'description="Supporting description for the above label."></ui-check>',
                *(f'<ui-check type="radio" name="theme-radios" checked variant="{name}" label="Example {name} radio"></ui-check>'
                  for name in ("success", "danger")),
            ),
            "preview_class": "d-grid gap-2",
        },
        {
            "id": "switch",
            "title": "Switch",
            "intro": "<code>switch</code> turns a checkbox into a switch (<code>role=\"switch\"</code>). Its width and "
            "indicator are tokens, e.g. a wider, more modern look:",
            "html": lines(
                '<ui-check switch label="Default switch"></ui-check>',
                '<ui-check switch checked variant="success" label="Success switch"></ui-check>',
                '<ui-check switch label="Custom width switch" '
                'style="--bs-switch-width: 2.75rem; --bs-switch-indicator-width: 1.5rem;"></ui-check>',
            ),
            "preview_class": "d-grid gap-2",
        },
        {
            "id": "inline",
            "title": "Inline",
            "intro": "<code>inline</code> places the checks side by side.",
            "html": lines(*(f'<ui-check inline label="{n}"></ui-check>' for n in ("1", "2", "3"))),
            "preview_class": "d-flex gap-3",
        },
        {
            "id": "toggle-buttons",
            "title": "Toggle buttons",
            "intro": "<code>button</code> shows the check as a button (<code>.btn-check</code>); its value is the "
            "appearance (<code>solid</code>, <code>outline</code>, <code>subtle</code>, <code>text</code>), "
            "<code>variant</code> the colour, <code>size</code> also <code>xs</code>. In a "
            "<code>&lt;ui-button-group&gt;</code> they join the group.",
            "html": lines(
                '<ui-check button variant="primary" checked>Checked</ui-check>',
                '<ui-check button variant="primary">Toggle</ui-check>',
                '<ui-check button variant="primary" disabled>Disabled</ui-check>',
                '<ui-check button="outline" variant="success" type="radio" name="options" checked>Checked</ui-check>',
                '<ui-check button="outline" variant="success" type="radio" name="options">Radio</ui-check>',
                '<ui-check button="outline" variant="danger" type="radio" name="options" size="sm">Small</ui-check>',
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "validation",
            "title": "Validation",
            "intro": "In a form with <code>data-bs-validate</code>, <code>required</code> marks an unchecked check invalid once "
            "it was changed or a submit was tried (or after <code>validate()</code>); <code>feedback</code> sets the message.",
            "html": lines(
                '<form class="d-grid gap-2" data-bs-validate novalidate onsubmit="event.preventDefault()">',
                '  <ui-check required label="Agree to terms and conditions" feedback="You must agree before submitting."></ui-check>',
                '  <ui-check type="radio" name="plan" value="a" required label="Plan A"></ui-check>',
                '  <ui-check type="radio" name="plan" value="b" required label="Plan B" feedback="Choose a plan."></ui-check>',
                '  <ui-button type="submit" variant="primary">Submit form</ui-button>',
                "</form>",
            ),
        },
    ],
    "elements": [
        {
            "tag": "ui-check",
            "attributes": [
                ("type", "string", "<code>checkbox</code> (default) or <code>radio</code>."),
                ("switch", "boolean", "A switch (checkbox)."),
                ("button", "string", "A toggle button; the value is the appearance: <code>solid</code> (default), "
                 "<code>outline</code>, <code>subtle</code>, <code>text</code>."),
                ("checked", "boolean", "Checked; reflects the user's changes."),
                ("indeterminate", "boolean", "Neither checked nor unchecked (checkbox)."),
                ("name / value", "string", "Submitted as <code>name=value</code> while checked (value default <code>on</code>)."),
                ("label", "string", "Text beside the box (or the content)."),
                ("description", "string", "Supporting text below the label (or the slot <code>description</code>)."),
                VARIANT_ATTRIBUTE,
                ("size", "string", "<code>sm</code> or <code>lg</code>; toggle buttons also <code>xs</code>."),
                ("disabled / required", "boolean", "As on native inputs."),
                ("inline", "boolean", "Side by side with the next one."),
                ("feedback", "string", "Message while invalid."),
            ],
            "slots": [
                ("(default)", "The label with markup."),
                ("description", "The description with markup."),
            ],
            "parts": [
                ("field", "The <code>.form-field</code> layout."),
                ("input", "The native input."),
                ("switch", "The <code>.switch</code> wrapper."),
                ("label / description", "Label and description."),
                ("button", "The <code>.btn-check</code> label of a toggle button."),
                ("feedback", "The invalid message."),
            ],
            "events": [("change", "After the user toggled it (bubbles)."), ("input", "Native, composed.")],
            "methods": [
                ("checked / indeterminate / value", "State as properties."),
                ("group", "The radios of its group."),
                ("validate()", "Shows the feedback and returns the validity."),
                ("form, validity, checkValidity(), reportValidity(), focus()", "As on native inputs."),
            ],
        }
    ],
    "tokens": {"host": "ui-check", "example_token": "--bs-check-border-radius", "example_value": "50%"},
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["check"]
