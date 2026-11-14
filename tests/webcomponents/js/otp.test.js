// Tests for the DOM-free helpers of the OTP input (Bootstrap 6).

import assert from "node:assert/strict";
import { test } from "node:test";

import { parseGroups, sanitizeOtp } from "../../../webcomponents/modules/bootstrap/ui-otp/otp-controller.js";

test("sanitizeOtp keeps the allowed characters up to the length", () => {
  assert.equal(sanitizeOtp("123-456", "numeric", 6), "123456");
  assert.equal(sanitizeOtp("12a3b4c5d6e7", "numeric", 6), "123456");
  assert.equal(sanitizeOtp("ab-12-cd", "alphanumeric", 6), "ab12cd");
  assert.equal(sanitizeOtp("ab12cd", "alpha", 6), "abcd");
  assert.equal(sanitizeOtp(null), "");
});

test("parseGroups reads [3,3] and 3,3", () => {
  assert.deepEqual(parseGroups("[3,3]"), [3, 3]);
  assert.deepEqual(parseGroups("2, 2, 2"), [2, 2, 2]);
  assert.equal(parseGroups(""), null);
  assert.equal(parseGroups("x"), null);
});
