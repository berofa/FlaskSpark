// Tests for webcomponents/core/files.js (accept filter of ui-dropzone).

import assert from "node:assert/strict";
import { test } from "node:test";

import { acceptsFile, formatSize, parseSize, selectFiles } from "../../../webcomponents/core/files.js";

const jpg = { name: "Foto.JPG", type: "image/jpeg" };
const pdf = { name: "Quittung.pdf", type: "application/pdf" };
const heic = { name: "IMG_0001.HEIC", type: "" };

test("everything without an accept list", () => {
  assert.ok(acceptsFile("", jpg) && acceptsFile(null, pdf));
});

test("wildcard types, exact types and extensions, case-insensitive", () => {
  assert.ok(acceptsFile("image/*", jpg));
  assert.ok(!acceptsFile("image/*", pdf));
  assert.ok(acceptsFile("video/*, application/pdf", pdf));
  assert.ok(acceptsFile("image/*,.heic", heic));
  assert.ok(!acceptsFile("image/*", heic));
  assert.ok(acceptsFile(".jpg", jpg));
});

test("parseSize reads bytes and units", () => {
  assert.equal(parseSize("500"), 500);
  assert.equal(parseSize("2KB"), 2048);
  assert.equal(parseSize("1.5 mb"), 1572864);
  assert.equal(parseSize(""), null);
  assert.equal(parseSize("big"), null);
});

test("formatSize is readable", () => {
  assert.equal(formatSize(512), "512 B");
  assert.equal(formatSize(1536), "1.5 KB");
  assert.equal(formatSize(12 * 1024 ** 2), "12 MB");
});

test("selectFiles rejects by type, size and count", () => {
  const files = [
    { name: "a.png", type: "image/png", size: 10 },
    { name: "b.pdf", type: "application/pdf", size: 10 },
    { name: "c.png", type: "image/png", size: 5000 },
    { name: "d.png", type: "image/png", size: 10 },
    { name: "e.png", type: "image/png", size: 10 },
  ];
  const { accepted, rejected } = selectFiles(files, { accept: "image/*", maxSize: 1000, maxFiles: 3, multiple: true, existing: 1 });
  assert.deepEqual(accepted.map((f) => f.name), ["a.png", "d.png"]);
  assert.deepEqual(rejected.map((r) => `${r.file.name}:${r.reason}`), ["b.pdf:type", "c.png:size", "e.png:count"]);
  assert.deepEqual(selectFiles(files.slice(0, 2), {}).accepted.map((f) => f.name), ["a.png"]);
});
