// Tests for the DOM-free parts of webcomponents/modules/bootstrap/ui-markdown-editor (editor-commands.js): texts,
// commands of the «/» and «+» menus, edits of the Markdown source, and that inserted blocks render as intended.

import assert from "node:assert/strict";
import { test } from "node:test";

const c = await import("../../../webcomponents/modules/bootstrap/ui-markdown-editor/editor-commands.js");
const m = await import("../../../webcomponents/modules/bootstrap/ui-markdown/markdown.js");
const { ICON_PATHS } = await import("../../../webcomponents/modules/bootstrap/ui-markdown-editor/editor-icons.js");
await m.loadMarkdown();

test("every built-in command has a label and an icon", () => {
  for (const cmd of c.BUILTIN_COMMANDS) {
    assert.ok(c.DEFAULT_LABELS[cmd.label], cmd.id);
    assert.ok(ICON_PATHS[cmd.icon], cmd.icon);
  }
});

test("no Mermaid or PlantUML among the commands", () => {
  const ids = c.BUILTIN_COMMANDS.map((cmd) => cmd.id).join(" ");
  assert.ok(!/mermaid|plantuml/i.test(ids));
});

test("the «+» menu: alerts, code block, collapsible section, line, table of contents", () => {
  assert.deepEqual(c.menuCommands("plus").map((cmd) => cmd.id), ["alert-note", "alert-tip", "alert-important",
    "alert-warning", "alert-caution", "code-block", "details", "rule", "toc"]);
});

test("commands of the page and of one editor join the menus; same id replaces", () => {
  c.addCommand({ id: "embed", label: "Embedded view", icon: "window", markdown: "```view\n```", menus: ["plus"] });
  c.addCommand({ id: "embed", label: "Embedded view 2", markdown: "x", menus: ["plus", "slash"] });
  const own = [c.normalizeCommand({ id: "mine", label: "Mine", run: () => {} })];
  assert.equal(c.menuCommands("plus", own).filter((cmd) => cmd.id === "embed").length, 1);
  assert.ok(c.menuCommands("slash", own).some((cmd) => cmd.id === "mine"));
  assert.equal(c.registeredCommands().find((cmd) => cmd.id === "embed").label, "Embedded view 2");
  c.removeCommand("embed");
  assert.ok(!c.menuCommands("plus").some((cmd) => cmd.id === "embed"));
  assert.throws(() => c.addCommand({ id: "x", label: "X" }), TypeError);
  assert.throws(() => c.addCommand({ label: "X", markdown: "y" }), TypeError);
});

test("filterCommands: start of label, id or keyword first, then contained", () => {
  const ids = (q, labels) => c.filterCommands(c.menuCommands("slash"), q, labels).map((cmd) => cmd.id);
  assert.equal(ids("tab")[0], "table");
  assert.ok(ids("warn").includes("alert-warning"));
  assert.ok(ids("hinweis", { ...c.DEFAULT_LABELS, "alert-note": "Hinweis" }).includes("alert-note"));
  assert.deepEqual(ids("zzz"), []);
  assert.equal(ids("").length, c.menuCommands("slash").length);
});

test("toggleWrap wraps, and unwraps a wrapped selection", () => {
  assert.deepEqual(c.toggleWrap("a b c", 2, 3, "**"), { value: "a **b** c", start: 4, end: 5 });
  assert.deepEqual(c.toggleWrap("a **b** c", 4, 5, "**"), { value: "a b c", start: 2, end: 3 });
  assert.deepEqual(c.toggleWrap("a **b** c", 2, 7, "**"), { value: "a b c", start: 2, end: 3 });
  assert.deepEqual(c.toggleWrap("ab", 1, 1, "`"), { value: "a``b", start: 2, end: 2 });
});

test("insertLink and insertBlock", () => {
  assert.equal(c.insertLink("see here", 4, 8, "https://x.ch").value, "see [here](https://x.ch)");
  assert.equal(c.insertLink("", 0, 0, "https://x.ch", "X").value, "[X](https://x.ch)");
  assert.equal(c.insertBlock("text", 4, 4, "---").value, "text\n\n---\n");
  assert.equal(c.insertBlock("", 0, 0, "---").value, "---\n");
  assert.equal(c.insertBlock("a\n\nb", 1, 1, "---").value, "a\n\n---\n\nb");
});

test("tables: the Markdown of the picker renders as a table with that size", () => {
  const html = m.render(c.tableMarkdown(4, 3));
  assert.equal((html.match(/<th>/g) || []).length, 4);
  assert.equal((html.match(/<td>/g) || []).length, 12);
  assert.equal((c.tableHtml(2, 1).match(/<td>/g) || []).length, 2);
});

test("built-in blocks in the Markdown mode render as intended", () => {
  const L = c.DEFAULT_LABELS;
  assert.match(m.render(c.builtinMarkdown("alert-warning", L, "x")), /markdown-alert-warning/);
  assert.match(m.render(c.builtinMarkdown("details", L, "x")), /<details>\s*<summary>Details<\/summary>/);
  assert.match(m.render(c.builtinMarkdown("toc", L)), /markdown-toc/);
  assert.match(m.render(c.builtinMarkdown("code-block", L, "x")), /<pre><code>x/);
  assert.match(m.render(c.builtinMarkdown("tasks", L, "x")), /task-list-item/);
  assert.equal(c.builtinMarkdown("attach", L), null);
});

test("attachments: images as images, other files as links", () => {
  assert.equal(c.attachmentMarkdown({ url: "/uploads/a.png", name: "a.png" }, "image/png"), "![a.png](/uploads/a.png)");
  assert.equal(c.attachmentMarkdown({ url: "/uploads/b.pdf", name: "b [1].pdf" }, "application/pdf"),
    "[b \\[1\\].pdf](/uploads/b.pdf)");
  assert.equal(c.attachmentMarkdown({ url: "/u/a b.jpg", name: "x" }), "![x](</u/a b.jpg>)");
  assert.equal(c.format("{columns} × {rows}", { columns: 3, rows: 2 }), "3 × 2");
});
