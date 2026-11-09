/**
 * Bootstrap 6's OTP input (js/src/otp-input.ts, MIT) for a `.otp` container with one <input>: the single real
 * text field is drawn as separate slots. Typing overwrites the slot at the caret, a click selects a slot, pastes
 * drop formatting (123-456), Backspace deletes; autocomplete="one-time-code" and the right inputmode for autofill.
 * Works in the document and in a shadow tree.
 *
 * Options: length (default: the input's maxlength, else 6), type ("numeric", "alphanumeric", "alpha"), mask,
 * groups ([3, 3]: separators between groups), separator ("·"), emit(name, value) (default: ui-otp:input and
 * ui-otp:complete on the container, detail.value).
 */
const TYPES = {
  numeric: { inputmode: "numeric", pattern: "[0-9]*", filter: /[^0-9]/g },
  alphanumeric: { inputmode: "text", pattern: "[A-Za-z0-9]*", filter: /[^A-Za-z0-9]/g },
  alpha: { inputmode: "text", pattern: "[A-Za-z]*", filter: /[^A-Za-z]/g },
};
const MASK = "•";

/** The characters of `value` an OTP of this type and length keeps (DOM-free). */
export function sanitizeOtp(value, type = "numeric", length = 6) {
  return String(value ?? "").replace((TYPES[type] || TYPES.numeric).filter, "").slice(0, length);
}

export class OtpController {
  constructor(element, options = {}) {
    this.element = element;
    this.options = { separator: "·", type: "numeric", mask: false, groups: null, ...options };
    this.input = element.querySelector("input");
    this.slots = [];
    this.pointerActive = false;
    this.pointerIndex = 0;
    this.listeners = {};
    if (!this.input) return;
    this.type = TYPES[this.options.type] ? this.options.type : "numeric";
    this.length = this.#resolveLength();
    this.#setupInput();
    this.#renderSlots();
    this.#listen();
    this.render();
  }

  #resolveLength() {
    if (this.options.length) return this.options.length;
    const max = Number.parseInt(this.input.getAttribute("maxlength"), 10);
    return Number.isNaN(max) || max < 1 ? 6 : max;
  }

  #focused() {
    return this.input.getRootNode().activeElement === this.input;
  }

  #setupInput() {
    const { input } = this;
    if (input.type === "number" || input.type === "password") input.type = "text";
    input.classList.add("otp-input");
    input.setAttribute("maxlength", String(this.length));
    input.setAttribute("inputmode", TYPES[this.type].inputmode);
    input.setAttribute("pattern", TYPES[this.type].pattern);
    if (!input.getAttribute("autocomplete")) input.setAttribute("autocomplete", "one-time-code");
    if (input.value) input.value = this.sanitize(input.value);
  }

  #renderSlots() {
    const container = document.createElement("div");
    container.className = "otp-slots";
    container.setAttribute("aria-hidden", "true");
    container.setAttribute("part", "slots");
    const groups = Array.isArray(this.options.groups) ? this.options.groups : [];
    let group = 0;
    let inGroup = 0;
    for (let index = 0; index < this.length; index += 1) {
      const slot = document.createElement("div");
      slot.className = "otp-slot";
      slot.setAttribute("part", "slot");
      container.append(slot);
      this.slots.push(slot);
      if (groups.length) {
        inGroup += 1;
        if (inGroup === groups[group] && index < this.length - 1) {
          const separator = document.createElement("div");
          separator.className = "otp-separator";
          separator.setAttribute("part", "separator");
          separator.textContent = this.options.separator;
          container.append(separator);
          group = Math.min(group + 1, groups.length - 1);
          inGroup = 0;
        }
      }
    }
    this.slotsContainer = container;
    this.element.append(container);
    this.element.classList.add("otp-rendered");
  }

  #listen() {
    const sync = () => this.render();
    this.listeners = {
      input: () => this.#handleInput(),
      beforeinput: (event) => this.#handleBeforeInput(event),
      paste: (event) => this.#handlePaste(event),
      pointerdown: (event) => this.#handlePointerDown(event),
      focus: () => {
        if (this.pointerActive) {
          this.pointerActive = false;
          this.#selectSlot(this.pointerIndex);
        } else {
          this.#selectSlot(this.#firstEmptyIndex());
        }
        this.render();
      },
      blur: sync,
      keyup: sync,
      select: sync,
    };
    Object.entries(this.listeners).forEach(([type, listener]) => this.input.addEventListener(type, listener));
    this.onSelectionChange = () => this.#focused() && this.render();
    document.addEventListener("selectionchange", this.onSelectionChange);
  }

  get value() {
    return this.input.value;
  }

  setValue(value) {
    this.input.value = this.sanitize(value);
    this.render();
    this.#checkComplete();
  }

  clear() {
    this.input.value = "";
    this.render();
    this.input.focus();
  }

  focus() {
    this.input.focus();
    this.#selectSlot(this.#firstEmptyIndex());
    this.render();
  }

  sanitize(value) {
    return sanitizeOtp(value, this.type, this.length);
  }

  #handleInput() {
    const clean = this.sanitize(this.input.value);
    if (clean !== this.input.value) this.input.value = clean;
    if (this.#focused()) this.#selectSlot(this.#firstEmptyIndex());
    this.#afterChange();
  }

  #handlePaste(event) {
    const pasted = event.clipboardData?.getData("text");
    if (!pasted || this.input.readOnly) return;
    const clean = this.sanitize(pasted);
    let start = this.input.selectionStart ?? this.input.value.length;
    let end = this.input.selectionEnd ?? start;
    if (clean.length === this.length) {
      start = 0;
      end = this.input.value.length;
    }
    const inserted = clean.slice(0, this.length - this.input.value.length + end - start);
    event.preventDefault();
    if (!inserted) return;
    this.input.setRangeText(inserted, start, end, "end");
    this.#afterChange();
  }

  #handleBeforeInput(event) {
    const { inputType, data } = event;
    if (inputType === "insertText" && data && data.length === 1) {
      event.preventDefault();
      const char = this.sanitize(data);
      if (!char) return;
      const index = Math.min(this.input.selectionStart ?? 0, this.length - 1);
      const chars = [...this.input.value];
      chars[index] = char;
      this.input.value = chars.join("").slice(0, this.length);
      this.#selectSlot(index + 1);
      this.#afterChange();
      return;
    }
    if (inputType === "deleteContentBackward") {
      event.preventDefault();
      const start = this.input.selectionStart ?? 0;
      const end = this.input.selectionEnd ?? start;
      const chars = [...this.input.value];
      if (end > start) {
        chars.splice(start, end - start);
        this.input.value = chars.join("");
        this.#selectSlot(start);
      } else if (start > 0) {
        chars.splice(start - 1, 1);
        this.input.value = chars.join("");
        this.#selectSlot(start - 1);
      }
      this.#afterChange();
    }
  }

  #handlePointerDown(event) {
    const index = this.slots.findIndex((slot, i) => event.clientX <= slot.getBoundingClientRect().right || i === this.slots.length - 1);
    if (index < 0) return;
    const target = Math.min(index, this.#firstEmptyIndex());
    if (this.#focused()) {
      event.preventDefault();
      this.#selectSlot(target);
      this.render();
      return;
    }
    this.pointerActive = true;
    this.pointerIndex = target;
  }

  #emit(name) {
    if (this.options.emit) {
      this.options.emit(name, this.input.value);
    } else {
      this.element.dispatchEvent(new CustomEvent(`ui-otp:${name}`, { bubbles: true, detail: { value: this.input.value } }));
    }
  }

  #afterChange() {
    this.render();
    this.#emit("input");
    this.#checkComplete();
  }

  #firstEmptyIndex() {
    return Math.min(this.input.value.length, this.length - 1);
  }

  #selectSlot(index) {
    const clamped = Math.max(0, Math.min(index, this.length - 1));
    const end = clamped < this.input.value.length ? clamped + 1 : clamped;
    this.input.setSelectionRange(clamped, end);
  }

  /** Draws the value into the slots (also after setting input.value from script). */
  render() {
    const { value } = this.input;
    const focused = this.#focused();
    const caret = Math.min(this.input.selectionStart ?? value.length, this.length - 1);
    this.slots.forEach((slot, index) => {
      const char = value[index] ?? "";
      slot.textContent = char && this.options.mask ? MASK : char;
      slot.classList.toggle("otp-slot-filled", Boolean(char));
      slot.classList.toggle("otp-slot-active", focused && index === caret);
    });
  }

  #checkComplete() {
    if (this.input.value.length === this.length) this.#emit("complete");
  }

  dispose() {
    Object.entries(this.listeners).forEach(([type, listener]) => this.input?.removeEventListener(type, listener));
    document.removeEventListener("selectionchange", this.onSelectionChange);
    this.slotsContainer?.remove();
    this.element.classList.remove("otp-rendered");
  }
}

/** data-bs-groups as an array: "[3,3]" or "3,3". */
export function parseGroups(value) {
  if (!value) return null;
  const numbers = String(value).replace(/[[\]\s]/g, "").split(",").map((n) => Number.parseInt(n, 10)).filter((n) => n > 0);
  return numbers.length ? numbers : null;
}

const plain = new WeakMap();

export function plainOtp(element) {
  let controller = plain.get(element);
  if (!controller) {
    const d = element.dataset;
    controller = new OtpController(element, {
      length: Number.parseInt(d.bsLength, 10) || null,
      type: d.bsType || "numeric",
      mask: d.bsMask === "true" || d.bsMask === "",
      groups: parseGroups(d.bsGroups),
      ...(d.bsSeparator ? { separator: d.bsSeparator } : {}),
    });
    plain.set(element, controller);
  }
  return controller;
}

let installed = false;

/** Bootstrap's data API: every `[data-bs-otp]` container of the page (also later ones). */
export function installOtpDataApi() {
  if (installed || typeof document === "undefined") return;
  installed = true;
  const scan = (root) => root.querySelectorAll?.("[data-bs-otp]").forEach((element) => plainOtp(element));
  const start = () => {
    scan(document);
    new MutationObserver((records) => records.forEach((record) => record.addedNodes.forEach((node) => {
      if (node.nodeType !== 1) return;
      if (node.matches("[data-bs-otp]")) plainOtp(node);
      scan(node);
    }))).observe(document.documentElement, { childList: true, subtree: true });
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
}
