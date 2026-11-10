import { registerComponent } from "../../../core/registry.js";
import { FormControlElement } from "../../../core/form-control-element.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";

const PASSTHROUGH = ["rows", "minlength", "maxlength", "wrap"];

/**
 * <ui-textarea> (Bootstrap 6: multi-line .form-control), form-associated.
 *
 * Attributes (besides those of every text field, see FormControlElement: label, help, size, floating,
 * prefix/suffix, plaintext, error, valid-feedback, tooltip, …):
 * - value: initial text. rows, minlength, maxlength, wrap: forwarded.
 *
 * Properties and events as ui-input (Enter inserts a line break).
 */
export class UiTextarea extends FormControlElement {
  static stylesheets = [
    ...BOOTSTRAP_SHADOW_STYLES,
    new URL("../grouped.css", import.meta.url).href,
    new URL("../form-field.css", import.meta.url).href,
  ];
  static observedAttributes = [...FormControlElement.sharedAttributes, ...PASSTHROUGH];

  get passthroughAttributes() {
    return PASSTHROUGH;
  }

  renderControl(attrs, classes) {
    // The value is assigned in afterRender(), so no text content is interpolated here.
    return `
      <textarea
        class="${classes}"
        id="control"
        part="control"
        data-control
        ${attrs}
      ></textarea>
    `;
  }
}

registerComponent("ui-textarea", UiTextarea);
