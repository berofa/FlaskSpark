import test from "node:test";
import assert from "node:assert/strict";

import { clickedIndex } from "../../../webcomponents/modules/bootstrap/ui-list-group/list-group-click.js";

const wrapper = (index, action = true) => ({ dataset: { index: String(index) }, classList: { contains: (c) => action && c === "list-group-item-action" } });
const node = () => ({ dataset: {}, classList: { contains: () => false } });

test("a click on an item's own padding: the wrapper is the target", () => {
  const root = {};
  assert.equal(clickedIndex([wrapper(2), node(), root], root), 2);
});

test("a click on the item's text: slotted light-DOM content comes first in the path, the wrapper later", () => {
  const root = {};
  const text = node();
  const slot = node();
  assert.equal(clickedIndex([text, node(), slot, wrapper(4), root], root), 4);
});

test("no action item, or a click outside the items: -1", () => {
  const root = {};
  assert.equal(clickedIndex([wrapper(1, false), root], root), -1);
  assert.equal(clickedIndex([node(), root], root), -1);
  assert.equal(clickedIndex([], root), -1);
});

test("nothing beyond the list's own shadow tree counts", () => {
  const root = {};
  assert.equal(clickedIndex([node(), root, wrapper(3)], root), -1);
});
