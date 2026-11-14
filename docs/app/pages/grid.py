"""ui-grid (equal-column grid; no Bootstrap counterpart)."""

from __future__ import annotations

from .common import lines


def cells(count: int, indent: str = "  ", extra: dict[int, str] | None = None) -> list[str]:
    return [f'{indent}<div class="p-3 bg-2 rounded-3"{(extra or {}).get(n, "")}>Cell {n + 1}</div>' for n in range(count)]


PAGE = {
    "title": "ui-grid",
    "summary": "Children in an equal-column grid with a column count per Bootstrap breakpoint, measured on the viewport "
    "or on the grid itself.",
    "submodule": "ui-grid",
    "entry": "modules/bootstrap/ui-grid/ui-grid.js",
    "sections": [
        {
            "id": "example",
            "title": "Columns per breakpoint",
            "intro": "<code>columns</code> applies below the first breakpoint, <code>columns-sm</code> … "
            "<code>columns-2xl</code> from 576 / 768 / 1024 / 1280 / 1536 px up; each falls back to the next smaller one.",
            "html": lines('<ui-grid columns="1" columns-sm="2" columns-lg="4">', *cells(8), "</ui-grid>"),
        },
        {
            "id": "container",
            "title": "Container queries",
            "intro": "<code>container</code> measures the grid's own width, so the same grid adapts in a narrow sidebar "
            "and in a wide column (Bootstrap 6 uses container queries the same way).",
            "html": lines('<div style="max-width: 420px">', '  <ui-grid container columns="1" columns-sm="3">', *cells(3, "    "),
                          "  </ui-grid>", "</div>"),
        },
        {
            "id": "gaps",
            "title": "Gaps, spans and alignment",
            "intro": "<code>gap</code>, <code>gap-x</code> and <code>gap-y</code> take a length or a spacer number; a child "
            "spans with <code>--ui-grid-span</code> (or <code>grid-column</code>); <code>align</code> aligns the cells.",
            "html": lines('<ui-grid columns="3" gap-x="5" gap-y="1" align="center">',
                          *cells(5, extra={0: ' style="--ui-grid-span: 2"', 2: ' style="min-height: 6rem"'}), "</ui-grid>"),
        },
    ],
    "tokens": {"host": "ui-grid", "example_token": "--ui-grid-gap", "example_value": "2rem"},
    "elements": [
        {
            "tag": "ui-grid",
            "attributes": [
                ("columns", "number", "Columns below <code>sm</code> (default 1)."),
                ("columns-sm / -md / -lg / -xl / -2xl", "number", "Columns from that breakpoint up."),
                ("container", "boolean", "Breakpoints of the grid's own width (container queries)."),
                ("gap / gap-x / gap-y", "string", "Spacing: a CSS length or a spacer <code>0</code>–<code>12</code>."),
                ("align", "string", "<code>start</code>, <code>center</code>, <code>end</code> or <code>stretch</code>."),
            ],
            "slots": [("(default)", "The cells.")],
            "parts": [("grid", "The grid element.")],
        }
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["grid"]
