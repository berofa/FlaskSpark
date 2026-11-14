import { SharedShadowStyles } from "../../../core/shared-shadow-styles.js";
import { afterTransition } from "../../../core/transitions.js";

const DOCUMENT_STYLES = new URL("./plain-dialog.document.css", import.meta.url).href;
const STATIC_PULSE = 300;
const controllers = new WeakMap();

/**
 * Bootstrap's dialog and drawer plugins for plain markup: a native <dialog class="dialog"> or
 * <dialog class="drawer drawer-end"> in the page (light DOM), opened by data-bs-toggle="dialog|drawer"
 * triggers. The page's Bootstrap CSS styles it (also rules like .md:navbar-expand [class*=drawer]), this
 * controller adds what Bootstrap's JavaScript does: showModal(), the animated close (.hiding), backdrop and
 * Escape handling (backdrop / keyboard / scroll / modal options), data-bs-dismiss, aria-expanded on triggers,
 * events (ui-dialog:* / ui-drawer:* on the <dialog>).
 */
export class PlainDialog {
  static for(dialog) {
    if (!controllers.has(dialog)) {
      controllers.set(dialog, new PlainDialog(dialog));
    }
    return controllers.get(dialog);
  }

  constructor(dialog) {
    SharedShadowStyles.applyToDocument(DOCUMENT_STYLES);
    this.dialog = dialog;
    this.kind = dialog.classList.contains("dialog") ? "dialog" : "drawer";
    this.options = {};
    this.trigger = null;
    dialog.addEventListener("click", (event) => this.#click(event));
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      this.#emit("cancel");
      if (this.options.keyboard === "false") this.#prevented();
      else this.hide();
    });
  }

  get isOpen() {
    return this.dialog.open && !this.dialog.classList.contains("hiding");
  }

  #emit(name, cancelable = false) {
    return this.dialog.dispatchEvent(new CustomEvent(`ui-${this.kind}:${name}`, { bubbles: true, cancelable }));
  }

  get #modal() {
    if (this.kind === "drawer") {
      return !(this.options.scroll === "true" && this.options.backdrop === "false");
    }
    return this.options.modal !== "false";
  }

  #prevented() {
    this.#emit("hide-prevented");
    const pulse = `${this.kind}-static`;
    this.dialog.classList.add(pulse);
    setTimeout(() => this.dialog.classList.remove(pulse), STATIC_PULSE);
  }

  #click(event) {
    if (event.target instanceof Element && event.target.closest(`[data-bs-dismiss="${this.kind}"]`)) {
      event.preventDefault();
      this.hide();
      return;
    }
    if (event.target !== this.dialog || !this.#modal) return;
    const box = this.dialog.getBoundingClientRect();
    const outside = event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom;
    if (!outside) return;
    if (this.options.backdrop === "static") this.#prevented();
    else if (this.options.backdrop !== "false") this.hide();
  }

  #syncTrigger(expanded) {
    this.trigger?.setAttribute("aria-expanded", String(expanded));
  }

  show(options = {}, trigger = null) {
    // Inline in its layout (a navbar's drawer above the breakpoint): nothing to open.
    if (this.isOpen || getComputedStyle(this.dialog).position === "static") return Promise.resolve(false);
    if (!this.#emit("show", true)) return Promise.resolve(false);
    this.options = options;
    this.trigger = trigger;
    const dialog = this.dialog;
    dialog.classList.toggle(`${this.kind}-nonmodal`, !this.#modal);
    dialog.classList.add("ui-opening");
    if (this.#modal) {
      dialog.showModal();
      if (!(this.kind === "drawer" && this.options.scroll === "true")) {
        document.documentElement.classList.add("dialog-open");
      }
    } else {
      dialog.show();
    }
    getComputedStyle(dialog).opacity; // the closed look applies once, so the transition runs
    dialog.classList.remove("ui-opening");
    this.#syncTrigger(true);
    return new Promise((resolve) => afterTransition(dialog, () => {
      this.#emit("shown");
      resolve(true);
    }));
  }

  hide() {
    if (!this.isOpen || !this.#emit("hide", true)) return Promise.resolve(false);
    const dialog = this.dialog;
    dialog.classList.add("hiding");
    this.#syncTrigger(false);
    return new Promise((resolve) => afterTransition(dialog, () => {
      dialog.close();
      dialog.classList.remove("hiding", `${this.kind}-nonmodal`);
      if (!document.querySelector("dialog:modal")) {
        document.documentElement.classList.remove("dialog-open");
      }
      this.#emit("hidden");
      resolve(true);
    }));
  }

  toggle(options = {}, trigger = null) {
    return this.isOpen ? this.hide() : this.show(options, trigger);
  }
}
