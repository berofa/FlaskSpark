// Tests for placeAligned / resolvePlacement (webcomponents/core/placement.js): menu placements like Bootstrap's.

import assert from "node:assert/strict";
import { test } from "node:test";

import { placeAligned, resolvePlacement } from "../../../webcomponents/core/placement.js";

const viewport = { width: 1000, height: 800 };
const anchor = { left: 100, top: 100, width: 80, height: 30 };
const box = { width: 160, height: 120 };

test("bottom-start: below the anchor, left edges aligned", () => {
  assert.deepEqual(placeAligned(anchor, box, viewport, "bottom-start", { offset: [0, 2] }), { placement: "bottom-start", left: 100, top: 132 });
});

test("bottom-end: right edges aligned", () => {
  assert.equal(placeAligned(anchor, box, viewport, "bottom-end").left, 20);
});

test("end-start: to the right, top edges aligned (logical end = right in LTR)", () => {
  assert.deepEqual(placeAligned(anchor, box, viewport, "end-start", { offset: [0, 2] }), { placement: "right-start", left: 182, top: 100 });
});

test("logical sides flip in RTL", () => {
  assert.equal(placeAligned({ ...anchor, left: 500 }, box, viewport, "end", { rtl: true }).placement, "left");
  assert.equal(placeAligned({ ...anchor, left: 500 }, box, viewport, "bottom-start", { rtl: true }).left, 500 + 80 - 160);
});

test("flips to the other side when it does not fit", () => {
  const low = { ...anchor, top: 740 };
  assert.equal(placeAligned(low, box, viewport, "bottom-start").placement, "top-start");
});

test("stays inside the viewport", () => {
  const right = { ...anchor, left: 950 };
  assert.equal(placeAligned(right, box, viewport, "bottom-start").left, 1000 - 160 - 4);
});

test("offset: along the side and away from the anchor", () => {
  const result = placeAligned(anchor, box, viewport, "bottom-start", { offset: [10, 20] });
  assert.deepEqual([result.left, result.top], [110, 150]);
});

test("resolvePlacement picks the largest matching breakpoint", () => {
  const breakpoints = { sm: 576, md: 768, lg: 1024 };
  const value = "bottom-start md:bottom-end lg:end-start";
  assert.equal(resolvePlacement(value, 500, breakpoints), "bottom-start");
  assert.equal(resolvePlacement(value, 800, breakpoints), "bottom-end");
  assert.equal(resolvePlacement(value, 1200, breakpoints), "end-start");
  assert.equal(resolvePlacement("", 1200, breakpoints), "bottom-start");
  assert.equal(resolvePlacement("top", 300, breakpoints), "top");
});
