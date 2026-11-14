// Tests for webcomponents/core/morph.js (morphChildren) on a small stand-in for the DOM (node has none).

import assert from "node:assert/strict";
import { test } from "node:test";

import { morphChildren } from "../../../webcomponents/core/morph.js";

class Node {
  constructor(nodeType) {
    this.nodeType = nodeType;
    this.childNodes = [];
    this.parentNode = null;
  }
  get lastChild() { return this.childNodes.at(-1) || null; }
  insertBefore(node, ref) {
    node.parentNode?.removeChild(node);
    const i = ref ? this.childNodes.indexOf(ref) : -1;
    if (i < 0) this.childNodes.push(node);
    else this.childNodes.splice(i, 0, node);
    node.parentNode = this;
    return node;
  }
  appendChild(node) { return this.insertBefore(node, null); }
  removeChild(node) {
    this.childNodes.splice(this.childNodes.indexOf(node), 1);
    node.parentNode = null;
    return node;
  }
  replaceWith(node) {
    const parent = this.parentNode;
    parent.insertBefore(node, this);
    parent.removeChild(this);
  }
}

class Text extends Node {
  constructor(value) { super(3); this.nodeValue = value; }
  get html() { return this.nodeValue; }
}

class Element extends Node {
  constructor(tag, attrs = {}, children = []) {
    super(1);
    this.tagName = tag.toUpperCase();
    this.attrs = new Map(Object.entries(attrs));
    children.forEach((c) => this.appendChild(typeof c === "string" ? new Text(c) : c));
  }
  get attributes() { return [...this.attrs].map(([name, value]) => ({ name, value })); }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  hasAttribute(name) { return this.attrs.has(name); }
  setAttribute(name, value) { this.attrs.set(name, String(value)); }
  removeAttribute(name) { this.attrs.delete(name); }
  get innerHTML() { return this.childNodes.map((c) => c.html).join(""); }
  get html() {
    const attrs = [...this.attrs].map(([k, v]) => ` ${k}="${v}"`).join("");
    return `<${this.tagName.toLowerCase()}${attrs}>${this.innerHTML}</${this.tagName.toLowerCase()}>`;
  }
}

const el = (tag, attrs, ...children) => new Element(tag, attrs, children);
const frag = (...children) => el("div", {}, ...children);

test("unchanged nodes stay, changed text and attributes are set", () => {
  const target = frag(el("p", { class: "a" }, "Milch"), el("img", { src: "1.jpg" }));
  const [p, img] = target.childNodes;
  morphChildren(target, frag(el("p", { class: "b" }, "Brot"), el("img", { src: "1.jpg" })));
  assert.equal(target.childNodes[0], p);
  assert.equal(target.childNodes[1], img); // the photo is not loaded again
  assert.equal(target.innerHTML, '<p class="b">Brot</p><img src="1.jpg"></img>');
});

test("new nodes inserted, superfluous ones removed, other tags replaced", () => {
  const target = frag(el("p", {}, "a"), el("span", {}, "b"), el("i", {}, "c"));
  const first = target.childNodes[0];
  morphChildren(target, frag(el("p", {}, "a"), el("b", {}, "B")));
  assert.equal(target.childNodes[0], first);
  assert.equal(target.innerHTML, "<p>a</p><b>B</b>");
});

test("keyed items keep their element when the list changes order", () => {
  const target = frag(el("li", { "data-key": "1" }, "eins"), el("li", { "data-key": "2" }, "zwei"));
  const [one, two] = target.childNodes;
  morphChildren(target, frag(el("li", { "data-key": "0" }, "null"), el("li", { "data-key": "2" }, "zwei"),
    el("li", { "data-key": "1" }, "eins")));
  assert.equal(target.childNodes[1], two);
  assert.equal(target.childNodes[2], one);
  assert.equal(target.innerHTML, '<li data-key="0">null</li><li data-key="2">zwei</li><li data-key="1">eins</li>');
});

test("a custom element keeps what it rendered while its markup stays; replaced when it changes", () => {
  const target = frag();
  morphChildren(target, frag(el("ui-chip", { active: "" }, "Privat ", el("small", {}, "(3)"))));
  const chip = target.childNodes[0];
  chip.childNodes = [new Text("rendered by the component")]; // a light component renders its own children
  morphChildren(target, frag(el("ui-chip", {}, "Privat ", el("small", {}, "(3)"))));
  assert.equal(target.childNodes[0], chip); // same markup: kept, only the attribute changed
  assert.equal(chip.hasAttribute("active"), false);
  assert.equal(chip.innerHTML, "rendered by the component");
  morphChildren(target, frag(el("ui-chip", {}, "Privat ", el("small", {}, "(4)"))));
  assert.notEqual(target.childNodes[0], chip); // its content changed: a new one
  assert.equal(target.childNodes[0].innerHTML, "Privat <small>(4)</small>");
});

test("a custom element with static morphChildren (its children are slotted, not rendered) is patched, not replaced", () => {
  class Card extends Element {
    static morphChildren = true;
  }
  const field = el("ui-input", { value: "a" });
  const target = frag(new Card("ui-card", {}, [el("div", { slot: "header" }, "Titel ", el("b", {}, "1")), field]));
  const card = target.childNodes[0];
  morphChildren(target, frag(new Card("ui-card", { class: "x" }, [el("div", { slot: "header" }, "Titel ", el("b", {}, "2")),
    el("ui-input", { value: "a" })])));
  assert.equal(target.childNodes[0], card); // its content changed, but it stays (and with it the focused field in it)
  assert.equal(card.childNodes[1], field);
  assert.equal(card.getAttribute("class"), "x");
  assert.equal(card.innerHTML, '<div slot="header">Titel <b>2</b></div><ui-input value="a"></ui-input>');
});

test("a clicked checkbox follows the html again", () => {
  const target = frag(el("input", { type: "checkbox", checked: "" }));
  const box = target.childNodes[0];
  box.type = "checkbox";
  box.checked = true; // the user clicked it (its property, no longer its attribute)
  morphChildren(target, frag(el("input", { type: "checkbox" })));
  assert.equal(target.childNodes[0], box);
  assert.equal(box.checked, false);
  morphChildren(target, frag(el("input", { type: "checkbox", checked: "" })));
  assert.equal(box.checked, true);
});
