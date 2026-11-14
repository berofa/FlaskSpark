"""Tests for webcomponents.grid_layout.

The shared-fixture cases assert the same inputs/outputs as the JS suite
(tests/webcomponents/js/grid-layout.test.js), which keeps grid_layout.py and
grid-layout.js semantically in sync. Regenerate the fixtures with
scripts/generate_grid_layout_fixtures.py after intentional behavior changes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from webcomponents.grid_layout import (  # noqa: E402
    build_unit_areas,
    default_layout,
    normalize_layout,
)

FIXTURES = json.loads(
    (ROOT / "tests" / "webcomponents" / "fixtures" / "grid_layout_cases.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", FIXTURES, ids=[case["name"] for case in FIXTURES])
def test_normalize_layout_fixture(case):
    assert normalize_layout(case["payload"], case["active_item_ids"]) == case["expected"]


def test_default_layout_shape():
    layout = default_layout()
    assert layout["rows_count"] == 1
    assert layout["columns_count"] == 1
    assert len(layout["areas"]) == 1
    assert layout["areas"][0]["item_ids"] == []


def test_build_unit_areas_covers_grid():
    areas = build_unit_areas(2, 3)
    assert len(areas) == 6
    assert {(area["row"], area["column"]) for area in areas} == {
        (row, column) for row in (1, 2) for column in (1, 2, 3)
    }
    assert all(area["row_span"] == 1 and area["column_span"] == 1 for area in areas)


def test_normalize_layout_does_not_mutate_payload():
    payload = {
        "rows_count": 1,
        "columns_count": 2,
        "areas": [
            {"row": 1, "column": 1, "row_span": 1, "column_span": 1, "item_ids": ["a"], "cell_items": {"1:1": ["a"]}},
        ],
    }
    snapshot = json.loads(json.dumps(payload))
    normalize_layout(payload, ["a", "b"])
    assert payload == snapshot
