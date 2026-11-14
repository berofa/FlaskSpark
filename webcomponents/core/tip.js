import { escapeHtml } from "./escape.js";
import { computePlacement, resolvePlacement } from "./placement.js";
import { sanitizeHtml } from "./sanitize.js";
import { afterTransition } from "./transitions.js";

const BREAKPOINTS = { sm: 576, md: 768, lg: 1024, xl: 1280, "2xl": 1536 };
const SIDES = { top: "top", bottom: "bottom", left: "start", right: "end" };
const supportsPopover = typeof HTMLElement !== "undefined" && "showPopover" in HTMLElement.prototype;
const open = new Set();

/**
 * A tooltip or popover box for a trigger (Bootstrap 6's Tooltip / Popover plugins without Floating UI):
 * the .tooltip / .popover element in the top layer (popover="manual", never clipped), placed at the trigger
 * (responsive placement like "top md:right", flipping when there is no room, offset), shown on the triggers
 * (hover, focus, click, manual) with delays, text or sanitized HTML (or slots, for components), customClass,
 * animation, enable / disable, events <prefix>:show / shown / hide / hidden / inserted on `events`.
 *
 * `root`: where the box is inserted (a component's shadow root, or document.body for plain markup).
 * `options()`: { title, content, html, sanitize, placement, offset, delay, trigger, customClass, animation,
 *   titleSlot, contentSlot, reference }.
 */
export class Tip {
  constructor(trigger, { kind, root, events, options }) {
    this.trigger = trigger;
    this.kind = kind; // "tooltip" | "popover"
    this.root = root;
    this.events = events || trigger;
    this.options = options;
    this.enabled = true;
    this.box = null;
    this.timer = 0;
    this.pinned = false; // opened by a click
    this.reposition = () => this.update();
    this.onDocumentClick = (event) => {
      const path = event.composedPath();
      if (!path.includes(this.trigger) && !path.includes(this.box)) this.hide();
    };
    this.onKeydown = (event) => {
      if (event.key === "Escape") this.hide();
    };
    this.#wire();
  }

  get isShown() {
    return Boolean(this.box?.classList.contains("show"));
  }

  #emit(name, cancelable = false) {
    return this.events.dispatchEvent(new CustomEvent(`ui-${this.kind}:${name}`, { bubbles: true, cancelable }));
  }

  /** The options with the content set by setContent(). */
  #options() {
    return { ...this.options(), ...(this.overrides || {}) };
  }

  #triggers() {
    const fallback = this.kind === "popover" ? "click" : "hover focus";
    return new Set(String(this.#options().trigger || fallback).split(/\s+/).filter(Boolean));
  }

  #delay(type) {
    const delay = this.#options().delay;
    if (delay && typeof delay === "object") return Number(delay[type]) || 0;
    if (typeof delay === "string" && delay.trim().startsWith("{")) {
      try {
        return Number(JSON.parse(delay)[type]) || 0;
      } catch {
        return 0;
      }
    }
    return Number(delay) || 0;
  }

  #wire() {
    const t = this.trigger;
    t.addEventListener("pointerenter", (event) => {
      if (this.#triggers().has("hover") && event.pointerType !== "touch") this.#schedule("show");
    });
    t.addEventListener("pointerleave", (event) => {
      if (this.#triggers().has("hover") && !this.pinned && !this.#overBox(event)) this.#schedule("hide");
    });
    t.addEventListener("focusin", () => {
      if (this.#triggers().has("focus")) this.#schedule("show");
    });
    t.addEventListener("focusout", (event) => {
      if (this.#triggers().has("focus") && !this.pinned && !this.box?.contains(event.relatedTarget)) this.#schedule("hide");
    });
    t.addEventListener("click", () => {
      const triggers = this.#triggers();
      if (triggers.has("click")) {
        this.pinned = !this.isShown || !this.pinned;
        (this.pinned ? this.show() : this.hide());
      } else if (triggers.has("hover") && !triggers.has("focus")) {
        // Touch: a tap shows a hover-only tip.
        this.toggle();
      }
    });
  }

  #overBox(event) {
    return Boolean(this.box && event.relatedTarget && this.box.contains(event.relatedTarget));
  }

  #schedule(action) {
    clearTimeout(this.timer);
    const wait = this.#delay(action);
    if (wait) {
      this.timer = setTimeout(() => (action === "show" ? this.show() : this.hide()), wait);
    } else if (action === "show") {
      this.show();
    } else {
      this.hide();
    }
  }

  #content(value, slotName) {
    const options = this.#options();
    if (slotName) return `<slot name="${slotName}">${this.#text(value, options)}</slot>`;
    return this.#text(value, options);
  }

  #text(value, options) {
    if (value === undefined || value === null) return "";
    if (options.html === true || options.html === "true") {
      return options.sanitize === false || options.sanitize === "false" ? String(value) : sanitizeHtml(String(value));
    }
    return escapeHtml(String(value));
  }

  #render() {
    const options = this.#options();
    const instant = options.animation === false || options.animation === "false";
    const classes = [this.kind, `bs-${this.kind}-auto`, instant ? `${this.kind}-instant` : "", options.customClass || ""].filter(Boolean).join(" ");
    const box = this.box || document.createElement("div");
    box.className = classes;
    box.setAttribute("role", "tooltip");
    if (supportsPopover) box.setAttribute("popover", "manual");
    if (this.kind === "tooltip") {
      box.innerHTML = `<div class="tooltip-arrow" part="arrow"></div><div class="tooltip-inner" part="inner">${this.#content(options.title, options.titleSlot)}</div>`;
    } else {
      const title = this.#content(options.title, options.titleSlot);
      const hasTitle = options.titleSlot ? true : Boolean(options.title);
      box.innerHTML = `<div class="popover-arrow" part="arrow"></div>${hasTitle ? `<h3 class="popover-header" part="header">${title}</h3>` : ""}`
        + `<div class="popover-body" part="body">${this.#content(options.content, options.contentSlot)}</div>`;
    }
    box.setAttribute("part", this.kind);
    if (!box.isConnected) {
      box.addEventListener("pointerleave", (event) => {
        if (this.#triggers().has("hover") && !this.pinned && !this.trigger.contains(event.relatedTarget)) this.#schedule("hide");
      });
      box.addEventListener("pointerenter", () => clearTimeout(this.timer));
      this.root.append(box);
      this.#emit("inserted");
    }
    this.box = box;
    if (!this.box.id) {
      this.box.id = `ui-${this.kind}-${Math.random().toString(36).slice(2, 9)}`;
    }
    this.trigger.setAttribute("aria-describedby", this.box.id);
  }

  show() {
    clearTimeout(this.timer);
    if (!this.enabled || this.isShown || !this.#emit("show", true)) return Promise.resolve(false);
    // One popover at a time; tooltips close only their own.
    if (this.kind === "popover") open.forEach((other) => other !== this && other.kind === "popover" && other.hide());
    this.#render();
    if (supportsPopover && !this.box.matches(":popover-open")) this.box.showPopover();
    this.box.classList.add("show");
    this.update();
    open.add(this);
    window.addEventListener("scroll", this.reposition, true);
    window.addEventListener("resize", this.reposition);
    document.addEventListener("keydown", this.onKeydown);
    document.addEventListener("click", this.onDocumentClick, true);
    return new Promise((resolve) => afterTransition(this.box, () => {
      this.#emit("shown");
      resolve(true);
    }));
  }

  hide() {
    clearTimeout(this.timer);
    if (!this.isShown || !this.#emit("hide", true)) return Promise.resolve(false);
    this.pinned = false;
    const box = this.box;
    box.classList.remove("show");
    open.delete(this);
    this.trigger.removeAttribute("aria-describedby");
    window.removeEventListener("scroll", this.reposition, true);
    window.removeEventListener("resize", this.reposition);
    document.removeEventListener("keydown", this.onKeydown);
    document.removeEventListener("click", this.onDocumentClick, true);
    return new Promise((resolve) => afterTransition(box, () => {
      if (!box.classList.contains("show")) {
        if (supportsPopover && box.matches(":popover-open")) box.hidePopover();
        this.#emit("hidden");
      }
      resolve(true);
    }));
  }

  toggle() {
    return this.isShown ? this.hide() : this.show();
  }

  /** Places the box at the trigger (or options.reference) again. */
  update() {
    if (!this.box || !this.isShown) return;
    const options = this.#options();
    const fallback = this.kind === "popover" ? "right" : "top";
    let side = resolvePlacement(options.placement || fallback, window.innerWidth, BREAKPOINTS).split("-")[0];
    const rtl = getComputedStyle(this.trigger).direction === "rtl";
    if (side === "start") side = rtl ? "right" : "left";
    if (side === "end") side = rtl ? "left" : "right";
    if (side === "auto") side = fallback;
    const offset = String(options.offset ?? (this.kind === "popover" ? "0,8" : "0,6")).split(",").map((v) => Number.parseFloat(v) || 0);
    const reference = (options.reference || this.trigger).getBoundingClientRect();
    const triggerRect = this.trigger.getBoundingClientRect();
    const size = { width: this.box.offsetWidth, height: this.box.offsetHeight };
    const viewport = { width: document.documentElement.clientWidth, height: window.innerHeight };
    const result = computePlacement(reference, size, viewport, side, { gap: offset[1] ?? 6 });
    const vertical = result.placement === "top" || result.placement === "bottom";
    const left = result.left + (vertical ? offset[0] : 0);
    const top = result.top + (vertical ? 0 : offset[0]);
    this.box.style.left = `${left}px`;
    this.box.style.top = `${top}px`;
    this.box.dataset.bsPlacement = result.placement;
    this.box.classList.remove(...Object.values(SIDES).map((s) => `bs-${this.kind}-${s}`));
    // The arrow points at the trigger (also when the box sits at another reference).
    const arrow = this.box.querySelector(`.${this.kind}-arrow`);
    if (arrow) {
      const center = vertical ? triggerRect.left + triggerRect.width / 2 - left : triggerRect.top + triggerRect.height / 2 - top;
      const half = (vertical ? arrow.offsetWidth : arrow.offsetHeight) / 2;
      arrow.style.left = vertical ? `${center - half}px` : "";
      arrow.style.top = vertical ? "" : `${center - half}px`;
    }
  }

  setContent({ title, content } = {}) {
    this.overrides = { ...(this.overrides || {}), ...(title !== undefined ? { title } : {}), ...(content !== undefined ? { content } : {}) };
    if (this.isShown) {
      this.#render();
      this.update();
    }
  }

  enable() { this.enabled = true; }

  disable() { this.enabled = false; this.hide(); }

  toggleEnabled() { (this.enabled ? this.disable() : this.enable()); }

  dispose() {
    this.hide();
    this.box?.remove();
    this.box = null;
  }
}
