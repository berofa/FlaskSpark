import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { morph } from "../../../core/morph.js";
import { assignItemSlots, observeItems } from "../../../core/slotted-items.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

const clampRatio = (value, min, max) => (max > min ? Math.min(Math.max((value - min) / (max - min), 0), 1) : 0);

/** The bar classes of a variant / striped / animated element. */
function barClasses(element) {
  const variant = themeColor(element.getAttribute("variant"));
  return ["progress-bar", variant ? `theme-${variant}` : "", element.hasAttribute("striped") || element.hasAttribute("animated") ? "progress-bar-striped" : "",
    element.hasAttribute("animated") ? "progress-bar-animated" : ""].filter(Boolean).join(" ");
}

function numberOf(element, name, fallback) {
  const value = Number.parseFloat(element.getAttribute(name));
  return Number.isNaN(value) ? fallback : value;
}

/**
 * <ui-progress> (Bootstrap 6 progress): a progress bar (role="progressbar" with aria values), or with
 * <ui-progress-bar> children a stacked bar of several segments.
 *
 * Attributes: value, min (0), max (100), label (accessible name), show-value (the percentage in the bar) or a
 * text in the default slot, variant (theme colour), striped, animated (moving stripes).
 * <ui-progress-bar>: value, variant, striped, animated, label; its text is shown in the segment.
 * Property value (number). Parts: progress, bar, segment.
 */
export class UiProgress extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-progress.css", import.meta.url).href];
  static observedAttributes = ["value", "min", "max", "label", "show-value", "variant", "striped", "animated"];

  #stopObserving = null;

  connectedCallback() {
    super.connectedCallback();
    this.#stopObserving ??= observeItems(this, ["value", "variant", "striped", "animated", "label"], () => this.requestRender());
  }

  disconnectedCallback() {
    this.#stopObserving?.();
    this.#stopObserving = null;
  }

  get value() {
    return numberOf(this, "value", 0);
  }

  set value(value) {
    this.setAttribute("value", String(value));
  }

  renderShadow() {
    morph(this.shadowRoot, this.render());
  }

  render() {
    const min = numberOf(this, "min", 0);
    const max = numberOf(this, "max", 100);
    const segments = assignItemSlots(this, "ui-progress-bar", "segment");
    if (segments.length) {
      const parts = segments.map((segment, index) => {
        const value = numberOf(segment, "value", 0);
        const label = segment.getAttribute("label") || "";
        return `<div class="progress ${HOST_TOKENS_CLASS}" part="segment" role="progressbar" aria-valuenow="${value}" aria-valuemin="${min}" `
          + `aria-valuemax="${max}"${label ? ` aria-label="${escapeHtml(label)}"` : ""} style="width: ${clampRatio(value, min, max) * 100}%">`
          + `<div class="${barClasses(segment)}" part="bar"><slot name="segment-${index}"></slot></div></div>`;
      });
      return `<div class="progress-stacked ${HOST_TOKENS_CLASS}" part="progress">${parts.join("")}</div>`;
    }
    const value = this.value;
    const ratio = clampRatio(value, min, max);
    const label = this.getAttribute("label");
    const text = this.hasAttribute("show-value") ? `${Math.round(ratio * 100)}%` : "<slot></slot>";
    return `<div class="progress ${HOST_TOKENS_CLASS}" part="progress" role="progressbar" aria-valuenow="${value}" aria-valuemin="${min}" `
      + `aria-valuemax="${max}"${label ? ` aria-label="${escapeHtml(label)}"` : ""}>`
      + `<div class="${barClasses(this)}" part="bar" style="width: ${ratio * 100}%">${text}</div></div>`;
  }
}

/** One segment of a stacked <ui-progress> (attributes value, variant, striped, animated, label; text: shown in it). */
export class UiProgressBar extends HTMLElement {}

registerComponent("ui-progress", UiProgress);
registerComponent("ui-progress-bar", UiProgressBar);
