import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { morph } from "../../../core/morph.js";
import { assignItemSlots, observeItems } from "../../../core/slotted-items.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";

const VARIANTS = new Set(["tabs", "pills", "underline", "list"]);
const STEPS = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
const PANEL_ATTRIBUTES = ["heading", "name", "active", "disabled"];

/**
 * <ui-tabs> (Bootstrap 6 nav with the tab plugin) with <ui-tab-panel> children.
 *
 * Renders the navigation from the panels' headings and one .tab-pane per panel (each panel slotted into
 * it), so Bootstrap's .tab-content > .tab-pane rules (fade on show) apply. WAI-ARIA tabs keyboard pattern
 * (arrow keys, Home / End) with automatic activation.
 *
 * Attributes:
 * - variant: tabs (default), pills, underline, or list (a list group beside the panes).
 * - vertical: the navigation in a column beside the panes (pills, list).
 * - fill / justified: nav-fill / nav-justified. instant: no fade (.tab-pane-instant).
 * - card: a card with the tabs in its header (.card-header-tabs / -pills) and the panes in its body.
 * - persist-key: remembers the active tab in localStorage under this key.
 * - label: accessible name of the tab list.
 *
 * <ui-tab-panel>: heading (tab label), name (stable id for persistence and events), active, disabled.
 * Slots: the panels; "actions" for content beside the tabs, on the same line.
 * Parts: nav, tab, content, pane, actions; with card also card, header, body.
 *
 * Methods: show(indexOrName). Events (bubble): ui-tabs:show (cancelable) before, ui-tabs:change and
 * ui-tabs:shown after a switch, detail { index, name, panel, previous }.
 *
 * Bootstrap's data API works on plain markup too: data-bs-toggle="tab" (also "pill", "list") on nav links or
 * list group items, data-bs-target / href pointing at a .tab-pane in a .tab-content.
 */
export class UiTabs extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-tabs.css", import.meta.url).href];
  static observedAttributes = ["variant", "vertical", "fill", "justified", "instant", "card", "label"];

  #stopObserving = null;
  #panels = [];
  #restored = false;

  constructor() {
    super();
    this.shadowRoot.addEventListener("click", (event) => {
      const tab = event.target instanceof Element ? event.target.closest("[data-index]") : null;
      if (tab) {
        this.show(Number(tab.dataset.index), true);
      }
    });
    this.shadowRoot.addEventListener("keydown", (event) => this.#onKeydown(event));
  }

  connectedCallback() {
    super.connectedCallback();
    this.#stopObserving ??= observeItems(this, PANEL_ATTRIBUTES, () => this.requestRender());
  }

  disconnectedCallback() {
    this.#stopObserving?.();
    this.#stopObserving = null;
  }

  renderShadow() {
    morph(this.shadowRoot, this.render());
  }

  get panels() {
    return [...this.#panels];
  }

  get activeIndex() {
    return this.#panels.findIndex((panel) => panel.hasAttribute("active"));
  }

  get variant() {
    const raw = (this.getAttribute("variant") || "tabs").trim().toLowerCase();
    return VARIANTS.has(raw) ? raw : "tabs";
  }

  #navClass() {
    if (this.variant === "list") {
      return `list-group ${HOST_TOKENS_CLASS}`;
    }
    return ["nav", HOST_TOKENS_CLASS, `nav-${this.variant}`, this.hasAttribute("vertical") ? "flex-column" : "",
      this.hasAttribute("fill") ? "nav-fill" : "", this.hasAttribute("justified") ? "nav-justified" : "",
      this.hasAttribute("card") ? `card-header-${this.variant === "pills" ? "pills" : "tabs"}` : ""].filter(Boolean).join(" ");
  }

  #tabMarkup(panel, index, active) {
    const disabled = panel.hasAttribute("disabled");
    const label = escapeHtml(panel.getAttribute("heading") || `Tab ${index + 1}`);
    const common = `id="tab-${index}" type="button" role="tab" data-index="${index}" aria-controls="pane-${index}" `
      + `aria-selected="${active}" tabindex="${active ? 0 : -1}"${disabled ? " disabled" : ""}`;
    if (this.variant === "list") {
      const classes = `list-group-item list-group-item-action${active ? " active" : ""}`;
      return `<button class="${classes}" part="tab" ${common}>${label}</button>`;
    }
    return `<li class="nav-item" role="presentation"><button class="nav-link${active ? " active" : ""}" part="tab" ${common}>${label}</button></li>`;
  }

  render() {
    this.#panels = assignItemSlots(this, "ui-tab-panel", "panel");
    this.#restore();
    if (this.activeIndex < 0) {
      const first = this.#panels.findIndex((panel) => !panel.hasAttribute("disabled"));
      this.#panels[first]?.toggleAttribute("active", true);
    }
    const active = this.activeIndex;
    const label = this.getAttribute("label");
    const tabs = this.#panels.map((panel, index) => this.#tabMarkup(panel, index, index === active)).join("");
    const listTag = this.variant === "list" ? "div" : "ul";
    const nav = `<${listTag} class="${this.#navClass()}" role="tablist" part="nav"${this.hasAttribute("vertical") ? ' aria-orientation="vertical"' : ""}`
      + `${label ? ` aria-label="${escapeHtml(label)}"` : ""}>${tabs}</${listTag}>`;
    const paneClass = `tab-pane ${HOST_TOKENS_CLASS}${this.hasAttribute("instant") ? " tab-pane-instant" : ""}`;
    const panes = this.#panels.map((panel, index) => `<div class="${paneClass}${index === active ? " active show" : ""}" `
      + `id="pane-${index}" role="tabpanel" aria-labelledby="tab-${index}" tabindex="0" part="pane"><slot name="panel-${index}"></slot></div>`).join("");
    const actions = '<div class="ui-tabs-actions" part="actions"><slot name="actions"></slot></div>';
    if (this.hasAttribute("card")) {
      return `<div class="card ui-tabs ui-tabs-card" part="card"><div class="card-header ui-tabs-header" part="header">${nav}${actions}</div>`
        + `<div class="card-body tab-content" part="body content">${panes}</div></div>`;
    }
    const side = this.hasAttribute("vertical") || this.variant === "list";
    return `<div class="ui-tabs${side ? " ui-tabs-side" : ""}"><div class="ui-tabs-header">${nav}${actions}</div>`
      + `<div class="tab-content" part="content">${panes}</div></div>`;
  }

  /** Activates a tab by index or name; `focus` moves the focus to it (keyboard, click). */
  show(target, focus = false) {
    const index = typeof target === "number" ? target : this.#panels.findIndex((panel) => panel.getAttribute("name") === target);
    const panel = this.#panels[index];
    const previous = this.activeIndex;
    if (!panel || panel.hasAttribute("disabled") || index === previous) {
      return false;
    }
    const detail = { index, name: panel.getAttribute("name") || "", panel, previous: this.#panels[previous] || null };
    if (!this.dispatchEvent(new CustomEvent("ui-tabs:show", { bubbles: true, cancelable: true, detail }))) {
      return false;
    }
    this.#panels.forEach((other, i) => other.toggleAttribute("active", i === index));
    this.#persist(panel, index);
    // The new render (attribute observer) shows the pane; focus and events after it.
    queueMicrotask(() => queueMicrotask(() => {
      if (focus) {
        this.shadowRoot.querySelector(`[data-index="${index}"]`)?.focus();
      }
      this.dispatchEvent(new CustomEvent("ui-tabs:change", { bubbles: true, detail }));
      this.dispatchEvent(new CustomEvent("ui-tabs:shown", { bubbles: true, detail }));
    }));
    return true;
  }

  #onKeydown(event) {
    const tab = event.target instanceof Element ? event.target.closest("[data-index]") : null;
    if (!tab) {
      return;
    }
    const enabled = this.#panels.map((panel, index) => (panel.hasAttribute("disabled") ? -1 : index)).filter((i) => i >= 0);
    const position = enabled.indexOf(Number(tab.dataset.index));
    let next = null;
    if (event.key in STEPS) {
      next = enabled[(position + STEPS[event.key] + enabled.length) % enabled.length];
    } else if (event.key === "Home") {
      next = enabled[0];
    } else if (event.key === "End") {
      next = enabled.at(-1);
    }
    if (next !== null && next !== undefined) {
      event.preventDefault();
      this.show(next, true);
    }
  }

  #storageKey() {
    return (this.getAttribute("persist-key") || "").trim();
  }

  #persist(panel, index) {
    const key = this.#storageKey();
    if (!key) return;
    try {
      window.localStorage.setItem(key, panel.getAttribute("name") || String(index));
    } catch {
      // Storage may be unavailable (private mode, quota); persistence is optional.
    }
  }

  #restore() {
    if (this.#restored || !this.#panels.length) return;
    this.#restored = true;
    const key = this.#storageKey();
    let stored = null;
    try {
      stored = key ? window.localStorage.getItem(key) : null;
    } catch {
      stored = null;
    }
    if (stored === null) return;
    const index = this.#panels.findIndex((panel, i) => (panel.getAttribute("name") || String(i)) === stored);
    if (index >= 0 && !this.#panels[index].hasAttribute("disabled")) {
      this.#panels.forEach((panel, i) => panel.toggleAttribute("active", i === index));
    }
  }
}

/** One pane of a <ui-tabs>; its content is slotted into the rendered .tab-pane. */
export class UiTabPanel extends HTMLElement {}

registerComponent("ui-tabs", UiTabs);
registerComponent("ui-tab-panel", UiTabPanel);

// Bootstrap's tab plugin for plain markup: data-bs-toggle="tab" | "pill" | "list".
const TOGGLES = '[data-bs-toggle="tab"], [data-bs-toggle="pill"], [data-bs-toggle="list"]';

function paneOf(toggle) {
  const selector = toggle.getAttribute("data-bs-target") || toggle.getAttribute("href");
  try {
    return selector && selector !== "#" ? document.querySelector(selector) : null;
  } catch {
    return null;
  }
}

function showPlainTab(toggle) {
  if (toggle.classList.contains("active") || toggle.matches(".disabled, :disabled")) return;
  const list = toggle.closest('.nav, .list-group, [role="tablist"]');
  const previous = list ? [...list.querySelectorAll(TOGGLES)].find((other) => other.classList.contains("active")) : null;
  const fire = (target, name, related) => target?.dispatchEvent(new CustomEvent(`ui-tab:${name}`, { bubbles: true, cancelable: name === "show", detail: { relatedTarget: related } }));
  if (fire(toggle, "show", previous) === false) return;
  fire(previous, "hide", toggle);
  previous?.classList.remove("active");
  previous?.setAttribute("aria-selected", "false");
  previous?.setAttribute("tabindex", "-1");
  toggle.classList.add("active");
  toggle.setAttribute("aria-selected", "true");
  toggle.removeAttribute("tabindex");
  const pane = paneOf(toggle);
  const oldPane = previous ? paneOf(previous) : null;
  oldPane?.classList.remove("active", "show");
  pane?.classList.add("active", "show");
  fire(previous, "hidden", toggle);
  fire(toggle, "shown", previous);
}

document.addEventListener("click", (event) => {
  const toggle = event.target instanceof Element ? event.target.closest(TOGGLES) : null;
  if (toggle) {
    event.preventDefault();
    showPlainTab(toggle);
  }
});

document.addEventListener("keydown", (event) => {
  const toggle = event.target instanceof Element ? event.target.closest(TOGGLES) : null;
  if (!toggle || !(event.key in STEPS || event.key === "Home" || event.key === "End")) return;
  const list = toggle.closest('.nav, .list-group, [role="tablist"]');
  const toggles = list ? [...list.querySelectorAll(TOGGLES)].filter((t) => !t.matches(".disabled, :disabled")) : [];
  const index = toggles.indexOf(toggle);
  const next = event.key === "Home" ? toggles[0] : event.key === "End" ? toggles.at(-1)
    : toggles[(index + STEPS[event.key] + toggles.length) % toggles.length];
  if (next) {
    event.preventDefault();
    next.focus();
    showPlainTab(next);
  }
});
