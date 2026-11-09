import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";

/**
 * <ui-check>: Bootstrap checkbox, radio or switch as a form-associated custom element.
 *
 * Attributes:
 * - type: "checkbox" (default) or "radio".
 * - switch: renders a toggle switch (checkbox only).
 * - checked: current state; reflected when the user toggles it.
 * - name, value (submitted value, default "on"), label, disabled, required.
 * - inline, reverse: Bootstrap .form-check-inline / .form-check-reverse.
 *
 * Slot: default — rich label content (replaces the label attribute).
 *
 * Properties: checked, value, form, validity, checkValidity(), focus().
 * Events: change (bubbles) after a user toggle; input (native, composed).
 *
 * Radios with the same name inside the same form (or document / shadow root)
 * uncheck each other, since native grouping does not reach across shadow trees.
 */
export class UiCheck extends ShadowComponentElement {
  static stylesheet = new URL("./ui-check.css", import.meta.url).href;
  static formAssociated = true;
  static observedAttributes = [
    "type",
    "switch",
    "checked",
    "name",
    "value",
    "label",
    "disabled",
    "required",
    "inline",
    "reverse",
    "aria-label",
  ];

  #internals;
  #defaultChecked = null;
  #formDisabled = false;

  constructor() {
    super();
    this.#internals = this.attachInternals();
  }

  connectedCallback() {
    if (this.#defaultChecked === null) {
      this.#defaultChecked = this.hasAttribute("checked");
    }
    super.connectedCallback();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "checked" && this.hasRendered) {
      // State change only: update the native input instead of re-rendering (keeps focus).
      this.#input.checked = newValue !== null;
      this.#syncFormState();
      return;
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  get #input() {
    return this.shadowRoot.querySelector("input");
  }

  get checked() {
    return this.hasAttribute("checked");
  }

  set checked(value) {
    this.toggleAttribute("checked", Boolean(value));
  }

  get type() {
    return this.getAttribute("type") === "radio" ? "radio" : "checkbox";
  }

  get value() {
    return this.getAttribute("value") ?? "on";
  }

  set value(value) {
    this.setAttribute("value", value);
  }

  get name() {
    return this.getAttribute("name") || "";
  }

  get form() {
    return this.#internals.form;
  }

  get validity() {
    return this.#internals.validity;
  }

  checkValidity() {
    return this.#internals.checkValidity();
  }

  reportValidity() {
    return this.#internals.reportValidity();
  }

  focus(options) {
    this.#input?.focus(options);
  }

  render() {
    const type = this.type;
    const isSwitch = type === "checkbox" && this.hasAttribute("switch");
    const label = this.getAttribute("label") || "";
    const disabled = this.hasAttribute("disabled") || this.#formDisabled;
    const classes = ["form-check"];
    if (isSwitch) classes.push("form-switch");
    if (this.hasAttribute("inline")) classes.push("form-check-inline");
    if (this.hasAttribute("reverse")) classes.push("form-check-reverse");
    const ariaLabel = this.getAttribute("aria-label");
    return `
      <div class="${classes.join(" ")}" part="check">
        <input
          class="form-check-input"
          id="control"
          part="input"
          type="${type}"
          ${isSwitch ? 'role="switch"' : ""}
          ${this.checked ? "checked" : ""}
          ${disabled ? "disabled" : ""}
          ${this.hasAttribute("required") ? "required" : ""}
          ${ariaLabel ? `aria-label="${escapeHtml(ariaLabel)}"` : ""}
        >
        <label class="form-check-label" for="control" part="label"><slot>${escapeHtml(label)}</slot></label>
      </div>
    `;
  }

  afterRender() {
    const input = this.#input;
    input.addEventListener("change", () => {
      this.checked = input.checked;
      if (input.checked) {
        this.#uncheckRadioSiblings();
      }
      this.dispatchEvent(new Event("change", { bubbles: true }));
    });
    this.#syncFormState();
  }

  #syncFormState() {
    const input = this.#input;
    if (!input) {
      return;
    }
    this.#internals.setFormValue(this.checked ? this.value : null);
    if (input.validity.valid) {
      this.#internals.setValidity({});
    } else {
      this.#internals.setValidity(input.validity, input.validationMessage, input);
    }
  }

  #uncheckRadioSiblings() {
    if (this.type !== "radio" || !this.name) {
      return;
    }
    const scope = this.form ?? this.getRootNode();
    scope.querySelectorAll(`ui-check[type="radio"][name="${CSS.escape(this.name)}"]`).forEach((other) => {
      if (other !== this && (other.form ?? other.getRootNode()) === (this.form ?? this.getRootNode())) {
        other.checked = false;
      }
    });
  }

  formResetCallback() {
    this.checked = Boolean(this.#defaultChecked);
  }

  formDisabledCallback(disabled) {
    this.#formDisabled = disabled;
    if (this.#input) {
      this.#input.disabled = disabled || this.hasAttribute("disabled");
    }
  }

  formStateRestoreCallback(state) {
    this.checked = state !== null;
  }
}

registerComponent("ui-check", UiCheck);
