import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { spriteIcon } from "../../../core/icons.js";
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
 * - heading: a title in the header (styled through part "heading"); with it the header is a row: icon, heading
 *   and the "header" slot at the start, the "actions" slot at the end.
 * - icon: an icon in front of the heading, by name from the page's icon sprite (webcomponents/core/icons.js:
 *   <meta name="ui-icon-sprite">); the "icon" slot takes any markup instead. Colour: --ui-card-icon-color.
 * - collapsible: the header folds the card away (a button with a chevron at the end); collapsed: folded (only
 *   the header shows). Toggling sets collapsed and fires "ui-card:toggle" (detail {collapsed}).
 * - toggle-label: the toggle's accessible name when there is no heading (default "Toggle").
 *
 * Slots (each part is only rendered when it has content, so Bootstrap's
 * sibling rules apply): header, image-top, image-start, image (background of
 * an overlay card), overlay, default (the card body; also eyebrow, title,
 * subtitle, text, link), list (a <ui-list-group flush>), image-end,
 * image-bottom, footer. Body content keeps the page's .card-title,
 * .card-subtitle and .card-text classes.
 * Slots of the header row (heading, icon or collapsible set, or "actions"/"icon" filled): icon, header (after the
 * heading), actions (at the end, outside the toggle).
 * Parts: card, header, body, list, footer, image-top, image-bottom,
 * image-start, image-end, image, overlay; header row: title, icon, heading, actions, toggle, chevron.
 * Custom properties: --ui-card-icon-color, --ui-card-heading-gap.
 *
 * Inside a <ui-card-group> the cards are attached to each other.
 */
export class UiCard extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-card.css", import.meta.url).href];
  static documentStylesheet = new URL("./ui-card.document.css", import.meta.url).href;
  static observedAttributes = ["variant", "subtle", "translucent", "row", "align", "shadow", "card-class", "body-class",
    "heading", "icon", "collapsible", "collapsed", "toggle-label"];
  static morphChildren = true; // its children are only slotted: morph() patches them instead of replacing the card

  #stopObserving = null;

  connectedCallback() {
    super.connectedCallback();
    this.#stopObserving ??= observeItems(this, ["slot"], () => this.requestRender());
    if (!this.#listening) {
      this.#listening = true;
      this.shadowRoot.addEventListener("click", (event) => {
        if (event.target.closest?.("[data-ui-card-toggle]")) this.toggle();
      });
    }
  }

  #listening = false;

  /** Folds the card (collapsible) or unfolds it; force: true folds, false unfolds. */
  toggle(force) {
    const collapsed = force === undefined ? !this.hasAttribute("collapsed") : Boolean(force);
    if (collapsed === this.hasAttribute("collapsed")) return;
    this.toggleAttribute("collapsed", collapsed);
    this.dispatchEvent(new CustomEvent("ui-card:toggle", { bubbles: true, composed: true, detail: { collapsed } }));
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

  /** The header as a row (heading, icon, actions, toggle), or "" when the plain header slot is enough. */
  headerRow(filled) {
    const heading = this.getAttribute("heading") || "";
    const iconName = this.getAttribute("icon") || "";
    const collapsible = this.hasAttribute("collapsible");
    if (!heading && !iconName && !collapsible && !filled.has("actions") && !filled.has("icon")) return "";
    const icon = filled.has("icon") || iconName
      ? `<span class="ui-card-icon" part="icon"><slot name="icon">${spriteIcon(iconName)}</slot></span>`
      : "";
    const title = `${icon}${heading ? `<span class="ui-card-heading" part="heading">${escapeHtml(heading)}</span>` : ""}`
      + (filled.has("header") ? '<slot name="header"></slot>' : "");
    const collapsed = this.hasAttribute("collapsed");
    const start = collapsible
      ? `<button type="button" class="ui-card-title ui-card-toggle" part="title toggle" data-ui-card-toggle aria-expanded="${!collapsed}"`
        + `${heading ? "" : ` aria-label="${escapeHtml(this.getAttribute("toggle-label") || "Toggle")}"`}>${title}`
        + '<svg class="ui-card-chevron" part="chevron" viewBox="0 0 16 16" width="1em" height="1em" fill="none" stroke="currentColor"'
        + ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 3 5 5-5 5"/></svg></button>'
      : `<div class="ui-card-title" part="title">${title}</div>`;
    const actions = filled.has("actions") ? '<div class="ui-card-actions" part="actions"><slot name="actions"></slot></div>' : "";
    return `<div class="card-header ui-card-head" part="header">${start}${actions}</div>`;
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
    if (this.hasAttribute("collapsible") && this.hasAttribute("collapsed")) {
      // Folded: only the header (the other slots stay unassigned, so their content is not shown; a page's
      // ::part(body) rule cannot bring it back).
      return `<div class="${escapeHtml(this.cardClasses())}" part="card">${this.headerRow(filled)}</div>`;
    }
    return `
      <div class="${escapeHtml(this.cardClasses())}" part="card">${[
        this.headerRow(filled) || part("header", "card-header"),
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
