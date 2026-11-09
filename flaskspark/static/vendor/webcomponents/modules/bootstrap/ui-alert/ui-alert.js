import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { afterTransition } from "../../../core/transitions.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";

// Bootstrap 6 colours an alert with a .theme-* class; without one it is neutral.
const VARIANTS = new Set([
  "primary",
  "accent",
  "secondary",
  "success",
  "danger",
  "warning",
  "info",
  "inverse",
]);
// Bootstrap 5 variant names that have a Bootstrap 6 counterpart.
const LEGACY_VARIANTS = new Map([["dark", "inverse"]]);

/**
 * <ui-alert> (Bootstrap 6).
 *
 * Attributes:
 * - variant: primary (default), accent, secondary, success, danger, warning,
 *   info, inverse, or "neutral" for no colour. "dark" maps to inverse.
 * - dismissible: renders a close button and fades out on dismiss.
 *
 * Slots: default (body), "heading" (styled like .alert-heading).
 * Parts: alert, content, close.
 *
 * Methods / events:
 * - close(): fades the alert out and hides the host element.
 * - ui-alert:closed (bubbles) after the alert is hidden.
 */
export class UiAlert extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-alert.css", import.meta.url).href];
  static observedAttributes = ["variant", "dismissible"];

  #closing = false;

  get variant() {
    const raw = (this.getAttribute("variant") || "primary").trim().toLowerCase();
    const mapped = LEGACY_VARIANTS.get(raw) || raw;
    if (mapped === "neutral") {
      return "";
    }
    return VARIANTS.has(mapped) ? mapped : "primary";
  }

  render() {
    const variant = this.variant;
    const dismissible = this.hasAttribute("dismissible");
    return `
      <div class="alert${variant ? ` theme-${escapeHtml(variant)}` : ""}" role="alert" part="alert">
        <div class="ui-alert-content" part="content">
          <slot name="heading"></slot>
          <slot></slot>
        </div>
        ${dismissible ? '<button type="button" class="btn-close" aria-label="Close" part="close"></button>' : ""}
      </div>
    `;
  }

  afterRender() {
    this.shadowRoot.querySelector(".btn-close")?.addEventListener("click", () => this.close());
  }

  close() {
    if (this.#closing || this.hidden) {
      return;
    }
    const alertNode = this.shadowRoot?.querySelector(".alert");
    if (!alertNode) {
      this.hidden = true;
      return;
    }
    this.#closing = true;
    // Bootstrap 6 animates the exit with .hiding (opacity transition).
    alertNode.classList.add("hiding");
    afterTransition(alertNode, () => {
      this.hidden = true;
      this.#closing = false;
      alertNode.classList.remove("hiding");
      this.dispatchEvent(new CustomEvent("ui-alert:closed", { bubbles: true }));
    });
  }
}

registerComponent("ui-alert", UiAlert);
