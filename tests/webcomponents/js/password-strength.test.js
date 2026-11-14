// Tests for webcomponents/core/password-strength.js (Bootstrap 6 strength scoring).

import assert from "node:assert/strict";
import { test } from "node:test";

import { scorePassword, strengthLevel } from "../../../webcomponents/core/password-strength.js";

test("an empty password scores 0 and has no level", () => {
  assert.equal(scorePassword(""), 0);
  assert.equal(strengthLevel(0), null);
});

test("the criteria add up like Bootstrap's", () => {
  assert.equal(scorePassword("abc"), 1); // lowercase
  assert.equal(scorePassword("abcdefgh"), 2); // + min length
  assert.equal(scorePassword("Abcdefgh1"), 4); // + uppercase, numbers
  assert.equal(scorePassword("Abcdefgh1!x?"), 7); // + extra length, special, multiple special
  assert.equal(scorePassword("Abcdefgh1!x?long"), 8); // + 16 characters
});

test("levels follow the thresholds", () => {
  assert.deepEqual([1, 2, 3, 4, 5, 6, 7].map((s) => strengthLevel(s)), ["weak", "weak", "fair", "fair", "good", "good", "strong"]);
  assert.equal(strengthLevel(3, [3, 5, 7]), "weak");
});

test("weights, min length and a custom scorer", () => {
  assert.equal(scorePassword("ABCDEFGH", { weights: { uppercase: 0 } }), 1);
  assert.equal(scorePassword("abcdef", { minLength: 6 }), 2);
  assert.equal(scorePassword("anything", { scorer: (p) => p.length * 10 }), 80);
});
