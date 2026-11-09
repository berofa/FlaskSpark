import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { morph } from "../../../core/morph.js";
import { observeItems } from "../../../core/slotted-items.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

const SHADOWS = new Set(["xs", "sm", "lg", "xl", "none"]);
const ALIGNMENTS = new Set(["start", "center", "end"]);
// Slots that belong into the card body, in this order (Bootstrap 5 API of ui-card), before the default slot.
const BODY_SLOTS = ["eyebrow", "title", "subtitle", "text", "link"];

/**
 * <ui-card> (Bootstrap 6 card).
 *
 * Attributes:
 * - variant: theme colour (border, header and footer in the theme's colour).
 * - subtle: theme colours as subtle backgrounds (.card-subtle).
 * - translucent: blurred, translucent background (.card-translucent).
 * - row: horizontal card (.card-row) with the image-start / image-end slots.
 * - align: start, center or end (text alignment of the whole card).
 * - shadow: a box shadow ("" or xs, sm, lg, xl, none).
 * - card-class / body-class: further Bootstrap classes for the card or its body.
 *
 * Slots (each part is only rendered when it has content, so Bootstrap's
 * sibling rules apply): header, image-top, image-start, image (background of
 * an overlay card), overlay, default (the card body; also eyebrow, title,
 * subtitle, text, link), list (a <ui-list-group flush>), image-end,
 * image-bottom, footer. Body content keeps the page's .card-title,
 * .card-subtitle and .card-text classes.
 * Parts: card, header, body, list, footer, image-top, image-bottom,
 * image-start, image-end, image, overlay.
 *
 * Inside a <ui-card-group> the cards are attached to each other.
 */
export class UiCard extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-card.css", import.meta.url).href];
  static documentStylesheet = new URL("./ui-card.document.css", import.meta.url).href;
  static observedAttributes = ["variant", "subtle", "translucent", "row", "align", "shadow", "card-class", "body-class"];

  #stopObserving = null;

  connectedCallback() {
    super.connectedCallback();
    this.#stopObserving ??= observeItems(this, ["slot"], () => this.requestRender());
  }

  disconnectedCallback() {
    this.#stopObserving?.();
    this.#stopObserving = null;
  }

  renderShadow() {
    morph(this.shadowRoot, this.render());
  }

  /** Names of the slots that have content; "" for the default slot. */
  filledSlots() {
    const filled = new Set();
    for (const node of this.childNodes) {
      if (node.nodeType === Node.ELEMENT_NODE) {
        filled.add(node.slot || "");
      } else if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
        filled.add("");
      }
    }
    return filled;
  }

  cardClasses() {
    const variant = themeColor(this.getAttribute("variant"));
    const shadow = this.hasAttribute("shadow") ? (this.getAttribute("shadow") || "").trim().toLowerCase() : null;
    const align = (this.getAttribute("align") || "").trim().toLowerCase();
    return [
      "card",
      HOST_TOKENS_CLASS,
      variant ? `theme-${variant}` : "",
      this.hasAttribute("subtle") ? "card-subtle" : "",
      this.hasAttribute("translucent") ? "card-translucent" : "",
      this.hasAttribute("row") ? "card-row" : "",
      ALIGNMENTS.has(align) ? `text-${align}` : "",
      shadow === null ? "" : SHADOWS.has(shadow) ? `shadow-${shadow}` : "shadow",
      this.getAttribute("card-class") || "",
    ].filter(Boolean).join(" ");
  }

  render() {
    const filled = this.filledSlots();
    const part = (slot, className, partName = slot) => (filled.has(slot)
      ? `<div class="${className}" part="${partName}"><slot name="${slot}"></slot></div>`
      : "");
    const hasBody = filled.has("") || BODY_SLOTS.some((name) => filled.has(name));
    const bodyClass = escapeHtml(["card-body", this.getAttribute("body-class") || ""].filter(Boolean).join(" "));
    const body = hasBody
      ? `<div class="${bodyClass}" part="body">${BODY_SLOTS.map((name) => `<slot name="${name}"></slot>`).join("")}<slot></slot></div>`
      : "";
    return `
      <div class="${escapeHtml(this.cardClasses())}" part="card">${[
        part("header", "card-header"),
        part("image-top", "card-img-top ui-card-media"),
        part("image-start", "card-img-start ui-card-media"),
        part("image", "card-img ui-card-media"),
        part("overlay", "card-img-overlay"),
        body,
        part("list", "list-group list-group-flush ui-card-list", "list"),
        part("image-end", "card-img-end ui-card-media"),
        part("image-bottom", "card-img-bottom ui-card-media"),
        part("footer", "card-footer"),
      ].join("")}</div>
    `;
  }
}

/**
 * <ui-card-group>: cards attached to each other with equal width and height
 * (from a width of 576px of the group on; stacked below, like .card-group).
 */
export class UiCardGroup extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-card-group.css", import.meta.url).href];

  #stopObserving = null;

  connectedCallback() {
    super.connectedCallback();
    this.#stopObserving ??= observeItems(this, ["slot"], () => this.markPositions());
  }

  disconnectedCallback() {
    this.#stopObserving?.();
    this.#stopObserving = null;
  }

  render() {
    return '<div class="ui-card-group" part="group"><slot></slot></div>';
  }

  afterRender() {
    this.markPositions();
  }

  /** Tells each card where it sits, so it drops the inner borders and radii. */
  markPositions() {
    const cards = [...this.children].filter((child) => child.localName === "ui-card");
    cards.forEach((card, index) => {
      const position = cards.length === 1 ? "only" : index === 0 ? "first" : index === cards.length - 1 ? "last" : "middle";
      if (card.getAttribute("group-position") !== position) {
        card.setAttribute("group-position", position);
      }
    });
  }
}

registerComponent("ui-card", UiCard);
registerComponent("ui-card-group", UiCardGroup);
