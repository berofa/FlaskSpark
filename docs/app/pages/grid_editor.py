"""ui-grid-editor (layout editor for ui-grid; no Bootstrap counterpart)."""

from __future__ import annotations

import json

from .common import lines

ITEMS = [
    {"id": "analytics", "eyebrow": "Module", "title": "Analytics", "description": "Charts and KPIs", "meta": "4 widgets", "badge": "New"},
    {"id": "team", "eyebrow": "Module", "title": "Team", "description": "Members and status", "meta": "12 members"},
    {"id": "files", "eyebrow": "Module", "title": "Files", "description": "Recent uploads", "meta": "32 assets"},
    {"id": "billing", "eyebrow": "Module", "title": "Billing", "description": "Invoices and subscriptions", "meta": "2 pending"},
]


def area(row: int, column: int, item: str) -> dict:
    return {"row": row, "column": column, "row_span": 1, "column_span": 1, "item_ids": [item], "cell_items": {f"{row}:{column}": [item]}}


LAYOUT = {"rows_count": 2, "columns_count": 2,
          "areas": [area(1, 1, "analytics"), area(1, 2, "team"), area(2, 1, "billing"), area(2, 2, "files")]}

DATA = json.dumps({"items": ITEMS, "layout": LAYOUT}, indent=2)

PAGE = {
    "title": "ui-grid-editor",
    "summary": "Edits a ui-grid layout: drag items between cells, merge and split cells, add and remove rows and columns; "
    "every change is reported and can be saved as JSON.",
    "submodule": "ui-grid-editor",
    "entry": "modules/bootstrap/ui-grid-editor/ui-grid-editor.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "stacked": True,
            "intro": "The items and the layout come from a <code>&lt;script type=\"application/json\"&gt;</code> child (or the "
            "<code>data</code> property). Drag a card to another cell; the arrows on a cell merge it with its neighbour, "
            "the buttons on the lines add or remove rows and columns.",
            "html": lines('<ui-grid-editor id="gridEditor">', '  <script type="application/json">',
                          *["  " + line for line in DATA.splitlines()], "  </script>", "</ui-grid-editor>",
                          '<pre class="small mt-3 mb-0" id="gridEditorLog">Change the layout to see it here.</pre>'),
        },
        {
            "id": "labels",
            "title": "Texts",
            "intro": "Every text has an attribute: <code>empty-label</code>, <code>merge-left-label</code>, "
            "<code>merge-up-label</code>, <code>merge-right-label</code>, <code>merge-down-label</code>, "
            "<code>unmerge-label</code>, <code>add-row-label</code>, <code>remove-row-label</code>, "
            "<code>add-column-label</code>, <code>remove-column-label</code>, <code>row-actions-label</code>, "
            "<code>column-actions-label</code>, <code>cell-actions-label</code>.",
            "script": lines('<ui-grid-editor empty-label="Leere Zelle" add-row-label="Zeile einfügen" save-url="/layout">…</ui-grid-editor>'),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines(
                'const editor = document.querySelector("ui-grid-editor");',
                'editor.addEventListener("ui-grid-editor:change", (event) => console.log(event.detail.layout));',
                'editor.addEventListener("ui-grid-editor:error", (event) => console.error(event.detail.error));',
                "editor.data = { items, layout };",
            ),
        },
    ],
    "tokens": {"host": "ui-grid-editor", "example_token": "--ui-grid-editor-area-radius", "example_value": "0"},
    "elements": [
        {
            "tag": "ui-grid-editor",
            "attributes": [
                ("save-url", "string", "POSTs <code>{layout}</code> as JSON after every change."),
                ("&lt;key&gt;-label", "string", "The texts (see above; English defaults)."),
            ],
            "slots": [("(none)", "A <code>&lt;script type=\"application/json\"&gt;</code> child holds the data.")],
            "events": [("ui-grid-editor:change", "After every change: <code>detail.layout</code>."),
                       ("ui-grid-editor:error", "Saving failed: <code>detail.error</code>, <code>detail.layout</code>.")],
            "methods": [("data", "Get / set <code>{items, layout}</code>; items: <code>{id, eyebrow, title, description, meta, badge}</code>.")],
        }
    ],
}

PAGE["page_script"] = lines(
    'document.querySelector("#gridEditor").addEventListener("ui-grid-editor:change", (event) => {',
    '  document.querySelector("#gridEditorLog").textContent = JSON.stringify(event.detail.layout);',
    "});",
)

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = {**CUSTOM["grid_editor"], "html": lines('<ui-grid-editor class="compact-editor">', '  <script type="application/json">',
                                                       *["  " + line for line in DATA.splitlines()], "  </script>", "</ui-grid-editor>")}
