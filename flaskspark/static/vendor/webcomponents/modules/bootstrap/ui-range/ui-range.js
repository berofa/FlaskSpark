import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { FormControlElement } from "../../../core/form-control-element.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";
import { RangeController, installRangeDataApi } from "./range-controller.js";

const PASSTHROUGH = ["min", "max", "step"];

/**
 * <ui-range> (Bootstrap 6 range, new in v6): a slider with a filled track, an optional value bubble and tick
 * marks; form-associated like ui-input (label, help, name, value, disabled, error …, see FormControlElement).
 *
 * Attributes: min (0), max (100), step (1), value, variant (theme colour of fill and thumb), bubble (value bubble),
 * format (bubble and label text, "{value}" is the value, e.g. "{value} %").
 * Ticks: <option value label> children (like a <datalist>); a label is shown below its tick.
 * Property formatter: (value) => text, wins over format. Method update() after changing the value from script.
 * Events: input (composed from the inner range), change, ui-range:changed with detail.value on every update.
 * Parts: field, label, range, control, bubble, ticks, help, feedback.
 */
export class UiRange extends FormControlElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("../form-field.css", import.meta.url).href, new URL("./ui-range.css", import.meta.url).href];
  static observedAttributes = [...FormControlElement.sharedAttributes, ...PASSTHROUGH, "variant", "bubble", "format"];

  #controller = null;
  #observer = null;
  formatter = null;

  get passthroughAttributes() {
    return PASSTHROUGH;
  }

  connectedCallback() {
    super.connectedCallback();
    this.#observer ??= new MutationObserver(() => this.requestRender());
    this.#observer.observe(this, { childList: true, subtree: true, attributes: true, attributeFilter: ["value", "label"] });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.#observer?.disconnect();
  }

  /** The value as a number. */
  get valueAsNumber() {
    return Number.parseFloat(this.value);
  }

  renderControl(attrs) {
    const variant = themeColor(this.getAttribute("variant"));
    return `<div class="form-range ${HOST_TOKENS_CLASS}${variant ? ` theme-${variant}` : ""}" part="range">`
      + `<input type="range" class="form-range-input" id="control" part="control" data-control ${attrs}></div>`;
  }

  afterRender() {
    super.afterRender();
    this.#controller?.dispose();
    const wrapper = this.shadowRoot.querySelector(".form-range");
    const format = this.getAttribute("format");
    this.#controller = new RangeController(wrapper, {
      bubble: this.hasAttribute("bubble"),
      formatter: (value) => (typeof this.formatter === "function" ? this.formatter(value)
        : format ? format.replaceAll("{value}", String(value)) : String(value)),
      ticks: () => [...this.querySelectorAll(":scope > option")].map((option) => ({ value: option.value, label: option.label })),
      emit: (value) => this.dispatchEvent(new CustomEvent("ui-range:changed", { bubbles: true, detail: { value } })),
    });
  }

  get value() {
    return super.value;
  }

  set value(value) {
    super.value = value;
    this.update();
  }

  update() {
    this.#controller?.update();
  }
}

registerComponent("ui-range", UiRange);
installRangeDataApi();
