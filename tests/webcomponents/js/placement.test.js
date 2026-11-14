// Tests for webcomponents/core/placement.js (tooltip positioning).

import assert from "node:assert/strict";
import { test } from "node:test";

import { computePlacement } from "../../../webcomponents/core/placement.js";

const viewport = { width: 1000, height: 800 };
const box = { width: 100, height: 40 };
const anchorAt = (left, top) => ({ left, top, width: 20, height: 20 });

test("places the box above and centred on the anchor", () => {
  const result = computePlacement(anchorAt(490, 400), box, viewport, "top", { gap: 6 });
  assert.deepStrictEqual(result, { placement: "top", left: 450, top: 354, arrow: 50 });
});

test("places right of the anchor with vertical centring", () => {
  const result = computePlacement(anchorAt(490, 400), box, viewport, "right", { gap: 6 });
  assert.deepStrictEqual(result, { placement: "right", left: 516, top: 390, arrow: 20 });
});

test("flips to the opposite side when the preferred side has no room", () => {
  const result = computePlacement(anchorAt(490, 10), box, viewport, "top", { gap: 6 });
  assert.equal(result.placement, "bottom");
  assert.equal(result.top, 36);
});

test("left placement flips to right at the viewport edge", () => {
  const result = computePlacement(anchorAt(20, 400), box, viewport, "left", { gap: 6 });
  assert.equal(result.placement, "right");
});

test("clamps along the edge and moves the arrow to stay on the anchor", () => {
  const result = computePlacement(anchorAt(970, 400), box, viewport, "top", { gap: 6, margin: 4 });
  assert.equal(result.left, 896);
  assert.equal(result.arrow, 84);
});

test("falls back to the preferred side when nothing fits", () => {
  const tiny = { width: 50, height: 50 };
  const result = computePlacement({ left: 0, top: 0, width: 50, height: 50 }, { width: 100, height: 100 }, tiny, "bottom");
  assert.equal(result.placement, "bottom");
});

test("unknown placement defaults to top", () => {
  const result = computePlacement(anchorAt(490, 400), box, viewport, "diagonal", { gap: 6 });
  assert.equal(result.placement, "top");
});
