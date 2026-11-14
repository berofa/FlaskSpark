// Tests for webcomponents/modules/bootstrap/ui-grid/grid-layout.js.
//
// The shared-fixture cases assert the same inputs/outputs as the Python
// suite (tests/webcomponents/python/test_grid_layout.py), which keeps grid-layout.js and
// grid_layout.py semantically in sync. Regenerate the fixtures with
// scripts/generate_grid_layout_fixtures.py after intentional behavior
// changes.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import {
  buildUnitAreas,
  coercePositiveInt,
  defaultLayout,
  normalizeGridLayout,
  normalizeItemId,
} from "../../../webcomponents/modules/bootstrap/ui-grid/grid-layout.js";

const fixturesPath = join(dirname(fileURLToPath(import.meta.url)), "..", "fixtures", "grid_layout_cases.json");
const fixtures = JSON.parse(readFileSync(fixturesPath, "utf-8"));

for (const fixture of fixtures) {
  test(`normalizeGridLayout fixture: ${fixture.name}`, () => {
    assert.deepStrictEqual(
      normalizeGridLayout(fixture.payload, fixture.active_item_ids),
      fixture.expected,
    );
  });
}

test("defaultLayout shape", () => {
  const layout = defaultLayout();
  assert.equal(layout.rows_count, 1);
  assert.equal(layout.columns_count, 1);
  assert.equal(layout.areas.length, 1);
  assert.deepStrictEqual(layout.areas[0].item_ids, []);
});

test("buildUnitAreas covers the grid", () => {
  const areas = buildUnitAreas(2, 3);
  assert.equal(areas.length, 6);
  const cells = new Set(areas.map((area) => `${area.row}:${area.column}`));
  assert.equal(cells.size, 6);
  assert.ok(areas.every((area) => area.row_span === 1 && area.column_span === 1));
});

test("coercePositiveInt falls back on invalid input", () => {
  assert.equal(coercePositiveInt("3"), 3);
  assert.equal(coercePositiveInt(0, 7), 7);
  assert.equal(coercePositiveInt("abc", 2), 2);
  assert.equal(coercePositiveInt(null), 1);
});

test("normalizeItemId trims and rejects empty values", () => {
  assert.equal(normalizeItemId("  a  "), "a");
  assert.equal(normalizeItemId(5), "5");
  assert.equal(normalizeItemId(""), null);
  assert.equal(normalizeItemId(null), null);
  assert.equal(normalizeItemId(undefined), null);
});

test("normalizeGridLayout does not mutate the payload", () => {
  const payload = {
    rows_count: 1,
    columns_count: 2,
    areas: [
      { row: 1, column: 1, row_span: 1, column_span: 1, item_ids: ["a"], cell_items: { "1:1": ["a"] } },
    ],
  };
  const snapshot = structuredClone(payload);
  normalizeGridLayout(payload, ["a", "b"]);
  assert.deepStrictEqual(payload, snapshot);
});
