import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";

const VARIANTS = new Set([
  "primary",
  "secondary",
  "success",
  "danger",
  "warning",
  "info",
  "light",
  "dark",
]);

/**
 * <ui-badge>.
 *
 * Attributes:
 * - variant: Bootstrap variant (default "primary"), rendered as text-bg-*
 *   so the text contrast is handled automatically.
 * - pill: rounded pill shape.
 */
export class UiBadge extends ShadowComponentElement {
  static stylesheet = new URL("./ui-badge.css", import.meta.url).href;
  static observedAttributes = ["variant", "pill"];

  render() {
    const rawVariant = this.getAttribute("variant") || "primary";
    const variant = VARIANTS.has(rawVariant) ? rawVariant : "primary";
    const pill = this.hasAttribute("pill");
    return `
      <span class="badge text-bg-${escapeHtml(variant)}${pill ? " rounded-pill" : ""}">
        <slot></slot>
      </span>
    `;
  }
}

registerComponent("ui-badge", UiBadge);
