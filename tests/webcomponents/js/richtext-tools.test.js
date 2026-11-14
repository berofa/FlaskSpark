// Tests for the toolbar of webcomponents/modules/bootstrap/ui-richtext (toolGroups): the default set and markdown.

import assert from "node:assert/strict";
import { test } from "node:test";

globalThis.HTMLElement ??= class {};
globalThis.customElements ??= { get: () => undefined, define: () => {} };
const { tableHtml, toolGroups } = await import("../../../webcomponents/modules/bootstrap/ui-richtext/ui-richtext.js");

test("the default tools are unchanged", () => {
  assert.deepEqual(toolGroups().flat(), ["bold", "italic", "underline", "strikeThrough", "insertUnorderedList",
    "insertOrderedList", "quote", "link", "unlink", "removeFormat"]);
});

test("markdown: no underline (Markdown has none), heading, code, code block and a line instead", () => {
  const tools = toolGroups(true).flat();
  assert.ok(!tools.includes("underline"));
  for (const tool of ["heading", "code", "codeBlock", "insertHorizontalRule", "bold", "quote", "link", "taskList", "table",
    "tableRow", "tableColumn"]) {
    assert.ok(tools.includes(tool), tool);
  }
  toolGroups(true)[0].push("x"); // a copy: the toolbar's groups stay as they are
  assert.ok(!toolGroups(true)[0].includes("x"));
});

test("a new table: a header row and empty rows, every cell editable", () => {
  assert.equal(tableHtml(2, 1), "<table><thead><tr><th><br></th><th><br></th></tr></thead>"
    + "<tbody><tr><td><br></td><td><br></td></tr></tbody></table>");
  assert.equal((tableHtml(3, 2).match(/<td>/g) || []).length, 6);
  assert.equal((tableHtml(0, 0).match(/<th>/g) || []).length, 1); // at least one column and one row
  assert.equal((tableHtml(0, 0).match(/<td>/g) || []).length, 1);
});
