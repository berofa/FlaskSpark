import { registerComponent } from "../../../core/registry.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";
import { installTipDataApi, TipElement } from "../tip-element.js";

/**
 * <ui-tooltip> (Bootstrap 6 tooltip) around its trigger content.
 *
 * The box is in the top layer (never clipped); shows on hover and focus by default, hides on Escape; it follows
 * the trigger while the page scrolls and flips when there is no room. Plain-text triggers get tabindex="0".
 *
 * Attributes: text (or the slot "content" for rich content; html: the text is sanitized HTML), placement
 * ("top" default; right, bottom, left, responsive "top md:right"), trigger ("hover focus", "click", "manual"),
 * delay, offset ("x,y", default 0,6), custom-class, animation="false", disabled.
 * Methods: show(), hide(), toggle(), update(), enable(), disable(), setContent({ title }).
 * Events (bubble): ui-tooltip:show / ui-tooltip:hide (cancelable), ui-tooltip:shown, ui-tooltip:hidden,
 * ui-tooltip:inserted. Parts: trigger, tooltip, arrow, inner.
 *
 * Plain markup works too: data-bs-toggle="tooltip" data-bs-title="…" on any element (getTooltip(element)
 * returns its controller).
 */
export class UiTooltip extends TipElement {
  static kind = "tooltip";
  static stylesheets = [
    ...BOOTSTRAP_SHADOW_STYLES,
    new URL("../../../core/tip.css", import.meta.url).href,
    new URL("./ui-tooltip.css", import.meta.url).href,
  ];
  static observedAttributes = ["text", "placement", "trigger", "delay", "offset", "html", "custom-class", "animation", "disabled"];

  tipOptions() {
    const hasSlot = [...this.children].some((child) => child.slot === "content");
    return { ...super.tipOptions(), title: this.getAttribute("text") || "", titleSlot: hasSlot ? "content" : "" };
  }
}

registerComponent("ui-tooltip", UiTooltip);

export const getTooltip = installTipDataApi("tooltip");
