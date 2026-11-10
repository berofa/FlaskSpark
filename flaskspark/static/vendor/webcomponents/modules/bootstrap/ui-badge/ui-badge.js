import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

const APPEARANCES = new Set(["solid", "subtle", "outline"]);

/**
 * <ui-badge> (Bootstrap 6 badge).
 *
 * Attributes:
 * - variant: theme colour (primary, accent, success, danger, warning, info,
 *   inverse, secondary); without one the badge is neutral.
 * - appearance: solid (default), subtle or outline.
 * - pill: fully rounded (rounded-pill).
 * - href (+ target, rel): renders the badge as a link.
 * - badge-class: further Bootstrap classes for the badge itself (utilities
 *   such as "border border-bg"); classes on <ui-badge> style the host
 *   (e.g. position-absolute top-0 start-100 translate-middle).
 *
 * Scales with the font size of its parent (em units). Empty badges are hidden.
 * Part: badge.
 */
export class UiBadge extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-badge.css", import.meta.url).href];
  static observedAttributes = ["variant", "appearance", "pill", "href", "target", "rel", "badge-class"];

  classNames() {
    const variant = themeColor(this.getAttribute("variant"));
    const appearance = (this.getAttribute("appearance") || "solid").trim().toLowerCase();
    return [
      "badge",
      HOST_TOKENS_CLASS,
      APPEARANCES.has(appearance) && appearance !== "solid" ? `badge-${appearance}` : "",
      variant ? `theme-${variant}` : "",
      this.hasAttribute("pill") ? "rounded-pill" : "",
      this.getAttribute("badge-class") || "",
    ].filter(Boolean).join(" ");
  }

  render() {
    const classes = escapeHtml(this.classNames());
    const href = this.getAttribute("href");
    if (href) {
      const target = this.hasAttribute("target") ? ` target="${escapeHtml(this.getAttribute("target"))}"` : "";
      const rel = this.hasAttribute("rel") ? ` rel="${escapeHtml(this.getAttribute("rel"))}"` : "";
      return `<a class="${classes}" part="badge" href="${escapeHtml(href)}"${target}${rel}><slot></slot></a>`;
    }
    return `<span class="${classes}" part="badge"><slot></slot></span>`;
  }
}

registerComponent("ui-badge", UiBadge);
