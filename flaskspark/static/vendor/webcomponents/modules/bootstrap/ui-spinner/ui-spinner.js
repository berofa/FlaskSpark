import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { morph } from "../../../core/morph.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

/**
 * <ui-spinner> (Bootstrap 6 spinner): a loading indicator in the current text colour.
 *
 * Attributes: type (border, default, or grow), size ("sm"), variant (theme colour of the text), label (the
 * screen-reader text, default "Loading…"; label="" for a decorative spinner, e.g. next to a visible text).
 * A child svg in the slot "icon" is rotated instead (.spinner-rotate). Parts: spinner.
 */
export class UiSpinner extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-spinner.css", import.meta.url).href];
  static observedAttributes = ["type", "size", "variant", "label"];

  renderShadow() {
    morph(this.shadowRoot, this.render());
  }

  render() {
    const variant = themeColor(this.getAttribute("variant"));
    const label = this.getAttribute("label") ?? "Loading…";
    const a11y = label ? ` role="status"><span class="visually-hidden">${escapeHtml(label)}</span>` : ' aria-hidden="true">';
    if (this.querySelector(':scope > [slot="icon"]')) {
      return `<span class="spinner-rotate ui-spinner-icon${variant ? ` fg-${variant}` : ""}" part="spinner"${a11y}<slot name="icon"></slot></span>`;
    }
    const type = this.getAttribute("type") === "grow" ? "grow" : "border";
    const classes = [`spinner-${type}`, HOST_TOKENS_CLASS, this.getAttribute("size") === "sm" ? "spinner-sm" : "",
      variant ? `fg-${variant}` : ""].filter(Boolean).join(" ");
    return `<span class="${classes}" part="spinner"${a11y}</span>`;
  }
}

registerComponent("ui-spinner", UiSpinner);
