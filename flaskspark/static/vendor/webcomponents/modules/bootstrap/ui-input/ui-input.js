import { registerComponent } from "../../../core/registry.js";
import { FormControlElement } from "../../../core/form-control-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";
import { StrengthController } from "../strength.js";

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
  "file",
]);

const PASSTHROUGH = ["min", "max", "step", "minlength", "maxlength", "pattern", "inputmode", "accept", "multiple", "capture"];
const CARET = '<svg class="ui-caret" part="caret" viewBox="0 0 16 16" aria-hidden="true"><path fill="none" '
  + 'stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m2 5 6 6 6-6"/></svg>';

/**
 * <ui-input> (Bootstrap 6 form control), form-associated.
 *
 * Attributes (besides those of every text field, see FormControlElement: label, help, size, floating,
 * prefix/suffix, start/end, plaintext, ghost, error, valid-feedback, tooltip, …):
 * - type: text (default), number, email, password, search, url, tel, date, time, datetime-local, month,
 *   week, color (.form-control-color), file (submits the chosen files; accept, multiple, capture).
 * - min, max, step, minlength, maxlength, pattern, inputmode: forwarded.
 * - A <datalist> child offers suggestions (it is copied into the field); caret shows the select arrow.
 * - clearable: an × at the right while there is a value; it empties the field (as does Escape) and fires
 *   input and change. Colours: --ui-input-clear-bg, --ui-input-clear-color, --ui-input-clear-hover-bg.
 * - strength (type password, Bootstrap 6 password strength): a meter below the field, "segments" (default) or
 *   "bar"; strength-text adds the message; strength-min-length (8); weak-label, fair-label, good-label,
 *   strong-label. Properties strengthWeights, strengthThresholds, strengthScorer(password); getter strength;
 *   event ui-input:strength {strength, score}.
 *
 * Properties: value, files (type file), form, validity, checkValidity(), reportValidity(), validate(),
 * focus(), clear(). Events: input (native, composed), change (re-dispatched on the host).
 * Enter submits the surrounding form like a native input.
 */
export class UiInput extends FormControlElement {
  static stylesheets = [
    ...BOOTSTRAP_SHADOW_STYLES,
    new URL("../grouped.css", import.meta.url).href,
    new URL("../form-field.css", import.meta.url).href,
    new URL("./ui-input.css", import.meta.url).href,
  ];
  static observedAttributes = [...FormControlElement.sharedAttributes, "type", "clearable", "caret", ...PASSTHROUGH,
    "strength", "strength-text", "strength-min-length", "weak-label", "fair-label", "good-label", "strong-label"];

  #strength = null;
  strengthWeights = null;
  strengthThresholds = null;
  strengthScorer = null;

  /** The password's level: null, "weak", "fair", "good" or "strong" (with the strength attribute). */
  get strength() {
    return this.#strength?.strength ?? null;
  }

  get passthroughAttributes() {
    return PASSTHROUGH;
  }

  get type() {
    const raw = this.getAttribute("type") || "text";
    return TYPES.has(raw) ? raw : "text";
  }

  get files() {
    return this.control?.files ?? null;
  }

  formValue(control) {
    if (control.type !== "file") {
      return control.value;
    }
    const data = new FormData();
    [...control.files].forEach((file) => data.append(this.name, file));
    return data;
  }

  renderControl(attrs, classes) {
    const type = this.type;
    const datalist = [...this.children].find((child) => child.localName === "datalist");
    const caret = this.hasAttribute("caret");
    const className = [classes, type === "color" ? "form-control-color" : "", caret ? "form-control-caret" : ""]
      .filter(Boolean).join(" ");
    // The author's suggestions, re-serialized by the browser (no raw string), under an id of this tree.
    const list = datalist ? `<datalist id="list">${datalist.innerHTML}</datalist>` : "";
    const input = `<input class="${className}" id="control" part="control" data-control type="${escapeHtml(type)}"`
      + `${datalist ? ' list="list"' : ""} ${attrs}>${list}`;
    if (caret) {
      return `<div class="ui-caret-wrap">${input}${CARET}</div>`;
    }
    if (!this.hasAttribute("clearable")) {
      return input;
    }
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
    this.#renderStrength();
    const clear = this.shadowRoot.querySelector(".ui-input-clear");
    if (clear) {
      const show = () => { clear.hidden = !this.control.value || this.control.disabled || this.control.readOnly; };
      this.control.addEventListener("input", show);
      clear.addEventListener("click", () => this.clear());
      show();
    }
  }

  /** The strength meter below the field (outside the control's wrappers: group, floating label, adornments). */
  #renderStrength() {
    this.#strength?.dispose();
    this.#strength = null;
    if (!this.hasAttribute("strength") || !this.control) return;
    const field = this.shadowRoot.querySelector(".form-field");
    const holder = [...field.children].find((child) => child === this.control || child.contains(this.control));
    const bar = this.getAttribute("strength") === "bar";
    const meter = document.createElement("div");
    meter.className = `${bar ? "strength-bar" : "strength"} ${HOST_TOKENS_CLASS}`;
    meter.setAttribute("part", "strength");
    meter.innerHTML = bar ? "" : '<div class="strength-segment"></div>'.repeat(4);
    holder.after(meter);
    let text = null;
    if (this.hasAttribute("strength-text")) {
      text = document.createElement("span");
      text.className = "strength-text";
      text.setAttribute("part", "strength-text");
      text.setAttribute("aria-live", "polite");
      meter.after(text);
    }
    const minLength = Number.parseInt(this.getAttribute("strength-min-length"), 10);
    const messages = Object.fromEntries(["weak", "fair", "good", "strong"]
      .filter((level) => this.hasAttribute(`${level}-label`)).map((level) => [level, this.getAttribute(`${level}-label`)]));
    this.#strength = new StrengthController(meter, {
      input: this.control,
      text,
      messages,
      ...(Number.isNaN(minLength) ? {} : { minLength }),
      ...(this.strengthWeights ? { weights: this.strengthWeights } : {}),
      ...(this.strengthThresholds ? { thresholds: this.strengthThresholds } : {}),
      scorer: this.strengthScorer,
      emit: (detail) => this.dispatchEvent(new CustomEvent("ui-input:strength", { bubbles: true, detail })),
    });
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
    this.#strength?.evaluate();
    const clear = this.shadowRoot?.querySelector(".ui-input-clear");
    if (clear && this.control) clear.hidden = !this.control.value;
  }

  get value() {
    return super.value;
  }
}

registerComponent("ui-input", UiInput);
