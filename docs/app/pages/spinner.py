"""ui-spinner (Bootstrap 6 spinners)."""

from __future__ import annotations

from .common import THEMES, VARIANT_ATTRIBUTE, lines

ROTATE = ('<svg slot="icon" viewBox="0 0 16 16" width="24" height="24" fill="none" stroke="currentcolor" stroke-width="2" stroke-linecap="round">'
          '<path d="M8 1V4"/><path opacity="0.8" d="M3.05 3.05L5.17 5.17"/><path opacity="0.6" d="M4 8L1 8"/>'
          '<path opacity="0.5" d="M5.17 10.83L3.05 12.95"/><path opacity="0.4" d="M8 12V15"/><path opacity="0.3" d="M10.83 10.83L12.95 12.95"/>'
          '<path opacity="0.2" d="M15 8L12 8"/><path opacity="0.1" d="M12.95 3.05L10.83 5.17"/></svg>')

PAGE = {
    "title": "ui-spinner",
    "summary": "A loading indicator in the current text colour, only CSS — border or growing, small, any size.",
    "submodule": "ui-spinner",
    "entry": "modules/bootstrap/ui-spinner/ui-spinner.js",
    "sections": [
        {
            "id": "border",
            "title": "Border spinner",
            "intro": "It has <code>role=\"status\"</code> and a hidden «Loading…» (<code>label</code>); with <code>label=\"\"</code> "
            "it is decorative, e.g. next to a visible text in a badge or button.",
            "html": lines(
                '<div class="d-flex align-items-center gap-3">',
                "  <ui-spinner></ui-spinner>",
                '  <ui-badge variant="primary"><ui-spinner label=""></ui-spinner> <span role="status">Loading</span></ui-badge>',
                '  <ui-button variant="primary" appearance="subtle" disabled><ui-spinner label=""></ui-spinner> <span role="status">Loading…</span></ui-button>',
                "</div>",
            ),
        },
        {"id": "grow", "title": "Growing spinner", "html": lines('<ui-spinner type="grow"></ui-spinner>')},
        {
            "id": "variants",
            "title": "Variants",
            "intro": "The spinner takes the text colour; <code>variant</code> sets a theme colour.",
            "html": lines('<div class="d-flex align-items-center gap-3">', *[f'  <ui-spinner variant="{t}"></ui-spinner>' for t in THEMES],
                          *[f'  <ui-spinner type="grow" variant="{t}"></ui-spinner>' for t in THEMES[:4]], "</div>"),
        },
        {
            "id": "size",
            "title": "Size",
            "intro": "<code>size=\"sm\"</code>, or the font size (spinners are <code>1em</code>), or the tokens.",
            "html": lines('<div class="d-flex align-items-center gap-3">', '  <ui-spinner size="sm"></ui-spinner>', '  <ui-spinner type="grow" size="sm"></ui-spinner>',
                          '  <ui-spinner style="font-size: 3rem"></ui-spinner>', '  <ui-spinner type="grow" style="--bs-spinner-width: 3rem; --bs-spinner-height: 3rem"></ui-spinner>',
                          "</div>"),
        },
        {
            "id": "custom",
            "title": "Custom spinners",
            "intro": "An svg in the <code>icon</code> slot is rotated (<code>.spinner-rotate</code>).",
            "html": lines("<ui-spinner>", f"  {ROTATE}", "</ui-spinner>"),
        },
    ],
    "tokens": {"host": "ui-spinner", "example_token": "--bs-spinner-animation-speed", "example_value": ".6s"},
    "elements": [
        {
            "tag": "ui-spinner",
            "attributes": [("type", "string", "<code>border</code> (default) or <code>grow</code>."), ("size", "string", "<code>sm</code>."),
                           VARIANT_ATTRIBUTE, ("label", "string", "Screen-reader text (default <code>Loading…</code>; empty: decorative).")],
            "slots": [("icon", "A custom svg that rotates.")],
            "parts": [("spinner", "The spinner element.")],
        }
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["spinner"]
