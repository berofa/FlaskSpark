import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { FormControlElement } from "../../../core/form-control-element.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";
import { OtpController, installOtpDataApi, parseGroups } from "./otp-controller.js";

/**
 * <ui-otp> (Bootstrap 6 OTP input, new in v6): one-time passwords, PINs and verification codes in one accessible
 * text field drawn as separate slots; form-associated like ui-input (label, help, name, value, required, error,
 * valid-feedback …, see FormControlElement).
 *
 * Attributes: length (slots, default 6), type (numeric, alphanumeric, alpha), mask (dots instead of the
 * characters), groups ("3,3": separators between groups), separator ("·"), connected (one field with shared
 * borders), size (sm, lg), incomplete-message (shown when a started code is too short; default "Code unvollständig").
 * Methods: setValue(value), clear(), focus(). Events: input, change, ui-otp:input and ui-otp:complete (detail.value).
 * Parts: field, label, otp, control, slots, slot, separator, help, feedback.
 */
export class UiOtp extends FormControlElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("../form-field.css", import.meta.url).href, new URL("./ui-otp.css", import.meta.url).href];
  static observedAttributes = [...FormControlElement.sharedAttributes, "length", "type", "mask", "groups", "separator", "connected",
    "incomplete-message"];

  #controller = null;

  constructor() {
    super();
    // A started but incomplete code is invalid (the slots show how many are missing).
    this.validator = (value) => (value && value.length < this.#length ? this.getAttribute("incomplete-message") || "Code unvollständig" : "");
  }

  get #length() {
    return Number.parseInt(this.getAttribute("length"), 10) || 6;
  }

  get validationTarget() {
    return this.shadowRoot.querySelector(".otp");
  }

  renderControl(attrs) {
    const size = this.getAttribute("size");
    const classes = ["otp", HOST_TOKENS_CLASS, this.hasAttribute("connected") ? "otp-connected" : "",
      size === "sm" || size === "lg" ? `otp-${size}` : ""].filter(Boolean).join(" ");
    return `<div class="${classes}" part="otp"><input type="text" id="control" part="control" data-control maxlength="${this.#length}" ${attrs}></div>`;
  }

  afterRender() {
    super.afterRender();
    this.#controller?.dispose();
    this.#controller = new OtpController(this.shadowRoot.querySelector(".otp"), {
      length: this.#length,
      type: this.getAttribute("type") || "numeric",
      mask: this.hasAttribute("mask"),
      groups: parseGroups(this.getAttribute("groups")),
      ...(this.getAttribute("separator") ? { separator: this.getAttribute("separator") } : {}),
      emit: (name, value) => {
        if (name === "input") {
          super.value = value; // typing goes around the native input event (beforeinput is handled)
          this.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
        }
        this.dispatchEvent(new CustomEvent(`ui-otp:${name}`, { bubbles: true, detail: { value } }));
      },
    });
  }

  get value() {
    return super.value;
  }

  set value(value) {
    if (this.#controller) {
      this.#controller.setValue(value);
      super.value = this.#controller.value;
    } else {
      super.value = value;
    }
  }

  setValue(value) {
    this.value = value;
  }

  clear() {
    this.#controller?.clear();
    super.value = "";
  }

  focus() {
    this.#controller?.focus();
  }
}

registerComponent("ui-otp", UiOtp);
installOtpDataApi();
