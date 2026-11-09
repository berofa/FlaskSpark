import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { morph } from "../../../core/morph.js";
import { assignItemSlots, observeItems } from "../../../core/slotted-items.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";

const ITEM_ATTRIBUTES = ["href", "active", "target", "rel"];

/**
 * <ui-breadcrumb> (Bootstrap 6 breadcrumb) with <ui-breadcrumb-item> children.
 *
 * Attributes:
 * - label: aria-label of the nav landmark (default "Breadcrumb").
 * - divider: text divider between items (e.g. "/" or "›"). Without it, a
 *   child element with slot="divider" (e.g. an SVG in currentColor) is used,
 *   else Bootstrap's chevron (--bs-breadcrumb-divider-icon).
 *
 * <ui-breadcrumb-item> attributes: href (+ target, rel) renders a link;
 * active marks the current page (aria-current="page").
 *
 * The items are rendered inside the breadcrumb's shadow tree (one slot each),
 * so Bootstrap's markup works unchanged. Parts: nav, list, item, link, divider.
 */
export class UiBreadcrumb extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-breadcrumb.css", import.meta.url).href];
  static observedAttributes = ["label", "divider"];

  #stopObserving = null;

  connectedCallback() {
    super.connectedCallback();
    this.#stopObserving ??= observeItems(this, [...ITEM_ATTRIBUTES, "slot"], () => this.requestRender());
  }

  disconnectedCallback() {
    this.#stopObserving?.();
    this.#stopObserving = null;
  }

  renderShadow() {
    morph(this.shadowRoot, this.render());
  }

  dividerMarkup() {
    if (this.hasAttribute("divider")) {
      return escapeHtml(this.getAttribute("divider"));
    }
    const custom = [...this.children].find((child) => child.slot === "divider");
    if (!custom) {
      return "";
    }
    // The author's own markup (e.g. an SVG), repeated between the items.
    const copy = custom.cloneNode(true);
    copy.removeAttribute("slot");
    return copy.outerHTML;
  }

  render() {
    const label = this.getAttribute("label") || "Breadcrumb";
    const divider = this.dividerMarkup();
    const items = assignItemSlots(this, "ui-breadcrumb-item", "item");
    const parts = items.map((item, index) => {
      const active = item.hasAttribute("active");
      const href = item.getAttribute("href");
      const slot = `<slot name="item-${index}"></slot>`;
      const linkClass = `breadcrumb-link${active ? " active" : ""}`;
      const link = href
        ? `<a class="${linkClass}" part="link" href="${escapeHtml(href)}"`
          + `${item.hasAttribute("target") ? ` target="${escapeHtml(item.getAttribute("target"))}"` : ""}`
          + `${item.hasAttribute("rel") ? ` rel="${escapeHtml(item.getAttribute("rel"))}"` : ""}>${slot}</a>`
        : `<span class="${linkClass}" part="link">${slot}</span>`;
      const entry = `<li class="breadcrumb-item" part="item"${active ? ' aria-current="page"' : ""}>${link}</li>`;
      return index === 0 ? entry : `<li class="breadcrumb-divider" part="divider" aria-hidden="true">${divider}</li>${entry}`;
    });
    return `
      <nav aria-label="${escapeHtml(label)}" part="nav">
        <ol class="breadcrumb ${HOST_TOKENS_CLASS}" part="list">${parts.join("")}</ol>
      </nav>
    `;
  }
}

/** One page of a <ui-breadcrumb>; its content is slotted into the breadcrumb's link. */
export class UiBreadcrumbItem extends HTMLElement {}

registerComponent("ui-breadcrumb", UiBreadcrumb);
registerComponent("ui-breadcrumb-item", UiBreadcrumbItem);
