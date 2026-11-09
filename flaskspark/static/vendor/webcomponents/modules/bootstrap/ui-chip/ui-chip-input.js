import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";
import { ChipsController, installChipsDataApi } from "./chips-controller.js";

let counter = 0;

/**
 * <ui-chip-input> (Bootstrap 6 chip input): a multi-value field, e.g. skills, tags or recipients. Typing and
 * Enter, the separator, a paste or leaving the field add chips; chips are selected Mail.app-style (click,
 * Ctrl/Cmd+click, Shift+click, arrow keys, Ctrl/Cmd+A) and removed with Backspace / Delete or their button.
 *
 * Form-associated: every value is submitted under `name` (like a multiple select); required needs one chip.
 *
 * Attributes:
 * - value: initial values (a JSON array, or text split at the separator). variant: theme colour of the chips.
 * - label (above, .form-label), inline-label (inside, .chip-input-label), help (.form-text), placeholder.
 * - separator (default ","; "" = none), allow-duplicates, max-chips, dismissible="false", create-on-blur="false".
 * - disabled, required, name, remove-label ("Remove"), error (message shown as invalid).
 * Properties / methods: values (get / set), selectedValues, add(value), remove(chipOrValue), removeSelected(),
 * clear(), clearSelection(), selectChip(chip, { addToSelection, rangeSelect }), focus().
 * Events (bubble): ui-chip-input:add and ui-chip-input:remove (cancelable, detail.value),
 * ui-chip-input:change (detail.values), ui-chip-input:select (detail.selected); `change` after add / remove.
 * Parts: field, label, chip-input, inline-label, chip, input, help, feedback.
 */
export class UiChipInput extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-chip.css", import.meta.url).href];
  static formAssociated = true;
  static observedAttributes = ["value", "variant", "label", "inline-label", "help", "placeholder", "separator", "allow-duplicates",
    "max-chips", "dismissible", "create-on-blur", "disabled", "required", "name", "remove-label", "error"];

  #internals;
  #controller = null;
  #values = null; // current values once rendered
  #formDisabled = false;
  #id = `ui-chip-input-${(counter += 1)}`;

  constructor() {
    super();
    this.#internals = this.attachInternals();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "value" && this.#values !== null) {
      return; // the initial value only (like an input's value attribute)
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  #initialValues() {
    const raw = this.getAttribute("value") || "";
    if (raw.trim().startsWith("[")) {
      try {
        return JSON.parse(raw).map(String);
      } catch {
        return [];
      }
    }
    const separator = this.#separator();
    return (separator ? raw.split(separator) : [raw]).map((part) => part.trim()).filter(Boolean);
  }

  #separator() {
    const separator = this.getAttribute("separator");
    return separator === null ? "," : separator;
  }

  get values() {
    return this.#controller ? this.#controller.values() : (this.#values ?? this.#initialValues());
  }

  set values(values) {
    this.#values = [...values].map(String);
    if (this.#controller) {
      this.renderShadow();
    }
  }

  get selectedValues() {
    return this.#controller?.selectedValues() ?? [];
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

  add(value) { return this.#controller?.add(value) ?? null; }

  remove(chipOrValue) { return this.#controller?.remove(chipOrValue) ?? false; }

  removeSelected() { this.#controller?.removeSelected(); }

  clear() { this.#controller?.clear(); }

  clearSelection() { this.#controller?.clearSelection(); }

  selectChip(chip, options) { this.#controller?.selectChip(chip, options); }

  focus() { this.#controller?.focus(); }

  render() {
    const values = this.#values ?? this.#initialValues();
    const variant = themeColor(this.getAttribute("variant"));
    const disabled = this.hasAttribute("disabled") || this.#formDisabled;
    const text = (name) => escapeHtml(this.getAttribute(name) || "");
    const id = `${this.#id}-input`;
    const label = this.getAttribute("label") ? `<label class="form-label" part="label" for="${id}">${text("label")}</label>` : "";
    const inline = this.getAttribute("inline-label") ? `<label class="chip-input-label" part="inline-label" for="${id}">${text("inline-label")}</label>` : "";
    const chips = values.map((value) => `<span class="chip" part="chip" data-bs-chip-value="${escapeHtml(value)}">${escapeHtml(value)}</span>`).join("");
    const help = this.getAttribute("help") ? `<div class="form-text" part="help" id="${this.#id}-help">${text("help")}</div>` : "";
    const describedBy = help ? ` aria-describedby="${this.#id}-help"` : "";
    return `<div class="form-field" part="field">${label}`
      + `<div class="chip-input ${HOST_TOKENS_CLASS}${variant ? ` theme-${variant}` : ""}${disabled ? " disabled" : ""}" part="chip-input">`
      + `${inline}${chips}<input type="text" class="form-ghost" part="input" id="${id}" placeholder="${text("placeholder")}"`
      + `${disabled ? " disabled" : ""}${describedBy}></div>`
      + `${help}<div class="invalid-feedback" part="feedback"></div></div>`;
  }

  renderShadow() {
    const focused = this.shadowRoot.activeElement?.classList.contains("form-ghost");
    const typed = this.#controller?.input.value || "";
    this.#values = this.values;
    this.shadowRoot.innerHTML = this.render();
    const element = this.shadowRoot.querySelector(".chip-input");
    this.#controller = new ChipsController(element, {
      config: () => ({
        separator: this.#separator(),
        allowDuplicates: this.hasAttribute("allow-duplicates"),
        maxChips: this.getAttribute("max-chips"),
        dismissible: this.getAttribute("dismissible") ?? true,
        createOnBlur: this.getAttribute("create-on-blur") ?? true,
      }),
      emit: (name, detail, cancelable) => {
        const result = this.dispatchEvent(new CustomEvent(`ui-chip-input:${name}`, { bubbles: true, cancelable, detail }));
        if (name === "change") {
          this.#values = detail.values;
          this.#sync();
          this.dispatchEvent(new Event("change", { bubbles: true }));
        }
        return result;
      },
      decorate: (chip) => {
        chip.classList.add(HOST_TOKENS_CLASS);
        chip.setAttribute("part", "chip");
        const dismiss = chip.querySelector(".chip-dismiss");
        if (dismiss) {
          dismiss.disabled = this.hasAttribute("disabled") || this.#formDisabled;
          dismiss.setAttribute("aria-label", this.getAttribute("remove-label") || "Remove");
        }
      },
    });
    const input = this.#controller.input;
    input.value = typed;
    if (focused) {
      input.focus();
    }
    this.#sync();
  }

  #sync() {
    const values = this.values;
    const input = this.#controller?.input;
    if (this.name) {
      const data = new FormData();
      values.forEach((value) => data.append(this.name, value));
      this.#internals.setFormValue(values.length ? data : null);
    } else {
      this.#internals.setFormValue(null);
    }
    const error = this.getAttribute("error");
    const missing = this.hasAttribute("required") && values.length === 0;
    if (error) {
      this.#internals.setValidity({ customError: true }, error, input);
    } else if (missing) {
      this.#internals.setValidity({ valueMissing: true }, "Pflichtfeld", input);
    } else {
      this.#internals.setValidity({});
    }
    const feedback = this.shadowRoot.querySelector(".invalid-feedback");
    if (feedback) {
      feedback.textContent = error || "";
      input?.classList.toggle("is-invalid", Boolean(error));
    }
  }

  formResetCallback() {
    this.#values = this.#initialValues();
    this.renderShadow();
  }

  formDisabledCallback(disabled) {
    this.#formDisabled = disabled;
    this.requestRender();
  }
}

registerComponent("ui-chip-input", UiChipInput);
installChipsDataApi();
