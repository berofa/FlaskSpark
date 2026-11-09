import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { collapseElement, expandElement } from "../../../core/collapse-transition.js";

/**
 * <ui-accordion> container.
 *
 * Attributes:
 * - flush: renders items edge-to-edge (mirrored onto child items).
 * - always-open: opening an item no longer closes its siblings.
 */
export class UiAccordion extends ShadowComponentElement {
  static stylesheet = new URL("./ui-accordion.css", import.meta.url).href;
  static observedAttributes = ["flush", "always-open"];

  constructor() {
    super();
    // Bound once on the host element, so re-renders never stack handlers.
    this.addEventListener("ui-accordion-item:toggle", (event) => this.#onItemToggle(event));
  }

  render() {
    return `
      <div class="accordion">
        <slot></slot>
      </div>
    `;
  }

  afterRender() {
    this.shadowRoot.querySelector("slot").addEventListener("slotchange", () => this.#syncItems());
    this.#syncItems();
  }

  getItems() {
    // Exclude items of nested accordions.
    return Array.from(this.querySelectorAll("ui-accordion-item"))
      .filter((item) => item.closest("ui-accordion") === this);
  }

  #syncItems() {
    const flush = this.hasAttribute("flush");
    this.getItems().forEach((item) => {
      item.toggleAttribute("flush", flush);
    });
  }

  #onItemToggle(event) {
    if (!event.detail?.open || this.hasAttribute("always-open")) {
      return;
    }
    if (event.target.closest("ui-accordion") !== this) {
      return;
    }
    this.getItems().forEach((item) => {
      if (item !== event.target && item.expanded) {
        item.collapse();
      }
    });
  }
}

/**
 * <ui-accordion-item> panel.
 *
 * Attributes:
 * - heading: plain-text header label (use the "heading" slot for rich content).
 * - open: expanded state; reflected when the user toggles the panel.
 *
 * Events:
 * - ui-accordion-item:toggle (bubbles) with detail.open after each toggle.
 */
export class UiAccordionItem extends ShadowComponentElement {
  static stylesheet = new URL("./ui-accordion.css", import.meta.url).href;
  static observedAttributes = ["heading", "open"];

  #suppressOpenAttribute = false;
  #animating = false;

  attributeChangedCallback(name, oldValue, newValue) {
    // Internal toggles animate the DOM directly and only reflect the state;
    // re-rendering here would cut the transition short.
    if (name === "open" && this.#suppressOpenAttribute) {
      return;
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  get expanded() {
    return this.hasAttribute("open");
  }

  render() {
    const heading = this.getAttribute("heading") || "";
    const open = this.expanded;
    return `
      <div class="accordion-item">
        <h2 class="accordion-header">
          <button class="accordion-button${open ? "" : " collapsed"}" type="button" aria-expanded="${open ? "true" : "false"}">
            <slot name="heading">${escapeHtml(heading)}</slot>
          </button>
        </h2>
        <div class="accordion-collapse collapse${open ? " show" : ""}">
          <div class="accordion-body">
            <slot></slot>
          </div>
        </div>
      </div>
    `;
  }

  afterRender() {
    this.shadowRoot.querySelector(".accordion-button").addEventListener("click", () => this.toggle());
  }

  toggle() {
    if (this.expanded) {
      this.collapse();
    } else {
      this.expand();
    }
  }

  expand() {
    if (this.#animating || this.expanded) {
      return;
    }
    const collapseNode = this.shadowRoot?.querySelector(".accordion-collapse");
    if (!collapseNode) {
      this.#reflectOpen(true);
      return;
    }
    this.#animating = true;
    this.#setButtonExpanded(true);
    expandElement(collapseNode, {
      onComplete: () => {
        this.#animating = false;
      },
    });
    this.#reflectOpen(true);
    this.#dispatchToggle(true);
  }

  collapse() {
    if (this.#animating || !this.expanded) {
      return;
    }
    const collapseNode = this.shadowRoot?.querySelector(".accordion-collapse");
    if (!collapseNode) {
      this.#reflectOpen(false);
      return;
    }
    this.#animating = true;
    this.#setButtonExpanded(false);
    collapseElement(collapseNode, {
      onComplete: () => {
        this.#animating = false;
      },
    });
    this.#reflectOpen(false);
    this.#dispatchToggle(false);
  }

  #setButtonExpanded(open) {
    const button = this.shadowRoot?.querySelector(".accordion-button");
    button?.classList.toggle("collapsed", !open);
    button?.setAttribute("aria-expanded", open ? "true" : "false");
  }

  #reflectOpen(open) {
    this.#suppressOpenAttribute = true;
    this.toggleAttribute("open", open);
    this.#suppressOpenAttribute = false;
  }

  #dispatchToggle(open) {
    this.dispatchEvent(new CustomEvent("ui-accordion-item:toggle", {
      bubbles: true,
      detail: { open },
    }));
  }
}

registerComponent("ui-accordion", UiAccordion);
registerComponent("ui-accordion-item", UiAccordionItem);
