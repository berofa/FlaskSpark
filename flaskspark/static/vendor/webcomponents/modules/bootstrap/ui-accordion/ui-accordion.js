import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { morph } from "../../../core/morph.js";
import { assignItemSlots, observeItems } from "../../../core/slotted-items.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

const ICON = '<svg class="accordion-icon" part="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none" '
  + 'stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m2 5 6 6 6-6"/></svg>';
let groups = 0;

/**
 * <ui-accordion> (Bootstrap 6 accordion on native <details>) with <ui-accordion-item> children.
 *
 * The accordion renders one <details class="accordion-item"> per item (the item's content slotted into its
 * body), so Bootstrap's rules for first / last items and the open state apply; the panel height animates with
 * interpolate-size (browsers without it switch at once). Items share a details name, so one is open at a time.
 *
 * Attributes:
 * - always-open: several items may be open (no shared name).
 * - variant: theme colour of open items. sm: compact. flush: edge-to-edge. gap: separate rounded items.
 * A child with slot="icon" replaces the chevron of every item.
 *
 * <ui-accordion-item>: heading (or a child with slot="heading"), open (reflected), disabled.
 * Methods: openAll(), closeAll() (both also with always-open off), items. Events (bubble):
 * ui-accordion-item:toggle on the item with detail.open after each toggle (by the user, by name exclusivity or by code).
 * Parts: accordion, item, header, icon, body.
 */
export class UiAccordion extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-accordion.css", import.meta.url).href];
  static observedAttributes = ["always-open", "variant", "sm", "flush", "gap"];

  #stopObserving = null;
  #openObserver;
  #items = [];
  #name = `ui-accordion-${(groups += 1)}`;
  #headings = new WeakMap();

  constructor() {
    super();
    this.shadowRoot.addEventListener("toggle", (event) => {
      const item = this.#items[Number(event.target.dataset?.index)];
      if (!item) {
        return;
      }
      const open = event.newState === "open";
      item.toggleAttribute("open", open);
      item.dispatchEvent(new CustomEvent("ui-accordion-item:toggle", { bubbles: true, detail: { open } }));
    }, true);
    // Open state goes straight to the details element: a full render while toggle events are still queued
    // would restore stale states (toggle events arrive a task later).
    this.#openObserver = new MutationObserver((records) => records.forEach(({ target }) => {
      const details = this.#detailsOf(target);
      if (details && details.open !== target.hasAttribute("open")) {
        details.open = target.hasAttribute("open");
      }
    }));
  }

  #detailsOf(item) {
    const index = this.#items.indexOf(item);
    return index < 0 ? null : this.shadowRoot.querySelector(`details[data-index="${index}"]`);
  }

  connectedCallback() {
    super.connectedCallback();
    this.#stopObserving ??= observeItems(this, ["heading", "disabled", "slot"], () => this.requestRender());
    this.#openObserver.observe(this, { subtree: true, attributes: true, attributeFilter: ["open"] });
  }

  disconnectedCallback() {
    this.#stopObserving?.();
    this.#stopObserving = null;
    this.#openObserver.disconnect();
  }

  renderShadow() {
    morph(this.shadowRoot, this.render());
  }

  get items() {
    return [...this.#items];
  }

  /** A rich heading (child with slot="heading") moves next to its item: only direct children can be slotted. */
  #headingOf(item, index) {
    let heading = this.#headings.get(item);
    const inner = [...item.children].find((child) => child.slot === "heading");
    if (inner) {
      heading = inner;
      this.#headings.set(item, heading);
      item.before(heading);
    }
    if (heading && heading.isConnected && heading.parentElement === this) {
      if (heading.slot !== `heading-${index}`) {
        // An attribute write records a mutation even with the same value: only write changes.
        heading.slot = `heading-${index}`;
      }
      return `<slot name="heading-${index}"></slot>`;
    }
    return escapeHtml(item.getAttribute("heading") || `Item ${index + 1}`);
  }

  render() {
    this.#items = assignItemSlots(this, "ui-accordion-item", "item");
    const icon = [...this.children].find((child) => child.slot === "icon");
    const iconMarkup = icon ? (() => {
      const copy = icon.cloneNode(true);
      copy.removeAttribute("slot");
      copy.classList.add("accordion-icon");
      copy.setAttribute("part", "icon");
      return copy.outerHTML;
    })() : ICON;
    const variant = themeColor(this.getAttribute("variant"));
    const classes = ["accordion", HOST_TOKENS_CLASS, variant ? `theme-${variant}` : "", this.hasAttribute("sm") ? "accordion-sm" : "",
      this.hasAttribute("flush") ? "accordion-flush" : "", this.hasAttribute("gap") ? "accordion-gap" : ""].filter(Boolean).join(" ");
    const name = this.hasAttribute("always-open") ? "" : ` name="${this.#name}"`;
    const items = this.#items.map((item, index) => {
      const disabled = item.hasAttribute("disabled");
      return `<details class="accordion-item" part="item" data-index="${index}"${name}${item.hasAttribute("open") ? " open" : ""}${disabled ? ' aria-disabled="true"' : ""}>`
        + `<summary class="accordion-header" part="header"${disabled ? ' tabindex="-1"' : ""}>${this.#headingOf(item, index)}${iconMarkup}</summary>`
        + `<div class="accordion-body" part="body"><slot name="item-${index}"></slot></div></details>`;
    });
    return `<div class="${classes}" part="accordion">${items.join("")}</div>`;
  }

  #setAll(open) {
    const exclusive = !this.hasAttribute("always-open");
    if (open && exclusive) {
      // Opening all needs several open at once: like Bootstrap's demo, the shared name goes away.
      this.toggleAttribute("always-open", true);
    }
    this.#items.forEach((item) => !item.hasAttribute("disabled") && item.toggleAttribute("open", open));
  }

  openAll() {
    this.#setAll(true);
  }

  closeAll() {
    this.#setAll(false);
  }
}

/** One item of a <ui-accordion>; its content is slotted into the rendered body. */
export class UiAccordionItem extends HTMLElement {
  get open() {
    return this.hasAttribute("open");
  }

  set open(value) {
    this.toggleAttribute("open", Boolean(value));
  }
}

registerComponent("ui-accordion", UiAccordion);
registerComponent("ui-accordion-item", UiAccordionItem);
