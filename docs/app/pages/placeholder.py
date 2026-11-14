"""ui-placeholder (Bootstrap 6 placeholders)."""

from __future__ import annotations

from .common import THEMES, lines

PAGE = {
    "title": "ui-placeholder",
    "summary": "Loading placeholders (skeletons) that stand in for content while it loads; sized by the text around them.",
    "submodule": "ui-placeholder",
    "entry": "modules/bootstrap/ui-placeholder/ui-placeholder.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "A card and its loading state: placeholders take the size of the text they stand in for "
            "(<code>aria-hidden</code> on the loading card).",
            "stacked": True,
            "html": lines(
                '<div class="d-flex gap-4 flex-wrap">',
                '  <ui-card style="width: 18rem">',
                '    <h5 class="card-title">Card title</h5>',
                '    <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card’s content.</p>',
                '    <ui-button variant="primary">Go somewhere</ui-button>',
                "  </ui-card>",
                '  <ui-card style="width: 18rem" aria-hidden="true">',
                '    <h5 class="card-title"><ui-placeholder width="6" animation="wave"></ui-placeholder></h5>',
                '    <p class="card-text">',
                *[f'      <ui-placeholder width="{w}" animation="wave"></ui-placeholder>' for w in (7, 4, 4, 6, 8)],
                "    </p>",
                '    <ui-placeholder width="6" variant="primary" size="lg"></ui-placeholder>',
                "  </ui-card>",
                "</div>",
            ),
        },
        {
            "id": "width",
            "title": "Width",
            "intro": "<code>width</code>: grid columns of the line (1–12) or any CSS width.",
            "html": lines('<ui-placeholder width="6"></ui-placeholder>', '<ui-placeholder width="75%"></ui-placeholder>',
                          '<ui-placeholder width="8rem"></ui-placeholder>'),
        },
        {
            "id": "color",
            "title": "Color",
            "intro": "The current text colour by default; <code>variant</code> for a theme colour.",
            "html": lines('<ui-placeholder width="9"></ui-placeholder>', *[f'<ui-placeholder width="6" variant="{t}"></ui-placeholder>' for t in THEMES]),
        },
        {
            "id": "sizing",
            "title": "Sizing",
            "html": lines('<div class="vstack gap-2">', '  <ui-placeholder size="lg"></ui-placeholder>', "  <ui-placeholder></ui-placeholder>",
                          '  <ui-placeholder size="sm"></ui-placeholder>', '  <ui-placeholder size="xs"></ui-placeholder>', "</div>"),
        },
        {
            "id": "animation",
            "title": "Animation",
            "intro": "<code>animation=\"wave\"</code> or <code>pulse</code> (<code>glow</code> is the old name of pulse). For text "
            "itself use Bootstrap's class: <code>&lt;span class=\"placeholder-wave\"&gt;</code>.",
            "html": lines('<p><ui-placeholder animation="wave"></ui-placeholder></p>', '<p><ui-placeholder animation="pulse"></ui-placeholder></p>',
                          '<span class="placeholder-wave fg-3">Working on it…</span>'),
        },
        {
            "id": "plain-markup",
            "title": "Plain markup",
            "intro": "Bootstrap's own classes work in the page as well: <code>.placeholder</code> with a <code>col-*</code> or width class.",
            "html": lines('<p aria-hidden="true" class="placeholder-wave"><span class="placeholder col-6"></span> <span class="placeholder col-4"></span></p>'),
        },
    ],
    "tokens": {"host": "ui-placeholder", "example_token": "--bs-placeholder-opacity-max", "example_value": ".3"},
    "elements": [
        {
            "tag": "ui-placeholder",
            "attributes": [("width", "string", "Grid columns 1–12 or a CSS width (default the whole line)."),
                           ("size", "string", "<code>lg</code>, <code>sm</code>, <code>xs</code>."),
                           ("animation", "string", "<code>wave</code> or <code>pulse</code>."),
                           ("variant", "string", "Theme colour (default: the text colour).")],
            "parts": [("placeholder", "The block.")],
        }
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["placeholder"]
