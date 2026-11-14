// Tests for the pure parts of ui-context-menu (placement at the pointer, markup, tidy items) and ui-emoji-picker.

import assert from "node:assert/strict";
import { test } from "node:test";

globalThis.HTMLElement ??= class {};
globalThis.customElements ??= { get: () => undefined, define: () => {} };
const { atPoint, itemsHtml, tidy, within } = await import("../../../webcomponents/modules/bootstrap/ui-context-menu/ui-context-menu.js");
const { matches, remember } = await import("../../../webcomponents/modules/bootstrap/ui-emoji-picker/ui-emoji-picker.js");

const VIEW = { width: 1000, height: 800 };
const BOX = { width: 200, height: 150 };

test("an item takes a theme colour (variant), danger is the red one, an unknown variant none", () => {
  assert.match(itemsHtml([{ label: "Spam", variant: "warning" }]), /class="menu-item theme-warning"/);
  assert.match(itemsHtml([{ label: "Weg", danger: true }]), /class="menu-item theme-danger"/);
  assert.match(itemsHtml([{ label: "X", variant: "nope" }]), /class="menu-item"/);
});

test("the menu opens right of and below the pointer", () => {
  assert.deepEqual(atPoint(100, 100, BOX, VIEW), { left: 100, top: 100 });
});

test("near an edge it opens to the left or above, never outside the window", () => {
  assert.deepEqual(atPoint(950, 780, BOX, VIEW), { left: 750, top: 630 });
  assert.deepEqual(atPoint(10, 10, { width: 1200, height: 900 }, VIEW), { left: 4, top: 4 });
  assert.deepEqual(atPoint(0, 0, BOX, VIEW), { left: 4, top: 4 });
});

test("items are Bootstrap's menu markup, escaped", () => {
  const html = itemsHtml([{ label: "<b>Antworten</b>", icon: "<svg></svg>" }, { divider: true }, { header: "Mehr" },
    { label: "Löschen", danger: true, description: "für alle" }, { label: "Aus", disabled: true }]);
  assert.match(html, /class="menu-item" role="menuitem" data-index="0"><span class="menu-item-icon" aria-hidden="true"><svg><\/svg><\/span><span>&lt;b&gt;Antworten&lt;\/b&gt;<\/span>/);
  assert.match(html, /<hr class="menu-divider">/);
  assert.match(html, /<h6 class="menu-header">Mehr<\/h6>/);
  assert.match(html, /class="menu-item theme-danger"[^>]*><span class="menu-item-content"><span>Löschen<\/span><small class="menu-item-description">für alle<\/small>/);
  assert.match(html, /class="menu-item disabled"[^>]*disabled>/);
});

test("left out items and dividers in the wrong place go", () => {
  const d = { divider: true };
  const a = { label: "a" };
  const b = { label: "b" };
  assert.deepEqual(tidy([d, a, false, d, d, null, b, d]), [a, d, b]);
  assert.deepEqual(tidy([d, false]), []);
});

test("emoji search: every word in the name", () => {
  assert.ok(matches("smiling face with heart-eyes", "heart smil"));
  assert.ok(!matches("red heart", "smile"));
});

test("recently used: newest first, once, at most max", () => {
  assert.deepEqual(remember(["a", "b", "c"], "b"), ["b", "a", "c"]);
  assert.deepEqual(remember(["a", "b"], "c", 2), ["c", "a"]);
});

test("an element inside the root also across a shadow root (rows of a ui-table)", () => {
  const root = { parentNode: null };
  const host = { parentNode: root };
  const shadow = { parentNode: null, host };
  const row = { parentNode: { parentNode: shadow } };
  assert.ok(within(root, row));
  assert.ok(!within({ parentNode: null }, row));
});
