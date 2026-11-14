"""ui-chip and ui-chip-input (Bootstrap 6 chips)."""

from __future__ import annotations

from .common import THEMES, VARIANT_ATTRIBUTE, lines

PERSON = ('<svg slot="icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" '
          'aria-hidden="true"><path d="M3 14s-1 0-1-1 1-4 6-4 6 3 6 4-1 1-1 1zm5-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6"/></svg>')
AVATAR = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' "
          "fill='%236f42c1'/%3E%3Ctext x='8' y='11.5' font-size='9' text-anchor='middle' fill='white' font-family='sans-serif'%3EM%3C/text%3E%3C/svg%3E")
DISMISS = ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" '
           'stroke-width="2" stroke-linecap="round"><line x1="4" y1="4" x2="12" y2="12"/><line x1="12" y1="4" x2="4" y2="12"/></svg>')

PAGE = {
    "title": "ui-chip / ui-chip-input",
    "summary": "Small interactive elements for people, places, tags or values, and a multi-value field built from them "
    "(skills, categories, recipients).",
    "submodule": "ui-chip",
    "entry": "modules/bootstrap/ui-chip/ui-chip.js",
    "sections": [
        {
            "id": "chips",
            "title": "Chips",
            "intro": "<code>img</code> adds an avatar, the <code>icon</code> slot an icon, <code>dismissible</code> a remove "
            "button (cancelable <code>ui-chip:remove</code>, then the chip goes).",
            "html": lines(
                '<div class="d-flex flex-wrap gap-2">',
                "  <ui-chip>Basic chip</ui-chip>",
                f'  <ui-chip img="{AVATAR}">With avatar</ui-chip>',
                f"  <ui-chip>{PERSON}With icon</ui-chip>",
                "  <ui-chip dismissible>Dismissible</ui-chip>",
                "</div>",
            ),
        },
        {
            "id": "themes",
            "title": "Themed chips",
            "intro": "<code>variant</code> colours a chip; chips are subtle by default, so the active state stands out.",
            "html": lines('<div class="d-flex flex-wrap gap-2">', "  <ui-chip>Default</ui-chip>",
                          *[f'  <ui-chip variant="{name}">{name.capitalize()}</ui-chip>' for name in THEMES], "</div>"),
        },
        {
            "id": "active",
            "title": "Active and toggle",
            "intro": "<code>active</code> uses the solid appearance. <code>toggle</code> makes a chip a toggle button "
            "(click, Enter or Space; <code>change</code> event, <code>aria-pressed</code>); with <code>name</code> it "
            "submits <code>value</code> while active. <code>color</code> adds a coloured dot, e.g. for filters.",
            "html": lines(
                '<div class="d-flex flex-wrap gap-2">',
                '  <ui-chip variant="primary">Default</ui-chip>',
                '  <ui-chip variant="primary" active>Active</ui-chip>',
                '  <ui-chip variant="success" toggle name="filter" value="open" active color="#198754">Open</ui-chip>',
                '  <ui-chip variant="danger" toggle name="filter" value="failed" color="#dc3545">Failed</ui-chip>',
                '  <ui-chip href="#chips">Link chip</ui-chip>',
                "  <ui-chip disabled dismissible>Disabled</ui-chip>",
                "</div>",
            ),
        },
        {
            "id": "chip-input",
            "title": "Chip input",
            "intro": "Type and press <kbd>Enter</kbd> or <kbd>,</kbd> to add chips; <kbd>Backspace</kbd> or "
            "<kbd>Delete</kbd> select and remove them (see keyboard behaviour below). <code>inline-label</code> "
            "sits inside the field.",
            "html": lines('<ui-chip-input inline-label="Skills:" value="JavaScript, TypeScript" placeholder="Add more…"></ui-chip-input>'),
        },
        {
            "id": "chip-input-themes",
            "title": "Chip input themes",
            "intro": "<code>variant</code> themes all chips of the field.",
            "html": lines(
                '<div class="vstack gap-3">',
                '  <ui-chip-input variant="primary" value="Approved, Verified" placeholder="Add status…"></ui-chip-input>',
                '  <ui-chip-input variant="danger" value="Bug, Critical" placeholder="Add issue"></ui-chip-input>',
                '  <ui-chip-input variant="primary" placeholder="Type and press Enter"></ui-chip-input>',
                "</div>",
            ),
        },
        {
            "id": "chip-input-form",
            "title": "Label, help and form",
            "intro": "<code>label</code>, <code>help</code> and <code>required</code> like the other fields; every value is "
            "submitted under <code>name</code>. <code>max-chips</code>, <code>allow-duplicates</code>, "
            "<code>separator</code>, <code>create-on-blur=\"false\"</code> and <code>dismissible=\"false\"</code> tune it.",
            "html": lines(
                '<form onsubmit="event.preventDefault(); this.querySelector(\'output\').value = new FormData(this).getAll(\'skills\').join(\' | \')">',
                '  <ui-chip-input name="skills" label="Skills" help="Press Enter or comma to add a skill (at most 4)." variant="primary"',
                '    value=\'["React"]\' max-chips="4" required placeholder="Add skill…"></ui-chip-input>',
                '  <ui-button type="submit" variant="primary" class="mt-3">Submit</ui-button> <output class="ms-2"></output>',
                "</form>",
            ),
        },
        {
            "id": "chip-input-disabled",
            "title": "Disabled",
            "intro": "A disabled field adds no chips and keeps the existing ones.",
            "html": lines('<ui-chip-input variant="primary" value="Read only" disabled placeholder="Disabled…"></ui-chip-input>'),
        },
        {
            "id": "plain-markup",
            "title": "Plain markup",
            "intro": "Bootstrap's own <code>.chip</code> and <code>.chip-input[data-bs-chips]</code> markup works as well; "
            "options come from <code>data-bs-separator</code>, <code>data-bs-allow-duplicates</code>, "
            "<code>data-bs-max-chips</code>, <code>data-bs-create-on-blur</code>.",
            "html": lines(
                '<div class="chip-input theme-success" data-bs-chips>',
                '  <label class="chip-input-label" for="plainChips">Tags:</label>',
                '  <span class="chip">Docs</span>',
                f'  <span class="chip">Release<button type="button" class="chip-dismiss" aria-label="Remove">{DISMISS}</button></span>',
                '  <input type="text" class="form-ghost" id="plainChips" placeholder="Add tag…">',
                "</div>",
            ),
        },
        {
            "id": "keyboard",
            "title": "Keyboard behaviour",
            "intro": "In the field: <kbd>Enter</kbd> / separator add a chip; <kbd>Backspace</kbd> / <kbd>Delete</kbd> on an empty "
            "field select the last chip, again removes it; <kbd>←</kbd> at the start moves to the last chip "
            "(<kbd>Shift</kbd> extends); <kbd>Escape</kbd> clears. On a chip: <kbd>←</kbd> / <kbd>→</kbd> move "
            "(<kbd>Shift</kbd> extends), <kbd>Home</kbd> / <kbd>End</kbd> go to the first chip / the field, "
            "<kbd>Ctrl/Cmd+A</kbd> selects all, <kbd>Backspace</kbd> / <kbd>Delete</kbd> remove the selection. "
            "Mouse: click selects, <kbd>Ctrl/Cmd</kbd>+click toggles, <kbd>Shift</kbd>+click selects a range.",
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines(
                'const field = document.querySelector("ui-chip-input");',
                'field.addEventListener("ui-chip-input:add", (event) => {',
                "  if (event.detail.value.length < 2) event.preventDefault(); // cancelable",
                "});",
                'field.addEventListener("ui-chip-input:change", (event) => console.log(event.detail.values));',
                'field.add("Python");',
                'field.remove("JavaScript");',
                'field.values = ["A", "B"];',
            ),
        },
    ],
    "tokens": {"host": "ui-chip", "example_token": "--bs-chip-border-radius", "example_value": "var(--bs-radius-3)"},
    "elements": [
        {
            "tag": "ui-chip",
            "attributes": [
                VARIANT_ATTRIBUTE,
                ("active", "boolean", "Solid appearance."),
                ("toggle", "boolean", "Click toggles <code>active</code> (button with <code>aria-pressed</code>, <code>change</code> event)."),
                ("href / target / rel", "string", "Link chip."),
                ("dismissible", "boolean", "Remove button."),
                ("img / img-alt", "string", "Avatar image."),
                ("color", "string", "Coloured dot (any CSS colour)."),
                ("disabled", "boolean", "Not interactive."),
                ("name / value", "string", "Form value of a toggle chip while active (value default <code>on</code>)."),
                ("label / remove-label", "string", "Accessible names (remove default <code>Remove</code>)."),
            ],
            "slots": [("(default)", "The text."), ("icon", "An icon in front.")],
            "parts": [("chip", "The <code>.chip</code>."), ("img / icon / dot", "Leading items."), ("dismiss", "The remove button.")],
            "events": [("change", "A toggle chip changed."), ("ui-chip:remove", "Before removal; cancelable.")],
            "methods": [("dismiss()", "Removes the chip (unless cancelled)."), ("active", "Property.")],
        },
        {
            "tag": "ui-chip-input",
            "attributes": [
                ("value", "string", "Initial values: a JSON array or text split at the separator."),
                VARIANT_ATTRIBUTE,
                ("label / inline-label / help / placeholder", "string", "Texts."),
                ("separator", "string", "Adds a chip when typed (default <code>,</code>; empty: none)."),
                ("allow-duplicates", "boolean", "Allow the same value twice."),
                ("max-chips", "number", "Maximum number of chips."),
                ("dismissible", "string", "<code>false</code>: no remove buttons."),
                ("create-on-blur", "string", "<code>false</code>: leaving the field does not add a chip."),
                ("disabled / required", "boolean", "Form states."),
                ("name", "string", "Every value is submitted under this name."),
                ("error", "string", "A message shown as invalid."),
                ("remove-label", "string", "Name of the remove buttons (default <code>Remove</code>)."),
            ],
            "parts": [("field", "The <code>.form-field</code>."), ("chip-input", "The <code>.chip-input</code>."),
                      ("chip", "Each chip."), ("input", "The text field."), ("label / inline-label / help / feedback", "Texts.")],
            "events": [("ui-chip-input:add / ui-chip-input:remove", "Before; cancelable, <code>detail.value</code>."),
                       ("ui-chip-input:change", "After; <code>detail.values</code> (plus a plain <code>change</code>)."),
                       ("ui-chip-input:select", "Selection changed; <code>detail.selected</code>.")],
            "methods": [("values", "Get / set the values."), ("selectedValues", "Read only."),
                        ("add(value) / remove(chipOrValue) / removeSelected() / clear()", "Change the chips."),
                        ("selectChip(chip, options) / clearSelection() / focus()", "Selection and focus.")],
        },
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["chip"]
