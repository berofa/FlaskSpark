import { registerComponent } from "../../../core/registry.js";
import { FormControlElement } from "../../../core/form-control-element.js";
import { escapeHtml } from "../../../core/escape.js";

const TYPES = new Set([
  "text",
  "number",
  "email",
  "password",
  "search",
  "url",
  "tel",
  "date",
  "time",
  "datetime-local",
  "month",
  "week",
  "color",
]);

const PASSTHROUGH = ["min", "max", "step", "minlength", "maxlength", "pattern", "inputmode"];

/**
 * <ui-input>: Bootstrap .form-control as a form-associated custom element.
 *
 * Attributes:
 * - type: input type (default "text"; text-like types, number, date/time, color).
 * - name, value (initial value), label, help, size ("sm" | "lg").
 * - placeholder, disabled, readonly, required, autocomplete, spellcheck,
 *   min, max, step, minlength, maxlength, pattern, inputmode: forwarded.
 * - clearable: an × at the right while there is a value (e.g. a search); it
 *   empties the field (as does Escape) and fires input and change. Its colours:
 *   --ui-input-clear-bg, --ui-input-clear-color, --ui-input-clear-hover-bg.
 *
 * Properties: value, form, validity, checkValidity(), reportValidity(), focus().
 * Events: input (native, composed), change (re-dispatched on the host).
 * Enter submits the surrounding form like a native input.
 */
export class UiInput extends FormControlElement {
  static stylesheet = new URL("./ui-input.css", import.meta.url).href;
  static observedAttributes = [...FormControlElement.sharedAttributes, "type", "clearable", ...PASSTHROUGH];

  get passthroughAttributes() {
    return PASSTHROUGH;
  }

  renderControl(attrs) {
    const rawType = this.getAttribute("type") || "text";
    const type = TYPES.has(rawType) ? rawType : "text";
    const colorClass = type === "color" ? " form-control-color" : "";
    const input = `
      <input
        class="form-control${this.sizeClass("form-control")}${colorClass}"
        id="control"
        part="control"
        data-control
        type="${escapeHtml(type)}"
        ${attrs}
      >
    `;
    if (!this.hasAttribute("clearable")) return input;
    return `<div class="ui-input-clearable" part="clearable">${input}
      <button type="button" class="ui-input-clear" part="clear" aria-label="Leeren" title="Leeren" hidden>&times;</button></div>`;
  }

  afterRender() {
    super.afterRender();
    this.control?.addEventListener("keydown", (event) => {
      // Implicit submission does not cross the shadow boundary.
      if (event.key === "Enter" && !event.isComposing) {
        this.form?.requestSubmit();
      }
      if (event.key === "Escape" && this.hasAttribute("clearable") && this.control.value) {
        event.preventDefault();
        this.clear();
      }
    });
    const clear = this.shadowRoot.querySelector(".ui-input-clear");
    if (clear) {
      const show = () => { clear.hidden = !this.control.value || this.control.disabled || this.control.readOnly; };
      this.control.addEventListener("input", show);
      clear.addEventListener("click", () => this.clear());
      show();
    }
  }

  /** Empty the field (clearable: its ×, Escape) and tell it as the user would (input, change). */
  clear() {
    if (!this.control || !this.control.value) return;
    this.control.value = "";
    this.control.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
    this.control.dispatchEvent(new Event("change"));
    this.control.focus();
  }

  set value(value) {
    super.value = value;
    const clear = this.shadowRoot?.querySelector(".ui-input-clear");
    if (clear && this.control) clear.hidden = !this.control.value;
  }

  get value() {
    return super.value;
  }
}

registerComponent("ui-input", UiInput);
