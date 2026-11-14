import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";
import { ALERT_TYPES, loadMarkdown, parseHtml, render, sanitize } from "./markdown.js";

/** The alert titles from the attributes note-label … caution-label (English defaults otherwise). */
export function alertTitlesOf(element) {
  const titles = {};
  for (const kind of ALERT_TYPES) {
    const label = element.getAttribute(`${kind}-label`);
    if (label) titles[kind] = label;
  }
  return titles;
}

/**
 * <ui-markdown>: Markdown shown as formatted text, sanitised in the browser (same rules as the server's
 * flaskspark.markdown; markdown-it is loaded on first use). The typography is the one of ui-markdown-editor.
 *
 * The Markdown comes from (first that applies): the property / attribute value, a child
 * <script type="text/markdown">, or the element's text. Already rendered HTML (e.g. the Jinja filter markdown)
 * goes in as child elements or the property html; it is sanitised again.
 *
 *   <ui-markdown value="**Hello**"></ui-markdown>
 *   <ui-markdown><script type="text/markdown">{{ text }}</script></ui-markdown>
 *   <ui-markdown>{{ text|markdown }}</ui-markdown>
 *
 * Attributes: value, base-url (prefix of relative links and images), breaks (a line break is a <br>),
 * note-label, tip-label, important-label, warning-label, caution-label (alert titles).
 * Properties: value, html, rewriteUrl(url, kind) -> url | null (e.g. an image proxy), body (the rendered element).
 * Events: ui-markdown:render (after the content was rendered).
 * CSS parts: body. Tokens: --ui-markdown-* (markdown-body.css).
 * Links to #ids inside (the table of contents) scroll inside the component.
 */
export class UiMarkdown extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./markdown-body.css", import.meta.url).href,
    new URL("./ui-markdown.css", import.meta.url).href];
  static observedAttributes = ["value", "base-url", "breaks", ...ALERT_TYPES.map((k) => `${k}-label`)];

  #value = null;
  #html = null;
  #rewriteUrl = null;
  #token = 0;

  get value() {
    return this.#value ?? this.getAttribute("value") ?? this.#sourceText();
  }

  set value(text) {
    this.#value = String(text ?? "");
    this.#html = null;
    this.requestRender();
  }

  get html() {
    return this.body?.innerHTML ?? "";
  }

  set html(html) {
    this.#html = String(html ?? "");
    this.#value = null;
    this.requestRender();
  }

  get rewriteUrl() {
    return this.#rewriteUrl;
  }

  set rewriteUrl(fn) {
    this.#rewriteUrl = typeof fn === "function" ? fn : null;
    this.requestRender();
  }

  get body() {
    return this.shadowRoot?.querySelector(".markdown-body") ?? null;
  }

  #sourceText() {
    const script = this.querySelector(':scope > script[type="text/markdown"]');
    if (script) return script.textContent.replace(/^\n/, "");
    return this.children.length ? null : this.textContent;
  }

  render() {
    return '<div class="markdown-body" part="body"></div>';
  }

  async afterRender() {
    const token = ++this.#token;
    const body = this.body;
    body.addEventListener("click", (e) => this.#jump(e));
    const options = { baseUrl: this.getAttribute("base-url"), rewriteUrl: this.#rewriteUrl,
      breaks: this.hasAttribute("breaks"), alertTitles: alertTitlesOf(this) };
    const text = this.value;
    let html;
    if (this.#html !== null || text === null) { // rendered HTML: sanitised again
      html = sanitize(parseHtml(this.#html ?? this.innerHTML), options);
    } else {
      await loadMarkdown();
      if (token !== this.#token) return;
      html = render(text, options);
    }
    body.innerHTML = html;
    this.dispatchEvent(new CustomEvent("ui-markdown:render", { bubbles: true, composed: true }));
  }

  /** A link to an id (the table of contents): the heading is in this shadow tree, the page's anchor can't find it. */
  #jump(e) {
    const link = e.composedPath().find((n) => n instanceof Element && n.tagName === "A");
    const href = link?.getAttribute("href") || "";
    if (!href.startsWith("#") || href.length < 2) return;
    const target = this.shadowRoot.getElementById(decodeURIComponent(href.slice(1)));
    if (!target) return;
    e.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

registerComponent("ui-markdown", UiMarkdown);
