// Tests for webcomponents/core/shadow-sheet-transforms.js on a small stand-in for the CSSOM (node has none).

import assert from "node:assert/strict";
import { test } from "node:test";

import { hoistComponentTokens, isRootTokenRule, stripRootTokenRules } from "../../../webcomponents/core/shadow-sheet-transforms.js";

const style = (selectorText) => ({ selectorText });

class Group {
  constructor(rules, conditionText) {
    this.cssRules = rules;
    if (conditionText !== undefined) this.conditionText = conditionText;
  }
  deleteRule(index) { this.cssRules.splice(index, 1); }
}

const selectors = (container) => container.cssRules.map((rule) => rule.selectorText ?? (rule.conditionText !== undefined ? `@media ${rule.conditionText}` : "@layer"));

test("root token rules are :root and :host only", () => {
  assert.equal(isRootTokenRule(style(":root,\n:host")), true);
  assert.equal(isRootTokenRule(style(":root")), true);
  assert.equal(isRootTokenRule(style(":host")), true);
  assert.equal(isRootTokenRule(style(":root.dialog-open")), false);
  assert.equal(isRootTokenRule(style(":root:dir(rtl) .drawer")), false);
  assert.equal(isRootTokenRule(style(".alert")), false);
  assert.equal(isRootTokenRule(style(":host, .alert")), false);
  assert.equal(isRootTokenRule({}), false);
});

test("strips root token rules at the top level and keeps the rest", () => {
  const sheet = new Group([style(":root, :host"), style(".alert"), style(":root.dialog-open")]);
  assert.equal(stripRootTokenRules(sheet), 1);
  assert.deepEqual(selectors(sheet), [".alert", ":root.dialog-open"]);
});

test("strips inside @layer and @media and drops @media blocks left empty", () => {
  const layer = new Group([style(":root, :host"), style("body")]);
  const darkOnly = new Group([style(":root, :host")], "(prefers-color-scheme: dark)");
  const sheet = new Group([layer, darkOnly, style(".btn")]);

  assert.equal(stripRootTokenRules(sheet), 2);
  assert.deepEqual(selectors(sheet), ["@layer", ".btn"]);
  assert.deepEqual(selectors(layer), ["body"]);
});

test("an empty @layer block is kept (it fixes the layer order)", () => {
  const layer = new Group([style(":root, :host")]);
  const sheet = new Group([layer]);
  stripRootTokenRules(sheet);
  assert.equal(sheet.cssRules.length, 1);
});

test("nested style rules are not touched", () => {
  const nested = { selectorText: ".alert", cssRules: [style(":root")], deleteRule() { throw new Error("must not recurse"); } };
  const sheet = new Group([nested]);
  assert.equal(stripRootTokenRules(sheet), 0);
});

test("missing input removes nothing", () => {
  assert.equal(stripRootTokenRules(null), 0);
  assert.equal(stripRootTokenRules({}), 0);
});

// --- hoistComponentTokens ---------------------------------------------------

class Style {
  constructor(entries) { this.entries = [...entries]; }
  get length() { return this.entries.length; }
  item(i) { return this.entries[i][0]; }
  getPropertyValue(name) { return this.entries.find(([n]) => n === name)?.[1] ?? ""; }
  removeProperty(name) { this.entries = this.entries.filter(([n]) => n !== name); }
}

class Sheet extends Group {
  insertRule(text, index) {
    const [, selectorText, body] = text.match(/^(.*?)\s*\{\s*(.*?)\s*\}$/);
    const entries = body.split(";").map((d) => d.trim()).filter(Boolean).map((d) => {
      const at = d.indexOf(":");
      return [d.slice(0, at).trim(), d.slice(at + 1).trim()];
    });
    this.cssRules.splice(index, 0, { selectorText, style: new Style(entries) });
    return index;
  }
}

const styled = (selectorText, entries) => ({ selectorText, style: new Style(entries) });
const BADGE = [{ selector: ".badge", prefix: "--bs-badge-", host: "ui-badge" }];

test("puts the defaults on the host and lets the component's element inherit them", () => {
  const badge = styled(".badge", [["--bs-badge-padding-x", "0.625em"], ["--bs-badge-bg", "var(--bs-bg-2)"], ["display", "inline-flex"]]);
  const sheet = new Sheet([badge]);

  assert.equal(hoistComponentTokens(sheet, BADGE), 2);
  assert.deepEqual(sheet.cssRules.map((r) => r.selectorText), [
    ":host(ui-badge)",
    ".badge",
    ":where(.ui-host-tokens):is(.badge)",
  ]);
  assert.deepEqual(sheet.cssRules[0].style.entries, [["--bs-badge-padding-x", "0.625em"], ["--bs-badge-bg", "var(--bs-bg-2)"]]);
  assert.deepEqual(sheet.cssRules[2].style.entries, [["--bs-badge-padding-x", "inherit"], ["--bs-badge-bg", "inherit"]]);
  // The class keeps Bootstrap's defaults for every other use (e.g. a .btn-close inside an alert).
  assert.equal(badge.style.length, 3);
});

test("keeps tokens of other prefixes and tokens that read the theme on the element", () => {
  const alert = styled(".alert", [["--bs-alert-gap", "1rem"], ["--bs-hr-border-color", "red"], ["--bs-alert-bg", "var(--bs-theme-bg)"]]);
  const sheet = new Sheet([alert]);

  hoistComponentTokens(sheet, [{ selector: ".alert", prefix: "--bs-alert-", host: "ui-alert" }]);

  assert.deepEqual(sheet.cssRules[0].style.entries, [["--bs-alert-gap", "1rem"]]);
  assert.deepEqual(sheet.cssRules[2].style.entries, [["--bs-alert-gap", "inherit"]]);
});

test("the inherit rule keeps the selector list, so it has the base rule's specificity", () => {
  const base = styled(".btn, .btn-solid", [["--bs-btn-gap", "1px"]]);
  const sheet = new Sheet([base]);

  hoistComponentTokens(sheet, [{ selector: ".btn", prefix: "--bs-btn-", host: "ui-button" }]);

  assert.equal(sheet.cssRules[2].selectorText, ":where(.ui-host-tokens):is(.btn, .btn-solid)");
});

test("matches the first selector of a list only, never modifiers", () => {
  const base = styled(".btn, .btn-solid", [["--bs-btn-gap", "1px"]]);
  const modifier = styled(".btn-sm", [["--bs-btn-gap", "2px"]]);
  const later = styled(".btn-solid, .btn", [["--bs-btn-gap", "3px"]]);
  const sheet = new Sheet([base, modifier, later]);

  assert.equal(hoistComponentTokens(sheet, [{ selector: ".btn", prefix: "--bs-btn-", host: "ui-button" }]), 1);
  // host rule, base, inherit rule, then the modifier still after it
  assert.deepEqual(sheet.cssRules.map((r) => r.selectorText), [
    ":host(ui-button)",
    ".btn, .btn-solid",
    ":where(.ui-host-tokens):is(.btn, .btn-solid)",
    ".btn-sm",
    ".btn-solid, .btn",
  ]);
});

test("hoists inside @layer blocks into the same block", () => {
  const layer = new Sheet([styled(".badge", [["--bs-badge-gap", "1px"]])]);
  const sheet = new Sheet([layer]);

  hoistComponentTokens(sheet, BADGE);

  assert.equal(sheet.cssRules.length, 1);
  assert.deepEqual(layer.cssRules.map((r) => r.selectorText), [":host(ui-badge)", ".badge", ":where(.ui-host-tokens):is(.badge)"]);
});

test("rules without matching tokens stay untouched", () => {
  const sheet = new Sheet([styled(".badge", [["display", "flex"]])]);
  assert.equal(hoistComponentTokens(sheet, BADGE), 0);
  assert.equal(sheet.cssRules.length, 1);
  assert.equal(hoistComponentTokens(null, BADGE), 0);
});

test("matches attribute selectors the CSSOM writes with quotes", () => {
  const calendar = styled('[data-vc="calendar"]', [["--bs-datepicker-bg", "var(--bs-bg-body)"]]);
  const sheet = new Sheet([calendar]);
  const hoists = [{ selector: "[data-vc=calendar]", prefix: "--bs-datepicker-", host: "ui-datepicker" }];
  assert.equal(hoistComponentTokens(sheet, hoists), 1);
  assert.deepEqual(selectors(sheet), [":host(ui-datepicker)", '[data-vc="calendar"]', ':where(.ui-host-tokens):is([data-vc="calendar"])']);
});
