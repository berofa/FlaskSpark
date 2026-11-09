import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { afterTransition } from "../../../core/transitions.js";

const VARIANTS = new Set(["primary", "secondary", "success", "danger", "warning", "info", "light", "dark"]);
const PLACEMENTS = new Set(["top-start", "top-center", "top-end", "bottom-start", "bottom-center", "bottom-end"]);

/**
 * <ui-toast>: a Bootstrap toast, a short message that does not move the page (in a <ui-toast-container>).
 *
 * Attributes:
 * - variant: colour (Bootstrap's subtle background of the variant; default none: the plain toast).
 * - delay: milliseconds until it goes away by itself (default 5000; "0": stays until closed).
 * - heading: a title line above the message.
 * - keep: stays in the DOM when hidden (default: removed).
 *
 * Slots: default (the message).
 * Methods / events: show() (fades it in; on connect by itself), close(); ui-toast:hidden (bubbles) after it went.
 * Hovering or focusing it pauses the delay. role="status" (an error: role="alert").
 * CSS parts: toast, header, body.
 */
export class UiToast extends ShadowComponentElement {
  static stylesheet = new URL("./ui-toast.css", import.meta.url).href;
  static observedAttributes = ["variant", "heading"];

  #timer = null;
  #closing = false;
  #shown = false;

  render() {
    const variant = VARIANTS.has(this.getAttribute("variant")) ? this.getAttribute("variant") : "";
    const heading = this.getAttribute("heading");
    const urgent = variant === "danger" || variant === "warning";
    const close = '<button type="button" class="btn-close" aria-label="Schliessen"></button>';
    return `
      <div class="toast fade${this.#shown ? " show" : ""}${variant ? ` ui-toast-${escapeHtml(variant)}` : ""}" part="toast"
        role="${urgent ? "alert" : "status"}" aria-live="${urgent ? "assertive" : "polite"}" aria-atomic="true">
        ${heading ? `<div class="toast-header" part="header"><strong class="me-auto">${escapeHtml(heading)}</strong>${close}</div>` : ""}
        <div class="toast-body" part="body"><slot></slot>${heading ? "" : close}</div>
      </div>`;
  }

  afterRender() {
    this.shadowRoot.querySelector(".btn-close")?.addEventListener("click", () => this.close());
    const toast = this.shadowRoot.querySelector(".toast");
    toast.addEventListener("mouseenter", () => this.#pause());
    toast.addEventListener("mouseleave", () => this.#arm());
    toast.addEventListener("focusin", () => this.#pause());
    toast.addEventListener("focusout", () => this.#arm());
    if (!this.#shown) requestAnimationFrame(() => this.show());
  }

  show() {
    this.#shown = true;
    this.hidden = false;
    this.shadowRoot.querySelector(".toast")?.classList.add("show");
    this.#arm();
  }

  #pause() {
    clearTimeout(this.#timer);
  }

  #arm() {
    clearTimeout(this.#timer);
    const delay = Number(this.getAttribute("delay") ?? 5000);
    if (delay > 0) this.#timer = setTimeout(() => this.close(), delay);
  }

  close() {
    if (this.#closing) return;
    this.#closing = true;
    clearTimeout(this.#timer);
    const toast = this.shadowRoot.querySelector(".toast");
    const done = () => {
      this.#closing = false;
      this.#shown = false;
      this.dispatchEvent(new CustomEvent("ui-toast:hidden", { bubbles: true }));
      if (this.hasAttribute("keep")) this.hidden = true;
      else this.remove();
    };
    if (!toast) return done();
    toast.classList.remove("show");
    afterTransition(toast, done);
  }

  disconnectedCallback() {
    clearTimeout(this.#timer);
  }
}

/**
 * <ui-toast-container>: the stack of toasts, fixed at a corner of the window (placement: top-end by default,
 * top-start, top-center, bottom-start, bottom-center, bottom-end). Newest at the top (top-*) or at the bottom.
 */
export class UiToastContainer extends ShadowComponentElement {
  static stylesheet = new URL("./ui-toast.css", import.meta.url).href;
  static observedAttributes = ["placement"];

  render() {
    const placement = PLACEMENTS.has(this.getAttribute("placement")) ? this.getAttribute("placement") : "top-end";
    return `<div class="ui-toast-stack ui-toast-${placement}" part="stack"><slot></slot></div>`;
  }
}

/**
 * A toast with `message` in the page's container (created on first use, at placement): showToast("Gespeichert."),
 * showToast("Fehler", {variant: "danger", delay: 0}). Returns the <ui-toast>.
 */
export function showToast(message, { variant = "", delay = 5000, heading = "", placement = "top-end" } = {}) {
  let stack = document.querySelector(`ui-toast-container[placement="${placement}"]`);
  if (!stack) {
    stack = document.createElement("ui-toast-container");
    stack.setAttribute("placement", placement);
    document.body.append(stack);
  }
  const toast = document.createElement("ui-toast");
  if (variant) toast.setAttribute("variant", variant);
  if (heading) toast.setAttribute("heading", heading);
  toast.setAttribute("delay", String(delay));
  toast.textContent = message;
  if (placement.startsWith("top")) stack.prepend(toast);
  else stack.append(toast);
  return toast;
}

registerComponent("ui-toast", UiToast);
registerComponent("ui-toast-container", UiToastContainer);
