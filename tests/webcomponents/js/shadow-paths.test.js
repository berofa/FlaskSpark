import test from "node:test";
import assert from "node:assert/strict";

import { findInPath, hostOf, inTables } from "../../../flaskspark/core/web/static/flaskspark/js/shadow-paths.js";

const element = (selector, root = null) => ({
  matches: (wanted) => wanted === selector,
  getRootNode: () => root ?? element.document,
});
element.document = {};

test("the element is found on the composed path, also when the event comes out of a <ui-table> retargeted", () => {
  const check = element("ui-check[data-role]");
  const table = element("ui-table");
  // a listener on the page sees the <ui-table> as the target; the path still starts at the control
  assert.equal(findInPath([check, element("td"), table, element.document], "ui-check[data-role]"), check);
  assert.equal(findInPath([table, element.document], "ui-check[data-role]"), undefined);
  assert.equal(findInPath([{}, "text", null], "ui-check[data-role]"), undefined); // no elements: nothing found
});

test("the host of an element in a shadow tree (to look further in the page), else the element itself", () => {
  const host = element("ui-table");
  const shadow = { host };
  assert.equal(hostOf(element("ui-check", shadow)), host);
  const plain = element("div");
  assert.equal(hostOf(plain), plain);
});

test("rows are found in the tables a <ui-table> moved into its shadow tree, and in plain ones", () => {
  const moved = { table: { querySelectorAll: (selector) => (selector === "tr[data-leftover]" ? ["a", "b"] : []) } };
  const plain = { querySelectorAll: (selector) => (selector === "tr[data-leftover]" ? ["c"] : []) };
  assert.deepEqual(inTables([moved, plain], "tr[data-leftover]"), ["a", "b", "c"]);
});
