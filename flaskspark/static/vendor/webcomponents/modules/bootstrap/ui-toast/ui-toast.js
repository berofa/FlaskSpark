import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { afterTransition } from "../../../core/transitions.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

const PLACEMENTS = new Set(["top-start", "top-center", "top-end", "middle-start", "middle-center", "middle-end",
  "bottom-start", "bottom-center", "bottom-end"]);

/**
 * <ui-toast> (Bootstrap 6 toast): a short message that does not move the page, usually in a <ui-toast-container>.
 *
 * Attributes:
 * - heading (or slot "heading"): the header line with a close button; meta: small text in it (e.g. "11 mins ago").
 * - variant: theme colour of border and header.
 * - translucent: blurred background. instant: no fade. data-bs-theme="dark": a dark toast.
 * - autohide="false" or delay="0": stays until closed; delay: ms until it hides (default 5000). Hovering or
 *   focusing it pauses the timer.
 * - keep: stays in the DOM when hidden (default: removed). static: not shown on connect (show() it).
 *
 * Slots: default (the body), heading. Elements inside with data-bs-dismiss="toast" close it.
 * Methods: show(), hide() (also close()) — promises. Events (bubble): ui-toast:show and ui-toast:hide
 * (cancelable), ui-toast:shown, ui-toast:hidden. role="status" (variant danger: role="alert").
 * Parts: toast, header, body, close.
 */
export class UiToast extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-toast.css", import.meta.url).href];
  static observedAttributes = ["heading", "meta", "variant", "translucent", "instant"];

  #timer = 0;
  #paused = false;

  constructor() {
    super();
    this.addEventListener("click", (event) => {
      if (event.target instanceof Element && event.target.closest('[data-bs-dismiss="toast"]')) {
        this.hide();
      }
    });
    for (const [type, paused] of [["pointerenter", true], ["pointerleave", false], ["focusin", true], ["focusout", false]]) {
      this.addEventListener(type, () => {
        this.#paused = paused;
        if (!paused) this.#arm();
        else clearTimeout(this.#timer);
      });
    }
  }

  get #toast() {
    return this.shadowRoot.querySelector(".toast");
  }

  get shown() {
    return Boolean(this.#toast?.classList.contains("show"));
  }

  render() {
    const variant = themeColor(this.getAttribute("variant"));
    const classes = ["toast", HOST_TOKENS_CLASS, variant ? `theme-${variant}` : "",
      this.hasAttribute("translucent") ? "toast-translucent" : "", this.hasAttribute("instant") ? "toast-instant" : "",
      this.shown ? "show" : ""].filter(Boolean).join(" ");
    const heading = this.getAttribute("heading");
    const meta = this.getAttribute("meta");
    const hasHeader = heading !== null || [...this.children].some((child) => child.slot === "heading");
    const role = variant === "danger" ? 'role="alert" aria-live="assertive"' : 'role="status" aria-live="polite"';
    const close = '<button type="button" class="btn-close" data-close part="close" aria-label="Close"></button>';
    return `
      <div class="${classes}" ${role} aria-atomic="true" part="toast">
        ${hasHeader ? `<div class="toast-header" part="header"><strong class="me-auto"><slot name="heading">${escapeHtml(heading || "")}</slot></strong>`
          + `${meta ? `<small>${escapeHtml(meta)}</small>` : ""}${close}</div>` : ""}
        <div class="toast-body" part="body"><slot></slot></div>
      </div>
    `;
  }

  afterRender() {
    this.shadowRoot.querySelector("[data-close]")?.addEventListener("click", () => this.hide());
    if (!this.hasAttribute("static") && !this.dataset.uiShown) {
      this.dataset.uiShown = "true";
      this.show();
    }
  }

  #arm() {
    clearTimeout(this.#timer);
    const delay = Number.parseInt(this.getAttribute("delay") ?? "5000", 10);
    if (this.getAttribute("autohide") === "false" || !(delay > 0) || this.#paused || !this.shown) return;
    this.#timer = setTimeout(() => this.hide(), delay);
  }

  show() {
    const toast = this.#toast;
    if (!toast || this.shown || !this.dispatchEvent(new CustomEvent("ui-toast:show", { bubbles: true, cancelable: true }))) {
      return Promise.resolve(false);
    }
    toast.classList.add("show");
    return new Promise((resolve) => afterTransition(toast, () => {
      this.dispatchEvent(new CustomEvent("ui-toast:shown", { bubbles: true }));
      this.#arm();
      resolve(true);
    }));
  }

  hide() {
    const toast = this.#toast;
    if (!toast || !this.shown || !this.dispatchEvent(new CustomEvent("ui-toast:hide", { bubbles: true, cancelable: true }))) {
      return Promise.resolve(false);
    }
    clearTimeout(this.#timer);
    toast.classList.remove("show");
    return new Promise((resolve) => afterTransition(toast, () => {
      this.dispatchEvent(new CustomEvent("ui-toast:hidden", { bubbles: true }));
      if (!this.hasAttribute("keep")) this.remove();
      resolve(true);
    }));
  }

  close() {
    return this.hide();
  }
}

/**
 * <ui-toast-container> (Bootstrap's .toast-container): a stack of toasts fixed in the window; placement
 * top-, middle- or bottom- with -start, -center or -end (default top-end). Newest at the edge.
 */
export class UiToastContainer extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-toast.css", import.meta.url).href];
  static observedAttributes = ["placement"];

  render() {
    const placement = PLACEMENTS.has(this.getAttribute("placement")) ? this.getAttribute("placement") : "top-end";
    return `<div class="toast-container ui-toast-${placement}" part="container"><slot></slot></div>`;
  }
}

/**
 * A toast with `message` in the page's container for `placement` (created on first use):
 * showToast("Saved."), showToast("Error", { variant: "danger", delay: 0, heading: "Upload" }). Returns the <ui-toast>.
 */
export function showToast(message, { variant = "", delay = 5000, heading = "", meta = "", placement = "top-end" } = {}) {
  let stack = document.querySelector(`ui-toast-container[placement="${placement}"]`);
  if (!stack) {
    stack = document.createElement("ui-toast-container");
    stack.setAttribute("placement", placement);
    document.body.append(stack);
  }
  const toast = document.createElement("ui-toast");
  if (variant) toast.setAttribute("variant", variant);
  if (heading) toast.setAttribute("heading", heading);
  if (meta) toast.setAttribute("meta", meta);
  toast.setAttribute("delay", String(delay));
  toast.textContent = message;
  if (placement.startsWith("top")) stack.prepend(toast);
  else stack.append(toast);
  return toast;
}

registerComponent("ui-toast", UiToast);
registerComponent("ui-toast-container", UiToastContainer);
