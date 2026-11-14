import test from "node:test";
import assert from "node:assert/strict";

import { absorb, compilePlural, nt, preload, preloadCatalog, t } from "../../../flaskspark/core/web/static/flaskspark/js/i18n.js";

const RUSSIAN = "(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)";

test("plural expressions of gettext, parsed without eval", () => {
  const german = compilePlural("(n != 1)");
  assert.deepEqual([0, 1, 2, 5].map(german), [1, 0, 1, 1]);
  const french = compilePlural("(n > 1)");
  assert.deepEqual([0, 1, 2].map(french), [0, 0, 1]);
  const russian = compilePlural(RUSSIAN);
  assert.deepEqual([1, 2, 5, 11, 21, 22, 25, 111].map(russian), [0, 1, 2, 2, 0, 1, 2, 2]);
  assert.deepEqual([0, 1, 2].map(compilePlural("0")), [0, 0, 0]);
  // unreadable: English's rule, nothing evaluated
  assert.deepEqual([1, 2].map(compilePlural("alert(1)")), [0, 1]);
  assert.deepEqual([1, 2].map(compilePlural("(n != ")), [0, 1]);
});

test("t() and nt() without a catalogue: the source texts, English's plural", () => {
  assert.equal(t("Never translated {x}", { x: 1 }), "Never translated 1");
  assert.equal(nt("{n} apple", "{n} apples", 1), "1 apple");
  assert.equal(nt("{n} apple", "{n} apples", 3), "3 apples");
  assert.equal(nt("{num} pear", "{num} pears", 2), "2 pears");
});

test("a catalogue (the page's or the server's): texts, plural forms and the language's rule", () => {
  absorb({
    language: "ru",
    plural: RUSSIAN,
    texts: { Saved: "Сохранено" },
    plurals: { "{n} file": ["{n} файл", "{n} файла", "{n} файлов"] },
  });
  assert.equal(t("Saved"), "Сохранено");
  assert.equal(nt("{n} file", "{n} files", 1), "1 файл");
  assert.equal(nt("{n} file", "{n} files", 3), "3 файла");
  assert.equal(nt("{n} file", "{n} files", 5), "5 файлов");
  assert.equal(nt("{n} file", "{n} files", 5, { n: "five" }), "five файлов");
  absorb({ plural: "(n != 1)" });
});

test("preloadCatalog() asks once per part; preload() single texts and plurals", async () => {
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push([url, options.body ? JSON.parse(options.body) : null]);
    if (url.startsWith("/api/i18n/catalog?")) {
      return { ok: true, json: async () => ({ plural: "(n != 1)", texts: { Calendar: "Kalender" }, plurals: {} }) };
    }
    if (url === "/api/i18n/catalog") {
      return { ok: true, json: async () => ({ plural: "(n != 1)", texts: { Day: "Tag" }, plurals: { "{n} day": ["{n} Tag", "{n} Tage"] } }) };
    }
    return { ok: true, json: async () => ({ Week: "Woche" }) };
  };
  await preloadCatalog("calendar");
  await preloadCatalog(["calendar"]);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "/api/i18n/catalog?modules=calendar");
  assert.equal(t("Calendar"), "Kalender");

  await preload(["Week"]);
  assert.equal(calls.at(-1)[0], "/api/i18n");
  assert.deepEqual(calls.at(-1)[1], { keys: ["Week"] });
  assert.equal(t("Week"), "Woche");

  await preload(["Day", ["{n} day", "{n} days"]]);
  assert.equal(calls.at(-1)[0], "/api/i18n/catalog");
  assert.deepEqual(calls.at(-1)[1], { keys: ["Day"], plurals: [["{n} day", "{n} days"]] });
  assert.equal(t("Day"), "Tag");
  assert.equal(nt("{n} day", "{n} days", 2), "2 Tage");

  const before = calls.length;
  await preload(["Day", "Week", ["{n} day", "{n} days"]]);
  assert.equal(calls.length, before);

  globalThis.fetch = async () => { throw new Error("offline"); };
  await preload(["Offline text"]);
  await preloadCatalog("other");
  assert.equal(t("Offline text"), "Offline text");
  delete globalThis.fetch;
});
