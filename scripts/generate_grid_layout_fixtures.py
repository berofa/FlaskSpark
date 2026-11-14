"""Regenerate the shared grid-layout test fixtures.

Runs the input cases through the Python implementation (the reference) and
writes inputs plus expected outputs to tests/webcomponents/fixtures/grid_layout_cases.json.
The Python and JS test suites both assert against this file, which keeps
grid_layout.py and grid-layout.js semantically in sync.

Usage:
    python scripts/generate_grid_layout_fixtures.py

Review the diff of the fixture file before committing — the expected outputs
define the contract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from webcomponents.grid_layout import normalize_layout  # noqa: E402

FIXTURES_PATH = ROOT / "tests" / "webcomponents" / "fixtures" / "grid_layout_cases.json"

CASES = [
    {
        "name": "empty_payload_no_items",
        "payload": {},
        "active_item_ids": [],
    },
    {
        "name": "empty_payload_items_stack_in_single_cell",
        "payload": {},
        "active_item_ids": ["a", "b", "c"],
    },
    {
        "name": "unplaced_item_fills_emptiest_area",
        "payload": {
            "rows_count": 2,
            "columns_count": 2,
            "areas": [
                {"row": 1, "column": 1, "row_span": 1, "column_span": 1, "item_ids": ["a"], "cell_items": {"1:1": ["a"]}},
            ],
        },
        "active_item_ids": ["a", "b"],
    },
    {
        "name": "overlapping_area_rejected",
        "payload": {
            "rows_count": 2,
            "columns_count": 2,
            "areas": [
                {"row": 1, "column": 1, "row_span": 2, "column_span": 2, "item_ids": ["a"], "cell_items": {"1:1": ["a"]}},
                {"row": 2, "column": 2, "row_span": 1, "column_span": 1, "item_ids": ["b"], "cell_items": {"2:2": ["b"]}},
            ],
        },
        "active_item_ids": ["a", "b"],
    },
    {
        "name": "out_of_bounds_area_rejected",
        "payload": {
            "rows_count": 1,
            "columns_count": 1,
            "areas": [
                {"row": 2, "column": 1, "row_span": 1, "column_span": 1, "item_ids": ["a"], "cell_items": {"2:1": ["a"]}},
            ],
        },
        "active_item_ids": ["a"],
    },
    {
        "name": "cell_items_outside_span_fall_back_to_anchor",
        "payload": {
            "rows_count": 1,
            "columns_count": 2,
            "areas": [
                {"row": 1, "column": 1, "row_span": 1, "column_span": 1, "item_ids": ["a"], "cell_items": {"1:2": ["a"]}},
            ],
        },
        "active_item_ids": ["a"],
    },
    {
        "name": "duplicate_ids_deduped_across_areas",
        "payload": {
            "rows_count": 1,
            "columns_count": 2,
            "areas": [
                {"row": 1, "column": 1, "row_span": 1, "column_span": 1, "item_ids": ["a"], "cell_items": {"1:1": ["a"]}},
                {"row": 1, "column": 2, "row_span": 1, "column_span": 1, "item_ids": ["a"], "cell_items": {"1:2": ["a"]}},
            ],
        },
        "active_item_ids": ["a"],
    },
    {
        "name": "inactive_ids_filtered_out",
        "payload": {
            "rows_count": 1,
            "columns_count": 1,
            "areas": [
                {"row": 1, "column": 1, "row_span": 1, "column_span": 1, "item_ids": ["a", "ghost"], "cell_items": {"1:1": ["a", "ghost"]}},
            ],
        },
        "active_item_ids": ["a"],
    },
    {
        "name": "numeric_ids_normalized_to_strings",
        "payload": {
            "rows_count": 1,
            "columns_count": 1,
            "areas": [
                {"row": 1, "column": 1, "row_span": 1, "column_span": 1, "item_ids": [5], "cell_items": {"1:1": [5]}},
            ],
        },
        "active_item_ids": [5],
    },
    {
        "name": "legacy_rows_columns_count_keys",
        "payload": {"rows": 2, "columns": 3},
        "active_item_ids": [],
    },
    {
        "name": "unused_item_ids_auto_assigned",
        "payload": {
            "rows_count": 1,
            "columns_count": 2,
            "areas": [
                {"row": 1, "column": 1, "row_span": 1, "column_span": 1, "item_ids": ["a"], "cell_items": {"1:1": ["a"]}},
                {"row": 1, "column": 2, "row_span": 1, "column_span": 1, "item_ids": [], "cell_items": {}},
            ],
            "unused_item_ids": ["b"],
        },
        "active_item_ids": ["a", "b"],
    },
    {
        "name": "fill_prefers_least_loaded_area",
        "payload": {
            "rows_count": 1,
            "columns_count": 2,
            "areas": [
                {"row": 1, "column": 1, "row_span": 1, "column_span": 1, "item_ids": ["a", "b"], "cell_items": {"1:1": ["a", "b"]}},
                {"row": 1, "column": 2, "row_span": 1, "column_span": 1, "item_ids": [], "cell_items": {}},
            ],
        },
        "active_item_ids": ["a", "b", "c", "d"],
    },
    {
        "name": "merged_area_with_per_cell_items",
        "payload": {
            "rows_count": 2,
            "columns_count": 2,
            "areas": [
                {
                    "row": 1,
                    "column": 1,
                    "row_span": 2,
                    "column_span": 1,
                    "item_ids": ["a", "b"],
                    "cell_items": {"1:1": ["a"], "2:1": ["b"]},
                },
            ],
        },
        "active_item_ids": ["a", "b"],
    },
    {
        "name": "non_dict_payload_falls_back_to_default",
        "payload": None,
        "active_item_ids": ["a"],
    },
]


def main() -> int:
    fixtures = []
    for case in CASES:
        expected = normalize_layout(case["payload"], case["active_item_ids"])
        fixtures.append({**case, "expected": expected})

    FIXTURES_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURES_PATH.write_text(json.dumps(fixtures, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(fixtures)} cases to {FIXTURES_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
