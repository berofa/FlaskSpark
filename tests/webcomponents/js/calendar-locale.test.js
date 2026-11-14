// Tests for webcomponents/modules/calendar/ui-calendar/locale.js (date locale and first day of the week).

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  canonicalLocale,
  firstDayOf,
  localeFirstDay,
  parseFirstDay,
} from "../../../webcomponents/modules/calendar/ui-calendar/locale.js";

test("canonicalises the language tag and falls back to en", () => {
  assert.equal(canonicalLocale("en-ch"), "en-CH");
  assert.equal(canonicalLocale("de_CH"), "de-CH");
  assert.equal(canonicalLocale(""), "en");
  assert.equal(canonicalLocale("not a tag!"), "en");
});

test("Monday first for de, en-GB, de-CH and en-CH; Sunday for en and en-US", () => {
  for (const tag of ["de", "de-CH", "en-GB", "en-CH", "fr-CH"]) assert.equal(localeFirstDay(tag), 1, tag);
  for (const tag of ["en", "en-US"]) assert.equal(localeFirstDay(tag), 0, tag);
});

test("the attribute first-day: numbers and weekday names, invalid ones ignored", () => {
  assert.equal(parseFirstDay("1"), 1);
  assert.equal(parseFirstDay("0"), 0);
  assert.equal(parseFirstDay("7"), 0);
  assert.equal(parseFirstDay("Monday"), 1);
  assert.equal(parseFirstDay("sat"), 6);
  assert.equal(parseFirstDay("8"), null);
  assert.equal(parseFirstDay("mo"), null);
  assert.equal(parseFirstDay(null), null);
});

test("the attribute wins over the locale", () => {
  assert.equal(firstDayOf("sunday", "de-CH"), 0);
  assert.equal(firstDayOf(null, "en-CH"), 1);
  assert.equal(firstDayOf("", "en-US"), 0);
});

test("the full locale gives day and month in its order (en-CH and en-GB not as in the US)", () => {
  const day = new Date(2026, 10, 4);
  const format = (tag) => new Intl.DateTimeFormat(canonicalLocale(tag), { day: "2-digit", month: "2-digit" }).format(day);
  assert.equal(format("en-GB"), "04/11");
  assert.equal(format("en-US"), "11/04");
  assert.notEqual(format("en-CH"), format("en-US"));
});
