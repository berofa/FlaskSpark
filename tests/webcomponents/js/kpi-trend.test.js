import test from "node:test";
import assert from "node:assert/strict";

import { trendOf, trendVariant } from "../../../webcomponents/modules/bootstrap/ui-kpi/kpi-trend.js";

test("trend words and signs", () => {
  assert.equal(trendOf("up"), "up");
  assert.equal(trendOf(" Rising "), "up");
  assert.equal(trendOf("+"), "up");
  assert.equal(trendOf("down"), "down");
  assert.equal(trendOf("−"), "down");
  assert.equal(trendOf("flat"), "flat");
  assert.equal(trendOf("="), "flat");
});

test("trend from a number: its sign", () => {
  assert.equal(trendOf("2.5"), "up");
  assert.equal(trendOf("-0.1"), "down");
  assert.equal(trendOf("−3"), "down");
  assert.equal(trendOf("0"), "flat");
  assert.equal(trendOf(0), "flat");
});

test("no trend", () => {
  assert.equal(trendOf(""), "");
  assert.equal(trendOf(null), "");
  assert.equal(trendOf("sideways"), "");
});

test("trend colours, inverse for costs", () => {
  assert.equal(trendVariant("up"), "success");
  assert.equal(trendVariant("down"), "danger");
  assert.equal(trendVariant("up", true), "danger");
  assert.equal(trendVariant("down", true), "success");
  assert.equal(trendVariant("flat"), "");
  assert.equal(trendVariant(""), "");
});
