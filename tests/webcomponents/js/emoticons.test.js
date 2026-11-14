// Tests for the pure part of the emoticons (core/emoticons.js): which emoticon before the caret becomes which emoji.

import assert from "node:assert/strict";
import { test } from "node:test";

const { replacement } = await import("../../../webcomponents/core/emoticons.js");

test("an emoticon ending in a bracket turns at once, at the start or after a space", () => {
  assert.deepEqual(replacement(":-)"), { start: 0, end: 3, emoji: "🙂" });
  assert.deepEqual(replacement("Super ;)"), { start: 6, end: 8, emoji: "😉" });
  assert.deepEqual(replacement("ok\n:("), { start: 3, end: 5, emoji: "🙁" });
});

test("the longest emoticon wins", () => {
  assert.deepEqual(replacement("hey >:("), { start: 4, end: 7, emoji: "😠" });
  assert.deepEqual(replacement(":'("), { start: 0, end: 3, emoji: "😢" });
});

test("one that could go on as a word, path or number turns only when a space or punctuation follows", () => {
  assert.equal(replacement("so :D"), null);
  assert.deepEqual(replacement("so :D "), { start: 3, end: 5, emoji: "😃" });
  assert.deepEqual(replacement(":P!"), { start: 0, end: 2, emoji: "😛" });
  assert.equal(replacement("Wert <3"), null);
  assert.deepEqual(replacement("ich <3 "), { start: 4, end: 6, emoji: "❤️" });
  assert.equal(replacement(" :/home"), null);
});

test("not inside a word, a URL or a numbered list", () => {
  assert.equal(replacement("http:/"), null);
  assert.equal(replacement("http:// "), null);
  assert.equal(replacement("Punkt 8)"), null);
  assert.equal(replacement("abc:)"), null);
  assert.equal(replacement(""), null);
  assert.equal(replacement("nur Text "), null);
});
