import test from "node:test";
import assert from "node:assert/strict";

import {
  badgeShades, contrastRatio, contrastText, DARK_PAGE, LINE_CONTRAST, luminance, mix, mixFor, parseColor, TEXT_CONTRAST,
} from "../../../webcomponents/modules/bootstrap/ui-badge/badge-color.js";

const near = (actual, expected, delta = 1.5) =>
  actual.forEach((v, i) => assert.ok(Math.abs(v - expected[i]) <= delta, `${actual} vs ${expected}`));

test("hex and rgb as getComputedStyle gives them", () => {
  assert.deepEqual(parseColor("#428fdc"), [66, 143, 220, 1]);
  assert.deepEqual(parseColor("#FFF"), [255, 255, 255, 1]);
  assert.deepEqual(parseColor("#00000080"), [0, 0, 0, 128 / 255]);
  assert.deepEqual(parseColor("rgb(66, 143, 220)"), [66, 143, 220, 1]);
  assert.deepEqual(parseColor("rgba(0, 0, 0, 0.5)"), [0, 0, 0, 0.5]);
  assert.deepEqual(parseColor("rgb(66 143 220 / 50%)"), [66, 143, 220, 0.5]);
  assert.deepEqual(parseColor("color(srgb 1 0 0.5)"), [255, 0, 127.5, 1]);
  assert.deepEqual(parseColor("transparent"), [0, 0, 0, 0]);
});

test("oklch and oklab (color-mix results) to sRGB", () => {
  near(parseColor("oklch(0.6279 0.2577 29.23)").slice(0, 3), [255, 0, 0]);
  near(parseColor("oklch(100% 0 0)").slice(0, 3), [255, 255, 255]);
  near(parseColor("oklab(0 0 0)").slice(0, 3), [0, 0, 0]);
});

test("what it does not read", () => {
  assert.equal(parseColor(""), null);
  assert.equal(parseColor("lab(50% 40 59)"), null);
  assert.equal(parseColor("#12"), null);
  assert.equal(parseColor("not a colour"), null);
});

test("WCAG luminance and contrast", () => {
  assert.equal(luminance([255, 255, 255]), 1);
  assert.equal(luminance([0, 0, 0]), 0);
  assert.equal(contrastRatio(1, 0), 21);
  assert.ok(Math.abs(contrastRatio(luminance([118, 118, 118]), 1) - 4.54) < 0.01);
});

test("the text on the fill: white or dark, whichever contrasts more", () => {
  assert.equal(contrastText([0, 0, 0]), "light");
  assert.equal(contrastText([0x69, 0x44, 0xd3]), "light"); // a purple label
  assert.equal(contrastText([0xdc, 0x14, 0x3c]), "light"); // crimson
  assert.equal(contrastText([0xff, 0xec, 0xdb]), "dark"); // a very light label
  assert.equal(contrastText([0xf9, 0xb7, 0x1b]), "dark"); // amber
});

test("mixing toward black or white", () => {
  assert.deepEqual(mix([100, 100, 100], [0, 0, 0], 0.5), [50, 50, 50]);
  assert.deepEqual(mix([100, 100, 100], [255, 255, 255], 0), [100, 100, 100]);
  assert.equal(mixFor([0, 0, 0], [0, 0, 0], 1, TEXT_CONTRAST), 0); // black on white: nothing to do
  const amount = mixFor([0, 0, 0], [255, 255, 255], DARK_PAGE, TEXT_CONTRAST);
  assert.ok(amount > 0.3 && amount < 0.7, String(amount));
  assert.ok(contrastRatio(luminance(mix([0, 0, 0], [255, 255, 255], amount)), DARK_PAGE) >= TEXT_CONTRAST);
});

test("shades of a label colour", () => {
  // black: dark mode lightens text and line, light mode keeps it
  const black = badgeShades([0, 0, 0]);
  assert.equal(black.contrast, "light");
  assert.equal(black.textShade, "0%");
  assert.notEqual(black.textTint, "0%");
  assert.notEqual(black.lineTint, "0%");
  // a very light label: darkened for the text in light mode, enough for AA
  const light = badgeShades([0xff, 0xec, 0xdb]);
  assert.equal(light.contrast, "dark");
  const shade = parseInt(light.textShade, 10) / 100;
  assert.ok(shade >= 0.5);
  assert.ok(contrastRatio(luminance(mix([0xff, 0xec, 0xdb], [0, 0, 0], shade)), 1) >= TEXT_CONTRAST);
  assert.ok(parseInt(light.lineShade, 10) <= parseInt(light.textShade, 10));
  // the line always a little lighter in dark mode, at least 3:1
  const blue = badgeShades([0x42, 0x8f, 0xdc]);
  assert.equal(blue.lineTint, "15%");
  assert.equal(blue.edgeTint, "0%");
  assert.notEqual(black.edgeTint, "0%");
  assert.ok(contrastRatio(luminance(mix([0x42, 0x8f, 0xdc], [255, 255, 255], 0.15)), DARK_PAGE) >= LINE_CONTRAST);
});
