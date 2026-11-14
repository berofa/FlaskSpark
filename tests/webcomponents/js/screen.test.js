// The pure parts of an info screen's script (flaskspark/screen.js): the date, the daily reload, the recovery after the
// push channel was down, what keeps working; and that no context menu opens on a screen.
import test from "node:test";
import assert from "node:assert/strict";

import {
  DOWN_RELOAD, DOWN_RELOAD_MAX, dayKey, downDelay, keeps, nextAt, shouldReload,
} from "../../../flaskspark/core/web/static/flaskspark/js/screen.js";

globalThis.HTMLElement ??= class {};
globalThis.customElements ??= { get: () => undefined, define: () => {} };
const { displayOnly } = await import("../../../webcomponents/modules/bootstrap/ui-context-menu/ui-context-menu.js");

test("the day of a date in local time", () => {
  assert.equal(dayKey(new Date(2026, 10, 14, 23, 59)), "2026-11-14");
  assert.equal(dayKey(new Date(2026, 0, 5, 0, 0)), "2026-01-05");
});

test("the next daily moment: later today, else tomorrow", () => {
  const now = new Date(2026, 10, 14, 3, 30);
  assert.deepEqual(nextAt(now, "04:00"), new Date(2026, 10, 14, 4, 0));
  assert.deepEqual(nextAt(now, "03:30"), new Date(2026, 10, 15, 3, 30)); // not again at the same minute
  assert.deepEqual(nextAt(new Date(2026, 11, 31, 22, 0), "04:00"), new Date(2027, 0, 1, 4, 0));
  assert.equal(nextAt(now, ""), null);
  assert.equal(nextAt(now, "24:00"), null);
  assert.equal(nextAt(now, "4:00"), null);
});

test("the wait before a reload doubles with every reload in a row, up to the maximum", () => {
  assert.equal(downDelay(0), DOWN_RELOAD);
  assert.equal(downDelay(1), 2 * DOWN_RELOAD);
  assert.equal(downDelay(3), 8 * DOWN_RELOAD);
  assert.equal(downDelay(50), DOWN_RELOAD_MAX);
  assert.equal(downDelay("x"), DOWN_RELOAD);
  assert.equal(downDelay(-2), DOWN_RELOAD);
});

test("reload only after the channel was down long enough", () => {
  assert.equal(shouldReload(null, 10_000_000), false);
  assert.equal(shouldReload(1000, 1000 + DOWN_RELOAD - 1), false);
  assert.equal(shouldReload(1000, 1000 + DOWN_RELOAD), true);
  assert.equal(shouldReload(0, 500, 400), true);
});

test("an element inside [data-screen-keep] keeps working", () => {
  const el = (keep) => ({ hasAttribute: (name) => keep && name === "data-screen-keep" });
  assert.equal(keeps([el(false), el(true), {}]), true);
  assert.equal(keeps([el(false), {}, null]), false);
  assert.equal(keeps(undefined), false);
});

test("a screen has no context menus", () => {
  const doc = (screen) => ({ documentElement: { hasAttribute: (name) => screen && name === "data-screen" } });
  assert.equal(displayOnly(doc(true)), true);
  assert.equal(displayOnly(doc(false)), false);
  assert.equal(displayOnly(null), false);
});
