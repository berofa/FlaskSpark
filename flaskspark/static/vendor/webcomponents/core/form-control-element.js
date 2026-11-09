import { ShadowComponentElement } from "./shadow-component-element.js";
import { escapeHtml } from "./escape.js";
import { HOST_TOKENS_CLASS } from "./shadow-sheet-transforms.js";
import { validationMessage } from "./validation.js";

/** Attributes forwarded 1:1 from the host to the native control. */
const SHARED_PASSTHROUGH = ["placeholder", "readonly", "required", "autocomplete", "spellcheck"];

/**
 * Base class for form-associated text controls (ui-input, ui-textarea, ui-select).
 *
 * The native control lives in the shadow tree. Value, validity and the
 * change event are forwarded through ElementInternals, so the host behaves
 * like a native field inside a light-DOM <form> (submit, reset, required,
 * FormData under the host's "name").
 *
 * Shared attributes: name, value (initial value), label, help, size
 * ("sm" | "lg"), disabled, plus the passthrough list of each subclass.
 * prefix / suffix: text attached in front of / behind the control (Bootstrap
 * .input-group-text, e.g. a short label or a unit); the prefix labels the
 * control. Changing a present text updates it in place (no re-render, the
 * control keeps focus and value). CSS parts: group, prefix, suffix.
 *
 * Slots: slot="prefix" content goes into the prefix (e.g. an icon before its text), slot="suffix" content
 * behind the control inside the group (buttons or a select that belong to the field, in its height).
 *
 * Validation feedback: once the user left the field (or validate() was called), an invalid value shows
 * Bootstrap's is-invalid with a message below (German: «Pflichtfeld», «Keine gültige E-Mail-Adresse», …),
 * updated while typing. type="email" also needs a domain with a dot. validate() marks it and returns validity.
 * A page may set two properties: validator(value) -> message ("" = valid), and formatter(value) ->
 * Promise<string|null>: applied after a pause in typing and on leaving the field (null: not readable,
 * shown as invalid with formatterMessage).
 *
 * Bootstrap 6 layout (.form-field): label, control, help text and feedback in a column.
 * - floating: floating label (.form-floating); "always" keeps it floated and shows the placeholder.
 * - start / end (attributes for text, slots for icons): adornments inside the field (.form-adorn), e.g. a
 *   search icon or a unit. ui-buttons in the prefix / suffix slots join the input group's corners.
 * - plaintext: readonly value as plain text (.form-control-plaintext); ghost: no field styling (.form-ghost).
 * - error: a message from the server: shown as invalid at once (until the value changes).
 * - valid-feedback: message for a valid value once left (green, .is-valid).
 * - tooltip: feedback as a tooltip under the field (.invalid-tooltip / .valid-tooltip).
 *
 * Subclasses implement renderControl(attrs, classes) and may override passthroughAttributes.
 */

const FORMAT_PAUSE = 700;
export class FormControlElement extends ShadowComponentElement {
  static formAssociated = true;
  static sharedAttributes = [
    "name", "value", "label", "help", "size", "disabled", "aria-label", "prefix", "suffix", "floating", "start", "end",
    "plaintext", "ghost", "error", "valid-feedback", "tooltip", ...SHARED_PASSTHROUGH,
  ];

  #internals;
  // Current value once the user (or script) changed it; null = follow the value attribute.
  #dirtyValue = null;
  #formDisabled = false;
  #touched = false; // left once (or validate()): its feedback shows from now on
  #formatTimer = 0;
  #formatError = "";
  #serverError = false; // the error attribute applies until the user changes the value
  /** (value) -> message, "" when valid: a check of the page on top of the native one. */
  validator = null;
  /** (value) -> Promise<string|null>: the value formatted (e.g. a phone number), null if it can't be read. */
  formatter = null;
  formatterMessage = "Ungültige Eingabe";

  constructor() {
    super();
    this.#internals = this.attachInternals();
  }

  /** Extra attributes forwarded to the native control (on top of the shared ones). */
  get passthroughAttributes() {
    return [];
  }

  get control() {
    return this.shadowRoot.querySelector("[data-control]");
  }

  get form() {
    return this.#internals.form;
  }

  get name() {
    return this.getAttribute("name") || "";
  }

  get defaultValue() {
    return this.getAttribute("value");
  }

  get value() {
    if (this.control) {
      return this.control.value;
    }
    return this.#dirtyValue ?? this.defaultValue ?? "";
  }

  set value(value) {
    this.#dirtyValue = String(value ?? "");
    if (this.control) {
      this.control.value = this.#dirtyValue;
      this.syncFormState();
    }
  }

  get validity() {
    return this.#internals.validity;
  }

  get validationMessage() {
    return this.#internals.validationMessage;
  }

  get willValidate() {
    return this.#internals.willValidate;
  }

  checkValidity() {
    return this.#internals.checkValidity();
  }

  reportValidity() {
    return this.#internals.reportValidity();
  }

  /** Show its feedback (also before it was left) and tell whether it is valid. */
  validate() {
    this.#touched = true;
    this.syncFormState();
    return this.checkValidity();
  }

  focus(options) {
    this.control?.focus(options);
  }

  attributeChangedCallback(name, oldValue, newValue) {
    // Attached texts change in place (e.g. a live amount), so typing in the control is not interrupted.
    if ((name === "prefix" || name === "suffix") && this.hasRendered && oldValue && newValue) {
      const part = this.shadowRoot.querySelector(`[part="${name === "prefix" ? "prefix-text" : name}"]`);
      if (part) {
        part.textContent = newValue;
        return;
      }
    }
    if (name === "error" && this.hasRendered) {
      this.#serverError = newValue !== null;
      this.syncFormState();
      return;
    }
    // Like native fields: the value attribute is the default value and only
    // applies while the value was not changed yet.
    if (name === "value" && this.hasRendered) {
      if (this.#dirtyValue === null) {
        this.control.value = newValue ?? "";
        this.syncFormState();
      }
      return;
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  /** Value to render: the changed value, else the value attribute (null = control default). */
  get renderValue() {
    return this.#dirtyValue ?? this.defaultValue;
  }

  /** Classes of the native control: .form-control (or plaintext / ghost), size, the host-token marker. */
  controlClasses() {
    if (this.hasAttribute("plaintext")) {
      return `form-control-plaintext${this.sizeClass("form-control")}`;
    }
    if (this.hasAttribute("ghost") || this.hasAdornments) {
      return "form-ghost";
    }
    return `form-control ${HOST_TOKENS_CLASS}${this.sizeClass("form-control")}`;
  }

  #slotted(name) {
    return [...this.children].some((child) => child.getAttribute("slot") === name);
  }

  get hasAdornments() {
    return ["start", "end"].some((side) => this.hasAttribute(side) || this.#slotted(side));
  }

  /** An adornment inside the field: an icon (slot) or a text (attribute). */
  #adornment(side) {
    if (this.#slotted(side)) {
      return `<div class="form-adorn-icon" part="${side}" aria-hidden="true"><slot name="${side}"></slot></div>`;
    }
    if (this.hasAttribute(side)) {
      return `<span class="form-adorn-text" part="${side}" aria-hidden="true">${escapeHtml(this.getAttribute(side))}</span>`;
    }
    return "";
  }

  render() {
    const label = this.getAttribute("label") || "";
    const help = this.getAttribute("help") || "";
    const floating = this.hasAttribute("floating") && label;
    const attrs = [];
    for (const name of [...SHARED_PASSTHROUGH, ...this.passthroughAttributes]) {
      if (this.hasAttribute(name)) {
        attrs.push(`${name}="${escapeHtml(this.getAttribute(name))}"`);
      }
    }
    if (floating && !this.hasAttribute("placeholder")) {
      // Bootstrap's floating label needs a placeholder (it reads :placeholder-shown).
      attrs.push(`placeholder="${escapeHtml(label)}"`);
    }
    if (this.hasAttribute("plaintext") && !this.hasAttribute("readonly")) {
      attrs.push("readonly");
    }
    if (this.hasAttribute("disabled") || this.#formDisabled) {
      attrs.push("disabled");
    }
    if (!label && this.hasAttribute("aria-label")) {
      attrs.push(`aria-label="${escapeHtml(this.getAttribute("aria-label"))}"`);
    }
    if (help) {
      attrs.push('aria-describedby="help"');
    }
    let control = this.renderControl(attrs.join(" "), this.controlClasses());
    if (this.hasAdornments) {
      const end = !this.hasAttribute("start") && !this.#slotted("start");
      control = `<label class="form-control form-adorn ${HOST_TOKENS_CLASS}${end ? " form-adorn-end" : ""}${this.sizeClass("form-control")}"`
        + ` part="adorn">${this.#adornment("start")}${end ? this.#adornment("end") : ""}${control}`
        + `${end ? "" : this.#adornment("end")}</label>`;
    }
    if (floating) {
      const always = this.getAttribute("floating") === "always" ? " form-floating-always" : "";
      control = `<div class="form-floating ${HOST_TOKENS_CLASS}${always}${this.floatingClass ? ` ${this.floatingClass}` : ""}" part="floating">`
        + `<label for="control" part="label">${escapeHtml(label)}</label>${control}</div>`;
    }
    const prefix = this.getAttribute("prefix");
    const suffix = this.getAttribute("suffix");
    const prefixSlot = this.#slotted("prefix");
    const suffixSlot = this.#slotted("suffix");
    if (prefix || suffix || prefixSlot || suffixSlot) {
      control = `
        <div class="input-group ${HOST_TOKENS_CLASS}${this.sizeClass("input-group")}" part="group">
          ${prefix ? `<label class="input-group-text" for="control" part="prefix"><span part="prefix-text">${escapeHtml(prefix)}</span></label>` : ""}
          ${prefixSlot ? '<span class="ui-addon ui-addon-prefix" part="prefix-slot"><slot name="prefix"></slot></span>' : ""}
          ${control}
          ${suffix ? `<span class="input-group-text" part="suffix">${escapeHtml(suffix)}</span>` : ""}
          ${suffixSlot ? '<span class="ui-addon ui-addon-suffix" part="suffix-slot"><slot name="suffix"></slot></span>' : ""}
        </div>`;
    }
    const tooltip = this.hasAttribute("tooltip");
    return `
      <div class="form-field" part="field">
        ${label && !floating ? `<label class="form-label" for="control" part="label">${escapeHtml(label)}</label>` : ""}
        ${control}
        <div class="${tooltip ? "tooltip invalid-tooltip" : "invalid-feedback"}" part="feedback" hidden></div>
        <div class="${tooltip ? "tooltip valid-tooltip" : "valid-feedback"}" part="valid-feedback" hidden></div>
        ${help ? `<div class="form-text ${HOST_TOKENS_CLASS}" id="help" part="help">${escapeHtml(help)}</div>` : ""}
      </div>
    `;
  }

  renderControl() {
    return "";
  }

  /** The element that carries is-valid / is-invalid: the one Bootstrap colours (the field, or the adorned wrapper). */
  get validationTarget() {
    return this.shadowRoot.querySelector('[part="adorn"]') || this.control;
  }

  /** Size modifier for Bootstrap control classes, e.g. sizeClass("form-control") -> " form-control-sm". */
  sizeClass(base) {
    const size = this.getAttribute("size");
    return size === "sm" || size === "lg" ? ` ${base}-${size}` : "";
  }

  afterRender() {
    const control = this.control;
    if (!control) {
      return;
    }
    if (this.renderValue !== null && control.type !== "file") {
      control.value = this.renderValue;
    }
    this.#serverError = this.hasAttribute("error");
    this.#joinAddonButtons();
    control.addEventListener("input", () => {
      this.#dirtyValue = control.value;
      this.#formatError = "";
      this.#serverError = false;
      this.syncFormState();
      if (this.formatter) {
        clearTimeout(this.#formatTimer);
        this.#formatTimer = setTimeout(() => this.#format(true), FORMAT_PAUSE);
      }
    });
    control.addEventListener("blur", () => {
      this.#touched = true;
      clearTimeout(this.#formatTimer);
      if (this.formatter) this.#format(false);
      else this.syncFormState();
    });
    control.addEventListener("change", () => {
      this.#dirtyValue = control.value;
      this.syncFormState();
      // "change" is not composed and stops at the shadow boundary; re-dispatch on the host.
      this.dispatchEvent(new Event("change", { bubbles: true }));
    });
    this.syncFormState();
  }

  /** The page's formatter on the value (typing: only with the caret at the end, so it never jumps). */
  async #format(typing) {
    const control = this.control;
    const value = control?.value ?? "";
    if (!this.formatter || !value.trim()) {
      this.#formatError = "";
      this.syncFormState();
      return;
    }
    if (typing && control.selectionStart !== value.length) return;
    let out;
    try {
      out = await this.formatter(value);
    } catch {
      return; // the formatter away (network): the value as it is
    }
    if (control.value !== value) return; // typed on meanwhile
    if (out === null || out === undefined) {
      this.#formatError = this.formatterMessage;
    } else {
      this.#formatError = "";
      if (out !== value) {
        control.value = out;
        this.#dirtyValue = out;
        this.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
      }
    }
    this.syncFormState();
  }

  /** The message of an invalid value ("" when valid): native checks, the email rule, the page's own. */
  #message(control) {
    return (this.#serverError ? this.getAttribute("error") || "" : "")
      || validationMessage(control.validity, control.type, control.value)
      || this.#formatError || (this.validator ? this.validator(control.value) || "" : "");
  }

  /** Extra class of the floating label wrapper (ui-select: it holds the caret, so the select stays the label's sibling). */
  get floatingClass() {
    return "";
  }

  /** What the form submits: the value (subclasses: files, several selected options). */
  formValue(control) {
    return control.value;
  }

  /** ui-buttons in the prefix / suffix slots get the input group's corners (like members of a button group). */
  #joinAddonButtons() {
    const prefix = [...this.children].filter((child) => child.slot === "prefix" && child.localName === "ui-button");
    const suffix = [...this.children].filter((child) => child.slot === "suffix" && child.localName === "ui-button");
    const hasText = (name) => this.hasAttribute(name);
    prefix.forEach((button, index) => {
      button.setAttribute("grouped", "horizontal");
      button.toggleAttribute("group-first", index === 0);
      button.toggleAttribute("group-last", false);
    });
    suffix.forEach((button, index) => {
      button.setAttribute("grouped", "horizontal");
      button.toggleAttribute("group-first", false);
      button.toggleAttribute("group-last", index === suffix.length - 1 && !hasText("suffix"));
    });
  }

  syncFormState() {
    const control = this.control;
    if (!control) {
      return;
    }
    this.#internals.setFormValue(this.formValue(control));
    const message = this.#message(control);
    if (!message) {
      this.#internals.setValidity({});
    } else {
      this.#internals.setValidity(control.validity.valid ? { customError: true } : control.validity, message, control);
    }
    const show = (this.#touched || this.#serverError) && Boolean(message);
    const validText = this.getAttribute("valid-feedback");
    const showValid = this.#touched && !message && validText !== null;
    const marked = this.validationTarget || control;
    marked.classList.toggle("is-invalid", show);
    marked.classList.toggle("is-valid", showValid);
    this.toggleAttribute("invalid", show);
    const feedback = this.shadowRoot.querySelector('[part="feedback"]');
    if (feedback) {
      feedback.hidden = !show;
      feedback.textContent = show ? message : "";
      feedback.classList.toggle("d-block", show);
    }
    const valid = this.shadowRoot.querySelector('[part="valid-feedback"]');
    if (valid) {
      valid.hidden = !(showValid && validText);
      valid.textContent = showValid ? validText : "";
      valid.classList.toggle("d-block", showValid && Boolean(validText));
    }
  }

  formResetCallback() {
    this.#dirtyValue = null;
    this.#touched = false;
    this.#formatError = "";
    this.requestRender();
  }

  formDisabledCallback(disabled) {
    this.#formDisabled = disabled;
    if (this.control) {
      this.control.disabled = disabled || this.hasAttribute("disabled");
    }
  }

  formStateRestoreCallback(state) {
    if (typeof state === "string") {
      this.value = state;
    }
  }
}
