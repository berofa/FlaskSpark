import { ShadowComponentElement } from "./shadow-component-element.js";
import { escapeHtml } from "./escape.js";
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
 * Subclasses implement renderControl(attrs) and may override
 * passthroughAttributes and controlSelector.
 */

const FORMAT_PAUSE = 700;
export class FormControlElement extends ShadowComponentElement {
  static formAssociated = true;
  static sharedAttributes = [
    "name", "value", "label", "help", "size", "disabled", "aria-label", "prefix", "suffix", ...SHARED_PASSTHROUGH,
  ];

  #internals;
  // Current value once the user (or script) changed it; null = follow the value attribute.
  #dirtyValue = null;
  #formDisabled = false;
  #touched = false; // left once (or validate()): its feedback shows from now on
  #formatTimer = 0;
  #formatError = "";
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

  render() {
    const label = this.getAttribute("label") || "";
    const help = this.getAttribute("help") || "";
    const attrs = [];
    for (const name of [...SHARED_PASSTHROUGH, ...this.passthroughAttributes]) {
      if (this.hasAttribute(name)) {
        attrs.push(`${name}="${escapeHtml(this.getAttribute(name))}"`);
      }
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
    const prefix = this.getAttribute("prefix");
    const suffix = this.getAttribute("suffix");
    const slotted = (name) => [...this.children].some((c) => c.getAttribute("slot") === name);
    const prefixSlot = slotted("prefix");
    const suffixSlot = slotted("suffix");
    let control = this.renderControl(attrs.join(" "));
    if (prefix || suffix || prefixSlot || suffixSlot) {
      control = `
        <div class="input-group${this.sizeClass("input-group")}" part="group">
          ${prefix || prefixSlot ? `<label class="input-group-text" for="control" part="prefix"><slot name="prefix"></slot><span part="prefix-text">${escapeHtml(prefix || "")}</span></label>` : ""}
          ${control}
          ${suffix ? `<span class="input-group-text" part="suffix">${escapeHtml(suffix)}</span>` : ""}
          ${suffixSlot ? '<span class="ui-suffix" part="suffix-slot"><slot name="suffix"></slot></span>' : ""}
        </div>`;
    }
    return `
      ${label ? `<label class="form-label" for="control" part="label">${escapeHtml(label)}</label>` : ""}
      ${control}
      <div class="invalid-feedback" part="feedback" hidden></div>
      ${help ? `<div class="form-text" id="help" part="help">${escapeHtml(help)}</div>` : ""}
    `;
  }

  renderControl() {
    return "";
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
    if (this.renderValue !== null) {
      control.value = this.renderValue;
    }
    control.addEventListener("input", () => {
      this.#dirtyValue = control.value;
      this.#formatError = "";
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
    return validationMessage(control.validity, control.type, control.value)
      || this.#formatError || (this.validator ? this.validator(control.value) || "" : "");
  }

  syncFormState() {
    const control = this.control;
    if (!control) {
      return;
    }
    this.#internals.setFormValue(control.value);
    const message = this.#message(control);
    if (!message) {
      this.#internals.setValidity({});
    } else {
      this.#internals.setValidity(control.validity.valid ? { customError: true } : control.validity, message, control);
    }
    const show = this.#touched && Boolean(message);
    control.classList.toggle("is-invalid", show);
    this.toggleAttribute("invalid", show);
    const feedback = this.shadowRoot.querySelector('[part="feedback"]');
    if (feedback) {
      feedback.hidden = !show;
      feedback.textContent = show ? message : "";
      feedback.classList.toggle("d-block", show);
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
