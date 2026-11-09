import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";

const VARIANTS = new Set([
  "primary",
  "secondary",
  "success",
  "danger",
  "warning",
  "info",
  "light",
  "dark",
]);

/**
 * <ui-list-group> container.
 *
 * Attributes:
 * - flush: removes outer borders and radii (mirrored onto the items).
 */
export class UiListGroup extends ShadowComponentElement {
  static stylesheet = new URL("./ui-list-group.css", import.meta.url).href;
  static observedAttributes = ["flush"];

  #knownItems = [];

  render() {
    return `
      <div class="list-group${this.hasAttribute("flush") ? " list-group-flush" : ""}" role="list">
        <slot></slot>
      </div>
    `;
  }

  afterRender() {
    // Re-rendering recreates the slot, which fires slotchange again — only
    // re-sync when the item set actually changed, or this would loop.
    this.#knownItems = this.getItems();
    this.shadowRoot.querySelector("slot").addEventListener("slotchange", () => {
      if (this.#itemsChanged()) {
        this.#syncItems();
      }
    });
    this.#syncItems();
  }

  getItems() {
    return Array.from(this.querySelectorAll(":scope > ui-list-group-item"));
  }

  #itemsChanged() {
    const items = this.getItems();
    const unchanged = items.length === this.#knownItems.length
      && items.every((item, index) => item === this.#knownItems[index]);
    if (unchanged) {
      return false;
    }
    this.#knownItems = items;
    return true;
  }

  #syncItems() {
    const flush = this.hasAttribute("flush");
    this.getItems().forEach((item) => {
      item.toggleAttribute("flush", flush);
    });
  }
}

/**
 * <ui-list-group-item>.
 *
 * Attributes:
 * - href: renders an actionable link item.
 * - action: hover/focus styles for clickable items (implied by href).
 * - active / disabled: item state.
 * - variant: contextual background (list-group-item-*).
 */
export class UiListGroupItem extends ShadowComponentElement {
  static stylesheet = new URL("./ui-list-group.css", import.meta.url).href;
  static observedAttributes = ["href", "action", "active", "disabled", "variant"];

  render() {
    const href = this.getAttribute("href");
    const active = this.hasAttribute("active");
    const disabled = this.hasAttribute("disabled");
    const classes = ["list-group-item"];
    if (href || this.hasAttribute("action")) {
      classes.push("list-group-item-action");
    }
    const variant = this.getAttribute("variant");
    if (VARIANTS.has(variant)) {
      classes.push(`list-group-item-${variant}`);
    }
    if (active) {
      classes.push("active");
    }
    if (disabled) {
      classes.push("disabled");
    }

    if (href) {
      return `
        <a
          class="${escapeHtml(classes.join(" "))}"
          href="${escapeHtml(href)}"
          ${active ? 'aria-current="true"' : ""}
          ${disabled ? 'aria-disabled="true" tabindex="-1"' : ""}
        ><slot></slot></a>
      `;
    }
    return `
      <div class="${escapeHtml(classes.join(" "))}" role="listitem" ${active ? 'aria-current="true"' : ""}>
        <slot></slot>
      </div>
    `;
  }
}

registerComponent("ui-list-group", UiListGroup);
registerComponent("ui-list-group-item", UiListGroupItem);
