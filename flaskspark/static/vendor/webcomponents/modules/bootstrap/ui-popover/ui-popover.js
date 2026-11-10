import { registerComponent } from "../../../core/registry.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";
import { installTipDataApi, TipElement } from "../tip-element.js";

/**
 * <ui-popover> (Bootstrap 6 popover: title and body) around its trigger content.
 *
 * Like <ui-tooltip> the box is in the top layer; it holds rich content (slots) and opens on click by default
 * (trigger "hover focus" for hover; a click then pins it open until Escape, a click outside or on the trigger).
 * Only one popover is open at a time.
 *
 * Attributes: heading (or slot "heading"), text (or slot "content"; html: sanitized HTML), placement ("right"
 * default; responsive "top md:right"), trigger, delay, offset ("x,y", default 0,8), custom-class,
 * animation="false", disabled, anchor (selector of an ancestor the box is placed at; the arrow still points at
 * the trigger).
 * Methods and events as <ui-tooltip> (ui-popover:*). Parts: trigger, popover, arrow, header, body.
 *
 * Plain markup works too: data-bs-toggle="popover" data-bs-title="…" data-bs-content="…" (getPopover(element)).
 */
export class UiPopover extends TipElement {
  static kind = "popover";
  static stylesheets = [
    ...BOOTSTRAP_SHADOW_STYLES,
    new URL("../../../core/tip.css", import.meta.url).href,
    new URL("../ui-tooltip/ui-tooltip.css", import.meta.url).href,
  ];
  static observedAttributes = ["heading", "text", "placement", "trigger", "delay", "offset", "html", "custom-class", "animation", "disabled", "anchor"];

  tipOptions() {
    const slots = new Set([...this.children].map((child) => child.slot));
    const anchor = this.getAttribute("anchor");
    return {
      ...super.tipOptions(),
      title: this.getAttribute("heading") || "",
      titleSlot: slots.has("heading") ? "heading" : "",
      content: this.getAttribute("text") || "",
      contentSlot: slots.has("content") ? "content" : "",
      reference: anchor ? this.closest(anchor) || undefined : undefined,
    };
  }
}

registerComponent("ui-popover", UiPopover);

export const getPopover = installTipDataApi("popover");
