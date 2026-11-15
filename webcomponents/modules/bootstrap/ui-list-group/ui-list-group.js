import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { morph } from "../../../core/morph.js";
import { assignItemSlots, observeItems } from "../../../core/slotted-items.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";
import { clickedIndex } from "./list-group-click.js";

const ITEM_ATTRIBUTES = ["href", "target", "rel", "action", "active", "disabled", "variant", "class"];
const BREAKPOINTS = new Set(["sm", "md", "lg", "xl", "2xl"]);

/**
 * <ui-list-group> (Bootstrap 6 list group) with <ui-list-group-item> children.
 *
 * Attributes:
 * - flush: no outer borders and radii (edge-to-edge, e.g. in a card).
 * - numbered: numbers the items (rendered as <ol>).
 * - horizontal: items side by side; with a breakpoint (sm, md, lg, xl, 2xl)
 *   only from that width of the element on (container query on the host).
 * - label: aria-label of the list.
 *
 * <ui-list-group-item> attributes:
 * - href (+ target, rel): a link item (.list-group-item-action).
 * - action: a button item (.list-group-item-action) without a link.
 * - active: the current selection (aria-current="true").
 * - disabled: inactive (aria-disabled, not focusable).
 * - variant: theme colour of the item.
 * - class: Bootstrap utilities for the item (d-flex, flex-fill, …) apply to
 *   the rendered item, like on a .list-group-item.
 *
 * The items are rendered inside the list's shadow tree (one slot each), so
 * Bootstrap's sibling rules work unchanged. Event ui-list-group:action
 * (bubbles, detail { item, index }) when an action or link item is clicked.
 * Parts: list, item (plus item-active, item-disabled).
 */
export class UiListGroup extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-list-group.css", import.meta.url).href];
  static documentStylesheet = new URL("./ui-list-group.document.css", import.meta.url).href;
  static observedAttributes = ["flush", "numbered", "horizontal", "label"];

  #stopObserving = null;
  #items = [];

  constructor() {
    super();
    this.shadowRoot.addEventListener("click", (event) => {
      // Through the composed path: a click on an item's slotted content has a target outside this shadow tree.
      const index = clickedIndex(event.composedPath(), this.shadowRoot);
      const item = index >= 0 ? this.#items[index] : null;
      if (!item || item.hasAttribute("disabled")) return;
      this.dispatchEvent(new CustomEvent("ui-list-group:action", { bubbles: true, detail: { item, index } }));
    });
  }

  connectedCallback() {
    super.connectedCallback();
    this.#stopObserving ??= observeItems(this, ITEM_ATTRIBUTES, () => this.requestRender());
  }

  disconnectedCallback() {
    this.#stopObserving?.();
    this.#stopObserving = null;
  }

  renderShadow() {
    morph(this.shadowRoot, this.render());
  }

  get items() {
    return [...this.#items];
  }

  listClasses() {
    const classes = ["list-group", HOST_TOKENS_CLASS];
    if (this.hasAttribute("flush")) {
      classes.push("list-group-flush");
    }
    if (this.hasAttribute("numbered")) {
      classes.push("list-group-numbered");
    }
    if (this.hasAttribute("horizontal")) {
      const breakpoint = (this.getAttribute("horizontal") || "").trim();
      classes.push(BREAKPOINTS.has(breakpoint) ? `${breakpoint}:list-group-horizontal` : "list-group-horizontal");
    }
    return classes.join(" ");
  }

  itemMarkup(item, index, inList) {
    const href = item.getAttribute("href");
    const action = Boolean(href) || item.hasAttribute("action");
    const active = item.hasAttribute("active");
    const disabled = item.hasAttribute("disabled");
    const variant = themeColor(item.getAttribute("variant"));
    // The item's own classes (d-flex, flex-fill, …) go onto the rendered item, as in Bootstrap's markup;
    // the element itself is display: contents (ui-list-group.document.css).
    const classes = escapeHtml(["list-group-item", action ? "list-group-item-action" : "", active ? "active" : "",
      disabled && !(action && !href) ? "disabled" : "", variant ? `theme-${variant}` : "", item.className]
      .filter(Boolean).join(" "));
    const parts = ["item", active ? "item-active" : "", disabled ? "item-disabled" : ""].filter(Boolean).join(" ");
    const common = `class="${classes}" part="${parts}" data-index="${index}"`;
    const current = active ? ' aria-current="true"' : "";
    const slot = `<slot name="item-${index}"></slot>`;

    if (href) {
      return `<a ${common} href="${escapeHtml(href)}"${current}`
        + `${item.hasAttribute("target") ? ` target="${escapeHtml(item.getAttribute("target"))}"` : ""}`
        + `${item.hasAttribute("rel") ? ` rel="${escapeHtml(item.getAttribute("rel"))}"` : ""}`
        + `${disabled ? ' aria-disabled="true" tabindex="-1"' : ""}>${slot}</a>`;
    }
    if (action) {
      return `<button type="button" ${common}${current}${disabled ? " disabled" : ""}>${slot}</button>`;
    }
    const tag = inList ? "li" : "div";
    return `<${tag} ${common}${current}${disabled ? ' aria-disabled="true"' : ""}>${slot}</${tag}>`;
  }

  render() {
    this.#items = assignItemSlots(this, "ui-list-group-item", "item");
    const tag = this.hasAttribute("numbered") ? "ol" : "ul";
    const label = this.getAttribute("label");
    const actionable = this.#items.some((item) => item.hasAttribute("href") || item.hasAttribute("action"));
    // Bootstrap's sibling rules (.list-group-item + .list-group-item) need the items as direct children:
    // a list with links or buttons is a <div> of them, like in Bootstrap's docs (numbered: an <ol>).
    const container = actionable && tag === "ul" ? "div" : tag;
    const items = this.#items.map((item, index) => this.itemMarkup(item, index, container !== "div"));
    return `<${container} class="${this.listClasses()}" part="list"${label ? ` aria-label="${escapeHtml(label)}"` : ""}>${items.join("")}</${container}>`;
  }
}

/** One entry of a <ui-list-group>; its content is slotted into the rendered item. */
export class UiListGroupItem extends HTMLElement {}

registerComponent("ui-list-group", UiListGroup);
registerComponent("ui-list-group-item", UiListGroupItem);
