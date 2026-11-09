import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { afterTransition } from "../../../core/transitions.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

/**
 * <ui-alert> (Bootstrap 6 alert).
 *
 * Attributes:
 * - variant: theme colour (primary, accent, success, danger, warning, info,
 *   inverse, secondary); without one the alert is neutral. "dark" maps to inverse.
 * - dismissible: renders a close button.
 * - close-label: accessible name of the close button (default "Close").
 * - instant: close at once instead of fading out (.alert-instant).
 *
 * Slots: default (body), "heading" (styled like .alert-heading), "icon"
 * (before the content, e.g. an SVG). Light-DOM elements with
 * data-bs-dismiss="alert" close the alert too.
 * Parts: alert, icon, content, close.
 *
 * Methods / events:
 * - close(): fires ui-alert:close (cancelable), fades out, fires
 *   ui-alert:closed and removes the element. Returns a promise that resolves
 *   once it is removed (false if a listener cancelled it).
 */
export class UiAlert extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-alert.css", import.meta.url).href];
  static documentStylesheet = new URL("./ui-alert.document.css", import.meta.url).href;
  static observedAttributes = ["variant", "dismissible", "close-label", "instant"];

  #closing = null;

  constructor() {
    super();
    this.addEventListener("click", (event) => {
      if (event.target instanceof Element && event.target.closest('[data-bs-dismiss="alert"]')) {
        event.preventDefault();
        this.close();
      }
    });
  }

  get variant() {
    return themeColor(this.getAttribute("variant"));
  }

  render() {
    const variant = this.variant;
    const classes = ["alert", HOST_TOKENS_CLASS, variant ? `theme-${variant}` : "", this.hasAttribute("instant") ? "alert-instant" : ""];
    const closeLabel = this.getAttribute("close-label") || "Close";
    return `
      <div class="${classes.filter(Boolean).join(" ")}" role="alert" part="alert">
        <span class="ui-alert-icon" part="icon"><slot name="icon"></slot></span>
        <div class="ui-alert-content" part="content">
          <slot name="heading"></slot>
          <slot></slot>
        </div>
        ${this.hasAttribute("dismissible")
          ? `<button type="button" class="btn-close" aria-label="${escapeHtml(closeLabel)}" part="close"></button>`
          : ""}
      </div>
    `;
  }

  afterRender() {
    this.shadowRoot.querySelector(".btn-close")?.addEventListener("click", () => this.close());
    const iconSlot = this.shadowRoot.querySelector('slot[name="icon"]');
    const syncIcon = () => {
      iconSlot.parentElement.hidden = iconSlot.assignedNodes().length === 0;
    };
    iconSlot.addEventListener("slotchange", syncIcon);
    syncIcon();
  }

  close() {
    if (this.#closing) {
      return this.#closing;
    }
    const proceed = this.dispatchEvent(new CustomEvent("ui-alert:close", { bubbles: true, cancelable: true }));
    if (!proceed) {
      return Promise.resolve(false);
    }
    this.#closing = new Promise((resolve) => {
      const finish = () => {
        // Before removing, so listeners on ancestors (event delegation) still get it.
        this.dispatchEvent(new CustomEvent("ui-alert:closed", { bubbles: true }));
        this.remove();
        resolve(true);
      };
      const alertNode = this.shadowRoot?.querySelector(".alert");
      if (!alertNode || this.hasAttribute("instant")) {
        finish();
        return;
      }
      // Bootstrap 6 animates the exit with .hiding (opacity transition).
      alertNode.classList.add("hiding");
      afterTransition(alertNode, finish);
    });
    return this.#closing;
  }
}

registerComponent("ui-alert", UiAlert);
