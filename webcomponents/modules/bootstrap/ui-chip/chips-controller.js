import { sanitizeHtml } from "../../../core/sanitize.js";

/**
 * Bootstrap 6's chip input behaviour (js/src/chips.ts, MIT) for a `.chip-input` container, in the document or
 * in a shadow tree: chips from typing (Enter, the separator, paste, leaving the field), dismiss buttons,
 * Mail.app-style selection (click, Ctrl/Cmd+click, Shift+click, arrows, Home / End, Ctrl/Cmd+A) and removal
 * (Backspace / Delete). Events add / remove (cancelable), change and select.
 *
 * Options: config() → { separator, allowDuplicates, maxChips, placeholder, dismissible, dismissIcon,
 * createOnBlur }, emit(name, detail, cancelable) → false when cancelled, decorate(chip) (e.g. extra classes).
 */

export const DISMISS_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="none" '
  + 'stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="4" y1="4" x2="12" y2="12"/><line x1="12" y1="4" x2="4" y2="12"/></svg>';
export const CHIPS_DEFAULTS = {
  separator: ",", allowDuplicates: false, maxChips: null, placeholder: "", dismissible: true, dismissIcon: DISMISS_ICON, createOnBlur: true,
};
const ICON_ALLOW_LIST = {
  svg: ["xmlns", "width", "height", "viewbox", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "class", "aria-hidden"],
  path: ["d", "fill", "stroke", "fill-rule", "clip-rule"],
  line: ["x1", "y1", "x2", "y2"],
  circle: ["cx", "cy", "r"],
  rect: ["x", "y", "width", "height", "rx", "ry"],
  polyline: ["points"],
  polygon: ["points"],
  g: [],
  i: ["class"],
  span: ["class"],
};
const isTrue = (value) => value === true || value === "true" || value === "";

export class ChipsController {
  constructor(element, options = {}) {
    this.element = element;
    this.options = options;
    this.selected = new Set();
    this.anchor = null;
    this.input = element.querySelector(".form-ghost") || this.#createInput();
    this.chips = [];
    this.#chipElements().forEach((chip) => {
      const value = this.valueOf(chip);
      if (value) {
        this.chips.push(value);
        this.#setupChip(chip);
      }
    });
    this.#listen();
  }

  config() {
    const config = { ...CHIPS_DEFAULTS, ...(this.options.config?.() || {}) };
    config.separator = config.separator === null || config.separator === "" || config.separator === "null" ? null : String(config.separator);
    config.allowDuplicates = isTrue(config.allowDuplicates);
    const max = Number.parseInt(config.maxChips, 10);
    config.maxChips = Number.isNaN(max) ? null : max;
    config.dismissible = !(config.dismissible === false || config.dismissible === "false");
    config.createOnBlur = !(config.createOnBlur === false || config.createOnBlur === "false");
    return config;
  }

  #emit(name, detail, cancelable = false) {
    if (this.options.emit) {
      return this.options.emit(name, detail, cancelable);
    }
    return this.element.dispatchEvent(new CustomEvent(`ui-chip-input:${name}`, { bubbles: true, cancelable, detail }));
  }

  /** Adds a chip; returns it, or null when empty, a duplicate, over the maximum or cancelled. */
  add(value) {
    const trimmed = String(value ?? "").trim();
    const config = this.config();
    if (!trimmed || (!config.allowDuplicates && this.chips.includes(trimmed))
      || (config.maxChips !== null && this.chips.length >= config.maxChips)) {
      return null;
    }
    if (!this.#emit("add", { value: trimmed, relatedTarget: this.input }, true)) {
      return null;
    }
    const chip = this.#createChip(trimmed);
    this.input.before(chip);
    this.chips.push(trimmed);
    this.#emit("change", { values: this.values() });
    return chip;
  }

  /** Removes a chip (element or value); true when removed. */
  remove(chipOrValue) {
    const chip = typeof chipOrValue === "string" ? this.#chipElements().find((c) => this.valueOf(c) === chipOrValue) : chipOrValue;
    const value = chip ? this.valueOf(chip) : "";
    if (!chip || !value || !this.#emit("remove", { value, chip, relatedTarget: this.input }, true)) {
      return false;
    }
    this.selected.delete(chip);
    if (this.anchor === chip) {
      this.anchor = null;
    }
    chip.remove();
    this.chips = this.#chipElements().map((c) => this.valueOf(c)).filter(Boolean);
    this.#emit("change", { values: this.values() });
    return true;
  }

  removeSelected() {
    [...this.selected].forEach((chip) => this.remove(chip));
    this.input.focus();
  }

  values() {
    return [...this.chips];
  }

  selectedValues() {
    return [...this.selected].map((chip) => this.valueOf(chip));
  }

  clear() {
    this.#chipElements().forEach((chip) => chip.remove());
    this.chips = [];
    this.selected.clear();
    this.anchor = null;
    this.#emit("change", { values: [] });
  }

  clearSelection() {
    this.selected.forEach((chip) => chip.classList.remove("active"));
    this.selected.clear();
    this.anchor = null;
    this.#emit("select", { selected: [] });
  }

  selectChip(chip, { addToSelection = false, rangeSelect = false } = {}) {
    const chips = this.#chipElements();
    if (!chips.includes(chip)) {
      return;
    }
    if (rangeSelect && this.anchor) {
      const start = Math.min(chips.indexOf(this.anchor), chips.indexOf(chip));
      const end = Math.max(chips.indexOf(this.anchor), chips.indexOf(chip));
      if (!addToSelection) {
        const anchor = this.anchor;
        this.clearSelection();
        this.anchor = anchor;
      }
      for (let index = start; index <= end; index += 1) {
        this.selected.add(chips[index]);
        chips[index].classList.add("active");
      }
    } else if (addToSelection) {
      if (this.selected.has(chip)) {
        this.selected.delete(chip);
        chip.classList.remove("active");
      } else {
        this.selected.add(chip);
        chip.classList.add("active");
        this.anchor = chip;
      }
    } else {
      this.clearSelection();
      this.selected.add(chip);
      chip.classList.add("active");
      this.anchor = chip;
    }
    this.#emit("select", { selected: this.selectedValues() });
  }

  focus() {
    this.input.focus();
  }

  /** The value of a chip: data-bs-chip-value, else its text without the dismiss button. */
  valueOf(chip) {
    if (chip.dataset.bsChipValue) {
      return chip.dataset.bsChipValue;
    }
    const copy = chip.cloneNode(true);
    copy.querySelector(".chip-dismiss")?.remove();
    return copy.textContent.trim();
  }

  #chipElements() {
    return [...this.element.querySelectorAll(".chip")];
  }

  #createInput() {
    const input = document.createElement("input");
    input.type = "text";
    input.className = "form-ghost";
    const { placeholder } = this.config();
    if (placeholder) {
      input.placeholder = placeholder;
    }
    this.element.append(input);
    return input;
  }

  #setupChip(chip) {
    chip.setAttribute("tabindex", "0");
    if (this.config().dismissible && !chip.querySelector(".chip-dismiss")) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "chip-dismiss";
      button.setAttribute("aria-label", this.options.removeLabel?.() || "Remove");
      button.tabIndex = -1; // chips handle the keyboard
      button.innerHTML = sanitizeHtml(this.config().dismissIcon, ICON_ALLOW_LIST);
      chip.append(button);
    }
    this.options.decorate?.(chip);
  }

  #createChip(value) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.dataset.bsChipValue = value;
    chip.append(document.createTextNode(value));
    this.#setupChip(chip);
    return chip;
  }

  #listen() {
    const input = this.input;
    input.addEventListener("keydown", (event) => this.#inputKeydown(event));
    input.addEventListener("input", () => this.#input());
    input.addEventListener("paste", (event) => this.#paste(event));
    input.addEventListener("focus", () => this.clearSelection());
    input.addEventListener("blur", (event) => {
      if (this.config().createOnBlur && !event.relatedTarget?.closest?.(".chip")) {
        this.#createFromInput();
      }
    });
    this.element.addEventListener("click", (event) => {
      const dismiss = event.target.closest?.(".chip-dismiss");
      const chip = event.target.closest?.(".chip");
      if (dismiss && chip && this.element.contains(chip)) {
        event.stopPropagation();
        this.remove(chip);
        this.input.focus();
      } else if (chip && this.element.contains(chip)) {
        event.preventDefault();
        this.selectChip(chip, { addToSelection: event.metaKey || event.ctrlKey, rangeSelect: event.shiftKey });
        chip.focus();
      } else if (event.target === this.element) {
        this.clearSelection();
        this.input.focus();
      }
    });
    this.element.addEventListener("keydown", (event) => {
      const chip = event.target.closest?.(".chip");
      if (chip && this.element.contains(chip)) {
        this.#chipKeydown(event, chip);
      }
    });
  }

  #inputKeydown(event) {
    const chips = this.#chipElements();
    const last = chips.at(-1);
    switch (event.key) {
      case "Enter":
        event.preventDefault();
        this.#createFromInput();
        break;
      case "Backspace":
      case "Delete":
        if (this.input.value === "") {
          event.preventDefault();
          if (last) {
            this.selectChip(last);
            last.focus();
          }
        }
        break;
      case "ArrowLeft":
        if (this.input.selectionStart === 0 && this.input.selectionEnd === 0) {
          event.preventDefault();
          if (last) {
            this.selectChip(last, event.shiftKey ? { addToSelection: true } : {});
            last.focus();
          }
        }
        break;
      case "Escape":
        this.input.value = "";
        this.clearSelection();
        this.input.blur();
        break;
      default:
    }
  }

  #chipKeydown(event, chip) {
    const chips = this.#chipElements();
    const index = chips.indexOf(chip);
    const range = event.shiftKey ? { addToSelection: true, rangeSelect: true } : {};
    const go = (target) => {
      this.selectChip(target, range);
      target.focus();
    };
    switch (event.key) {
      case "Backspace":
      case "Delete": {
        event.preventDefault();
        if (this.selected.size === 0) {
          break;
        }
        const next = Math.min(index, chips.length - this.selected.size - 1);
        this.removeSelected();
        const remaining = this.#chipElements();
        if (remaining.length > 0) {
          const target = remaining[Math.max(0, Math.min(next, remaining.length - 1))];
          target.focus();
          this.selectChip(target);
        } else {
          this.input.focus();
        }
        break;
      }
      case "ArrowLeft":
        event.preventDefault();
        if (index > 0) {
          go(chips[index - 1]);
        }
        break;
      case "ArrowRight":
        event.preventDefault();
        if (index < chips.length - 1) {
          go(chips[index + 1]);
        } else {
          this.clearSelection();
          this.input.focus();
        }
        break;
      case "Home":
        event.preventDefault();
        if (chips.length) {
          this.selectChip(chips[0], event.shiftKey ? { rangeSelect: true } : {});
          chips[0].focus();
        }
        break;
      case "End":
        event.preventDefault();
        this.clearSelection();
        this.input.focus();
        break;
      case "a":
        if (event.metaKey || event.ctrlKey) {
          event.preventDefault();
          chips.forEach((c) => {
            this.selected.add(c);
            c.classList.add("active");
          });
          this.#emit("select", { selected: this.selectedValues() });
        }
        break;
      case "Escape":
        event.preventDefault();
        this.clearSelection();
        this.input.focus();
        break;
      default:
    }
  }

  #input() {
    const { separator } = this.config();
    const { value } = this.input;
    if (separator && value.includes(separator)) {
      const parts = value.split(separator);
      parts.slice(0, -1).forEach((part) => this.add(part.trim()));
      this.input.value = parts.at(-1);
    }
  }

  #paste(event) {
    const { separator } = this.config();
    const text = event.clipboardData?.getData("text") || "";
    if (separator && text.includes(separator)) {
      event.preventDefault();
      text.split(separator).forEach((part) => this.add(part.trim()));
    }
  }

  #createFromInput() {
    const value = this.input.value.trim();
    if (value) {
      this.add(value);
      this.input.value = "";
    }
  }
}

const plain = new WeakMap();

/** The controller of a plain `.chip-input[data-bs-chips]` (options from its data-bs-* attributes). */
export function plainChips(element) {
  let controller = plain.get(element);
  if (!controller) {
    controller = new ChipsController(element, {
      config: () => {
        const d = element.dataset;
        const entries = { separator: d.bsSeparator, allowDuplicates: d.bsAllowDuplicates, maxChips: d.bsMaxChips,
          placeholder: d.bsPlaceholder, dismissible: d.bsDismissible, createOnBlur: d.bsCreateOnBlur };
        return Object.fromEntries(Object.entries(entries).filter(([, value]) => value !== undefined));
      },
    });
    plain.set(element, controller);
  }
  return controller;
}

let installed = false;

/** Bootstrap's chips data API: every `[data-bs-chips]` container gets a controller on load (and later ones on first contact). */
export function installChipsDataApi() {
  if (installed || typeof document === "undefined") {
    return;
  }
  installed = true;
  const all = () => document.querySelectorAll("[data-bs-chips]").forEach((element) => plainChips(element));
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", all, { once: true });
  } else {
    all();
  }
  document.addEventListener("focusin", (event) => {
    const container = event.target instanceof Element ? event.target.closest("[data-bs-chips]") : null;
    if (container) {
      plainChips(container);
    }
  });
}
