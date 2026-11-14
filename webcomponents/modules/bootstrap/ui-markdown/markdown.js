/**
 * Markdown in the browser: render it (GitHub/GitLab flavoured, sanitised) and turn HTML back into Markdown.
 * The same rules as FlaskSpark's Python module flaskspark.markdown, so server and browser agree (a test compares
 * both). No DOM needed (works in node and workers too); in a browser DOMParser reads the HTML.
 *
 *   import { loadMarkdown, render, toMarkdown } from ".../ui-markdown/markdown.js";
 *   await loadMarkdown();                       // markdown-it (vendor/markdown-it), loaded on first use
 *   const html = render("**hi** [[_TOC_]]", { baseUrl: "https://git.example.com/group/project" });
 *   const text = toMarkdown(html);              // or toMarkdown(element): an element's content
 *
 * What it renders: CommonMark with tables, strikethrough, autolinks; task lists (- [ ] / - [x]), alerts
 * (> [!note] … [!caution], optional title after the marker), collapsible sections (raw <details><summary>), a table
 * of contents ([[_TOC_]] or [TOC] alone in a paragraph; headings get ids), code blocks with class="language-…"
 * (Mermaid and PlantUML stay code blocks). The result is sanitised with an allowlist (see ALLOWED_TAGS).
 */

export const ALERT_TYPES = ["note", "tip", "important", "warning", "caution"];
export const DEFAULT_ALERT_TITLES = { note: "Note", tip: "Tip", important: "Important", warning: "Warning",
  caution: "Caution" };

const MARKDOWN_IT_URL = new URL("../../../vendor/markdown-it/markdown-it.min.js", import.meta.url).href;
let markdownit = globalThis.markdownit || null;
let loading = null;

/** Loads markdown-it once (resolves when render() can be used). */
export function loadMarkdown() {
  if (markdownit) return Promise.resolve();
  loading ??= import(MARKDOWN_IT_URL).then(() => {
    markdownit = globalThis.markdownit;
    if (!markdownit) throw new Error("markdown-it did not load");
  });
  return loading;
}

/** True once render() can be used. */
export function isMarkdownLoaded() {
  return Boolean(markdownit);
}

// --- sanitiser -------------------------------------------------------------------------------------------------

export const ALLOWED_TAGS = new Set([
  "a", "abbr", "b", "blockquote", "br", "code", "dd", "del", "details", "div", "dl", "dt", "em", "h1", "h2", "h3",
  "h4", "h5", "h6", "hr", "i", "img", "input", "ins", "kbd", "li", "mark", "nav", "ol", "p", "pre", "q", "s",
  "samp", "small", "span", "strong", "sub", "summary", "sup", "table", "tbody", "td", "tfoot", "th", "thead", "tr",
  "u", "ul", "var",
]);
// Removed together with their content (other tags not allowed are unwrapped: their text stays).
const DROPPED_TAGS = new Set([
  "script", "style", "template", "iframe", "object", "embed", "svg", "math", "noscript", "textarea", "select",
  "title", "xmp", "noembed", "noframes", "head", "frameset", "frame", "applet", "audio", "video", "canvas",
]);
const HEADINGS = ["h1", "h2", "h3", "h4", "h5", "h6"];
const ALLOWED_ATTRIBUTES = {
  a: ["href", "title"],
  abbr: ["title"],
  img: ["src", "alt", "title", "width", "height"],
  input: ["type", "checked", "disabled", "class"],
  ol: ["start", "class"],
  ul: ["class"],
  li: ["class"],
  p: ["class"],
  div: ["class"],
  nav: ["class"],
  code: ["class"],
  pre: ["class"],
  th: ["style", "colspan", "rowspan"],
  td: ["style", "colspan", "rowspan"],
  details: ["open"],
  ...Object.fromEntries(HEADINGS.map((h) => [h, ["id"]])),
};
const CLASSES = {
  ul: /^contains-task-list$/,
  ol: /^contains-task-list$/,
  li: /^task-list-item$/,
  input: /^task-list-item-checkbox$/,
  div: /^markdown-alert(-(note|tip|important|warning|caution))?$/,
  p: /^markdown-alert-title$/,
  nav: /^markdown-toc$/,
  code: /^language-[A-Za-z0-9_+#.-]+$/,
  pre: /^language-[A-Za-z0-9_+#.-]+$/,
};
const LINK_SCHEMES = new Set(["http", "https", "mailto", "tel"]);
const IMAGE_SCHEMES = new Set(["http", "https"]);
const SCHEME = /^([A-Za-z][A-Za-z0-9+.-]*):/;
const ALIGN = /^\s*text-align\s*:\s*(left|right|center)\s*;?\s*$/i;
const VOID = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track",
  "wbr"]);

/** The URL as a browser reads it: tabs and line breaks inside dropped, controls and spaces around trimmed. */
function cleanUrl(url) {
  // eslint-disable-next-line no-control-regex
  return String(url ?? "").replace(/[\t\n\r]/g, "").replace(/^[\x00-\x20]+|[\x00-\x20]+$/g, "");
}

/** A relative URL (path, query or fragment), not an absolute or a protocol-relative one. */
export function isRelative(url) {
  return !SCHEME.test(url) && !/^(\/\/|\\\\|\/\\|\\\/)/.test(url);
}

/**
 * The URL of a link (kind "link") or image ("image") as it is put out, null to drop it. A relative URL (not #…)
 * gets baseUrl in front (a prefix: "/uploads/a.png" with "https://h/g/p" gives "https://h/g/p/uploads/a.png"),
 * then rewriteUrl(url, kind) may change it (null or "" drops it). Allowed: links http(s), mailto, tel, relative;
 * images http(s), relative.
 */
export function resolveUrl(value, kind, baseUrl = null, rewriteUrl = null) {
  let url = cleanUrl(value);
  if (!url && kind === "image") return null;
  if (baseUrl && url && isRelative(url) && !url.startsWith("#")) {
    url = baseUrl.replace(/\/+$/, "") + (/^[/?]/.test(url) ? "" : "/") + url;
  }
  if (rewriteUrl) {
    url = cleanUrl(rewriteUrl(url, kind) || "");
    if (!url) return null;
  }
  const match = SCHEME.exec(url);
  if (match) return (kind === "image" ? IMAGE_SCHEMES : LINK_SCHEMES).has(match[1].toLowerCase()) ? url : null;
  if (/^(\/\/|\\\\|\/\\|\\\/)/.test(url)) return url.startsWith("//") ? url : null;
  return url;
}

const escapeText = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\u00a0/g, "&nbsp;");
const escapeAttr = (s) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/\u00a0/g, "&nbsp;");

function filterAttribute(tag, name, value, options) {
  if (name === "class") {
    const pattern = CLASSES[tag];
    if (!pattern) return null;
    const kept = [...new Set(value.split(/\s+/).filter((c) => pattern.test(c)))];
    return kept.length ? kept.join(" ") : null;
  }
  if (name === "style") {
    const match = ALIGN.exec(value);
    return match ? `text-align:${match[1].toLowerCase()}` : null;
  }
  if (tag === "a" && name === "href") return resolveUrl(value, "link", options.baseUrl, options.rewriteUrl);
  if (tag === "img" && name === "src") return resolveUrl(value, "image", options.baseUrl, options.rewriteUrl);
  if (["width", "height", "start", "colspan", "rowspan"].includes(name)) {
    return /^[0-9]+$/.test(value.trim()) ? value.trim() : null;
  }
  if (name === "id") return /^[\p{L}\p{N}_-]+$/u.test(value) ? value : null;
  return value;
}

function cleanNode(node, options) {
  if (node.tag === null) return escapeText(node.text);
  const tag = node.tag;
  if (DROPPED_TAGS.has(tag)) return "";
  const inner = () => node.children.map((c) => cleanNode(c, options)).join("");
  if (!ALLOWED_TAGS.has(tag)) return inner();
  const allowed = ALLOWED_ATTRIBUTES[tag] || [];
  const forced = tag === "input" ? { type: "checkbox", disabled: "" } : tag === "a" ? { rel: "noopener noreferrer" } : {};
  const attrs = [];
  for (const [name, raw] of Object.entries(node.attrs)) { // in the source's order, like the server's sanitiser
    if (name in forced) {
      attrs.push([name, forced[name]]);
      continue;
    }
    if (!allowed.includes(name)) continue;
    const value = filterAttribute(tag, name, raw, options);
    if (value !== null && value !== undefined) attrs.push([name, value]);
  }
  for (const [name, value] of Object.entries(forced)) if (!(name in node.attrs)) attrs.push([name, value]);
  const open = `<${tag}${attrs.map(([n, v]) => ` ${n}="${escapeAttr(v)}"`).join("")}>`;
  return VOID.has(tag) ? open : `${open}${inner()}</${tag}>`;
}

/** HTML (a string or a parsed tree) reduced to the allowlist of Markdown's output. */
export function sanitize(html, options = {}) {
  const root = typeof html === "string" || html == null ? parseHtml(html || "") : html;
  return root.children.map((c) => cleanNode(c, options)).join("");
}

// --- HTML tree ---------------------------------------------------------------------------------------------------

const BLOCKS = new Set([
  "address", "article", "aside", "blockquote", "details", "dd", "div", "dl", "dt", "fieldset", "figcaption",
  "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p",
  "pre", "section", "summary", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
]);
const CLOSES = { li: ["li"], dt: ["dt", "dd"], dd: ["dt", "dd"], tr: ["tr", "td", "th"], td: ["td", "th"],
  th: ["td", "th"], thead: ["tbody", "tr", "td", "th"], tbody: ["thead", "tr", "td", "th"],
  tfoot: ["tbody", "tr", "td", "th"] };
const SKIP_CONTENT = new Set(["script", "style", "template", "head", "title", "noscript", "textarea", "select"]);
const CLOSE_STOP = new Set(["ul", "ol", "table", "blockquote", "div", "details"]);
const ENTITIES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: "\u00a0", Tab: "\t", NewLine: "\n",
  colon: ":", lpar: "(", rpar: ")", sol: "/", hellip: "\u2026", mdash: "\u2014", ndash: "\u2013", copy: "\u00a9",
  laquo: "\u00ab", raquo: "\u00bb", auml: "\u00e4", ouml: "\u00f6", uuml: "\u00fc", Auml: "\u00c4", Ouml: "\u00d6",
  Uuml: "\u00dc", eacute: "\u00e9", egrave: "\u00e8", agrave: "\u00e0" };

/** Character references decoded (numeric ones and common names). */
export function decodeEntities(text) {
  return text.replace(/&(#[xX][0-9a-fA-F]+|#[0-9]+|[A-Za-z][A-Za-z0-9]*);?/g, (all, ref) => {
    if (ref[0] === "#") {
      const code = ref[1] === "x" || ref[1] === "X" ? parseInt(ref.slice(2), 16) : parseInt(ref.slice(1), 10);
      if (!code || code > 0x10ffff || (code >= 0xd800 && code <= 0xdfff)) return "\ufffd";
      return String.fromCodePoint(code);
    }
    return ENTITIES[ref] !== undefined && (all.endsWith(";") || ["amp", "lt", "gt", "quot", "nbsp"].includes(ref))
      ? ENTITIES[ref] : all;
  });
}

const node = (tag, attrs = {}, text = "") => ({ tag, attrs, children: [], text });

/** A small, lenient HTML tree builder (for node and as a fallback without DOMParser). */
function buildTree(html) {
  const root = node("#root");
  const stack = [root];
  const top = () => stack[stack.length - 1];
  const add = (n) => top().children.push(n);
  const close = (tags) => {
    for (let i = stack.length - 1; i > 0; i--) {
      if (tags.includes(stack[i].tag)) {
        stack.length = i;
        return;
      }
      if (CLOSE_STOP.has(stack[i].tag)) return;
    }
  };
  let i = 0;
  const n = html.length;
  while (i < n) {
    const lt = html.indexOf("<", i);
    const textEnd = lt === -1 ? n : lt;
    if (textEnd > i) add(node(null, {}, decodeEntities(html.slice(i, textEnd))));
    if (lt === -1) break;
    i = lt;
    if (html.startsWith("<!--", i)) {
      const end = html.indexOf("-->", i + 4);
      i = end === -1 ? n : end + 3;
      continue;
    }
    if (html[i + 1] === "!" || html[i + 1] === "?") {
      const end = html.indexOf(">", i);
      i = end === -1 ? n : end + 1;
      continue;
    }
    const isEnd = html[i + 1] === "/";
    const nameMatch = /^[A-Za-z][^\s/>]*/.exec(html.slice(i + (isEnd ? 2 : 1)));
    if (!nameMatch) { // a lone "<": text
      add(node(null, {}, "<"));
      i += 1;
      continue;
    }
    const tag = nameMatch[0].toLowerCase();
    // the end of the tag, outside quotes
    let j = i + (isEnd ? 2 : 1) + nameMatch[0].length;
    let quote = null;
    for (; j < n; j++) {
      const c = html[j];
      if (quote) {
        if (c === quote) quote = null;
      } else if (c === '"' || c === "'") {
        quote = c;
      } else if (c === ">") {
        break;
      }
    }
    const attrText = html.slice(i + (isEnd ? 2 : 1) + nameMatch[0].length, j);
    i = j + 1;
    if (isEnd) {
      const k = stack.map((e) => e.tag).lastIndexOf(tag);
      if (k > 0) stack.length = k;
      else if (tag === "p") add(node("p")); // like a browser: a stray </p> is an empty paragraph
      else if (tag === "br") add(node("br"));
      continue;
    }
    if (SKIP_CONTENT.has(tag)) { // skipped with its content
      const end = html.toLowerCase().indexOf(`</${tag}`, i);
      if (end === -1) {
        i = n;
      } else {
        const close = html.indexOf(">", end);
        i = close === -1 ? n : close + 1;
      }
      continue;
    }
    const attrs = {};
    const re = /([^\s"'>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
    let m;
    while ((m = re.exec(attrText))) {
      const name = m[1].toLowerCase();
      if (!(name in attrs)) attrs[name] = decodeEntities(m[2] ?? m[3] ?? m[4] ?? "");
    }
    if (BLOCKS.has(tag) && top().tag === "p") stack.pop();
    if (CLOSES[tag]) close(CLOSES[tag]);
    const el = node(tag, attrs);
    add(el);
    if (!VOID.has(tag) && !/\/\s*$/.test(attrText)) stack.push(el);
  }
  return root;
}

/** A DOM node as the plain tree the converters use ({tag, attrs, children, text}; text nodes have tag null). */
export function fromDom(domNode) {
  const walk = (n) => {
    if (n.nodeType === 3) return node(null, {}, n.nodeValue);
    if (n.nodeType !== 1) return null;
    const tag = n.localName.toLowerCase();
    if (SKIP_CONTENT.has(tag)) return null;
    const attrs = {};
    for (const a of n.attributes) attrs[a.name.toLowerCase()] = a.value;
    if (tag === "input" && n.checked && n.type === "checkbox") attrs.checked = "";
    if (tag === "details" && n.open) attrs.open = attrs.open ?? "";
    const el = node(tag, attrs);
    const kids = tag === "template" ? n.content.childNodes : n.childNodes;
    for (const child of kids) {
      const c = walk(child);
      if (c) el.children.push(c);
    }
    return el;
  };
  const root = node("#root");
  const kids = domNode.nodeType === 11 || domNode.nodeType === 9 ? domNode.childNodes : domNode.childNodes;
  for (const child of kids) {
    const c = walk(child);
    if (c) root.children.push(c);
  }
  return root;
}

/** HTML as a plain tree: with DOMParser in a browser (like the server's parser), the small builder elsewhere. */
export function parseHtml(html, { native = true } = {}) {
  if (native && typeof DOMParser !== "undefined") {
    const doc = new DOMParser().parseFromString(`<!doctype html><body>${html || ""}`, "text/html");
    return fromDom(doc.body);
  }
  return buildTree(String(html || ""));
}

// --- rendering ---------------------------------------------------------------------------------------------------

const TASK = /^\[([ xX])\](?=\s|$)[ \t]?/;
const ALERT = /^\[!(note|tip|important|warning|caution)\][ \t]*([^\n]*)(?:\n|$)/i;
const TOC = /^(\[\[_TOC_\]\]|\[TOC\])$/;
const escapeHtml = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/** The id of a heading (like GitLab): lower case, letters, digits, «_» and «-» only, spaces become «-». */
export function slugify(text) {
  const kept = [...String(text).toLowerCase()].filter((c) => /[\p{L}\p{N}_\-\s]/u.test(c)).join("");
  const slug = kept.trim().replace(/\s+/g, "-").replace(/-{2,}/g, "-").replace(/^-+|-+$/g, "");
  return slug || "section";
}

function plain(inline) {
  let out = "";
  for (const child of inline.children || []) {
    if (["text", "code_inline", "text_special"].includes(child.type)) out += child.content;
    else if (child.type === "softbreak" || child.type === "hardbreak") out += " ";
    else if (child.type === "image") out += plain(child);
  }
  return out;
}

function closing(tokens, start) {
  let level = 0;
  for (let i = start; i < tokens.length; i++) {
    level += tokens[i].nesting;
    if (level === 0) return i;
  }
  return tokens.length - 1;
}

/** The table of contents: nested lists of links to the headings ([level, id, text]). */
export function tocHtml(entries) {
  if (!entries.length) return '<nav class="markdown-toc"></nav>\n';
  const out = ['<nav class="markdown-toc">'];
  const stack = [];
  for (const [level, slug, text] of entries) {
    if (!stack.length || level > stack[stack.length - 1]) {
      out.push("<ul>");
      stack.push(level);
    } else {
      out.push("</li>");
      while (stack.length > 1 && level < stack[stack.length - 1]) {
        stack.pop();
        out.push("</ul></li>");
      }
    }
    out.push(`<li><a href="#${escapeHtml(slug).replace(/"/g, "&quot;")}">${escapeHtml(text)}</a>`);
  }
  out.push("</li>");
  while (stack.length > 1) {
    stack.pop();
    out.push("</ul></li>");
  }
  out.push("</ul></nav>\n");
  return out.join("");
}

function makeMd(breaks, titles) {
  const md = markdownit("commonmark", { html: true, linkify: true, breaks });
  md.enable(["table", "strikethrough", "linkify"]);
  md.core.ruler.before("inline", "flaskspark_blocks", (state) => {
    const tokens = state.tokens;
    for (let i = 0; i < tokens.length; i++) {
      const token = tokens[i];
      if (token.type === "list_item_open" && tokens[i + 2]?.type === "inline") {
        const inline = tokens[i + 2];
        const match = TASK.exec(inline.content);
        if (match) {
          const checked = /[xX]/.test(match[1]) ? " checked" : "";
          inline.content = `<input type="checkbox" class="task-list-item-checkbox" disabled${checked}> `
            + inline.content.slice(match[0].length);
          token.attrJoin("class", "task-list-item");
          for (let j = i - 1; j >= 0; j--) {
            if (["bullet_list_open", "ordered_list_open"].includes(tokens[j].type) && tokens[j].level === token.level - 1) {
              if (!(tokens[j].attrGet("class") || "").includes("contains-task-list")) {
                tokens[j].attrJoin("class", "contains-task-list");
              }
              break;
            }
          }
        }
      } else if (token.type === "blockquote_open" && tokens[i + 1]?.type === "paragraph_open"
        && tokens[i + 2]?.type === "inline") {
        const inline = tokens[i + 2];
        const match = ALERT.exec(inline.content);
        if (match) {
          const kind = match[1].toLowerCase();
          const title = match[2].trim() || titles[kind] || DEFAULT_ALERT_TITLES[kind];
          const end = closing(tokens, i);
          token.tag = "div";
          tokens[end].tag = "div";
          token.attrSet("class", `markdown-alert markdown-alert-${kind}`);
          const heading = new state.Token("html_block", "", 0);
          heading.content = `<p class="markdown-alert-title">${escapeHtml(title)}</p>\n`;
          inline.content = inline.content.slice(match[0].length);
          if (!inline.content.trim()) tokens.splice(i + 1, 3);
          tokens.splice(i + 1, 0, heading);
        }
      }
    }
  });
  md.core.ruler.push("flaskspark_headings", (state) => {
    const tokens = state.tokens;
    const seen = new Map();
    const entries = [];
    tokens.forEach((token, i) => {
      if (token.type === "heading_open" && tokens[i + 1]) {
        const text = plain(tokens[i + 1]);
        let slug = slugify(text);
        if (seen.has(slug)) {
          seen.set(slug, seen.get(slug) + 1);
          slug = `${slug}-${seen.get(slug)}`;
        } else {
          seen.set(slug, 0);
        }
        token.attrSet("id", slug);
        entries.push([Number(token.tag[1]), slug, text]);
      }
    });
    for (let i = 0; i < tokens.length; i++) {
      if (tokens[i].type === "paragraph_open" && tokens[i + 1]?.type === "inline" && TOC.test(tokens[i + 1].content.trim())) {
        const toc = new state.Token("html_block", "", 0);
        toc.content = tocHtml(entries);
        tokens.splice(i, 3, toc);
      }
    }
  });
  return md;
}

const mdCache = new Map();

/**
 * Markdown as sanitised HTML. Needs loadMarkdown() first. Options: baseUrl, rewriteUrl(url, kind) (see
 * resolveUrl), breaks (a single line break is a <br>), alertTitles ({note: "Hinweis", …}; English otherwise).
 */
export function render(text, options = {}) {
  if (!markdownit) throw new Error("render(): call await loadMarkdown() first");
  const titles = { ...DEFAULT_ALERT_TITLES, ...(options.alertTitles || {}) };
  const key = JSON.stringify([Boolean(options.breaks), titles]);
  let md = mdCache.get(key);
  if (!md) {
    md = makeMd(Boolean(options.breaks), titles);
    mdCache.set(key, md);
  }
  return sanitize(md.render(String(text ?? "")), options);
}

/** render() after loading markdown-it. */
export async function renderAsync(text, options = {}) {
  await loadMarkdown();
  return render(text, options);
}

// --- HTML to Markdown ----------------------------------------------------------------------------------------------

const WS = /[ \t\r\n\f]+/g;
const ALNUM = /[\p{L}\p{N}]/u;

function escapeMarkdown(text) {
  let out = "";
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    const prev = text[i - 1] || "";
    const next = text[i + 1] || "";
    if ("\\`*[]".includes(c)) out += `\\${c}`;
    else if (c === "_") out += ALNUM.test(prev) && ALNUM.test(next) ? "_" : "\\_";
    else if (c === "~") out += prev === "~" || next === "~" ? "\\~" : "~";
    else if (c === "<") out += /[A-Za-z/!?]/.test(next) ? "\\<" : "<";
    else if (c === "&") out += /^#?[\p{L}\p{N}_]+;/u.test(text.slice(i + 1)) ? "\\&" : "&";
    else out += c;
  }
  return out;
}

const LINE_START = /^(#{1,6}(?=\s|$)|>|[-+](?=\s|$)|\d+(?=[.)](\s|$))|=+\s*$|-+\s*$)/;

function escapeLineStarts(text) {
  return text.split("\n").map((line) => {
    const match = LINE_START.exec(line);
    if (!match) return line;
    if (/\d/.test(match[0][0])) return `${line.slice(0, match[0].length)}\\${line.slice(match[0].length)}`;
    return `\\${line}`;
  }).join("\n");
}

const textContent = (n) => (n.tag === null ? n.text : n.children.map(textContent).join(""));
const classesOf = (n) => (n.attrs.class || "").split(/\s+/).filter(Boolean);
const hasBlocks = (n) => n.children.some((c) => c.tag !== null && BLOCKS.has(c.tag));

function fence(content) {
  const longest = Math.max(0, ...(content.match(/`+/g) || []).map((m) => m.length));
  return "`".repeat(Math.max(3, longest + 1));
}

function codeSpan(content) {
  const longest = Math.max(0, ...(content.match(/`+/g) || []).map((m) => m.length));
  const ticks = "`".repeat(longest + 1);
  const pad = /^[` ]|[` ]$/.test(content) || !content.trim() ? " " : "";
  return `${ticks}${pad}${content}${pad}${ticks}`;
}

function destination(url) {
  if (/[\s<>]/.test(url) || (url.match(/\(/g) || []).length !== (url.match(/\)/g) || []).length) {
    return `<${url.replace(/</g, "%3C").replace(/>/g, "%3E").replace(/ /g, "%20")}>`;
  }
  return url;
}

const linkTitle = (title) => (title ? ` "${title.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"` : "");

function wrap(inner, mark) {
  const stripped = inner.replace(/^ +| +$/g, "");
  if (!stripped) return inner;
  const lead = inner.slice(0, inner.length - inner.replace(/^ +/, "").length);
  const trail = inner.slice(inner.replace(/ +$/, "").length);
  return `${lead}${mark}${stripped}${mark}${trail}`;
}

const escapeHtmlText = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const escapeHtmlAttr = (s) => escapeHtmlText(s).replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
const INLINE_HTML = ["u", "ins", "sub", "sup", "kbd", "mark", "small", "abbr", "q", "samp", "var"];

class Converter {
  constructor(alertTitles) {
    this.alertTitles = alertTitles;
  }

  inline(n, table = false) {
    if (n.tag === null) return escapeMarkdown(n.text.replace(/\u00a0/g, " ").replace(WS, " "));
    const tag = n.tag;
    const inner = () => n.children.map((c) => this.inline(c, table)).join("");
    if (tag === "strong" || tag === "b") return wrap(inner(), "**");
    if (tag === "em" || tag === "i") return wrap(inner(), "*");
    if (["s", "del", "strike"].includes(tag)) return wrap(inner(), "~~");
    if (tag === "code") return codeSpan(textContent(n).replace(/\u00a0/g, " ").replace(WS, " "));
    if (tag === "br") return table ? "<br>" : "\\\n";
    if (tag === "input") return "";
    if (tag === "img") {
      const src = n.attrs["data-md-src"] || n.attrs.src || ""; // an editor keeps the original
      if (!src) return "";
      if (n.attrs.width || n.attrs.height) {
        const given = { ...n.attrs, src };
        const attrs = ["src", "alt", "title", "width", "height"].filter((k) => given[k])
          .map((k) => ` ${k}="${escapeHtmlAttr(given[k])}"`).join("");
        return `<img${attrs}>`;
      }
      const alt = (n.attrs.alt || "").replace(/\[/g, "\\[").replace(/\]/g, "\\]");
      return `![${alt}](${destination(src)}${linkTitle(n.attrs.title)})`;
    }
    if (tag === "a") {
      const href = (n.attrs["data-md-href"] || n.attrs.href || "").trim();
      const text = inner();
      const plainText = textContent(n).trim();
      if (!href) return text;
      if (n.children.every((c) => c.tag === null) && plainText
        && [plainText, `mailto:${plainText}`, `http://${plainText}`].includes(href) && !n.attrs.title
        && /^(https?|mailto):/i.test(href)) {
        return /[*_~[\]\\`<>\s]/.test(plainText) ? `<${href}>` : plainText;
      }
      return `[${text}](${destination(href)}${linkTitle(n.attrs.title)})`;
    }
    if (INLINE_HTML.includes(tag)) {
      const attr = tag === "abbr" && n.attrs.title ? ` title="${escapeHtmlAttr(n.attrs.title)}"` : "";
      return `<${tag}${attr}>${inner()}</${tag}>`;
    }
    return inner();
  }

  blocks(container) {
    const out = [];
    let buffer = [];
    const flush = () => {
      if (buffer.length) {
        const text = this.paragraph(buffer);
        if (text) out.push(["p", text]);
        buffer = [];
      }
    };
    for (const child of container.children) {
      if (child.tag !== null && BLOCKS.has(child.tag) && child.tag !== "li" && child.tag !== "summary") {
        flush();
        const text = this.block(child);
        if (text) {
          if (out.length && ["ul", "ol"].includes(child.tag) && out[out.length - 1][0] === child.tag) {
            out.push(["comment", "<!-- -->"]);
          }
          out.push([child.tag, text]);
        }
      } else if (child.tag === "li" || child.tag === "summary") {
        flush();
        for (const b of this.blocks(child)) out.push(["p", b]);
      } else {
        buffer.push(child);
      }
    }
    flush();
    return out.map(([, text]) => text);
  }

  paragraph(nodes, table = false) {
    let text = nodes.map((n) => this.inline(n, table)).join("");
    text = text.split("\n").map((line) => line.replace(/^ +| +$/g, "")).join("\n").replace(/^\n+|\n+$/g, "");
    while (text.endsWith("\\")) text = text.slice(0, -1).replace(/[\n ]+$/, "");
    return escapeLineStarts(text);
  }

  block(n) {
    const tag = n.tag;
    if (["p", "dt", "dd", "figcaption", "address"].includes(tag)) {
      return hasBlocks(n) ? this.blocks(n).join("\n\n") : this.paragraph(n.children);
    }
    if (HEADINGS.includes(tag)) {
      let text = this.paragraph(n.children).replaceAll("\\\n", " ").replaceAll("\n", " ");
      if (text.startsWith("\\#")) text = text.slice(1);
      if (text.endsWith("#")) text = `${text.slice(0, -1)}\\#`;
      return text ? `${"#".repeat(Number(tag[1]))} ${text}`.trimEnd() : "";
    }
    if (tag === "hr") return "---";
    if (tag === "pre") {
      const code = n.children.length === 1 && n.children[0].tag === "code" ? n.children[0] : null;
      const source = code || n;
      const lang = [...classesOf(source), ...classesOf(n)].find((c) => c.startsWith("language-"))?.slice(9) || "";
      let content = textContent(source).replace(/\u00a0/g, " ");
      if (content.endsWith("\n")) content = content.slice(0, -1);
      const f = fence(content);
      return `${f}${lang}\n${content}\n${f}`;
    }
    if (tag === "blockquote") return quote(this.blocks(n).join("\n\n"));
    if (tag === "ul" || tag === "ol") return this.list(n);
    if (tag === "table") return this.table(n);
    if (tag === "nav" && classesOf(n).includes("markdown-toc")) return "[[_TOC_]]";
    if (tag === "div" && classesOf(n).includes("markdown-alert")) return this.alert(n);
    if (tag === "details") return this.details(n);
    return this.blocks(n).join("\n\n");
  }

  alert(n) {
    const kind = classesOf(n).map((c) => c.slice(15)).find((c) => ALERT_TYPES.includes(c)) || "note";
    const children = [...n.children];
    let title = "";
    for (let i = 0; i < children.length; i++) {
      const child = children[i];
      if (child.tag === null && !child.text.trim()) continue;
      if (child.tag === "p" && classesOf(child).includes("markdown-alert-title")) {
        const text = textContent(child).replace(WS, " ").trim();
        const defaults = [kind, DEFAULT_ALERT_TITLES[kind].toLowerCase(), (this.alertTitles[kind] || "").toLowerCase()];
        title = defaults.includes(text.toLowerCase()) ? "" : text;
        children.splice(i, 1);
      }
      break;
    }
    const content = this.blocks({ ...node("div"), children }).join("\n\n");
    const head = `[!${kind.toUpperCase()}]${title ? ` ${title}` : ""}`;
    return quote(head + (content ? `\n${content}` : ""));
  }

  details(n) {
    const summary = n.children.find((c) => c.tag === "summary") || null;
    const content = this.blocks({ ...node("div"), children: n.children.filter((c) => c !== summary) }).join("\n\n");
    const open = "open" in n.attrs && !("data-md-closed" in n.attrs);
    const title = summary ? escapeHtmlText(textContent(summary).replace(WS, " ").trim()) : "";
    const parts = [(open ? "<details open>" : "<details>") + (summary ? `\n<summary>${title}</summary>` : "")];
    if (content) parts.push(content);
    parts.push("</details>");
    return parts.join("\n\n");
  }

  list(n) {
    const ordered = n.tag === "ol";
    const start = (n.attrs.start || "").trim();
    let number = /^[0-9]+$/.test(start) ? Number(start) : 1;
    const items = n.children.filter((c) => c.tag === "li");
    const loose = items.some((li) => li.children.some((c) => c.tag === "p"));
    const taskList = "data-task" in n.attrs;
    const out = [];
    for (const li of items) {
      const marker = ordered ? `${number}. ` : "- ";
      number += 1;
      let box = li.children.find((c) => c.tag === "input" && (c.attrs.type || "") === "checkbox") || null;
      if (!box) {
        const first = li.children.find((c) => c.tag !== null);
        if (first?.tag === "p") box = first.children.find((c) => c.tag === "input") || null;
      }
      let check = "";
      if (box) check = "checked" in box.attrs ? "[x] " : "[ ] ";
      else if (taskList || "data-checked" in li.attrs) check = li.attrs["data-checked"] === "true" ? "[x] " : "[ ] ";
      const text = this.blocks(li).join(loose ? "\n\n" : "\n");
      const lines = (check + text).split("\n");
      const indent = " ".repeat(marker.length);
      const body = [marker + lines[0], ...lines.slice(1).map((line) => (line ? indent + line : ""))].join("\n");
      out.push(body.trimEnd());
    }
    return out.join(loose ? "\n\n" : "\n");
  }

  table(n) {
    const rows = [];
    const collect = (parent) => {
      for (const child of parent.children) {
        if (child.tag === "tr") rows.push(child);
        else if (["thead", "tbody", "tfoot"].includes(child.tag)) collect(child);
      }
    };
    collect(n);
    if (!rows.length) return "";
    const cells = rows.map((row) => row.children.filter((c) => c.tag === "td" || c.tag === "th"));
    const width = Math.max(...cells.map((r) => r.length)) || 1;
    const header = cells[0];
    const aligns = [];
    for (let i = 0; i < width; i++) {
      const cell = header[i];
      const match = /text-align\s*:\s*(left|right|center)/i.exec(cell?.attrs.style || "");
      const align = match ? match[1].toLowerCase() : (cell?.attrs.align || "").toLowerCase();
      aligns.push({ left: ":---", right: "---:", center: ":---:" }[align] || "---");
    }
    const line = (row) => {
      const texts = [];
      for (let i = 0; i < width; i++) {
        if (i < row.length) {
          const text = hasBlocks(row[i])
            ? this.blocks(row[i]).map((b) => b.replaceAll("\n", " ")).join("<br>")
            : this.paragraph(row[i].children, true);
          texts.push(text.replace(/(\s*<br>)+$/, "").replaceAll("|", "\\|").replaceAll("\n", " ")); // empty cell
        } else {
          texts.push("");
        }
      }
      return `| ${texts.join(" | ")} |`;
    };
    return [line(header), `| ${aligns.join(" | ")} |`, ...cells.slice(1).map(line)].join("\n");
  }
}

function quote(text) {
  return text ? text.split("\n").map((line) => (line ? `> ${line}` : ">")).join("\n") : ">";
}

/**
 * HTML as Markdown: a string, a parsed tree or a DOM element / fragment (its content). Headings, paragraphs,
 * emphasis, strikethrough, code, links, images, lists, task lists (<input type="checkbox"> or <ul data-task> with
 * <li data-checked>), quotes, alerts, collapsible sections, tables, the table of contents. Other tags give their text.
 * Options: alertTitles (as for render(), so a default title is not written as a custom one), native (false: the
 * small parser instead of DOMParser).
 */
export function toMarkdown(html, options = {}) {
  let root;
  if (html && typeof html === "object" && "nodeType" in html) root = fromDom(html);
  else if (html && typeof html === "object" && "children" in html) root = html;
  else root = parseHtml(html || "", options);
  const converter = new Converter({ ...DEFAULT_ALERT_TITLES, ...(options.alertTitles || {}) });
  const text = converter.blocks(root).filter(Boolean).join("\n\n");
  return text.trim() ? `${text.replace(/^\n+|\n+$/g, "")}\n` : "";
}
