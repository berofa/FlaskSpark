/**
 * Bootstrap 6's range behaviour (js/src/range.ts, MIT) for a `.form-range` wrapper with its `.form-range-input`:
 * the filled track (--bs-range-fill on the wrapper), the value bubble (a tooltip that follows the thumb) and tick
 * marks with labels. Works in the document and in a shadow tree.
 *
 * Options: bubble (boolean), formatter(value) → text (bubble and labels), ticks() → [{value, label}] (default:
 * the options of the <datalist> the input's list attribute names), emit(value) (default: `ui-range:changed` on the
 * input, detail.value).
 */
export class RangeController {
  constructor(element, options = {}) {
    this.element = element;
    this.options = options;
    this.input = element.querySelector(".form-range-input");
    this.bubble = null;
    this.bubbleText = null;
    this.ticks = null;
    this.onUpdate = () => this.update();
    if (!this.input) {
      return;
    }
    if (options.bubble) {
      this.#createBubble();
    }
    this.#createTicks();
    this.input.addEventListener("input", this.onUpdate);
    this.input.addEventListener("change", this.onUpdate);
    this.update();
  }

  #min() {
    return this.input.min === "" ? 0 : Number.parseFloat(this.input.min);
  }

  #max() {
    return this.input.max === "" ? 100 : Number.parseFloat(this.input.max);
  }

  get value() {
    return Number.parseFloat(this.input.value);
  }

  #ratio() {
    const span = this.#max() - this.#min();
    return span > 0 ? (this.value - this.#min()) / span : 0;
  }

  format(value) {
    return typeof this.options.formatter === "function" ? this.options.formatter(value) : String(value);
  }

  /** Fill and bubble from the input's current value (also after setting it from script). */
  update() {
    if (!this.input) return;
    this.element.style.setProperty("--bs-range-fill", `${this.#ratio()}`);
    if (this.bubbleText) {
      this.bubbleText.textContent = this.format(this.value);
    }
    if (this.options.emit) {
      this.options.emit(this.value);
    } else {
      this.input.dispatchEvent(new CustomEvent("ui-range:changed", { bubbles: true, detail: { value: this.value } }));
    }
  }

  #createBubble() {
    this.bubble = document.createElement("output");
    this.bubble.className = "form-range-bubble tooltip bs-tooltip-top show";
    this.bubble.setAttribute("aria-hidden", "true");
    this.bubble.setAttribute("part", "bubble");
    const arrow = document.createElement("div");
    arrow.className = "tooltip-arrow";
    this.bubbleText = document.createElement("div");
    this.bubbleText.className = "tooltip-inner";
    this.bubble.append(arrow, this.bubbleText);
    this.input.insertAdjacentElement("afterend", this.bubble);
  }

  #tickSource() {
    if (this.options.ticks) {
      return this.options.ticks();
    }
    const id = this.input.getAttribute("list");
    const datalist = id ? (this.input.getRootNode().getElementById?.(id) || document.getElementById(id)) : null;
    return datalist ? [...datalist.querySelectorAll("option")].map((option) => ({ value: option.value, label: option.label })) : [];
  }

  #createTicks() {
    this.ticks?.remove();
    this.ticks = null;
    const min = this.#min();
    const span = this.#max() - min || 1;
    const points = this.#tickSource()
      .map(({ value, label }) => ({ value: Number.parseFloat(value), label: label || "" }))
      .filter(({ value }) => !Number.isNaN(value))
      .map(({ value, label }) => ({ ratio: Math.min(Math.max((value - min) / span, 0), 1), label }))
      .sort((a, b) => a.ratio - b.ratio);
    if (!points.length) {
      return;
    }
    this.ticks = document.createElement("div");
    this.ticks.className = "form-range-ticks";
    this.ticks.setAttribute("aria-hidden", "true");
    this.ticks.setAttribute("part", "ticks");
    const stops = [0, ...points.map((point) => point.ratio), 1];
    this.ticks.style.gridTemplateColumns = stops.slice(1).map((stop, index) => `${stop - stops[index]}fr`).join(" ");
    points.forEach((point, index) => {
      const tick = document.createElement("span");
      tick.className = "form-range-tick";
      tick.style.gridColumnStart = `${index + 2}`;
      if (point.label) {
        const label = document.createElement("span");
        label.className = "form-range-tick-label";
        label.textContent = point.label;
        tick.append(label);
      }
      this.ticks.append(tick);
    });
    this.element.append(this.ticks);
  }

  dispose() {
    this.input?.removeEventListener("input", this.onUpdate);
    this.input?.removeEventListener("change", this.onUpdate);
    this.bubble?.remove();
    this.ticks?.remove();
  }
}

const plain = new WeakMap();

/** The controller of a plain `.form-range` (data-bs-bubble shows the bubble). */
export function plainRange(element) {
  let controller = plain.get(element);
  if (!controller) {
    controller = new RangeController(element, { bubble: element.hasAttribute("data-bs-bubble") });
    plain.set(element, controller);
  }
  return controller;
}

let installed = false;

/** Bootstrap's range data API: every `.form-range` of the page (also ones added later) gets a controller. */
export function installRangeDataApi() {
  if (installed || typeof document === "undefined") {
    return;
  }
  installed = true;
  const scan = (root) => root.querySelectorAll?.(".form-range").forEach((element) => plainRange(element));
  const start = () => {
    scan(document);
    new MutationObserver((records) => records.forEach((record) => record.addedNodes.forEach((node) => {
      if (node.nodeType !== 1) return;
      if (node.matches(".form-range")) plainRange(node);
      scan(node);
    }))).observe(document.documentElement, { childList: true, subtree: true });
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
}
