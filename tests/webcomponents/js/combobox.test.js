// Tests for the DOM-free search helper of the combobox (Bootstrap 6).

import assert from "node:assert/strict";
import { test } from "node:test";

import { searchText } from "../../../webcomponents/modules/bootstrap/ui-combobox/search.js";

test("searchText lowers and trims, and drops accents when asked", () => {
  assert.equal(searchText("  Zürich "), "zürich");
  assert.equal(searchText("Zürich", true), "zurich");
  assert.equal(searchText("São Paulo", true), "sao paulo");
  assert.equal(searchText(null), "");
});
