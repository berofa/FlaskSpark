// Tests for webcomponents/core/pages.js (the page numbers of ui-pagination).

import assert from "node:assert/strict";
import { test } from "node:test";

import { pageWindow } from "../../../webcomponents/core/pages.js";

test("all pages when they fit", () => {
  assert.deepEqual(pageWindow(2, 5), [1, 2, 3, 4, 5]);
  assert.deepEqual(pageWindow(1, 7, 7), [1, 2, 3, 4, 5, 6, 7]);
  assert.deepEqual(pageWindow(1, 1), [1]);
});

test("gaps around a window, always max entries", () => {
  assert.deepEqual(pageWindow(1, 20, 7), [1, 2, 3, 4, 5, "gap", 20]);
  assert.deepEqual(pageWindow(10, 20, 7), [1, "gap", 9, 10, 11, "gap", 20]);
  assert.deepEqual(pageWindow(20, 20, 7), [1, "gap", 16, 17, 18, 19, 20]);
  assert.deepEqual(pageWindow(5, 20, 7), [1, "gap", 4, 5, 6, "gap", 20]);
  for (let page = 1; page <= 20; page += 1) {
    const window = pageWindow(page, 20, 7);
    assert.equal(window.length, 7, `page ${page}: ${window}`);
    assert.ok(window.includes(page));
  }
});

test("out-of-range pages are clamped", () => {
  assert.deepEqual(pageWindow(99, 3), [1, 2, 3]);
  assert.ok(pageWindow(0, 30, 9).includes(1));
});
