// Tests for the stacked tables in the light DOM (core/stacked-tables.js): which cells get which column label.

import assert from "node:assert/strict";
import { test } from "node:test";

const { columnLabels, isStackedTable, labelStackedCells } = await import("../../../webcomponents/core/stacked-tables.js");

/** Just enough of a table cell for the labelling. */
function cell(text, { colSpan = 1, attrs = {} } = {}) {
  const map = new Map(Object.entries(attrs));
  return {
    textContent: text,
    colSpan,
    getAttribute: (name) => (map.has(name) ? map.get(name) : null),
    hasAttribute: (name) => map.has(name),
    setAttribute: (name, value) => map.set(name, value),
  };
}

function table(className, head, body, foot = []) {
  return {
    tagName: "TABLE",
    getAttribute: (name) => (name === "class" ? className : null),
    tHead: { rows: [{ cells: head }] },
    tBodies: [{ rows: body.map((cells) => ({ cells })) }],
    tFoot: foot.length ? { rows: foot.map((cells) => ({ cells })) } : null,
  };
}

test("only tables with table-stacked or a breakpoint variant count", () => {
  assert.equal(isStackedTable(table("table table-stacked", [], [])), true);
  assert.equal(isStackedTable(table("table sm:table-stacked app-table", [], [])), true);
  assert.equal(isStackedTable(table("table table-sm", [], [])), false);
  assert.equal(isStackedTable(table("table my-table-stacked-x", [], [])), false);
  assert.equal(isStackedTable(null), false);
});

test("labels come from the header text (whitespace folded) or its data-cell, spans repeat", () => {
  const head = [cell("  Account \n"), cell("Price", { colSpan: 2 }), cell("", {}), cell("PnL", { attrs: { "data-cell": "Profit" } })];
  assert.deepEqual(columnLabels(table("table-stacked", head, [])), ["Account", "Price", "Price", "", "Profit"]);
});

test("body and footer cells get the label of their column, own labels and spanning cells stay", () => {
  const head = [cell("Account"), cell("Side"), cell("Size"), cell("")];
  const own = cell("x", { attrs: { "data-cell": "Mine" } });
  const row = [cell("Main"), own, cell("0.1"), cell("⋯")];
  const empty = [cell("Nothing yet", { colSpan: 4 })];
  const total = [cell("Total", { colSpan: 2 }), cell("0.3"), cell("")];
  const t = table("table sm:table-stacked", head, [row, empty], [total]);
  labelStackedCells(t);
  assert.equal(row[0].getAttribute("data-cell"), "Account");
  assert.equal(own.getAttribute("data-cell"), "Mine");
  assert.equal(row[2].getAttribute("data-cell"), "Size");
  assert.equal(row[3].hasAttribute("data-cell"), false); // icon column without a header
  assert.equal(empty[0].hasAttribute("data-cell"), false);
  assert.equal(total[0].hasAttribute("data-cell"), false);
  assert.equal(total[1].getAttribute("data-cell"), "Size"); // after the span of two
});

test("a table without header labels is left alone", () => {
  const row = [cell("a"), cell("b")];
  labelStackedCells({ ...table("table-stacked", [], [row]), tHead: null });
  assert.equal(row[0].hasAttribute("data-cell"), false);
});
