import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { onSubmitAttempt, validationMessage, validationMode } from "../../../core/validation.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

const BUTTON_APPEARANCES = new Set(["solid", "outline", "subtle", "text"]);
const CHECK_SIZES = new Set(["sm", "lg"]);
const BUTTON_SIZES = new Set(["xs", "sm", "lg"]);
const NEXT_KEYS = new Set(["ArrowDown", "ArrowRight"]);
const PREVIOUS_KEYS = new Set(["ArrowUp", "ArrowLeft"]);

/**
 * <ui-check> (Bootstrap 6 checkbox, radio, switch and toggle button), form-associated.
 *
 * Attributes:
 * - type: checkbox (default) or radio. switch: a switch (checkbox).
 * - button: a toggle button (.btn-check) instead of the box; its value is the
 *   appearance: solid (default), outline, subtle or text.
 * - checked: the state, reflected when the user toggles it.
 * - indeterminate: neither checked nor unchecked (checkbox); a click clears it.
 * - name, value (submitted value, default "on"), required, disabled.
 * - label, description (or the default and "description" slots): the text
 *   beside the box and a supporting text under it (.form-field).
 * - variant: theme colour of the checked state.
 * - size: sm or lg (.check-sm, .radio-lg, .switch-sm, …); buttons also xs.
 * - inline: next to the following check instead of below it.
 * - feedback: message shown while invalid (default: the browser's reason).
 *
 * Radios with the same name in the same form (or document) form a group:
 * checking one unchecks the others, arrow keys move between them and
 * `required` is met by any checked one (native grouping ends at shadow trees).
 * In a <ui-button-group> the toggle buttons join the group (../grouped.css).
 *
 * Properties: checked, indeterminate, value, form, validity, checkValidity(),
 * reportValidity(), validate(), focus(). Events: change (bubbles), input.
 * Parts: field, input, switch, label, description, button, feedback.
 */
export class UiCheck extends ShadowComponentElement {
  static stylesheets = [
    ...BOOTSTRAP_SHADOW_STYLES,
    new URL("../grouped.css", import.meta.url).href,
    new URL("./ui-check.css", import.meta.url).href,
  ];
  static formAssociated = true;
  static observedAttributes = [
    "type", "switch", "button", "checked", "indeterminate", "name", "value", "label", "description", "variant",
    "size", "disabled", "required", "inline", "feedback", "aria-label",
  ];

  #internals;
  #defaultChecked = null;
  #formDisabled = false;
  #touched = false;
  #forced = false;
  #stopSubmitWatch = null;

  constructor() {
    super();
    this.#internals = this.attachInternals();
  }

  connectedCallback() {
    if (this.#defaultChecked === null) {
      this.#defaultChecked = this.hasAttribute("checked");
    }
    super.connectedCallback();
    this.#watchForm(this.#internals.form);
  }

  disconnectedCallback() {
    this.#stopSubmitWatch?.();
    this.#stopSubmitWatch = null;
  }

  formAssociatedCallback(form) {
    this.#watchForm(form);
  }

  /** A submit attempt shows the feedback (like :user-invalid). */
  #watchForm(form) {
    this.#stopSubmitWatch?.();
    this.#stopSubmitWatch = onSubmitAttempt(form, this, () => {
      this.#touched = true;
      this.#syncFormState();
    });
  }

  attributeChangedCallback(name, oldValue, newValue) {
    // State changes only: update the native input instead of re-rendering (keeps the focus).
    if ((name === "checked" || name === "indeterminate") && this.hasRendered && this.#input) {
      this.#input.checked = this.checked;
      this.#input.indeterminate = this.indeterminate;
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

  get indeterminate() {
    return this.type === "checkbox" && this.hasAttribute("indeterminate");
  }

  set indeterminate(value) {
    this.toggleAttribute("indeterminate", Boolean(value));
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

  get disabled() {
    return this.hasAttribute("disabled") || this.#formDisabled;
  }

  get form() {
    return this.#internals.form;
  }

  get validity() {
    return this.#internals.validity;
  }

  get validationMessage() {
    return this.#internals.validationMessage;
  }

  checkValidity() {
    return this.#internals.checkValidity();
  }

  reportValidity() {
    return this.#internals.reportValidity();
  }

  /** Show its feedback (also without data-bs-validate) and tell whether it is valid. */
  validate() {
    this.#touched = true;
    this.#forced = true;
    this.#syncFormState();
    return this.checkValidity();
  }

  focus(options) {
    this.#input?.focus(options);
  }

  /** The radios of this one's group (same name, same form or root), in document order. */
  get group() {
    if (this.type !== "radio" || !this.name) {
      return [this];
    }
    const scope = this.form ?? this.getRootNode();
    const owner = (element) => element.form ?? element.getRootNode();
    return [...scope.querySelectorAll(`ui-check[type="radio"][name="${CSS.escape(this.name)}"]`)]
      .filter((other) => owner(other) === owner(this));
  }

  render() {
    const type = this.type;
    const variant = themeColor(this.getAttribute("variant"));
    const size = (this.getAttribute("size") || "").trim().toLowerCase();
    const ariaLabel = this.getAttribute("aria-label");
    const inputAttributes = [
      `type="${type}"`,
      'id="control"',
      'part="input"',
      this.checked ? "checked" : "",
      this.disabled ? "disabled" : "",
      this.hasAttribute("required") ? "required" : "",
      ariaLabel ? `aria-label="${escapeHtml(ariaLabel)}"` : "",
    ].filter(Boolean).join(" ");
    const label = `<slot>${escapeHtml(this.getAttribute("label") || "")}</slot>`;
    const feedback = '<div class="invalid-feedback" part="feedback" hidden></div>';

    if (this.hasAttribute("button")) {
      const raw = (this.getAttribute("button") || "").trim().toLowerCase();
      const appearance = BUTTON_APPEARANCES.has(raw) ? raw : "solid";
      const classes = ["btn-check", `btn-${appearance}`, variant ? `theme-${variant}` : "",
        BUTTON_SIZES.has(size) ? `btn-${size}` : ""].filter(Boolean).join(" ");
      return `<label class="${classes}" part="button"><input ${inputAttributes} autocomplete="off">${label}</label>${feedback}`;
    }

    const kind = type === "checkbox" && this.hasAttribute("switch") ? "switch" : type === "radio" ? "radio" : "check";
    const classes = [kind, HOST_TOKENS_CLASS, CHECK_SIZES.has(size) ? `${kind}-${size}` : "",
      variant ? `theme-${variant}` : ""].filter(Boolean).join(" ");
    const control = kind === "switch"
      ? `<div class="${classes}" part="switch"><input ${inputAttributes} role="switch" switch></div>`
      : `<input class="${classes}" ${inputAttributes}>`;
    const hasLabel = this.hasAttribute("label") || [...this.childNodes].some((node) => (
      node.nodeType === Node.ELEMENT_NODE ? !node.slot : node.nodeType === Node.TEXT_NODE && node.textContent.trim()));
    const hasDescription = this.hasAttribute("description") || [...this.children].some((child) => child.slot === "description");
    if (!hasLabel && !hasDescription) {
      return `${control}${feedback}`;
    }
    const labelElement = `<label for="control" part="label">${label}</label>`;
    const content = hasDescription
      ? `<div class="form-field-content">${labelElement}<small class="form-text ${HOST_TOKENS_CLASS}" part="description">`
        + `<slot name="description">${escapeHtml(this.getAttribute("description") || "")}</slot></small></div>`
      : labelElement;
    return `<div class="form-field" part="field">${control}${content}${feedback}</div>`;
  }

  afterRender() {
    const input = this.#input;
    input.indeterminate = this.indeterminate;
    input.addEventListener("change", () => {
      this.#touched = true;
      this.indeterminate = false;
      this.checked = input.checked;
      if (input.checked) {
        this.#uncheckRadioSiblings();
      }
      this.group.forEach((radio) => radio !== this && radio.#syncFormState());
      this.dispatchEvent(new Event("change", { bubbles: true }));
    });
    input.addEventListener("keydown", (event) => this.#onKeydown(event));
    this.#syncFormState();
  }

  #onKeydown(event) {
    if (this.type !== "radio" || !(NEXT_KEYS.has(event.key) || PREVIOUS_KEYS.has(event.key))) {
      return;
    }
    const radios = this.group.filter((radio) => !radio.disabled);
    if (radios.length < 2) {
      return;
    }
    event.preventDefault();
    const step = NEXT_KEYS.has(event.key) ? 1 : -1;
    const next = radios[(radios.indexOf(this) + step + radios.length) % radios.length];
    next.focus();
    next.#input.click();
  }

  #syncFormState() {
    const input = this.#input;
    if (!input) {
      return;
    }
    this.#internals.setFormValue(this.checked ? this.value : null);
    // A required radio is met by any checked radio of its group.
    const missing = this.hasAttribute("required") && !this.group.some((radio) => radio.checked);
    const message = missing ? (this.getAttribute("feedback") || validationMessage({ valueMissing: true })) : "";
    if (message) {
      this.#internals.setValidity({ valueMissing: true }, message, input);
    } else {
      this.#internals.setValidity({});
    }
    // Like Bootstrap 6: client-side feedback only inside data-bs-validate ("valid": also valid), or after validate().
    const mode = validationMode(this, this.#internals.form);
    const show = (this.#forced || (mode !== null && this.#touched)) && Boolean(message);
    input.classList.toggle("is-invalid", show);
    input.classList.toggle("is-valid", !message && Boolean(mode?.valid) && this.#touched);
    this.toggleAttribute("invalid", show);
    const feedback = this.shadowRoot.querySelector('[part="feedback"]');
    if (feedback) {
      feedback.hidden = !show;
      feedback.textContent = show ? message : "";
      feedback.classList.toggle("d-block", show);
    }
  }

  #uncheckRadioSiblings() {
    if (this.type !== "radio") {
      return;
    }
    this.group.forEach((other) => {
      if (other !== this) {
        other.checked = false;
      }
    });
  }

  formResetCallback() {
    this.#touched = false;
    this.#forced = false;
    this.checked = Boolean(this.#defaultChecked);
  }

  formDisabledCallback(disabled) {
    this.#formDisabled = disabled;
    this.requestRender();
  }

  formStateRestoreCallback(state) {
    this.checked = state !== null;
  }
}

registerComponent("ui-check", UiCheck);
