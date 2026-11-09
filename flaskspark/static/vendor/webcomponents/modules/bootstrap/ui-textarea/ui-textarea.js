import { registerComponent } from "../../../core/registry.js";
import { FormControlElement } from "../../../core/form-control-element.js";

const PASSTHROUGH = ["rows", "minlength", "maxlength", "wrap"];

/**
 * <ui-textarea>: multi-line Bootstrap .form-control as a form-associated custom element.
 *
 * Attributes:
 * - name, value (initial text), label, help, size ("sm" | "lg"), rows.
 * - placeholder, disabled, readonly, required, autocomplete, spellcheck,
 *   minlength, maxlength, wrap: forwarded.
 *
 * Properties and events as ui-input (Enter inserts a line break).
 */
export class UiTextarea extends FormControlElement {
  static stylesheet = new URL("./ui-textarea.css", import.meta.url).href;
  static observedAttributes = [...FormControlElement.sharedAttributes, ...PASSTHROUGH];

  get passthroughAttributes() {
    return PASSTHROUGH;
  }

  renderControl(attrs) {
    // The value is assigned in afterRender(), so no text content is interpolated here.
    return `
      <textarea
        class="form-control${this.sizeClass("form-control")}"
        id="control"
        part="control"
        data-control
        ${attrs}
      ></textarea>
    `;
  }
}

registerComponent("ui-textarea", UiTextarea);
