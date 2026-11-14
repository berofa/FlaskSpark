// Tests for webcomponents/modules/bootstrap/ui-markdown/markdown.js: rendering, sanitising (XSS), HTML back to
// Markdown and the roundtrip. The cases are shared with tests/test_markdown.py (flaskspark.markdown), so the
// browser and the server give the same results.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const m = await import("../../../webcomponents/modules/bootstrap/ui-markdown/markdown.js");
await m.loadMarkdown();
const CASES = JSON.parse(readFileSync(new URL("../fixtures/markdown_cases.json", import.meta.url), "utf8"));

const options = (o) => {
  const out = { baseUrl: o?.base_url, breaks: o?.breaks, alertTitles: o?.alert_titles };
  if (o?.rewrite === "javascript") out.rewriteUrl = () => "javascript:alert(1)";
  return out;
};

for (const c of CASES.render) {
  test(`render: ${c.name}`, () => {
    const html = m.render(c.md, options(c.options));
    for (const part of c.contains || []) assert.ok(html.includes(part), `${part}\n${html}`);
    for (const part of c.absent || []) assert.ok(!html.includes(part), `${part}\n${html}`);
  });
}

const ATTRIBUTES = {
  a: ["href", "title", "rel"], abbr: ["title"], img: ["src", "alt", "title", "width", "height"],
  input: ["type", "checked", "disabled", "class"], ol: ["start", "class"], ul: ["class"], li: ["class"], p: ["class"],
  div: ["class"], nav: ["class"], code: ["class"], pre: ["class"], th: ["style", "colspan", "rowspan"],
  td: ["style", "colspan", "rowspan"], details: ["open"], h1: ["id"], h2: ["id"], h3: ["id"], h4: ["id"], h5: ["id"],
  h6: ["id"],
};

function assertSafe(html) {
  assert.ok(!/<\s*(script|style|iframe|object|embed|svg|math|form|meta|base|button|textarea)/i.test(html), html);
  const walk = (n) => {
    for (const child of n.children) {
      if (child.tag === null) continue;
      assert.ok(m.ALLOWED_TAGS.has(child.tag), child.tag);
      for (const [name, value] of Object.entries(child.attrs)) {
        assert.ok(!name.startsWith("on"), name);
        assert.ok((ATTRIBUTES[child.tag] || []).includes(name), `${child.tag} ${name}`);
        if (name === "style") assert.match(value, /^text-align:(left|right|center)$/);
        if (name === "href" || name === "src") {
          const scheme = /^([a-z][a-z0-9+.-]*):/i.exec(value.trim());
          const allowed = name === "src" ? ["http", "https"] : ["http", "https", "mailto", "tel"];
          assert.ok(!scheme || allowed.includes(scheme[1].toLowerCase()), value);
        }
      }
      if (child.tag === "input") assert.ok(child.attrs.type === "checkbox" && "disabled" in child.attrs);
      walk(child);
    }
  };
  walk(m.parseHtml(html, { native: false }));
}

for (const c of CASES.xss) {
  test(`xss: ${c.name}`, () => assertSafe(m.render(c.md, options(c.options))));
}

test("sanitize: raw HTML is reduced, checkboxes are disabled, links get rel", () => {
  const html = m.sanitize('<input type="text" value="y"><a href="/x" rel="opener" target="_blank">x</a>'
    + '<div class="btn markdown-alert" onclick="x()">y</div>');
  assert.equal(html, '<input type="checkbox" disabled=""><a href="/x" rel="noopener noreferrer">x</a>'
    + '<div class="markdown-alert">y</div>');
});

test("resolveUrl: base URL as a prefix, the hook, allowed schemes", () => {
  assert.equal(m.resolveUrl("/uploads/a.png", "image", "https://h/g/p/"), "https://h/g/p/uploads/a.png");
  assert.equal(m.resolveUrl("a.png", "image", "https://h/g/p"), "https://h/g/p/a.png");
  assert.equal(m.resolveUrl("#x", "link", "https://h/g/p"), "#x");
  assert.equal(m.resolveUrl("mailto:a@b.ch", "image"), null);
  assert.equal(m.resolveUrl("data:image/png;base64,AA", "image"), null);
  assert.equal(m.resolveUrl(" java\tscript:alert(1)", "link"), null);
  assert.equal(m.resolveUrl("https://o/a.png", "image", null, (url) => `/proxy?u=${url}`), "/proxy?u=https://o/a.png");
  assert.equal(m.resolveUrl("https://o/a.png", "image", null, () => null), null);
});

test("slugify", () => {
  assert.equal(m.slugify("Über uns!"), "über-uns");
  assert.equal(m.slugify("  a -- b  "), "a-b");
  assert.equal(m.slugify("snake_case 2"), "snake_case-2");
  assert.equal(m.slugify("???"), "section");
});

for (const md of CASES.roundtrip) {
  test(`roundtrip: ${JSON.stringify(md).slice(0, 60)}`, () => assert.equal(m.toMarkdown(m.render(md)), md));
}

for (const c of CASES.to_markdown) {
  test(`toMarkdown: ${c.name}`, () => assert.equal(m.toMarkdown(c.html, options(c.options)), c.md));
}

test("toMarkdown takes a parsed tree as well", () => {
  assert.equal(m.toMarkdown(m.parseHtml("<p><b>x</b></p>")), "**x**\n");
});

test("render needs markdown-it, which loads once", async () => {
  assert.ok(m.isMarkdownLoaded());
  await m.loadMarkdown();
  assert.equal(await m.renderAsync("*a*"), "<p><em>a</em></p>\n");
});
