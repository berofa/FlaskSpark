/**
 * Bootstrap 6's datepicker (js/src/datepicker.ts, MIT): Vanilla Calendar Pro (vendor/vanilla-calendar-pro, loaded on
 * first use) styled by Bootstrap. A popup below an input or a button, or an inline calendar; single, multiple or
 * ranged selection, several months, min / max, first weekday, locale and date formats, colour mode.
 * In a shadow tree the popup is placed into that shadow root (the calendar library does that), where the
 * component's Bootstrap sheet styles it.
 *
 * Options (Bootstrap's): datepickerTheme, dateMin, dateMax, dateFormat (Intl options or (date, locale) => text),
 * displayElement, displayMonthsCount, firstWeekday, inline, locale, positionElement, selectedDates, selectionMode
 * ("single", "multiple", "multiple-ranged"), placement ("left", "center", "right", "auto"), vcpOptions.
 * Extra: boundInput (an input that gets the ISO dates), themeElement (where to look for data-bs-theme; default the
 * element), decorate(calendarElement) (e.g. extra classes), emit(name, detail, cancelable) (default: ui-datepicker:<name> on the element).
 */
const VCP_URL = new URL("../../../vendor/vanilla-calendar-pro/index.mjs", import.meta.url).href;
const HIDE_DELAY = 100;
let vcp = null;

/** Vanilla Calendar Pro, imported once. */
export function loadCalendar() {
  vcp ??= import(VCP_URL);
  return vcp;
}

export const DATEPICKER_DEFAULTS = {
  datepickerTheme: null,
  dateMin: null,
  dateMax: null,
  dateFormat: null,
  displayElement: null,
  displayMonthsCount: 1,
  firstWeekday: 1,
  inline: false,
  locale: "default",
  positionElement: null,
  selectedDates: [],
  selectionMode: "single",
  placement: "left",
  vcpOptions: {},
};

/** "2026-06-10" as a local Date. */
export function parseIsoDate(text) {
  const [year, month, day] = String(text).split("-").map(Number);
  return new Date(year, month - 1, day);
}

/** A Date as "YYYY-MM-DD". */
export function isoDate(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

/** The text of selected ISO dates: one date, a list ("a, b") or a range ("a – b"). */
export function formatDates(dates, { selectionMode = "single", locale = "default", dateFormat = null } = {}) {
  const loc = locale === "default" ? undefined : locale;
  const one = (text) => {
    const date = parseIsoDate(text);
    if (typeof dateFormat === "function") return dateFormat(date, loc);
    if (dateFormat && typeof dateFormat === "object") return new Intl.DateTimeFormat(loc, dateFormat).format(date);
    return date.toLocaleDateString(loc);
  };
  if (!dates.length) return "";
  if (dates.length === 1) return one(dates[0]);
  return dates.map(one).join(selectionMode === "multiple-ranged" ? " – " : ", ");
}

export class DatepickerController {
  constructor(element, options = {}) {
    this.element = element;
    this.config = { ...DATEPICKER_DEFAULTS, ...options };
    this.calendar = null;
    this.isShown = false;
    this.ready = this.#init();
  }

  #emit(name, detail = {}, cancelable = false) {
    if (this.config.emit) return this.config.emit(name, detail, cancelable);
    return this.element.dispatchEvent(new CustomEvent(`ui-datepicker:${name}`, { bubbles: true, cancelable, detail }));
  }

  async #init() {
    const { Calendar, months } = await loadCalendar();
    if (!this.element.isConnected) return;
    this.isInput = this.element.tagName === "INPUT";
    this.isInline = Boolean(this.config.inline);
    this.boundInput = this.config.boundInput
      || (this.isInline && !this.isInput ? this.element.querySelector('input[type="hidden"], input[name]') : null);
    this.positionElement = this.#resolvePositionElement();
    this.displayElement = this.#resolveDisplayElement();
    this.calendar = new Calendar(this.positionElement, this.#calendarOptions(months));
    this.calendar.init();
    this.#setupThemeObserver();
    this.#setupDismiss();
    if (this.isInput && this.element.value && !this.config.selectedDates.length) {
      this.#parseInputValue();
    }
    const dates = [...(this.calendar.context.selectedDates || [])];
    const selected = dates.length ? dates : this.config.selectedDates;
    if (selected.length) this.#sync(selected);
  }

  get disabled() {
    return this.element.disabled || this.element.hasAttribute("disabled") || this.element.classList.contains("disabled");
  }

  async toggle() {
    await this.ready;
    return this.isShown ? this.hide() : this.show();
  }

  async show() {
    await this.ready;
    if (this.isInline || !this.calendar || this.disabled || this.isShown) return;
    if (!this.#emit("show", {}, true)) return;
    this.calendar.show();
    this.isShown = true;
    this.#emit("shown");
  }

  async hide() {
    await this.ready;
    if (this.isInline || !this.calendar || !this.isShown) return;
    if (!this.#emit("hide", {}, true)) return;
    this.calendar.hide();
    this.isShown = false;
    this.#emit("hidden");
  }

  getSelectedDates() {
    const dates = this.calendar?.context?.selectedDates;
    return dates ? [...dates] : [...this.config.selectedDates];
  }

  async setSelectedDates(dates) {
    await this.ready;
    if (!this.calendar) return;
    this.calendar.set({ selectedDates: dates });
    this.#sync([...this.calendar.context.selectedDates]);
  }

  #sync(dates) {
    const text = formatDates(dates, this.config);
    if (this.isInput) this.element.value = text;
    if (this.boundInput) this.boundInput.value = dates.join(",");
    if (this.displayElement) this.displayElement.textContent = text;
  }

  #resolvePositionElement() {
    let { positionElement } = this.config;
    if (typeof positionElement === "string") positionElement = this.element.getRootNode().querySelector(positionElement);
    if (!positionElement && this.isInput && !this.isInline) positionElement = this.element.closest(".form-adorn");
    return positionElement || this.element;
  }

  #resolveDisplayElement() {
    const { displayElement } = this.config;
    if (typeof displayElement === "string") return this.element.getRootNode().querySelector(displayElement);
    if (displayElement === true || (displayElement === null && !this.isInput && !this.isInline)) {
      return this.element.querySelector("[data-bs-datepicker-display]") || this.element;
    }
    return displayElement;
  }

  #themeAncestor() {
    if (this.themeAncestor === undefined) {
      this.themeAncestor = (this.config.themeElement || this.element).closest("[data-bs-theme]");
    }
    return this.themeAncestor;
  }

  #theme() {
    return this.config.datepickerTheme || this.#themeAncestor()?.getAttribute("data-bs-theme") || null;
  }

  #syncTheme(element) {
    if (!element) return;
    const theme = this.#theme();
    if (theme) element.setAttribute("data-bs-theme", theme);
    else element.removeAttribute("data-bs-theme");
  }

  #setupThemeObserver() {
    const ancestor = this.#themeAncestor();
    if (!ancestor || this.config.datepickerTheme) return;
    this.themeObserver = new MutationObserver(() => this.#syncTheme(this.calendar?.context?.mainElement));
    this.themeObserver.observe(ancestor, { attributes: true, attributeFilter: ["data-bs-theme"] });
  }

  #setupDismiss() {
    if (this.isInline) return;
    if (!this.isInput) {
      this.onTriggerClick = () => {
        if (!this.isShown) this.calendar?.hide();
      };
      this.positionElement.addEventListener("click", this.onTriggerClick);
    }
    this.onOutside = (event) => {
      const main = this.calendar?.context?.mainElement;
      const path = event.composedPath();
      const outside = !path.includes(this.element) && !(main && path.includes(main));
      if (this.isShown && outside) this.hide();
    };
    document.addEventListener("focusin", this.onOutside);
    document.addEventListener("pointerdown", this.onOutside);
  }

  /**
   * The library places the popup with page coordinates (position: absolute), which only fits when its containing
   * block is the page. Inside a positioned ancestor (or a component's shadow root under one) the popup is moved by
   * the measured difference whenever the library writes its position.
   */
  #setupPositionFix(main) {
    if (this.isInline || !main || this.positionObserver) return;
    let written = null;
    const fix = () => {
      const { left, top } = main.style;
      if (!left || !top || `${left}|${top}` === written) return;
      // The library's values are page coordinates: measure where they landed and move by the difference.
      const x = Number.parseFloat(left);
      const y = Number.parseFloat(top);
      const rect = main.getBoundingClientRect();
      const dx = rect.left - (x - window.scrollX);
      const dy = rect.top - (y - window.scrollY);
      if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) {
        written = `${left}|${top}`;
        return;
      }
      main.style.left = `${x - dx}px`;
      main.style.top = `${y - dy}px`;
      written = `${main.style.left}|${main.style.top}`;
    };
    this.positionObserver = new MutationObserver(fix);
    this.positionObserver.observe(main, { attributes: true, attributeFilter: ["style"] });
  }

  #calendarOptions(months) {
    const theme = this.#theme();
    const c = this.config;
    const options = {
      ...c.vcpOptions,
      extensions: [months],
      inputMode: !this.isInline,
      positionToInput: c.placement,
      firstWeekday: Number(c.firstWeekday),
      locale: c.locale,
      selectionDatesMode: c.selectionMode,
      selectedDates: c.selectedDates,
      displayMonthsCount: Number(c.displayMonthsCount),
      type: Number(c.displayMonthsCount) > 1 ? "multiple" : "default",
      selectedTheme: !theme || theme === "auto" ? "system" : theme,
      themeAttrDetect: "[data-bs-theme]",
      onClickDate: (self, event) => this.#dateClick(self, event),
      // In input mode the library creates the popup on the first show and calls onInit then.
      onInit: (self) => {
        this.config.decorate?.(self.context.mainElement);
        this.#syncTheme(self.context.mainElement);
        this.#setupPositionFix(self.context.mainElement);
      },
      onShow: () => {
        if (!this.calendar) return;
        this.isShown = true;
        this.#syncTheme(this.calendar.context.mainElement);
      },
      onHide: () => {
        this.isShown = false;
      },
    };
    if (c.selectedDates.length) {
      const first = parseIsoDate(c.selectedDates[0]);
      options.selectedMonth = first.getMonth();
      options.selectedYear = first.getFullYear();
    }
    if (c.dateMin) options.dateMin = c.dateMin;
    if (c.dateMax) options.dateMax = c.dateMax;
    return options;
  }

  #dateClick(self, event) {
    const dates = [...self.context.selectedDates];
    this.#sync(dates);
    this.#emit("change", { dates, event });
    if (this.isInline) return;
    const done = (this.config.selectionMode === "single" && dates.length > 0)
      || (this.config.selectionMode === "multiple-ranged" && dates.length >= 2);
    if (done) setTimeout(() => this.hide(), HIDE_DELAY);
  }

  #parseInputValue() {
    const value = this.element.value.trim();
    const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    const date = iso ? new Date(Number(iso[1]), Number(iso[2]) - 1, Number(iso[3])) : new Date(value);
    if (!Number.isNaN(date.getTime())) this.calendar.set({ selectedDates: [isoDate(date)] });
  }

  dispose() {
    this.themeObserver?.disconnect();
    this.positionObserver?.disconnect();
    if (this.onOutside) {
      document.removeEventListener("focusin", this.onOutside);
      document.removeEventListener("pointerdown", this.onOutside);
    }
    if (this.onTriggerClick) this.positionElement?.removeEventListener("click", this.onTriggerClick);
    this.calendar?.destroy();
    this.calendar = null;
  }
}

const plain = new WeakMap();

/** Options of plain markup from its data-bs-* attributes. */
function dataOptions(element) {
  const d = element.dataset;
  const json = (value, fallback) => {
    try {
      return value ? JSON.parse(value) : fallback;
    } catch {
      return fallback;
    }
  };
  const options = {
    inline: d.bsInline === "true",
    selectedDates: json(d.bsSelectedDates, []),
  };
  if (d.bsDateMin) options.dateMin = d.bsDateMin;
  if (d.bsDateMax) options.dateMax = d.bsDateMax;
  if (d.bsSelectionMode) options.selectionMode = d.bsSelectionMode;
  if (d.bsDisplayMonthsCount) options.displayMonthsCount = Number(d.bsDisplayMonthsCount);
  if (d.bsFirstWeekday) options.firstWeekday = Number(d.bsFirstWeekday);
  if (d.bsLocale) options.locale = d.bsLocale;
  if (d.bsPlacement) options.placement = d.bsPlacement;
  if (d.bsDatepickerTheme) options.datepickerTheme = d.bsDatepickerTheme;
  return options;
}

export function plainDatepicker(element) {
  let controller = plain.get(element);
  if (!controller) {
    controller = new DatepickerController(element, dataOptions(element));
    plain.set(element, controller);
  }
  return controller;
}

let installed = false;

/** Bootstrap's data API for [data-bs-toggle="datepicker"]: inputs open on focus, other triggers on click. */
export function installDatepickerDataApi() {
  if (installed || typeof document === "undefined") return;
  installed = true;
  const trigger = (event) => (event.target instanceof Element ? event.target.closest('[data-bs-toggle="datepicker"]') : null);
  document.addEventListener("click", (event) => {
    const element = trigger(event);
    if (!element || element.tagName === "INPUT" || element.dataset.bsInline === "true") return;
    event.preventDefault();
    plainDatepicker(element).toggle();
  });
  document.addEventListener("focusin", (event) => {
    const element = trigger(event);
    if (element?.tagName === "INPUT") plainDatepicker(element).show();
  });
  const start = () => document.querySelectorAll('[data-bs-toggle="datepicker"][data-bs-inline="true"], [data-bs-toggle="datepicker"][data-bs-selected-dates]')
    .forEach((element) => plainDatepicker(element));
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
}
