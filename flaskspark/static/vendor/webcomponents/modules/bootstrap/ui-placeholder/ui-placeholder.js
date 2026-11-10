import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { morph } from "../../../core/morph.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

const SIZES = new Set(["lg", "sm", "xs"]);

/**
 * <ui-placeholder> (Bootstrap 6 placeholder): a loading placeholder (skeleton) block, sized by the text around it.
 *
 * Attributes: width (grid columns 1–12 of its line, or any CSS width, e.g. "75%"), size (lg, sm, xs),
 * animation (wave, pulse; glow is pulse), variant (theme colour; default the current text colour).
 * Several in a row: they are inline, like Bootstrap's spans. Parts: placeholder.
 */
export class UiPlaceholder extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-placeholder.css", import.meta.url).href];
  static observedAttributes = ["width", "size", "animation", "variant"];

  renderShadow() {
    morph(this.shadowRoot, this.render());
    this.#applyWidth();
  }

  #applyWidth() {
    const width = (this.getAttribute("width") || "").trim();
    const columns = Number.parseInt(width, 10);
    if (/^\d+$/.test(width) && columns >= 1 && columns <= 12) {
      this.style.setProperty("--ui-placeholder-width", `${(columns / 12) * 100}%`);
    } else if (width) {
      this.style.setProperty("--ui-placeholder-width", width);
    } else {
      this.style.removeProperty("--ui-placeholder-width");
    }
  }

  render() {
    const animation = { wave: "placeholder-wave", pulse: "placeholder-pulse", glow: "placeholder-pulse" }[this.getAttribute("animation")] || "";
    const size = SIZES.has(this.getAttribute("size")) ? `placeholder-${this.getAttribute("size")}` : "";
    const variant = themeColor(this.getAttribute("variant"));
    const classes = ["placeholder", HOST_TOKENS_CLASS, size, variant ? `bg-${variant}` : ""].filter(Boolean).join(" ");
    return `<span class="${animation || "ui-placeholder-static"}" aria-hidden="true"><span class="${classes}" part="placeholder"></span></span>`;
  }
}

registerComponent("ui-placeholder", UiPlaceholder);
