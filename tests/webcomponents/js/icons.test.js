import test from "node:test";
import assert from "node:assert/strict";

import { iconSprite, setIconSprite, spriteIcon } from "../../../webcomponents/core/icons.js";

test("no sprite: no icon (outside a page, nothing set)", () => {
  assert.equal(iconSprite(), "");
  assert.equal(spriteIcon("trash"), "");
});

test("a sprite set by script: inline SVG with <use>, escaped", () => {
  setIconSprite("/static/icons.svg");
  assert.equal(iconSprite(), "/static/icons.svg");
  const markup = spriteIcon("graph-up");
  assert.match(markup, /^<svg class="ui-icon" [^>]*aria-hidden="true"/);
  assert.match(markup, /<use href="\/static\/icons\.svg#graph-up"><\/use>/);
  assert.match(spriteIcon('x"><script>'), /#x&quot;&gt;&lt;script&gt;/);
  assert.equal(spriteIcon(""), "");
  assert.match(spriteIcon("x", "my-icon"), /class="my-icon"/);
  setIconSprite("");
  assert.equal(spriteIcon("x"), "");
});
