import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { morph } from "../../../core/morph.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";
import { trendOf, trendVariant } from "./kpi-trend.js";

const SIZES = new Set(["sm", "lg"]);
const ARROWS = {
  up: '<path d="M8 3.5 13 10H3z"/>',
  down: '<path d="M8 12.5 3 6h10z"/>',
  flat: '<path d="M3 7h10v2H3z"/>',
};

/**
 * <ui-kpi>: a key figure as a small tile: a label, the value, an optional line below (e.g. a comparison) and an
 * optional trend arrow.
 *
 * Attributes:
 * - label: the caption above the value (or the "label" slot, e.g. with a tooltip).
 * - value: the value as text (or the default slot, for markup such as a coloured amount).
 * - sub: a line below the value (or the "sub" slot).
 * - variant: theme colour of the value (success, danger, …).
 * - size: "sm" (compact) or "lg" (an emphasised figure, e.g. a total).
 * - trend: up, down or flat (also a number: its sign); an arrow in front of the value, green up and red down.
 * - trend-inverse: red up and green down (e.g. costs).
 * - trend-up-label / trend-down-label / trend-flat-label: the arrow's text for screen readers
 *   ("Rising", "Falling", "Unchanged").
 * Slots: label, (default) the value, sub.
 * Parts: kpi, label, value, trend, sub.
 * Inside a <ui-kpi-group> the tiles share a responsive grid.
 */
export class UiKpi extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-kpi.css", import.meta.url).href];
  static observedAttributes = ["label", "value", "sub", "variant", "size", "trend", "trend-inverse",
    "trend-up-label", "trend-down-label", "trend-flat-label"];

  renderShadow() {
    morph(this.shadowRoot, this.render());
  }

  render() {
    const size = (this.getAttribute("size") || "").trim().toLowerCase();
    const variant = themeColor(this.getAttribute("variant"));
    const trend = trendOf(this.getAttribute("trend"));
    const trendColor = trendVariant(trend, this.hasAttribute("trend-inverse"));
    const labels = { up: "Rising", down: "Falling", flat: "Unchanged" };
    const trendLabel = trend ? this.getAttribute(`trend-${trend}-label`) ?? labels[trend] : "";
    const has = (slot) => [...this.children].some((child) => child.slot === slot);
    const hasValue = [...this.childNodes].some((node) => (node.nodeType === Node.ELEMENT_NODE && !node.slot)
      || (node.nodeType === Node.TEXT_NODE && node.textContent.trim()));
    const sub = this.getAttribute("sub") || "";
    const arrow = trend
      ? `<svg class="ui-kpi-trend${trendColor ? ` fg-${trendColor}` : " fg-3"}" part="trend" viewBox="0 0 16 16" width="0.8em" height="0.8em"`
        + ` fill="currentColor" role="img" aria-label="${escapeHtml(trendLabel)}">${ARROWS[trend]}</svg>`
      : "";
    return `<div class="ui-kpi${SIZES.has(size) ? ` ui-kpi-${size}` : ""}" part="kpi">`
      + `<span class="ui-kpi-label" part="label"><slot name="label">${escapeHtml(this.getAttribute("label") || "")}</slot></span>`
      + `<span class="ui-kpi-value${variant ? ` fg-${variant}` : ""}" part="value">${arrow}`
      + `<span class="ui-kpi-text">${hasValue ? "<slot></slot>" : escapeHtml(this.getAttribute("value") ?? "")}</span></span>`
      + (sub || has("sub") ? `<span class="ui-kpi-sub" part="sub"><slot name="sub">${escapeHtml(sub)}</slot></span>` : "")
      + "</div>";
  }
}

/**
 * <ui-kpi-group>: key figures in a responsive grid (as many columns as fit, each at least --ui-kpi-group-min wide).
 * Attributes: compact (narrower tiles, smaller gaps; the tiles inside become size="sm" unless they have a size).
 * Parts: group.
 */
export class UiKpiGroup extends ShadowComponentElement {
  static stylesheets = [new URL("./ui-kpi.css", import.meta.url).href];
  static observedAttributes = ["compact"];

  #slot = null;

  render() {
    return '<div class="ui-kpi-group" part="group"><slot></slot></div>';
  }

  afterRender() {
    const slot = this.shadowRoot.querySelector("slot");
    if (slot !== this.#slot) {
      this.#slot = slot;
      slot.addEventListener("slotchange", () => this.#syncSize());
    }
    this.#syncSize();
  }

  /** compact: the tiles without a size of their own become small (marked, so they grow again without compact). */
  #syncSize() {
    const compact = this.hasAttribute("compact");
    for (const kpi of this.querySelectorAll(":scope > ui-kpi")) {
      if (compact && !kpi.hasAttribute("size")) {
        kpi.setAttribute("size", "sm");
        kpi.dataset.uiKpiCompact = "";
      } else if (!compact && "uiKpiCompact" in kpi.dataset) {
        kpi.removeAttribute("size");
        delete kpi.dataset.uiKpiCompact;
      }
    }
  }
}

registerComponent("ui-kpi", UiKpi);
registerComponent("ui-kpi-group", UiKpiGroup);
