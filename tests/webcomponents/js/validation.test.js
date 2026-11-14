// Tests for webcomponents/core/validation.js (the messages of FormControlElement).

import assert from "node:assert/strict";
import { test } from "node:test";

import { validationMessage } from "../../../webcomponents/core/validation.js";

test("a required field left empty", () => {
  assert.equal(validationMessage({ valueMissing: true }, "text", ""), "Pflichtfeld");
  assert.equal(validationMessage({}, "text", ""), "");
});

test("email: valid, empty (not required) and invalid ones", () => {
  assert.equal(validationMessage({}, "email", "jane.doe@example.com"), "");
  assert.equal(validationMessage({}, "email", " a.b+c@sub.example.org "), "");
  assert.equal(validationMessage({}, "email", ""), ""); // optional: may stay empty
  for (const bad of ["a@b", "a@b.c", "a b@c.ch", "@x.ch", "a@.ch"]) {
    assert.equal(validationMessage({}, "email", bad), "Keine gültige E-Mail-Adresse", bad);
  }
  assert.equal(validationMessage({ typeMismatch: true }, "email", "x"), "Keine gültige E-Mail-Adresse");
  assert.equal(validationMessage({ typeMismatch: true }, "url", "x"), "Keine gültige Adresse (https://…)");
});

test("validationMode needs data-bs-validate on the element or an ancestor (or the form)", async () => {
  const { validationMode } = await import("../../../webcomponents/core/validation.js");
  const element = (attrs, parent = null) => ({
    closest: (selector) => (attrs?.["data-bs-validate"] !== undefined ? fake(attrs) : parent?.closest(selector) ?? null),
  });
  const fake = (attrs) => ({ getAttribute: (name) => attrs[name] ?? null, matches: () => attrs["data-bs-validate"] !== undefined });
  const form = { ...fake({ "data-bs-validate": "valid" }), closest: () => fake({ "data-bs-validate": "valid" }) };
  assert.equal(validationMode(element({}), null), null);
  assert.deepEqual(validationMode(element({ "data-bs-validate": "" })), { valid: false });
  assert.deepEqual(validationMode(element({}, form)), { valid: true });
  assert.deepEqual(validationMode(element({}), fake({ "data-bs-validate": "" })), { valid: false });
});
