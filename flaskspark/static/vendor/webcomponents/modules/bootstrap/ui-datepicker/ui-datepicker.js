import { registerComponent } from "../../../core/registry.js";
import { FormControlElement } from "../../../core/form-control-element.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";
import { DatepickerController, installDatepickerDataApi } from "./datepicker-controller.js";

const MODES = { single: "single", multiple: "multiple", range: "multiple-ranged", "multiple-ranged": "multiple-ranged" };

/**
 * <ui-datepicker> (Bootstrap 6 datepicker, new in v6): a date field with a calendar popup (Vanilla Calendar Pro,
 * loaded on first use, styled by Bootstrap), or an inline calendar. Form-associated like ui-input (label, help,
 * name, required, disabled, error, floating, start / end adornments …, see FormControlElement); the field shows the
 * dates formatted, the form gets them as ISO dates (YYYY-MM-DD, several comma-separated).
 *
 * Attributes:
 * - value: ISO date(s), comma-separated (a range: start,end).
 * - mode: single (default), multiple or range. months: months side by side (default 1).
 * - min, max: ISO dates. first-weekday: 0 Sunday … (default 1, Monday). locale (e.g. de-CH; default: the browser's).
 * - placement: left (default), center, right, auto. inline: always visible, no field.
 * - date-format: Intl.DateTimeFormat options as JSON, e.g. {"day":"numeric","month":"short","year":"numeric"}.
 * - datepicker-theme: light, dark or auto for the popup only (default: the colour mode of the page around it).
 * Properties: selectedDates (get / set, ISO), dateFormat (Intl options or (date, locale) => text), vcpOptions
 * (Vanilla Calendar Pro options, set before it renders). Methods: show(), hide(), toggle().
 * Events: ui-datepicker:show / hide (cancelable), shown / hidden, ui-datepicker:change {dates}; change and input.
 * Parts: field, label, control, calendar (inline), help, feedback.
 */
export class UiDatepicker extends FormControlElement {
  static stylesheets = [
    ...BOOTSTRAP_SHADOW_STYLES,
    new URL("../grouped.css", import.meta.url).href,
    new URL("../form-field.css", import.meta.url).href,
    new URL("./ui-datepicker.css", import.meta.url).href,
  ];
  static observedAttributes = [...FormControlElement.sharedAttributes, "mode", "months", "min", "max", "first-weekday", "locale",
    "placement", "inline", "date-format", "datepicker-theme"];

  #controller = null;
  #dates = null; // chosen dates once changed; null: the value attribute
  dateFormat = null;
  vcpOptions = {};

  constructor() {
    super();
    this.validator = () => (this.hasAttribute("required") && !this.selectedDates.length ? "Pflichtfeld" : "");
  }

  get #initialDates() {
    return (this.getAttribute("value") || "").split(",").map((d) => d.trim()).filter((d) => /^\d{4}-\d{2}-\d{2}$/.test(d));
  }

  /** The chosen dates as ISO texts. */
  get selectedDates() {
    return this.#controller?.calendar ? this.#controller.getSelectedDates() : [...(this.#dates ?? this.#initialDates)];
  }

  set selectedDates(dates) {
    this.#dates = [...dates];
    if (this.#controller) {
      this.#controller.setSelectedDates(this.#dates).then(() => this.syncFormState());
    }
  }

  get value() {
    return this.selectedDates.join(",");
  }

  set value(value) {
    this.selectedDates = String(value ?? "").split(",").map((d) => d.trim()).filter(Boolean);
  }

  formValue() {
    return this.selectedDates.join(",") || null;
  }

  renderControl(attrs, classes) {
    if (this.hasAttribute("inline")) {
      return '<div class="ui-datepicker-inline" part="calendar"></div><input type="hidden" id="control" data-control>';
    }
    return `<input type="text" class="${classes}" id="control" part="control" data-control autocomplete="off" ${attrs}>`;
  }

  get renderValue() {
    return null; // the controller writes the formatted dates
  }

  afterRender() {
    super.afterRender();
    this.#controller?.dispose();
    const inline = this.hasAttribute("inline");
    const element = inline ? this.shadowRoot.querySelector(".ui-datepicker-inline") : this.control;
    let format = this.dateFormat;
    if (!format && this.getAttribute("date-format")) {
      try {
        format = JSON.parse(this.getAttribute("date-format"));
      } catch {
        format = null;
      }
    }
    const number = (name, fallback) => {
      const value = Number.parseInt(this.getAttribute(name), 10);
      return Number.isNaN(value) ? fallback : value;
    };
    this.#controller = new DatepickerController(element, {
      inline,
      boundInput: inline ? this.control : null,
      themeElement: this,
      decorate: (calendar) => {
        calendar.classList.add(HOST_TOKENS_CLASS);
        calendar.setAttribute("part", "calendar");
      },
      selectedDates: this.#dates ?? this.#initialDates,
      selectionMode: MODES[this.getAttribute("mode")] || "single",
      displayMonthsCount: number("months", 1),
      firstWeekday: number("first-weekday", 1),
      dateMin: this.getAttribute("min") || null,
      dateMax: this.getAttribute("max") || null,
      locale: this.getAttribute("locale") || "default",
      placement: this.getAttribute("placement") || "left",
      datepickerTheme: this.getAttribute("datepicker-theme") || null,
      dateFormat: format,
      vcpOptions: this.vcpOptions || {},
      emit: (name, detail, cancelable) => {
        const result = this.dispatchEvent(new CustomEvent(`ui-datepicker:${name}`, { bubbles: true, cancelable, detail }));
        if (name === "change") {
          this.#dates = [...detail.dates];
          this.syncFormState();
          this.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
          this.dispatchEvent(new Event("change", { bubbles: true }));
        }
        return result;
      },
    });
    this.#controller.ready.then(() => this.syncFormState());
  }

  disconnectedCallback() {
    this.#controller?.dispose();
    this.#controller = null;
  }

  show() {
    return this.#controller?.show();
  }

  hide() {
    return this.#controller?.hide();
  }

  toggle() {
    return this.#controller?.toggle();
  }

  formResetCallback() {
    this.#dates = null;
    this.requestRender();
  }
}

registerComponent("ui-datepicker", UiDatepicker);
installDatepickerDataApi();
