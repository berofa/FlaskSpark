import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { SharedShadowStyles } from "../../../core/shared-shadow-styles.js";
import { escapeHtml } from "../../../core/escape.js";
import { placeAligned } from "../../../core/placement.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";
import {
  ALERT_TYPES, isRelative, loadMarkdown, render, resolveUrl, sanitize, parseHtml, slugify, toMarkdown, tocHtml,
} from "../ui-markdown/markdown.js";
import {
  DEFAULT_LABELS, addCommand, attachmentMarkdown, builtinMarkdown, filterCommands, format, insertBlock, insertLink,
  insertText, menuCommands, normalizeCommand, removeCommand, tableHtml, toggleWrap,
} from "./editor-commands.js";
import { icon } from "./editor-icons.js";

const MARKDOWN_BODY = new URL("../ui-markdown/markdown-body.css", import.meta.url).href;
const HEADINGS = ["h1", "h2", "h3", "h4", "h5", "h6"];
const TASK_LI = "ul[data-task] > li";
const TABLE_PICKER = [8, 6]; // columns × rows of the table picker
// Tools of the toolbar: [id, label key, icon]; groups separated. «md»: also shown in the Markdown mode.
const TOOL_GROUPS = [
  [["bold", "bold", "type-bold", "md"], ["italic", "italic", "type-italic", "md"],
    ["strike", "strike", "type-strikethrough", "md"]],
  [["quote", "quote", "quote"], ["code", "code", "code", "md"], ["link", "link", "link-45deg", "md"]],
  [["bullets", "bullets", "list-ul"], ["numbers", "numbers", "list-ol"], ["tasks", "tasks", "list-check"]],
  [["table", "table", "table"], ["attach", "attach", "paperclip", "md"], ["more", "more", "plus-lg"]],
];
const TABLE_TOOLS = [["row-add", "arrow-bar-down"], ["column-add", "arrow-bar-right"], ["row-delete", "dash-square"],
  ["column-delete", "dash-square"], ["table-delete", "trash"]];
const WRAP = { bold: "**", italic: "*", strike: "~~", code: "`" };
const EXEC = { bold: "bold", italic: "italic", strike: "strikeThrough", bullets: "insertUnorderedList",
  numbers: "insertOrderedList" };

const iconMarkup = (name) => (String(name || "").trim().startsWith("<") ? name : icon(name));

/**
 * <ui-markdown-editor>: a text field for Markdown with two modes: «Text» (formatted, like a word processor) and
 * «Markdown» (the source in a monospace textarea). The value is always Markdown; the conversion follows the same
 * rules as flaskspark.markdown on the server (ui-markdown/markdown.js).
 *
 * Toolbar (text mode, the scope of GitLab's editor): text style (normal text, heading 1–6), bold, italic,
 * strikethrough, quote, inline code, link (a small dialog), bulleted, numbered and task list, table (rows ×
 * columns; inside a table: add/delete rows and columns), attachment, «+» (alerts, code block, collapsible section,
 * horizontal line, table of contents and the page's commands). «/» at the start of a line or after a space opens the
 * command menu (type to filter, arrows, Enter). Markdown mode: a slim toolbar (bold, italic, strikethrough, code,
 * link, attachment) and Ctrl+B / Ctrl+I / Ctrl+K. No Mermaid or PlantUML: they stay code blocks.
 *
 * Attributes: name, value (initial Markdown), label, help, placeholder, rows (minimum height in lines, default 8),
 * required, disabled, readonly, error (a message shown as invalid), mode ("text" | "markdown"), base-url (prefix
 * of relative links and images while showing them; the Markdown keeps them as written), breaks, labels (JSON:
 * texts by key, see DEFAULT_LABELS in editor-commands.js; English otherwise).
 *
 * Properties: value (Markdown), mode, labels, uploadHandler(file) -> Promise<{url, name}>, rewriteUrl(url, kind),
 * form, validity, focus(), addCommand({...}), removeCommand(id), insertMarkdown(text).
 * Static: UiMarkdownEditor.addCommand({...}) / removeCommand(id) for every editor of the page.
 * Command: { id, label, icon (name or SVG), menus: ["slash", "plus"], keywords, markdown (text or
 *   (editor) => text, inserted at the cursor) or run(editor) }.
 *
 * Events: input, change (bubbles; change after leaving the field), ui-markdown-editor:mode {mode},
 * ui-markdown-editor:attach {file, insert({url, name})} (cancelable: preventDefault() and call insert() later
 * to upload yourself; without it uploadHandler is used), ui-markdown-editor:upload-error {file, error}.
 * Files can also be dropped or pasted into the field.
 *
 * CSS parts: field, label, frame, toolbar, group, tool, modes, mode, source, menu, help, feedback.
 * Tokens: --ui-markdown-editor-* (ui-markdown-editor.css) and --ui-markdown-* (typography, markdown-body.css).
 * The editable text is a light-DOM child (contenteditable; the browser's editing commands do not work reliably in a
 * shadow tree), styled by markdown-body.css and ui-markdown-editor.document.css.
 */
export class UiMarkdownEditor extends ShadowComponentElement {
  static formAssociated = true;
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-markdown-editor.css", import.meta.url).href];
  static documentStylesheet = new URL("./ui-markdown-editor.document.css", import.meta.url).href;
  static observedAttributes = ["label", "help", "placeholder", "rows", "disabled", "readonly", "required", "error",
    "mode", "labels"];

  static addCommand(command) {
    return addCommand(command);
  }

  static removeCommand(id) {
    removeCommand(id);
  }

  /** A command for this editor only. */
  addCommand(command) {
    const cmd = normalizeCommand(command);
    this.#commands = [...this.#commands.filter((c) => c.id !== cmd.id), cmd];
    return cmd;
  }

  removeCommand(id) {
    this.#commands = this.#commands.filter((c) => c.id !== id);
  }

  /** (file) -> Promise<{url, name}>: uploads an attachment (used unless an attach listener prevents it). */
  uploadHandler = null;

  #internals;
  #text = null; // the editable element (light DOM)
  #markdown = null; // the value (null: the value attribute)
  #mode = null;
  #labels = null;
  #commands = [];
  #rewriteUrl = null;
  #loaded = false;
  #filled = false; // the text mode shows the current value
  #changed = false;
  #formDisabled = false;
  #range = null; // the selection saved while a menu or dialog is open
  #slash = null; // {node, offset} of the «/» while its menu is open
  #menuItems = [];
  #menuIndex = 0;
  #onSelection = () => this.#updateTools();
  #onOutside = (e) => {
    const path = e.composedPath();
    for (const pop of this.shadowRoot?.querySelectorAll(".ui-mde-pop:popover-open") || []) {
      if (!path.includes(pop) && !path.includes(this.#anchorOf(pop))) this.#close(pop);
    }
  };

  constructor() {
    super();
    this.#internals = this.attachInternals();
  }

  // --- properties --------------------------------------------------------------------------------------------------

  get value() {
    if (this.#markdown === null) return this.getAttribute("value") ?? "";
    return this.#markdown;
  }

  set value(text) {
    this.#markdown = String(text ?? "");
    this.#filled = false;
    const source = this.#source;
    if (source) source.value = this.#markdown;
    if (this.mode === "text") this.#fill();
    this.#sync();
  }

  get mode() {
    return this.#mode ?? (this.getAttribute("mode") === "markdown" ? "markdown" : "text");
  }

  set mode(mode) {
    this.#switch(mode === "markdown" ? "markdown" : "text");
  }

  get labels() {
    let fromAttribute = {};
    try {
      fromAttribute = JSON.parse(this.getAttribute("labels") || "{}");
    } catch {
      fromAttribute = {};
    }
    return { ...DEFAULT_LABELS, ...fromAttribute, ...(this.#labels || {}) };
  }

  set labels(labels) {
    this.#labels = labels && typeof labels === "object" ? { ...labels } : null;
    this.requestRender();
  }

  get rewriteUrl() {
    return this.#rewriteUrl;
  }

  set rewriteUrl(fn) {
    this.#rewriteUrl = typeof fn === "function" ? fn : null;
    this.#filled = false;
    if (this.mode === "text") this.#fill();
  }

  get editor() {
    return this.#text;
  }

  get form() {
    return this.#internals.form;
  }

  get name() {
    return this.getAttribute("name") || "";
  }

  get validity() {
    return this.#internals.validity;
  }

  checkValidity() {
    return this.#internals.checkValidity();
  }

  reportValidity() {
    return this.#internals.reportValidity();
  }

  focus(options) {
    (this.mode === "markdown" ? this.#source : this.#text)?.focus(options);
  }

  /** Markdown inserted at the cursor (rendered in the text mode). */
  insertMarkdown(text) {
    if (this.mode === "markdown") {
      this.#editSource((v, s, e) => insertBlock(v, s, e, String(text)));
    } else {
      this.#restore();
      this.#insertHtml(this.#prepare(render(String(text), this.#renderOptions())));
    }
  }

  get #source() {
    return this.shadowRoot?.querySelector(".ui-mde-source") ?? null;
  }

  get #disabled() {
    return this.hasAttribute("disabled") || this.#formDisabled;
  }

  get #readonly() {
    return this.#disabled || this.hasAttribute("readonly");
  }

  #alertTitles() {
    const labels = this.labels;
    return Object.fromEntries(ALERT_TYPES.map((k) => [k, labels[`alert-${k}`]]));
  }

  #renderOptions() {
    return { breaks: this.hasAttribute("breaks"), alertTitles: this.#alertTitles() };
  }

  // --- lifecycle ---------------------------------------------------------------------------------------------------

  connectedCallback() {
    super.connectedCallback();
    SharedShadowStyles.applyToDocument(MARKDOWN_BODY);
    document.addEventListener("selectionchange", this.#onSelection);
    document.addEventListener("pointerdown", this.#onOutside, true);
  }

  disconnectedCallback() {
    document.removeEventListener("selectionchange", this.#onSelection);
    document.removeEventListener("pointerdown", this.#onOutside, true);
  }

  render() {
    const L = this.labels;
    const label = this.getAttribute("label");
    const help = this.getAttribute("help");
    const error = this.getAttribute("error");
    const markdown = this.mode === "markdown";
    const off = this.#readonly ? " disabled" : "";
    const tool = ([id, key, name, md]) => (markdown && !md ? "" : `<button type="button" class="btn-icon btn-sm btn-text ui-mde-tool" `
      + `part="tool" data-cmd="${id}" title="${escapeHtml(L[key])}" aria-label="${escapeHtml(L[key])}"${off}`
      + `${id === "more" || id === "table" ? ' aria-haspopup="menu"' : ""}>${icon(name)}</button>`);
    const groups = TOOL_GROUPS.map((group) => group.map(tool).join("")).filter(Boolean)
      .map((html) => `<div class="ui-mde-group" part="group" role="group">${html}</div>`).join("");
    const formatButton = markdown ? "" : `<div class="ui-mde-group" part="group"><button type="button" `
      + `class="btn btn-sm btn-text ui-mde-format" part="tool" data-cmd="format" aria-haspopup="menu" `
      + `title="${escapeHtml(L.format)}"${off}><span class="ui-mde-format-label">${escapeHtml(L.paragraph)}</span>`
      + `${icon("chevron-down")}</button></div>`;
    const tableTools = markdown ? "" : `<div class="ui-mde-group ui-mde-table-tools" part="group" role="group" hidden>${
      TABLE_TOOLS.map(([id, name]) => `<button type="button" class="btn-icon btn-sm btn-text ui-mde-tool" part="tool" `
        + `data-cmd="${id}" title="${escapeHtml(L[id])}" aria-label="${escapeHtml(L[id])}"${off}>${icon(name)}</button>`).join("")}</div>`;
    const modes = `<div class="ui-mde-modes" part="modes" role="group" aria-label="${escapeHtml(L.mode)}">${
      ["text", "markdown"].map((m) => `<button type="button" class="ui-mde-mode" part="mode" data-mode="${m}" `
        + `title="${escapeHtml(L[`mode-${m}`])}" aria-label="${escapeHtml(L[`mode-${m}`])}" `
        + `aria-pressed="${this.mode === m}"${this.#disabled ? " disabled" : ""}>${icon(m === "text" ? "type" : "markdown")}`
        + `<span>${escapeHtml(L[`mode-${m}`])}</span></button>`).join("")}</div>`;
    const rows = Math.max(2, Number(this.getAttribute("rows")) || 8);
    const placeholder = this.getAttribute("placeholder");
    const source = `<textarea class="ui-mde-source" part="source" spellcheck="true" rows="${rows}"`
      + `${placeholder ? ` placeholder="${escapeHtml(placeholder)}"` : ""}${this.#disabled ? " disabled" : ""}`
      + `${this.hasAttribute("readonly") ? " readonly" : ""}${label ? ` aria-label="${escapeHtml(label)}"` : ""}`
      + `${markdown ? "" : " hidden"}></textarea>`;
    const picker = Array.from({ length: TABLE_PICKER[1] }, (_, r) => Array.from({ length: TABLE_PICKER[0] }, (__, c) => {
      const text = format(L["table-size"], { columns: c + 1, rows: r + 1 });
      return `<button type="button" class="ui-mde-cell" data-columns="${c + 1}" data-rows="${r + 1}" title="${escapeHtml(text)}" `
        + `aria-label="${escapeHtml(text)}"></button>`;
    }).join("")).join("");
    return `<div class="form-field" part="field">`
      + `${label ? `<div class="form-label" part="label">${escapeHtml(label)}</div>` : ""}`
      + `<div class="ui-mde${error ? " is-invalid" : ""}${this.#disabled ? " is-disabled" : ""}" part="frame" data-mode="${this.mode}">`
      + `<div class="ui-mde-toolbar" part="toolbar" role="toolbar" aria-label="${escapeHtml(L.toolbar)}">`
      + `${formatButton}${groups}${tableTools}<span class="ui-mde-spacer"></span>${modes}</div>`
      + `<div class="ui-mde-body"><slot></slot>${source}</div>`
      + `<div class="ui-mde-status" part="status" aria-live="polite" hidden></div></div>`
      + `${help ? `<div class="form-text" part="help">${escapeHtml(help)}</div>` : ""}`
      + `<div class="invalid-feedback" part="feedback"${error ? ' style="display: block"' : ""}>${escapeHtml(error || "")}</div></div>`
      + `<div class="menu ui-mde-pop" part="menu" popover="manual" role="menu" data-pop="format"></div>`
      + `<div class="menu ui-mde-pop" part="menu" popover="manual" role="menu" data-pop="more"></div>`
      + `<div class="menu ui-mde-pop" part="menu" popover="manual" role="listbox" data-pop="slash" aria-label="${escapeHtml(L.commands)}"></div>`
      + `<div class="menu ui-mde-pop ui-mde-picker" part="menu" popover="manual" data-pop="table">`
      + `<div class="ui-mde-grid" style="--columns: ${TABLE_PICKER[0]}">${picker}</div><div class="ui-mde-size"></div></div>`
      + `<form class="menu ui-mde-pop ui-mde-dialog" part="menu" popover="manual" data-pop="ask"></form>`
      + `<input type="file" class="ui-mde-file" multiple hidden>`;
  }

  afterRender() {
    if (!this.#text) {
      this.#text = this.querySelector(":scope > .ui-markdown-editor-text") || document.createElement("div");
      this.#text.className = "markdown-body ui-markdown-editor-text";
      if (!this.#text.isConnected) this.append(this.#text);
      this.#wireText();
    }
    const rows = Math.max(2, Number(this.getAttribute("rows")) || 8);
    this.style.setProperty("--ui-markdown-editor-rows", String(rows));
    this.#text.setAttribute("contenteditable", this.#readonly ? "false" : "true");
    this.#text.setAttribute("role", "textbox");
    this.#text.setAttribute("aria-multiline", "true");
    this.#text.hidden = this.mode === "markdown";
    const label = this.getAttribute("label") || this.getAttribute("aria-label");
    if (label) this.#text.setAttribute("aria-label", label);
    if (this.hasAttribute("placeholder")) this.#text.dataset.placeholder = this.getAttribute("placeholder");
    const source = this.#source;
    source.value = this.value;
    this.#wireShadow();
    if (!this.#loaded) {
      loadMarkdown().then(() => {
        this.#loaded = true;
        this.#fill();
        this.#sync();
      });
    } else {
      this.#fill();
    }
    this.#sync();
  }

  formResetCallback() {
    this.#markdown = null;
    this.#filled = false;
    if (this.#source) this.#source.value = this.value;
    this.#fill();
    this.#sync();
  }

  formDisabledCallback(disabled) {
    this.#formDisabled = disabled;
    this.requestRender();
  }

  // --- text mode: content ----------------------------------------------------------------------------------------

  /** The text mode shows the value (once markdown-it is there). */
  #fill() {
    if (!this.#loaded || !this.#text || this.#filled || this.mode !== "text") return;
    this.#text.innerHTML = this.#prepare(render(this.value, this.#renderOptions()));
    this.#filled = true;
    this.#sync();
  }

  /**
   * Rendered HTML made editable: task lists as <ul data-task> with <li data-checked> (the boxes are drawn), closed
   * sections open while editing (data-md-closed keeps that they were closed), the table of contents not editable,
   * relative links and images shown with base-url (data-md-src / data-md-href keep the original).
   */
  #prepare(html) {
    const template = document.createElement("template");
    template.innerHTML = html;
    const root = template.content;
    for (const list of root.querySelectorAll("ul.contains-task-list, ol.contains-task-list")) {
      list.setAttribute("data-task", "");
      list.removeAttribute("class");
      for (const li of list.children) {
        const box = li.querySelector(":scope > input, :scope > p > input");
        if (box) {
          li.setAttribute("data-checked", String(box.hasAttribute("checked")));
          const next = box.nextSibling;
          if (next?.nodeType === Node.TEXT_NODE) next.nodeValue = next.nodeValue.replace(/^ /, "");
          box.remove();
        } else {
          li.setAttribute("data-checked", "false");
        }
        li.removeAttribute("class");
      }
    }
    for (const details of root.querySelectorAll("details:not([open])")) {
      details.setAttribute("open", "");
      details.setAttribute("data-md-closed", "");
    }
    for (const toc of root.querySelectorAll("nav.markdown-toc")) toc.setAttribute("contenteditable", "false");
    const base = this.getAttribute("base-url");
    for (const [selector, attr, kind] of [["img[src]", "src", "image"], ["a[href]", "href", "link"]]) {
      for (const el of root.querySelectorAll(selector)) {
        const original = el.getAttribute(attr);
        const shown = resolveUrl(original, kind, isRelative(original) ? base : null, this.#rewriteUrl);
        if (shown !== original) {
          el.setAttribute(`data-md-${attr}`, original);
          if (shown) el.setAttribute(attr, shown);
        }
      }
    }
    return template.innerHTML;
  }

  /** The Markdown of the text mode. */
  #textMarkdown() {
    const clone = this.#text.cloneNode(true);
    for (const toc of clone.querySelectorAll("nav.markdown-toc")) toc.replaceChildren(); // regenerated on render
    return toMarkdown(clone, { alertTitles: this.#alertTitles() });
  }

  #wireText() {
    const text = this.#text;
    try {
      document.execCommand("defaultParagraphSeparator", false, "p");
    } catch {
      // not supported: Chrome's <div> blocks are paragraphs all the same
    }
    text.addEventListener("input", (e) => {
      if (e.inputType === "insertParagraph") this.#at(TASK_LI)?.setAttribute("data-checked", "false");
      this.#changed = true;
      this.#markdown = this.#textMarkdown();
      if (this.#source) this.#source.value = this.#markdown;
      this.#sync();
      this.#slashInput(e);
    });
    text.addEventListener("blur", () => this.#blurred());
    text.addEventListener("mousedown", (e) => this.#tick(e));
    text.addEventListener("keydown", (e) => this.#textKey(e));
    text.addEventListener("paste", (e) => this.#paste(e));
    text.addEventListener("drop", (e) => {
      if (e.dataTransfer?.files?.length && !this.#readonly) {
        e.preventDefault();
        const pos = document.caretPositionFromPoint?.(e.clientX, e.clientY);
        const range = pos ? document.createRange() : document.caretRangeFromPoint?.(e.clientX, e.clientY);
        if (pos) range.setStart(pos.offsetNode, pos.offset);
        if (range) this.#range = range;
        this.#attach([...e.dataTransfer.files]);
      }
    });
    text.addEventListener("click", (e) => {
      if (e.target.closest?.("a[href]") && (e.ctrlKey || e.metaKey)) window.open(e.target.closest("a").href, "_blank", "noopener");
    });
  }

  #wireShadow() {
    const root = this.shadowRoot;
    const toolbar = root.querySelector(".ui-mde-toolbar");
    toolbar.addEventListener("mousedown", (e) => {
      if (e.composedPath().some((n) => n.dataset?.cmd)) e.preventDefault(); // the text keeps its selection
    });
    toolbar.addEventListener("click", (e) => {
      const button = e.composedPath().find((n) => n instanceof Element && (n.dataset.cmd || n.dataset.mode));
      if (!button) return;
      if (button.dataset.mode) this.#switch(button.dataset.mode);
      else this.#tool(button.dataset.cmd, button);
    });
    const source = this.#source;
    source.addEventListener("input", () => {
      this.#changed = true;
      this.#markdown = source.value;
      this.#filled = false;
      this.#sync();
    });
    source.addEventListener("blur", () => this.#blurred());
    source.addEventListener("keydown", (e) => this.#sourceKey(e));
    source.addEventListener("paste", (e) => {
      const files = [...(e.clipboardData?.files || [])];
      if (files.length) {
        e.preventDefault();
        this.#attach(files);
      }
    });
    source.addEventListener("drop", (e) => {
      if (e.dataTransfer?.files?.length) {
        e.preventDefault();
        this.#attach([...e.dataTransfer.files]);
      }
    });
    const file = root.querySelector(".ui-mde-file");
    file.addEventListener("change", () => {
      const files = [...file.files];
      file.value = "";
      if (files.length) this.#attach(files);
    });
    for (const pop of root.querySelectorAll(".ui-mde-pop")) {
      pop.addEventListener("mousedown", (e) => {
        if (!e.target.closest("input")) e.preventDefault();
      });
      pop.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
          e.preventDefault();
          this.#close(pop);
          this.focus();
        }
      });
    }
    const picker = root.querySelector(".ui-mde-picker");
    const size = picker.querySelector(".ui-mde-size");
    const mark = (cols, rows) => {
      for (const cell of picker.querySelectorAll(".ui-mde-cell")) {
        cell.classList.toggle("active", Number(cell.dataset.columns) <= cols && Number(cell.dataset.rows) <= rows);
      }
      size.textContent = cols ? format(this.labels["table-size"], { columns: cols, rows }) : "";
    };
    picker.addEventListener("pointerover", (e) => {
      const cell = e.target.closest(".ui-mde-cell");
      if (cell) mark(Number(cell.dataset.columns), Number(cell.dataset.rows));
    });
    picker.addEventListener("focusin", (e) => {
      const cell = e.target.closest(".ui-mde-cell");
      if (cell) mark(Number(cell.dataset.columns), Number(cell.dataset.rows));
    });
    picker.addEventListener("click", (e) => {
      const cell = e.target.closest(".ui-mde-cell");
      if (!cell) return;
      this.#close(picker);
      this.#insertTable(Number(cell.dataset.columns), Number(cell.dataset.rows));
    });
    for (const pop of root.querySelectorAll('[data-pop="format"], [data-pop="more"], [data-pop="slash"]')) {
      pop.addEventListener("click", (e) => {
        const item = e.target.closest("[data-item]");
        if (!item) return;
        this.#close(pop);
        if (pop.dataset.pop === "slash") this.#removeSlash();
        else this.#restore();
        this.#run(item.dataset.item);
      });
    }
  }

  #blurred() {
    if (!this.#changed) return;
    // a click into the toolbar or a menu of this editor is not leaving it
    queueMicrotask(() => {
      if (this.matches(":focus-within") || this.shadowRoot.activeElement) return;
      this.#changed = false;
      this.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }

  // --- modes -------------------------------------------------------------------------------------------------------

  #switch(mode) {
    if (mode === this.mode) return;
    // the value follows every edit already: an unchanged text keeps its Markdown as written
    this.#mode = mode;
    this.#filled = false;
    this.setAttribute("mode", mode);
    this.requestRender();
    this.dispatchEvent(new CustomEvent("ui-markdown-editor:mode", { bubbles: true, composed: true, detail: { mode } }));
    queueMicrotask(() => queueMicrotask(() => this.focus()));
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "mode") this.#mode = newValue === "markdown" ? "markdown" : "text";
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  // --- toolbar and commands ---------------------------------------------------------------------------------------

  #tool(id, button) {
    if (this.#readonly) return;
    if (this.mode === "markdown") {
      if (WRAP[id]) this.#editSource((v, s, e) => toggleWrap(v, s, e, WRAP[id]));
      else if (id === "link") this.#linkDialog(button);
      else if (id === "attach") this.shadowRoot.querySelector(".ui-mde-file").click();
      return;
    }
    this.#save();
    if (id === "format") this.#openMenu("format", button, this.#formatItems());
    else if (id === "more") this.#openMenu("more", button, this.#commandItems("plus"));
    else if (id === "table") this.#openPop(this.shadowRoot.querySelector('[data-pop="table"]'), button);
    else if (id === "link") this.#linkDialog(button);
    else this.#run(id);
  }

  /** Runs a command by id (built in or added) in the current mode. */
  #run(id) {
    const custom = [...menuCommands("slash", this.#commands), ...menuCommands("plus", this.#commands)]
      .find((c) => c.id === id && c.custom);
    if (custom) {
      if (custom.run) custom.run(this);
      else this.insertMarkdown(typeof custom.markdown === "function" ? custom.markdown(this) : custom.markdown);
      this.#changedByCommand();
      return;
    }
    if (id === "attach") {
      this.shadowRoot.querySelector(".ui-mde-file").click();
      return;
    }
    if (this.mode === "markdown") {
      const md = builtinMarkdown(id, this.labels);
      if (md !== null) this.#editSource((v, s, e) => insertBlock(v, s, e, md));
      return;
    }
    this.#text.focus();
    this.#restore();
    if (id === "paragraph" || id.startsWith("heading-")) {
      document.execCommand("formatBlock", false, id === "paragraph" ? "<p>" : `<h${id.slice(8)}>`);
    } else if (EXEC[id]) {
      document.execCommand(EXEC[id], false, null);
    } else if (id === "quote") {
      this.#quote();
    } else if (id === "code") {
      this.#code();
    } else if (id === "tasks") {
      this.#taskList();
    } else if (id === "table") {
      this.#insertTable(3, 2);
      return;
    } else if (id.startsWith("alert-")) {
      const kind = id.slice(6);
      const selected = this.#selectedText();
      this.#insertHtml(`<div class="markdown-alert markdown-alert-${kind}"><p class="markdown-alert-title">`
        + `${escapeHtml(this.labels[id])}</p><p data-caret>${escapeHtml(selected) || "<br>"}</p></div><p><br></p>`);
    } else if (id === "code-block") {
      this.#codeBlockDialog();
      return;
    } else if (id === "details") {
      this.#insertHtml(`<details open data-md-closed><summary>${escapeHtml(this.labels["details-summary"])}</summary>`
        + `<p data-caret>${escapeHtml(this.#selectedText()) || "<br>"}</p></details><p><br></p>`);
    } else if (id === "rule") {
      document.execCommand("insertHorizontalRule", false, null);
    } else if (id === "toc") {
      const entries = [...this.#text.querySelectorAll(HEADINGS.join(","))]
        .map((h) => [Number(h.tagName[1]), slugify(h.textContent), h.textContent]);
      this.#insertHtml(this.#prepare(sanitize(tocHtml(entries))) + "<p><br></p>");
    } else if (["row-add", "column-add", "row-delete", "column-delete", "table-delete"].includes(id)) {
      this.#tableEdit(id);
    }
    this.#changedByCommand();
  }

  #changedByCommand() {
    this.#changed = true;
    if (this.mode === "text") {
      this.#markdown = this.#textMarkdown();
      if (this.#source) this.#source.value = this.#markdown;
      this.#text.dispatchEvent(new Event("input", { bubbles: true }));
    }
    this.#sync();
  }

  #formatItems() {
    const L = this.labels;
    return [["paragraph", "text-paragraph"], ...HEADINGS.map((h, i) => [`heading-${i + 1}`, i < 3 ? `type-h${i + 1}` : "type"])]
      .map(([id, name]) => ({ id, label: L[id], icon: icon(name) }));
  }

  #commandItems(menu, query = "") {
    const L = this.labels;
    const list = filterCommands(menuCommands(menu, this.#commands), query, L);
    return list.map((c) => ({ id: c.id, label: c.custom ? c.label : L[c.label] || c.label, icon: iconMarkup(c.icon) }));
  }

  // --- menus -------------------------------------------------------------------------------------------------------

  #anchorOf(pop) {
    return pop._anchor || null;
  }

  #openPop(pop, anchor, rect = null) {
    for (const other of this.shadowRoot.querySelectorAll(".ui-mde-pop:popover-open")) if (other !== pop) this.#close(other);
    pop._anchor = anchor;
    pop.classList.add("show");
    if (!pop.matches(":popover-open")) pop.showPopover?.();
    const box = pop.getBoundingClientRect();
    const r = rect || anchor.getBoundingClientRect();
    const place = placeAligned(r, box, { width: innerWidth, height: innerHeight }, "bottom-start",
      { rtl: getComputedStyle(this).direction === "rtl" });
    pop.style.left = `${place.left}px`;
    pop.style.top = `${place.top}px`;
    if (anchor) anchor.setAttribute?.("aria-expanded", "true");
  }

  #close(pop) {
    if (!pop) return;
    pop.classList.remove("show");
    if (pop.matches(":popover-open")) pop.hidePopover?.();
    pop._anchor?.setAttribute?.("aria-expanded", "false");
    if (pop.dataset.pop === "slash") this.#slash = null;
  }

  #openMenu(name, anchor, items, rect = null) {
    const pop = this.shadowRoot.querySelector(`[data-pop="${name}"]`);
    this.#menuItems = items;
    this.#menuIndex = 0;
    pop.innerHTML = items.length ? items.map((item, i) => `<button type="button" class="menu-item${name === "slash" && i === 0 ? " active" : ""}" `
      + `role="${name === "slash" ? "option" : "menuitem"}" data-item="${escapeHtml(item.id)}">`
      + `<span class="menu-item-icon">${item.icon || ""}</span>${escapeHtml(item.label)}</button>`).join("")
      : `<div class="menu-header">${escapeHtml(this.labels["no-commands"])}</div>`;
    this.#openPop(pop, anchor, rect);
    if (name !== "slash") pop.querySelector(".menu-item")?.focus();
  }

  // --- «/» commands ------------------------------------------------------------------------------------------------

  #slashInput(e) {
    const sel = document.getSelection();
    const node = sel?.anchorNode;
    if (e.inputType === "insertText" && e.data === "/" && node?.nodeType === Node.TEXT_NODE) {
      const offset = sel.anchorOffset - 1;
      const before = node.data.slice(0, offset);
      if (!before || /\s$/.test(before.replace(/ /g, " "))) {
        this.#slash = { node, offset };
        const range = sel.getRangeAt(0).cloneRange();
        this.#openMenu("slash", this.#text, this.#commandItems("slash"), range.getBoundingClientRect());
        return;
      }
    }
    if (!this.#slash) return;
    const { node: slashNode, offset } = this.#slash;
    if (node !== slashNode || sel.anchorOffset <= offset || slashNode.data[offset] !== "/") {
      this.#close(this.shadowRoot.querySelector('[data-pop="slash"]'));
      return;
    }
    const query = slashNode.data.slice(offset + 1, sel.anchorOffset);
    if (/\s\s|^\s/.test(query)) {
      this.#close(this.shadowRoot.querySelector('[data-pop="slash"]'));
      return;
    }
    const items = this.#commandItems("slash", query);
    const slash = this.#slash;
    this.#openMenu("slash", this.#text, items, sel.getRangeAt(0).getBoundingClientRect());
    this.#slash = slash;
  }

  #removeSlash() {
    if (!this.#slash) return;
    const { node, offset } = this.#slash;
    const sel = document.getSelection();
    const end = node === sel.anchorNode ? sel.anchorOffset : offset + 1;
    const range = document.createRange();
    range.setStart(node, offset);
    range.setEnd(node, Math.max(offset + 1, end));
    range.deleteContents();
    if (!node.data) node.parentNode?.append?.(document.createElement("br"));
    range.collapse(true);
    sel.removeAllRanges();
    sel.addRange(range);
    this.#slash = null;
  }

  #slashKey(e) {
    const pop = this.shadowRoot.querySelector('[data-pop="slash"]');
    if (!this.#slash || !pop.matches(":popover-open")) return false;
    const items = [...pop.querySelectorAll(".menu-item")];
    if (e.key === "Escape") {
      this.#close(pop);
    } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (!items.length) return true;
      this.#menuIndex = (this.#menuIndex + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
      items.forEach((item, i) => item.classList.toggle("active", i === this.#menuIndex));
      items[this.#menuIndex].scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter" || e.key === "Tab") {
      const item = items[this.#menuIndex];
      if (!item) {
        this.#close(pop);
        return false;
      }
      this.#close(pop);
      this.#slash = this.#slash || null;
      return this.#chooseSlash(item.dataset.item);
    } else {
      return false;
    }
    e.preventDefault();
    return true;
  }

  #chooseSlash(id) {
    // #close() cleared #slash; the text node still holds «/query» before the cursor
    const sel = document.getSelection();
    const node = sel.anchorNode;
    if (node?.nodeType === Node.TEXT_NODE) {
      const at = node.data.lastIndexOf("/", sel.anchorOffset - 1);
      if (at >= 0) this.#slash = { node, offset: at };
    }
    this.#removeSlash();
    this.#run(id);
    return true;
  }

  // --- keyboard ----------------------------------------------------------------------------------------------------

  #textKey(e) {
    if (this.#slash && ["ArrowDown", "ArrowUp", "Enter", "Tab", "Escape"].includes(e.key)) {
      if (e.key === "Enter" || e.key === "Tab") {
        const pop = this.shadowRoot.querySelector('[data-pop="slash"]');
        const item = pop.querySelectorAll(".menu-item")[this.#menuIndex];
        if (item && pop.matches(":popover-open")) {
          e.preventDefault();
          this.#close(pop);
          this.#chooseSlash(item.dataset.item);
          return;
        }
      } else if (this.#slashKey(e)) {
        return;
      }
    }
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key.toLowerCase() === "k") {
      e.preventDefault();
      this.#save();
      this.#linkDialog(this.shadowRoot.querySelector('[data-cmd="link"]'));
      return;
    }
    if (mod && e.shiftKey && e.key.toLowerCase() === "x") {
      e.preventDefault();
      this.#run("strike");
      return;
    }
    if (e.key === "Enter" && !e.shiftKey && this.#at("pre")) { // a line break inside a code block
      e.preventDefault();
      document.execCommand("insertText", false, "\n");
      return;
    }
    if (e.key === "Enter" && !e.shiftKey) this.#leaveBlock(e);
  }

  /** Enter in an empty last paragraph of a quote, alert or section: the paragraph moves out, below it. */
  #leaveBlock(e) {
    const block = this.#at("p, div:not(.markdown-alert):not(.ui-markdown-editor-text)");
    const container = block?.parentElement?.closest("blockquote, .markdown-alert, details");
    if (!block || !container || block.parentElement !== container || block.nextElementSibling || block.textContent.trim()) {
      return;
    }
    e.preventDefault();
    const p = document.createElement("p");
    p.innerHTML = "<br>";
    container.after(p);
    block.remove();
    const range = document.createRange();
    range.setStart(p, 0);
    range.collapse(true);
    document.getSelection().removeAllRanges();
    document.getSelection().addRange(range);
    this.#changedByCommand();
  }

  #sourceKey(e) {
    const mod = e.ctrlKey || e.metaKey;
    if (!mod || this.#readonly) return;
    const key = e.key.toLowerCase();
    if (key === "b" || key === "i") {
      e.preventDefault();
      this.#editSource((v, s, en) => toggleWrap(v, s, en, key === "b" ? "**" : "*"));
    } else if (key === "k") {
      e.preventDefault();
      this.#linkDialog(this.shadowRoot.querySelector('[data-cmd="link"]'));
    }
  }

  /** An edit of the Markdown source (value, start, end) -> {value, start, end}, then input as typing would. */
  #editSource(edit) {
    const source = this.#source;
    if (!source) return;
    const { value, start, end } = edit(source.value, source.selectionStart, source.selectionEnd);
    source.value = value;
    source.focus();
    source.setSelectionRange(start, end);
    this.#markdown = value;
    this.#filled = false;
    this.#changed = true;
    this.#sync();
    source.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
  }

  // --- dialogs -----------------------------------------------------------------------------------------------------

  /** A small dialog under the anchor: fields [{name, label, value}] -> Promise<values | null>. */
  #ask(anchor, fields) {
    const L = this.labels;
    const form = this.shadowRoot.querySelector('[data-pop="ask"]');
    form.innerHTML = fields.map((f) => `<label class="ui-mde-ask-field"><span>${escapeHtml(f.label)}</span>`
      + `<input class="form-control form-control-sm" name="${escapeHtml(f.name)}" value="${escapeHtml(f.value || "")}"`
      + `${f.required ? " required" : ""}${f.type ? ` type="${f.type}"` : ""}></label>`).join("")
      + `<div class="ui-mde-ask-actions"><button type="button" class="btn btn-sm btn-text" data-ask="cancel">${escapeHtml(L.cancel)}</button>`
      + `<button type="submit" class="btn btn-sm btn-solid theme-primary">${escapeHtml(L.insert)}</button></div>`;
    this.#openPop(form, anchor || this.#text);
    form.querySelector("input")?.focus();
    return new Promise((resolve) => {
      const done = (values) => {
        form.onsubmit = null;
        form.onclick = null;
        this.#close(form);
        resolve(values);
      };
      form.onsubmit = (e) => {
        e.preventDefault();
        done(Object.fromEntries(new FormData(form)));
      };
      form.onclick = (e) => {
        if (e.target.closest('[data-ask="cancel"]')) done(null);
      };
      form.addEventListener("keydown", (e) => {
        if (e.key === "Escape") done(null);
      }, { once: true });
    });
  }

  async #linkDialog(anchor) {
    const L = this.labels;
    const markdown = this.mode === "markdown";
    const source = this.#source;
    const selStart = source?.selectionStart ?? 0;
    const selEnd = source?.selectionEnd ?? 0;
    const selected = markdown ? source.value.slice(selStart, selEnd) : this.#selectedText();
    const existing = markdown ? null : this.#at("a");
    const values = await this.#ask(anchor, [
      { name: "url", label: L["link-url"], value: existing?.getAttribute("data-md-href") || existing?.getAttribute("href") || "https://", required: true },
      ...(selected || existing ? [] : [{ name: "text", label: L["link-text"] }]),
    ]);
    if (!values) {
      this.focus();
      return;
    }
    const url = values.url.trim();
    const safe = resolveUrl(url, "link");
    if (!safe || url === "https://") {
      this.focus();
      return;
    }
    if (markdown) {
      source.setSelectionRange(selStart, selEnd);
      this.#editSource((v) => insertLink(v, selStart, selEnd, url, values.text || ""));
      return;
    }
    this.#text.focus();
    this.#restore();
    if (existing) {
      existing.setAttribute("href", url);
      existing.removeAttribute("data-md-href");
    } else if (selected) {
      document.execCommand("createLink", false, url);
    } else {
      document.execCommand("insertHTML", false, `<a href="${escapeHtml(url)}">${escapeHtml(values.text || url)}</a>`);
    }
    this.#changedByCommand();
  }

  async #codeBlockDialog() {
    const selected = this.#selectedText();
    const anchor = this.shadowRoot.querySelector('[data-cmd="more"]');
    const values = await this.#ask(anchor, [{ name: "language", label: this.labels.language }]);
    if (!values) {
      this.focus();
      return;
    }
    const lang = (values.language || "").trim().replace(/[^A-Za-z0-9_+#.-]/g, "");
    this.#text.focus();
    this.#restore();
    this.#insertHtml(`<pre><code${lang ? ` class="language-${escapeHtml(lang)}"` : ""} data-caret>`
      + `${escapeHtml(selected) || "\n"}</code></pre><p><br></p>`);
    this.#changedByCommand();
  }

  // --- text editing helpers ----------------------------------------------------------------------------------------

  #save() {
    const sel = document.getSelection();
    if (sel?.rangeCount && this.#text?.contains(sel.anchorNode)) this.#range = sel.getRangeAt(0).cloneRange();
  }

  #restore() {
    if (!this.#text) return;
    this.#text.focus({ preventScroll: true });
    const sel = document.getSelection();
    if (this.#range && this.#text.contains(this.#range.startContainer)) {
      sel.removeAllRanges();
      sel.addRange(this.#range);
    } else if (!sel.rangeCount || !this.#text.contains(sel.anchorNode)) {
      const range = document.createRange(); // at the end of the last block
      const last = this.#text.lastElementChild;
      range.selectNodeContents(last && !["TABLE", "NAV", "HR"].includes(last.tagName) ? last : this.#text);
      range.collapse(false);
      sel.removeAllRanges();
      sel.addRange(range);
    }
    this.#range = null;
  }

  #selectedText() {
    const sel = document.getSelection();
    return sel?.rangeCount && this.#text?.contains(sel.anchorNode) ? sel.toString() : "";
  }

  /** HTML inserted at the cursor; an element marked data-caret gets the cursor. */
  #insertHtml(html) {
    document.execCommand("insertHTML", false, html);
    const target = this.#text.querySelector("[data-caret]");
    if (target) {
      target.removeAttribute("data-caret");
      const range = document.createRange();
      range.selectNodeContents(target);
      range.collapse(false);
      document.getSelection().removeAllRanges();
      document.getSelection().addRange(range);
    }
  }

  #insertTable(columns, rows) {
    this.#restore();
    document.execCommand("insertHTML", false, `${tableHtml(columns, rows)}<p><br></p>`);
    this.#changedByCommand();
  }

  #at(selector) {
    const node = document.getSelection()?.anchorNode;
    const element = node?.nodeType === Node.ELEMENT_NODE ? node : node?.parentElement;
    const found = element?.closest?.(selector);
    return found && this.#text?.contains(found) && found !== this.#text ? found : null;
  }

  /** The blocks of the selection into a quote, or out of it (by hand: formatBlock differs between browsers). */
  #quote() {
    const sel = document.getSelection();
    if (!sel?.rangeCount || !this.#text.contains(sel.anchorNode)) return;
    const range = sel.getRangeAt(0);
    const top = (node) => {
      let n = node;
      while (n && n.parentNode !== this.#text) n = n.parentNode;
      return n;
    };
    const quote = this.#at("blockquote");
    if (quote) {
      quote.replaceWith(...quote.childNodes);
      return;
    }
    let start = top(range.startContainer);
    let end = top(range.endContainer);
    if (!start) {
      const block = document.createElement("p");
      block.innerHTML = "<br>";
      this.#text.append(block);
      start = end = block;
    }
    const blockquote = document.createElement("blockquote");
    this.#text.insertBefore(blockquote, start);
    for (let n = start; n;) {
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

  /** Inline code: the selection into <code>, or the code around the cursor back to text. */
  #code() {
    const inside = this.#at("code");
    if (inside && !inside.closest("pre")) {
      inside.replaceWith(...inside.childNodes);
      return;
    }
    const text = this.#selectedText() || "code";
    document.execCommand("insertHTML", false, `<code>${escapeHtml(text)}</code>`);
  }

  /** A task list: the list at the cursor becomes one (or a plain list again); without a list a new one. */
  #taskList() {
    let list = this.#at("ul, ol");
    if (list?.hasAttribute("data-task")) {
      list.removeAttribute("data-task");
      for (const li of list.children) li.removeAttribute("data-checked");
      return;
    }
    if (!list || list.tagName === "OL") {
      document.execCommand("insertUnorderedList", false, null);
      list = this.#at("ul");
    }
    if (!list) return;
    list.setAttribute("data-task", "");
    for (const li of list.children) if (!li.hasAttribute("data-checked")) li.setAttribute("data-checked", "false");
  }

  /** A click on the box of a task (left of its text) ticks or unticks it. */
  #tick(e) {
    const li = e.target.closest?.(TASK_LI);
    if (!li || li !== e.target || this.#readonly) return;
    const box = parseFloat(getComputedStyle(li).paddingInlineStart) || 24;
    const rect = li.getBoundingClientRect();
    const fromStart = getComputedStyle(li).direction === "rtl" ? rect.right - e.clientX : e.clientX - rect.left;
    if (fromStart > box) return;
    e.preventDefault();
    li.setAttribute("data-checked", String(li.getAttribute("data-checked") !== "true"));
    this.#changedByCommand();
  }

  #tableEdit(id) {
    const cell = this.#at("td, th");
    if (!cell) return;
    const row = cell.parentElement;
    const table = cell.closest("table");
    const index = [...row.children].indexOf(cell);
    if (id === "table-delete") {
      table.remove();
    } else if (id === "row-add") {
      const next = document.createElement("tr");
      next.innerHTML = "<td><br></td>".repeat(row.children.length);
      if (row.parentElement.tagName === "THEAD") (table.tBodies[0] || table.createTBody()).prepend(next);
      else row.after(next);
    } else if (id === "row-delete") {
      if (row.parentElement.tagName !== "THEAD") row.remove();
    } else if (id === "column-add") {
      for (const tr of table.rows) {
        const fresh = document.createElement(tr.parentElement.tagName === "THEAD" ? "th" : "td");
        fresh.innerHTML = "<br>";
        tr.children[index] ? tr.children[index].after(fresh) : tr.append(fresh);
      }
    } else if (id === "column-delete") {
      if (row.children.length <= 1) table.remove();
      else for (const tr of table.rows) tr.children[index]?.remove();
    }
  }

  #paste(e) {
    const files = [...(e.clipboardData?.files || [])];
    if (files.length) {
      e.preventDefault();
      this.#save();
      this.#attach(files);
      return;
    }
    if (this.#at("pre")) { // code: as it is
      const text = e.clipboardData?.getData("text/plain");
      if (text) {
        e.preventDefault();
        document.execCommand("insertText", false, text);
      }
      return;
    }
    const html = e.clipboardData?.getData("text/html");
    const text = e.clipboardData?.getData("text/plain");
    if (!html && !text) return;
    e.preventDefault();
    // HTML: reduced to what Markdown has; plain text is read as Markdown (a pasted URL becomes a link)
    const clean = html ? render(toMarkdown(parseHtml(html)), this.#renderOptions()) : render(text, this.#renderOptions());
    document.execCommand("insertHTML", false, this.#prepare(clean));
  }

  // --- attachments -------------------------------------------------------------------------------------------------

  #status(message) {
    const status = this.shadowRoot?.querySelector(".ui-mde-status");
    if (!status) return;
    status.textContent = message || "";
    status.hidden = !message;
  }

  async #attach(files) {
    if (this.#readonly) return;
    if (this.mode === "text") this.#save();
    const L = this.labels;
    for (const file of files) {
      let inserted = false;
      const insert = (result) => {
        if (!result?.url || inserted) return;
        inserted = true;
        this.#insertAttachment(result, file);
      };
      const event = new CustomEvent("ui-markdown-editor:attach", { bubbles: true, composed: true, cancelable: true,
        detail: { file, insert } });
      if (!this.dispatchEvent(event) || !this.uploadHandler) continue;
      this.#status(format(L.uploading, { name: file.name }));
      try {
        insert(await this.uploadHandler(file));
        this.#status("");
      } catch (error) {
        this.#status(format(L["upload-failed"], { name: file.name }));
        this.dispatchEvent(new CustomEvent("ui-markdown-editor:upload-error", { bubbles: true, composed: true,
          detail: { file, error } }));
      }
    }
  }

  #insertAttachment({ url, name }, file) {
    const md = attachmentMarkdown({ url, name: name || file?.name }, file?.type || "");
    if (this.mode === "markdown") {
      this.#editSource((v, s, e) => insertText(v, s, e, md));
      return;
    }
    this.#restore();
    const html = this.#prepare(render(md, this.#renderOptions())).replace(/^<p>|<\/p>\s*$/g, "");
    document.execCommand("insertHTML", false, `${html} `);
    this.#save();
    this.#changedByCommand();
  }

  // --- state -------------------------------------------------------------------------------------------------------

  #updateTools() {
    const sel = document.getSelection();
    if (!this.#text || this.mode !== "text" || !sel?.anchorNode || !this.#text.contains(sel.anchorNode)) return;
    const root = this.shadowRoot;
    for (const id of ["bold", "italic", "strike", "bullets", "numbers"]) {
      let state = false;
      try {
        state = document.queryCommandState(EXEC[id]);
      } catch {
        state = false;
      }
      root.querySelector(`[data-cmd="${id}"]`)?.setAttribute("aria-pressed", String(state));
    }
    for (const [id, selector] of [["quote", "blockquote"], ["code", "code"], ["tasks", "ul[data-task]"],
      ["link", "a"], ["table", "table"]]) {
      root.querySelector(`[data-cmd="${id}"]`)?.classList.toggle("active", Boolean(this.#at(selector)));
    }
    const block = this.#at(HEADINGS.join(","));
    const label = root.querySelector(".ui-mde-format-label");
    if (label) label.textContent = this.labels[block ? `heading-${block.tagName[1]}` : "paragraph"];
    const tableTools = root.querySelector(".ui-mde-table-tools");
    if (tableTools) tableTools.hidden = !this.#at("td, th");
  }

  #sync() {
    const value = this.value;
    const empty = !value.trim();
    this.#text?.classList.toggle("is-empty", empty && !this.#text.querySelector("img, li, table, hr, blockquote, pre, details, .markdown-alert"));
    this.#internals.setFormValue(value);
    const error = this.getAttribute("error");
    const anchor = this.mode === "markdown" ? this.#source : this.#text;
    if (error) this.#internals.setValidity({ customError: true }, error, anchor || undefined);
    else if (this.hasAttribute("required") && empty) this.#internals.setValidity({ valueMissing: true }, this.labels.required, anchor || undefined);
    else this.#internals.setValidity({});
    this.#updateTools();
  }
}

registerComponent("ui-markdown-editor", UiMarkdownEditor);
