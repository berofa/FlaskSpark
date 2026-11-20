// Tests for LightComponentElement's `static morph` (core/light-component-element.js): the first render replaces the
// children, later ones patch them with morph() when the component asks for it, and never otherwise.

import assert from "node:assert/strict";
import { test } from "node:test";

globalThis.HTMLElement ??= class {};

const { LightComponentElement } = await import("../../../webcomponents/core/light-component-element.js");

/** A component instance without a DOM: counts innerHTML writes, morph() sees no children either way. */
function instance(Base) {
  const el = new Base();
  el.writes = 0;
  el.childNodes = [];
  Object.defineProperty(el, "isConnected", { value: true });
  Object.defineProperty(el, "innerHTML", { set() { el.writes += 1; } });
  // morph() builds a <template> for the html: an empty one is enough here
  el.ownerDocument = { createElement: () => ({ set innerHTML(_) {}, content: { childNodes: [] } }) };
  return el;
}

const tick = () => new Promise((resolve) => queueMicrotask(resolve));

test("without morph every render replaces the children", async () => {
  class Plain extends LightComponentElement {
    render() { return "<p>x</p>"; }
  }
  const el = instance(Plain);
  el.requestRender();
  await tick();
  el.requestRender();
  await tick();
  assert.equal(el.writes, 2);
  assert.equal(el.hasRendered, true);
});

test("with morph only the first render replaces the children, later ones are patched", async () => {
  class Live extends LightComponentElement {
    static morph = true;
    renders = 0;
    afterRender() { this.renders += 1; }
    render() { return "<p>x</p>"; }
  }
  const el = instance(Live);
  el.requestRender();
  await tick();
  el.requestRender();
  await tick();
  el.requestRender();
  await tick();
  assert.equal(el.writes, 1);
  assert.equal(el.renders, 3); // afterRender() still runs every time
});
