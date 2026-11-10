import { STRENGTH_LEVELS, scorePassword, strengthLevel } from "../../core/password-strength.js";

/**
 * Bootstrap 6's password strength meter (js/src/strength.ts, MIT) for a `.strength` (segments) or `.strength-bar`
 * element: rates the password field while typing and shows the level (data-bs-strength, active segments, the bar's
 * width) and a message in a `.strength-text` next to it. Scoring: core/password-strength.js.
 *
 * Options: input (the field), text (the message element), messages {weak, fair, good, strong}, minLength,
 * weights, thresholds, scorer(password) → number, emit({strength, score}) (default: ui-strength:change on the meter).
 */
export const STRENGTH_MESSAGES = { weak: "Weak", fair: "Fair", good: "Good", strong: "Strong" };
// The message takes the text colour of its level (Bootstrap's segments use the background colours).
const TEXT_COLORS = { weak: "danger", fair: "warning", good: "info", strong: "success" };

export class StrengthController {
  constructor(element, options = {}) {
    this.element = element;
    this.options = options;
    this.input = options.input || null;
    this.text = options.text || null;
    this.strength = null;
    this.score = 0;
    this.onInput = () => this.evaluate();
    if (this.input) {
      this.input.addEventListener("input", this.onInput);
      this.input.addEventListener("change", this.onInput);
      this.evaluate();
    }
  }

  evaluate() {
    const password = this.input?.value || "";
    const score = scorePassword(password, this.options);
    const strength = strengthLevel(score, this.options.thresholds);
    this.score = score;
    if (strength === this.strength) {
      return;
    }
    this.strength = strength;
    this.#show(strength);
    const detail = { strength, score };
    if (this.options.emit) {
      this.options.emit(detail);
    } else {
      this.element.dispatchEvent(new CustomEvent("ui-strength:change", { bubbles: true, detail }));
    }
  }

  #show(strength) {
    if (strength) {
      this.element.dataset.bsStrength = strength;
    } else {
      delete this.element.dataset.bsStrength;
    }
    const level = strength ? STRENGTH_LEVELS.indexOf(strength) : -1;
    this.element.querySelectorAll(".strength-segment").forEach((segment, index) => segment.classList.toggle("active", index <= level));
    if (this.text) {
      const messages = { ...STRENGTH_MESSAGES, ...(this.options.messages || {}) };
      this.text.textContent = strength ? messages[strength] || "" : "";
      if (strength) {
        this.text.dataset.bsStrength = strength;
        this.text.style.setProperty("--bs-strength-color", `var(--bs-${TEXT_COLORS[strength]}-fg)`);
      } else {
        delete this.text.dataset.bsStrength;
        this.text.style.removeProperty("--bs-strength-color");
      }
    }
  }

  dispose() {
    this.input?.removeEventListener("input", this.onInput);
    this.input?.removeEventListener("change", this.onInput);
  }
}

const plain = new WeakMap();

/** The controller of a plain `[data-bs-strength]` meter (data-bs-input, data-bs-min-length). */
export function plainStrength(element) {
  let controller = plain.get(element);
  if (!controller) {
    const selector = element.getAttribute("data-bs-input");
    const input = selector ? document.querySelector(selector) : element.parentElement?.querySelector('input[type="password"]');
    const minLength = Number.parseInt(element.getAttribute("data-bs-min-length"), 10);
    controller = new StrengthController(element, {
      input,
      text: element.parentElement?.querySelector(".strength-text") || null,
      ...(Number.isNaN(minLength) ? {} : { minLength }),
    });
    plain.set(element, controller);
  }
  return controller;
}

let installed = false;

/** Bootstrap's data API: every `[data-bs-strength]` (with a password field) on load. Static meters stay as they are. */
export function installStrengthDataApi() {
  if (installed || typeof document === "undefined") {
    return;
  }
  installed = true;
  const start = () => document.querySelectorAll(".strength[data-bs-strength], .strength-bar[data-bs-strength]").forEach((element) => {
    if (!element.getAttribute("data-bs-strength")) plainStrength(element); // a set level is a static display
  });
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
}

installStrengthDataApi();
