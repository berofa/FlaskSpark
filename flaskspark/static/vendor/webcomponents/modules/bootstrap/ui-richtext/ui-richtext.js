import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";

const svg = (path) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">${path}</svg>`;

// Bootstrap Icons 1.11 (MIT): type-bold, type-italic, type-underline, type-strikethrough, list-ul, list-ol, quote,
// link-45deg, slash-circle (unlink), eraser.
const TOOLS = [
  ["bold", "Fett (Ctrl+B)", svg('<path d="M8.21 13c2.106 0 3.412-1.087 3.412-2.823 0-1.306-.984-2.283-2.324-2.386v-.055a2.176 2.176 0 0 0 1.852-2.14c0-1.51-1.162-2.46-3.014-2.46H3.843V13zM5.908 4.674h1.696c.963 0 1.517.451 1.517 1.244 0 .834-.629 1.32-1.73 1.32H5.908V4.673zm0 6.788V8.598h1.73c1.217 0 1.88.492 1.88 1.415 0 .943-.643 1.449-1.832 1.449H5.907z"/>')],
  ["italic", "Kursiv (Ctrl+I)", svg('<path d="M7.991 11.674 9.53 4.455c.123-.595.246-.71 1.347-.807l.11-.52H7.211l-.11.52c1.06.096 1.128.212 1.005.807L6.57 11.674c-.123.595-.246.71-1.346.806l-.11.52h3.774l.11-.52c-1.06-.095-1.129-.211-1.006-.806z"/>')],
  ["underline", "Unterstrichen (Ctrl+U)", svg('<path d="M5.313 3.136h-1.23V9.54c0 2.105 1.47 3.623 3.917 3.623s3.917-1.518 3.917-3.623V3.136h-1.23v6.323c0 1.49-.978 2.57-2.687 2.57s-2.687-1.08-2.687-2.57zM12.5 15h-9v-1h9z"/>')],
  ["strikeThrough", "Durchgestrichen", svg('<path d="M6.333 5.686c0 .31.083.581.27.814H5.166a2.8 2.8 0 0 1-.099-.76c0-1.627 1.436-2.768 3.48-2.768 1.969 0 3.39 1.175 3.445 2.85h-1.23c-.11-1.08-.964-1.743-2.25-1.743-1.23 0-2.18.602-2.18 1.607zm2.194 7.478c-2.153 0-3.589-1.107-3.705-2.81h1.23c.144 1.06 1.129 1.703 2.544 1.703 1.34 0 2.31-.705 2.31-1.675 0-.827-.547-1.374-1.914-1.675L8.046 8.5H1v-1h14v1h-3.504c.468.437.675.994.675 1.697 0 1.826-1.436 2.967-3.644 2.967"/>')],
  ["insertUnorderedList", "Aufzählung", svg('<path fill-rule="evenodd" d="M5 11.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5m-3 1a1 1 0 1 0 0-2 1 1 0 0 0 0 2m0 4a1 1 0 1 0 0-2 1 1 0 0 0 0 2m0 4a1 1 0 1 0 0-2 1 1 0 0 0 0 2"/>')],
  ["insertOrderedList", "Nummerierung", svg('<path fill-rule="evenodd" d="M5 11.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5m0-4a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5"/><path d="M1.713 11.865v-.474H2c.217 0 .363-.137.363-.317 0-.185-.158-.31-.361-.31-.223 0-.367.152-.373.31h-.59c.016-.467.373-.787.986-.787.588-.002.954.291.957.703a.595.595 0 0 1-.492.594v.033a.615.615 0 0 1 .569.631c.003.533-.502.8-1.051.8-.656 0-1-.37-1.008-.794h.582c.008.178.186.306.422.309.254 0 .424-.145.422-.35-.002-.195-.155-.348-.414-.348h-.3zm-.004-4.699h-.604v-.035c0-.408.295-.844.958-.844.583 0 .96.326.96.756 0 .389-.257.617-.476.848l-.537.572v.03h1.054V9H1.143v-.395l.957-.99c.138-.142.293-.304.293-.508 0-.18-.147-.32-.342-.32a.33.33 0 0 0-.342.338zM2.564 5h-.635V2.924h-.031l-.598.42v-.567l.629-.443h.635z"/>')],
  ["quote", "Zitat", svg('<path d="M12 12a1 1 0 0 0 1-1V8.558a1 1 0 0 0-1-1h-1.388q0-.527.062-1.054.093-.558.31-.992t.559-.683q.34-.279.868-.279V3q-.868 0-1.52.372a3.3 3.3 0 0 0-1.085.992 4.9 4.9 0 0 0-.62 1.458A7.7 7.7 0 0 0 9 7.558V11a1 1 0 0 0 1 1zm-6 0a1 1 0 0 0 1-1V8.558a1 1 0 0 0-1-1H4.612q0-.527.062-1.054.094-.558.31-.992.217-.434.559-.683.34-.279.868-.279V3q-.868 0-1.52.372a3.3 3.3 0 0 0-1.085.992 4.9 4.9 0 0 0-.62 1.458A7.7 7.7 0 0 0 3 7.558V11a1 1 0 0 0 1 1z"/>')],
  ["link", "Link", svg('<path d="M4.715 6.542 3.343 7.914a3 3 0 1 0 4.243 4.243l1.828-1.829A3 3 0 0 0 8.586 5.5L8 6.086a1 1 0 0 0-.154.199 2 2 0 0 1 .861 3.337L6.88 11.45a2 2 0 1 1-2.83-2.83l.793-.792a4 4 0 0 1-.128-1.287z"/><path d="M6.586 4.672A3 3 0 0 0 7.414 9.5l.775-.776a2 2 0 0 1-.896-3.346L9.12 3.55a2 2 0 1 1 2.83 2.83l-.793.792c.112.42.155.855.128 1.287l1.372-1.372a3 3 0 1 0-4.243-4.243z"/>')],
  ["unlink", "Link entfernen", svg('<path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/><path d="M11.354 4.646a.5.5 0 0 0-.708 0l-6 6a.5.5 0 0 0 .708.708l6-6a.5.5 0 0 0 0-.708"/>')],
  ["removeFormat", "Formatierung entfernen", svg('<path d="M8.086 2.207a2 2 0 0 1 2.828 0l3.879 3.879a2 2 0 0 1 0 2.828l-5.5 5.5A2 2 0 0 1 7.879 15H5.12a2 2 0 0 1-1.414-.586l-2.5-2.5a2 2 0 0 1 0-2.828zm2.121.707a1 1 0 0 0-1.414 0L4.16 7.547l5.293 5.293 4.633-4.633a1 1 0 0 0 0-1.414zM8.746 13.547 3.453 8.254 1.914 9.793a1 1 0 0 0 0 1.414l2.5 2.5a1 1 0 0 0 .707.293H7.88a1 1 0 0 0 .707-.293z"/>')],
];
const GROUPS = [["bold", "italic", "underline", "strikeThrough"], ["insertUnorderedList", "insertOrderedList", "quote"],
  ["link", "unlink"], ["removeFormat"]];

// What stays of pasted HTML: structure and simple markup, no styles, classes, scripts or frames.
const KEEP = new Set(["P", "DIV", "BR", "B", "STRONG", "I", "EM", "U", "S", "STRIKE", "DEL", "UL", "OL", "LI", "BLOCKQUOTE",
  "A", "H1", "H2", "H3", "H4", "PRE", "CODE", "SPAN", "TABLE", "THEAD", "TBODY", "TR", "TD", "TH", "HR", "SUB", "SUP"]);
const DROP = new Set(["SCRIPT", "STYLE", "IFRAME", "OBJECT", "EMBED", "FORM", "INPUT", "BUTTON", "SELECT", "TEXTAREA",
  "META", "LINK", "HEAD", "TITLE", "SVG", "MATH", "NOSCRIPT", "TEMPLATE", "IMG", "VIDEO", "AUDIO", "CANVAS"]);

/** Pasted or given HTML reduced to what the editor keeps (links only http(s) and mailto). */
export function cleanHtml(html) {
  const doc = new DOMParser().parseFromString(`<body>${html || ""}</body>`, "text/html");
  const walk = (node) => {
    for (const child of [...node.childNodes]) {
      if (child.nodeType === Node.COMMENT_NODE) {
        child.remove();
      } else if (child.nodeType === Node.ELEMENT_NODE) {
        if (DROP.has(child.tagName)) {
          child.remove();
          continue;
        }
        walk(child);
        if (!KEEP.has(child.tagName)) {
          child.replaceWith(...child.childNodes);
          continue;
        }
        for (const attr of [...child.attributes]) {
          const keep = child.tagName === "A" && attr.name === "href" && /^(https?:|mailto:)/i.test(attr.value.trim());
          if (!keep) child.removeAttribute(attr.name);
        }
      }
    }
  };
  walk(doc.body);
  return doc.body.innerHTML;
}

// The content of the editable area is light DOM: ::slotted reaches only the area itself, so its quote, lists and
// paragraphs get their look from one style element in the document (themable through the custom properties).
const LIGHT_STYLE = `
.ui-richtext-editor p { margin: 0 0 0.5em; }
.ui-richtext-editor ul, .ui-richtext-editor ol { margin: 0 0 0.5em; padding-left: 1.5em; }
.ui-richtext-editor blockquote { margin: 0 0 0.5em; padding-left: 0.75em;
  border-left: 3px solid var(--ui-richtext-quote-border, var(--bs-border-color, #ccc));
  color: var(--ui-richtext-quote-color, var(--bs-secondary-color, #555)); }
.ui-richtext-editor a { color: var(--bs-link-color, #0d6efd); }`;

function lightStyle() {
  if (document.querySelector("style[data-ui-richtext]")) return;
  const style = document.createElement("style");
  style.dataset.uiRichtext = "";
  style.textContent = LIGHT_STYLE;
  document.head.append(style);
}

/**
 * <ui-richtext>: formatted text (bold, italic, underline, strikethrough, lists, quote, links) as a form-associated
 * custom element; the value is HTML.
 *
 * Attributes:
 * - name, value (initial HTML), label, placeholder, rows (height in lines, default 8), disabled.
 *
 * The toolbar is in the shadow tree; the editable area is a light-DOM child (a [contenteditable] in the slot), so the
 * browser's editing commands and selection work in every browser. Pasted HTML is reduced to structure and simple
 * markup (cleanHtml: no styles, classes, images, scripts). Ctrl+B/I/U as usual; «Link» asks for the address.
 *
 * Properties: value (HTML; set by script it is taken as it is, the value attribute and pasted HTML are cleaned),
 * text (the plain text), editor (the editable element), focus(), form.
 * Events: input (bubbles, from the editable area), change (bubbles) when it lost the focus after a change.
 * CSS parts: toolbar, tool, label. The editable area is styled through ::slotted from here; its content (quote,
 * lists, paragraphs) by one style element the component puts into the document (--ui-richtext-quote-border,
 * --ui-richtext-quote-color).
 */
export class UiRichtext extends ShadowComponentElement {
  static formAssociated = true;
  static stylesheet = new URL("./ui-richtext.css", import.meta.url).href;
  static observedAttributes = ["label", "placeholder", "rows", "disabled"];

  #internals;
  #editor = null;
  #pending = null; // the value set before the editor existed
  #changed = false;

  constructor() {
    super();
    this.#internals = this.attachInternals();
  }

  get editor() {
    return this.#editor;
  }

  get form() {
    return this.#internals.form;
  }

  get name() {
    return this.getAttribute("name") || "";
  }

  get value() {
    return this.#editor ? this.#editor.innerHTML : this.#pending ?? this.getAttribute("value") ?? "";
  }

  set value(html) {
    if (this.#editor) {
      this.#editor.innerHTML = String(html ?? "");
      this.#sync();
    } else {
      this.#pending = String(html ?? "");
    }
  }

  get text() {
    return this.#editor ? this.#editor.innerText : "";
  }

  focus(options) {
    this.#editor?.focus(options);
  }

  render() {
    const label = this.getAttribute("label");
    const tools = GROUPS.map((group) => `<div class="ui-richtext-group" role="group">${group.map((cmd) => {
      const [, title, icon] = TOOLS.find(([k]) => k === cmd);
      return `<button type="button" class="ui-richtext-tool" part="tool" data-cmd="${cmd}" title="${escapeHtml(title)}"
        aria-label="${escapeHtml(title)}"${this.hasAttribute("disabled") ? " disabled" : ""}>${icon}</button>`;
    }).join("")}</div>`).join("");
    return `
      ${label ? `<div class="form-label" part="label">${escapeHtml(label)}</div>` : ""}
      <div class="ui-richtext" part="frame">
        <div class="ui-richtext-toolbar" part="toolbar" role="toolbar" aria-label="Formatierung">${tools}</div>
        <slot></slot>
      </div>`;
  }

  afterRender() {
    lightStyle();
    if (!this.#editor) {
      this.#editor = this.querySelector(":scope > [contenteditable]") || document.createElement("div");
      if (!this.#editor.isConnected) {
        this.#editor.className = "ui-richtext-editor";
        // a value given by script stays as it is (the host app's own markup); the attribute's is cleaned
        this.#editor.innerHTML = this.#pending ?? cleanHtml(this.getAttribute("value") ?? "");
        this.append(this.#editor);
      }
      this.#pending = null;
      this.#editor.addEventListener("input", () => {
        this.#changed = true;
        this.#sync();
      });
      this.#editor.addEventListener("blur", () => {
        if (this.#changed) {
          this.#changed = false;
          this.dispatchEvent(new Event("change", { bubbles: true }));
        }
      });
      this.#editor.addEventListener("paste", (e) => this.#paste(e));
      this.#editor.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { // Ctrl+K: a link, as in most editors
          e.preventDefault();
          this.#run("link");
        }
      });
    }
    const rows = Math.max(2, Number(this.getAttribute("rows")) || 8);
    this.#editor.style.minHeight = `${rows * 1.5}em`;
    this.#editor.setAttribute("contenteditable", this.hasAttribute("disabled") ? "false" : "true");
    this.#editor.setAttribute("role", "textbox");
    this.#editor.setAttribute("aria-multiline", "true");
    const label = this.getAttribute("label") || this.getAttribute("aria-label");
    if (label) this.#editor.setAttribute("aria-label", label);
    if (this.hasAttribute("placeholder")) this.#editor.dataset.placeholder = this.getAttribute("placeholder");
    // the toolbar keeps the editor's selection: no focus on mousedown
    this.shadowRoot.querySelector(".ui-richtext-toolbar").addEventListener("mousedown", (e) => e.preventDefault());
    this.shadowRoot.querySelector(".ui-richtext-toolbar").addEventListener("click", (e) => {
      const tool = e.composedPath().find((n) => n instanceof Element && n.dataset?.cmd);
      if (tool) this.#run(tool.dataset.cmd);
    });
    this.#sync();
  }

  #run(cmd) {
    this.#editor.focus();
    if (cmd === "link") {
      const href = prompt("Adresse des Links (https://… oder mailto:…):", "https://");
      if (!href || !/^(https?:\/\/.+|mailto:.+)/i.test(href.trim())) return;
      if (document.getSelection()?.isCollapsed) {
        document.execCommand("insertHTML", false, `<a href="${escapeHtml(href.trim())}">${escapeHtml(href.trim())}</a>`);
      } else {
        document.execCommand("createLink", false, href.trim());
      }
    } else if (cmd === "quote") {
      this.#quote();
    } else {
      document.execCommand(cmd, false, null);
    }
    this.#changed = true;
    this.#sync();
    this.#editor.dispatchEvent(new Event("input", { bubbles: true }));
  }

  /** The blocks of the selection into a quote, or out of it when they are in one. By hand: formatBlock with
   *  «blockquote» works differently in every browser (Firefox leaves it out). */
  #quote() {
    const sel = document.getSelection();
    if (!sel?.rangeCount || !this.#editor.contains(sel.anchorNode)) return;
    const range = sel.getRangeAt(0);
    const top = (node) => { // the child of the editor the node is in
      let n = node;
      while (n && n.parentNode !== this.#editor) n = n.parentNode;
      return n;
    };
    const inside = (node) => (node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement)?.closest?.("blockquote");
    const quote = inside(range.startContainer);
    if (quote && this.#editor.contains(quote)) { // out of the quote: its content in its place
      const first = quote.firstChild;
      const last = quote.lastChild;
      quote.replaceWith(...quote.childNodes);
      if (first) {
        const r = document.createRange();
        r.setStartBefore(first);
        r.setEndAfter(last);
        sel.removeAllRanges();
        sel.addRange(r);
      }
      return;
    }
    let start = top(range.startContainer);
    let end = top(range.endContainer);
    if (!start) { // the editor itself (empty, or the cursor between its children)
      const block = document.createElement("p");
      block.innerHTML = "<br>";
      this.#editor.append(block);
      start = end = block;
    }
    const blockquote = document.createElement("blockquote");
    this.#editor.insertBefore(blockquote, start);
    for (let n = start; n; ) {
      const next = n.nextSibling;
      blockquote.append(n);
      if (n === end) break;
      n = next;
    }
    const r = document.createRange();
    r.selectNodeContents(blockquote);
    r.collapse(false);
    sel.removeAllRanges();
    sel.addRange(r);
  }

  #paste(e) {
    const html = e.clipboardData?.getData("text/html");
    const text = e.clipboardData?.getData("text/plain");
    if (!html && !text) return;
    e.preventDefault();
    const clean = html ? cleanHtml(html) : escapeHtml(text).replace(/\r?\n/g, "<br>");
    document.execCommand("insertHTML", false, clean);
  }

  #sync() {
    if (!this.#editor) return;
    this.#editor.classList.toggle("is-empty", !this.#editor.textContent.trim() && !this.#editor.querySelector("img, li, blockquote"));
    this.#internals.setFormValue(this.#editor.innerHTML);
  }

  formResetCallback() {
    if (this.#editor) {
      this.#editor.innerHTML = cleanHtml(this.getAttribute("value") || "");
      this.#sync();
    }
  }

  formDisabledCallback(disabled) {
    this.#editor?.setAttribute("contenteditable", disabled ? "false" : "true");
  }
}

registerComponent("ui-richtext", UiRichtext);
