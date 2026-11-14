"""ui-range (Bootstrap 6 range, new in v6)."""

from __future__ import annotations

from .common import THEMES, VARIANT_ATTRIBUTE, lines

PAGE = {
    "title": "ui-range",
    "summary": "A slider with a filled track, a value bubble and tick marks — new in Bootstrap 6 — as a form field.",
    "submodule": "ui-range",
    "entry": "modules/bootstrap/ui-range/ui-range.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "The track fills up to the thumb (Bootstrap 6 does that with JavaScript; CSS cannot read the value).",
            "html": lines('<ui-range label="Example range" value="40"></ui-range>'),
        },
        {
            "id": "themes",
            "title": "Theme colors",
            "intro": "<code>variant</code> colours the fill and the thumb.",
            "html": lines('<div class="vstack gap-3">', *[f'  <ui-range variant="{name}" value="{20 + i * 9}" aria-label="{name} range"></ui-range>'
                                                          for i, name in enumerate(THEMES)], "</div>"),
        },
        {
            "id": "disabled",
            "title": "Disabled",
            "html": lines('<ui-range label="Disabled range" value="30" disabled></ui-range>'),
        },
        {
            "id": "min-max-step",
            "title": "Min, max and steps",
            "intro": "<code>min</code> and <code>max</code> (default 0 and 100), <code>step</code> (default 1).",
            "html": lines('<ui-range label="0 to 5" min="0" max="5" value="2"></ui-range>',
                          '<ui-range label="Half steps" min="0" max="5" step="0.5" value="2.5" bubble class="mt-4"></ui-range>'),
        },
        {
            "id": "bubble",
            "title": "Value bubble",
            "intro": "<code>bubble</code> shows the value above the thumb (Bootstrap's tooltip); <code>format</code> or the "
            "<code>formatter</code> property shapes the text.",
            "html": lines('<ui-range label="Brightness" value="60" bubble format="{value} %" class="mt-3"></ui-range>'),
        },
        {
            "id": "ticks",
            "title": "Tick marks",
            "intro": "<code>&lt;option&gt;</code> children add a tick at their value (also unevenly spaced); a <code>label</code> "
            "is shown beneath.",
            "html": lines('<ui-range label="Temperature" min="0" max="100" step="25" value="50">', '  <option value="0" label="Cold"></option>',
                          '  <option value="25"></option>', '  <option value="50" label="Mild"></option>', '  <option value="75"></option>',
                          '  <option value="100" label="Hot"></option>', "</ui-range>"),
        },
        {
            "id": "form-field",
            "title": "Form field",
            "intro": "<code>name</code>, <code>help</code> and the form behaviour of the other fields.",
            "html": lines('<form oninput="this.querySelector(\'output\').value = new FormData(this).get(\'volume\')">',
                          '  <ui-range name="volume" label="Volume" help="Adjust the volume level." value="70" bubble></ui-range>',
                          '  <p class="small mt-2 mb-0">Form value: <output>70</output></p>', "</form>"),
        },
        {
            "id": "plain-markup",
            "title": "Plain markup",
            "intro": "Bootstrap's own <code>.form-range</code> markup is set up automatically (<code>data-bs-bubble</code>, a "
            "<code>&lt;datalist&gt;</code> through <code>list</code>).",
            "html": lines('<div class="form-range theme-success" data-bs-bubble>', '  <input type="range" class="form-range-input" value="30" list="plainTicks" aria-label="Plain range">',
                          "</div>", '<datalist id="plainTicks"><option value="0" label="0"></option><option value="50" label="50"></option><option value="100" label="100"></option></datalist>'),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines('const range = document.querySelector("ui-range");', "range.formatter = (value) => `${value} °C`;",
                            'range.addEventListener("ui-range:changed", (event) => console.log(event.detail.value));',
                            "range.value = 75; // fill and bubble follow"),
        },
    ],
    "tokens": {"host": "ui-range", "example_token": "--bs-range-track-height", "example_value": "0.25rem"},
    "elements": [
        {
            "tag": "ui-range",
            "attributes": [
                ("min / max / step", "number", "Like the native range (0, 100, 1)."),
                ("value / name", "string", "Initial value and form name."),
                VARIANT_ATTRIBUTE,
                ("bubble", "boolean", "Value bubble above the thumb."),
                ("format", "string", "Bubble text, <code>{value}</code> is the value."),
                ("label / help / disabled / error", "string", "Like the other form fields."),
            ],
            "slots": [("(options)", "<code>&lt;option value label&gt;</code> children: tick marks.")],
            "parts": [("field / label / help / feedback", "The form field."), ("range / control", "The wrapper and the input."),
                      ("bubble / ticks", "Bubble and tick marks.")],
            "events": [("input / change", "As usual."), ("ui-range:changed", "On every update; <code>detail.value</code>.")],
            "methods": [("value / valueAsNumber", "The value."), ("formatter", "<code>(value) =&gt; text</code>."), ("update()", "Fill and bubble again.")],
        }
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["range_"]
