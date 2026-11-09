import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";

/**
 * <ui-close-button> (Bootstrap 6 close button).
 *
 * Attributes:
 * - label: accessible name (default "Close").
 * - disabled: inactive, not focusable.
 * - dismiss: selector of the ancestor to close on click (e.g. "ui-alert");
 *   it calls the ancestor's close() method.
 *
 * The icon is a CSS mask in currentColor, so it follows the text colour and
 * the colour mode (data-bs-theme on any ancestor).
 * Part: button. Events: click (from the host; never while disabled).
 */
export class UiCloseButton extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-close-button.css", import.meta.url).href];
  static observedAttributes = ["label", "disabled"];

  constructor() {
    super();
    // Suppress clicks on a disabled button: the host would still receive them.
    this.addEventListener("click", (event) => {
      if (this.hasAttribute("disabled")) {
        event.stopImmediatePropagation();
        event.preventDefault();
        return;
      }
      const selector = this.getAttribute("dismiss");
      if (selector) {
        this.parentElement?.closest(selector)?.close?.();
      }
    });
  }

  render() {
    const label = this.getAttribute("label") || "Close";
    const disabled = this.hasAttribute("disabled");
    return `<button type="button" class="btn-close ${HOST_TOKENS_CLASS}" part="button" aria-label="${escapeHtml(label)}"${disabled ? " disabled" : ""}></button>`;
  }

  focus(options) {
    this.shadowRoot.querySelector("button")?.focus(options);
  }
}

registerComponent("ui-close-button", UiCloseButton);
