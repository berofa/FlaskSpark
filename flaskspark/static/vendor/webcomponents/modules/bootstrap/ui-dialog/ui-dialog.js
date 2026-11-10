import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { morph } from "../../../core/morph.js";
import { observeItems } from "../../../core/slotted-items.js";
import { afterTransition } from "../../../core/transitions.js";
import { registerToggle } from "../../../core/triggers.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";
import { PlainDialog } from "./plain-dialog.js";

const SIZES = new Set(["sm", "lg", "xl"]);
const BREAKPOINTS = new Set(["sm", "md", "lg", "xl", "2xl"]);
const ANIMATIONS = new Map([["instant", "dialog-instant"], ["slide-down", "dialog-slide-down"], ["slide-up", "dialog-slide-up"]]);
const STATIC_PULSE = 300;
// Classes the component sets while open or animating; a new render keeps them.
export const STATE_CLASSES = ["hiding", "dialog-nonmodal", "dialog-static", "drawer-static", "dialog-swap-in", "ui-opening", "ui-no-backdrop"];
const openModals = new Set();
// Dialog elements whose listeners are bound (morph keeps the element across renders; an attribute would not survive).
const wired = new WeakSet();

/**
 * <ui-dialog> (Bootstrap 6 dialog on the native <dialog>: top layer, backdrop, focus trap).
 *
 * Attributes:
 * - open: shown; reflected, can be set declaratively.
 * - heading: title text (or the slot "heading"); with a heading the header has a close button
 *   (no-close: without it; close-label: its accessible name).
 * - size: sm, lg or xl. fullscreen: always, or below a breakpoint (sm, md, lg, xl, 2xl).
 * - scrollable: the body scrolls, header and footer stay.
 * - animation: fade (default), instant, slide-down or slide-up.
 * - backdrop: "static" (outside clicks don't close it, the dialog pulses) or "false" (no backdrop).
 * - keyboard="false": Escape does not close it. modal="false": a non-modal dialog (no backdrop,
 *   no focus trap, the page stays usable).
 * - data-bs-theme="dark": a dark dialog.
 *
 * Slots: default (body), heading, footer. Elements inside with data-bs-dismiss="dialog" close it.
 * Triggers anywhere: data-bs-toggle="dialog" data-bs-target="#id" (options as data-bs-backdrop,
 * data-bs-keyboard, data-bs-modal); a trigger inside an open dialog swaps the dialogs. Invoker commands
 * (commandfor + command="show-modal" / "close") work too. Triggers also open Bootstrap's plain
 * <dialog class="dialog"> markup (PlainDialog).
 *
 * Methods: show(options), hide(), toggle(options) — promises that resolve once shown / hidden (false if
 * cancelled). Events (bubble): ui-dialog:show and ui-dialog:hide (cancelable), ui-dialog:shown,
 * ui-dialog:hidden, ui-dialog:hide-prevented, ui-dialog:cancel (Escape).
 * Parts: dialog, header, title, close, body, footer.
 */
export class UiDialog extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-dialog.css", import.meta.url).href];
  static observedAttributes = [
    "open", "heading", "no-close", "close-label", "size", "fullscreen", "scrollable", "animation", "backdrop",
    "keyboard", "modal",
  ];

  /** Prefix of the events (ui-drawer: "ui-drawer"), the class of the pulse when a close is prevented. */
  static eventPrefix = "ui-dialog";
  static staticClass = "dialog-static";

  #stopObserving = null;
  #busy = null;
  #reflecting = false;
  #options = {};

  constructor() {
    super();
    this.addEventListener("click", (event) => {
      if (event.target instanceof Element && event.target.closest('[data-bs-dismiss="dialog"]')) {
        event.preventDefault();
        this.hide();
      }
    });
    // Invoker commands: commandfor="<this id>" command="show-modal" | "close" | "request-close".
    this.addEventListener("command", (event) => {
      if (event.command === "show-modal" || event.command === "show" || event.command === "--show") {
        this.show({ modal: event.command === "show" ? "false" : undefined });
      } else if (event.command === "close" || event.command === "request-close" || event.command === "--hide") {
        this.hide();
      } else if (event.command === "--toggle") {
        this.toggle();
      }
    });
  }

  connectedCallback() {
    super.connectedCallback();
    this.#stopObserving ??= observeItems(this, ["slot"], () => this.requestRender());
  }

  disconnectedCallback() {
    this.#stopObserving?.();
    this.#stopObserving = null;
    openModals.delete(this);
    this.#syncRootClass();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "open") {
      if (!this.#reflecting && this.hasRendered) {
        (newValue === null ? this.hide() : this.show());
      }
      return;
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  /** Fires <prefix>:<name> (bubbles); returns false when a cancelable one was cancelled. */
  emit(name, cancelable = false) {
    return this.dispatchEvent(new CustomEvent(`${this.constructor.eventPrefix}:${name}`, { bubbles: true, cancelable }));
  }

  get dialog() {
    return this.shadowRoot.querySelector("dialog");
  }

  get isOpen() {
    return Boolean(this.dialog?.open) && !this.dialog.classList.contains("hiding");
  }

  /** The effective option: the one passed to show(), else the attribute. */
  option(name) {
    return this.#options[name] ?? this.getAttribute(name);
  }

  renderShadow() {
    morph(this.shadowRoot, this.render());
  }

  render() {
    const size = (this.getAttribute("size") || "").trim().toLowerCase();
    const fullscreen = this.hasAttribute("fullscreen") ? (this.getAttribute("fullscreen") || "").trim().toLowerCase() : null;
    const animation = ANIMATIONS.get((this.getAttribute("animation") || "").trim().toLowerCase());
    const classes = [
      "dialog",
      HOST_TOKENS_CLASS,
      SIZES.has(size) ? `dialog-${size}` : "",
      fullscreen === null ? "" : BREAKPOINTS.has(fullscreen) ? `${fullscreen}-down:dialog-fullscreen` : "dialog-fullscreen",
      this.hasAttribute("scrollable") ? "dialog-scrollable" : "",
      animation || "",
    ].filter(Boolean).join(" ");
    const filled = new Set([...this.children].map((child) => child.slot));
    const heading = this.getAttribute("heading");
    const hasHeader = heading !== null || filled.has("heading");
    const close = this.hasAttribute("no-close")
      ? ""
      : `<button type="button" class="btn-close" part="close" data-close aria-label="${escapeHtml(this.getAttribute("close-label") || "Close")}"></button>`;
    const { stateClasses, openAttribute } = this.currentState();
    return `
      <dialog class="${classes}${stateClasses}" part="dialog"${hasHeader ? ' aria-labelledby="title"' : ""}${openAttribute}>
        ${hasHeader ? `<div class="dialog-header" part="header"><h1 class="dialog-title" id="title" part="title"><slot name="heading">${escapeHtml(heading || "")}</slot></h1>${close}</div>` : ""}
        <div class="dialog-body" part="body"><slot></slot></div>
        ${filled.has("footer") ? '<div class="dialog-footer" part="footer"><slot name="footer"></slot></div>' : ""}
      </dialog>
    `;
  }

  /** The open state and state classes of the current <dialog>: a new render keeps them (morph changes only what differs). */
  currentState() {
    const dialog = this.dialog;
    if (!dialog) {
      return { stateClasses: "", openAttribute: "" };
    }
    return {
      stateClasses: STATE_CLASSES.filter((name) => dialog.classList.contains(name)).map((name) => ` ${name}`).join(""),
      openAttribute: dialog.open ? " open" : "",
    };
  }

  afterRender() {
    const dialog = this.dialog;
    if (wired.has(dialog)) {
      return;
    }
    wired.add(dialog);
    dialog.addEventListener("click", (event) => {
      if (event.target instanceof Element && event.target.closest("[data-close]")) {
        this.hide();
        return;
      }
      // A click on the backdrop: outside the dialog's box (the dialog itself is the target there).
      if (event.target !== dialog || !this.modal) {
        return;
      }
      const box = dialog.getBoundingClientRect();
      const outside = event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom;
      if (!outside) {
        return;
      }
      if (this.option("backdrop") === "static") {
        this.#prevented();
      } else if (this.option("backdrop") !== "false") {
        this.hide();
      }
    });
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      this.emit("cancel");
      if (this.option("keyboard") === "false") {
        this.#prevented();
      } else {
        this.hide();
      }
    });
    if (this.hasAttribute("open") && !dialog.open) {
      this.show();
    }
  }

  /** Opened with showModal() (backdrop, focus trap, top layer). */
  get modal() {
    return this.option("modal") !== "false";
  }

  /** Whether an open dialog stops the page from scrolling (:root.dialog-open). */
  get locksScroll() {
    return this.modal;
  }

  /** Outside click (static backdrop) or Escape (keyboard false): the dialog pulses and stays. */
  #prevented() {
    this.emit("hide-prevented");
    const dialog = this.dialog;
    const pulse = this.constructor.staticClass;
    dialog.classList.add(pulse);
    setTimeout(() => dialog.classList.remove(pulse), STATIC_PULSE);
  }

  #reflect(open) {
    this.#reflecting = true;
    this.toggleAttribute("open", open);
    this.#reflecting = false;
  }

  #syncRootClass() {
    document.documentElement.classList.toggle("dialog-open", openModals.size > 0);
  }

  /** Opens the dialog; options: { modal, backdrop, keyboard } (strings like the attributes) and swap. */
  async show(options = {}) {
    await this.#busy;
    // Not rendered yet (its stylesheets load asynchronously): wait for it, at most a few seconds.
    for (let waited = 0; !this.hasRendered && waited < 5000; waited += 16) {
      await new Promise((resolve) => setTimeout(resolve, 16));
    }
    if (!this.hasRendered) {
      return false;
    }
    if (this.isOpen) {
      return true;
    }
    const allowed = this.emit("show", true);
    if (!allowed) {
      return false;
    }
    this.#options = Object.fromEntries(Object.entries(options).filter(([, value]) => value !== undefined)
      .map(([key, value]) => [key, String(value)]));
    const dialog = this.dialog;
    const modal = this.modal;
    dialog.classList.toggle("dialog-nonmodal", !modal);
    dialog.classList.toggle("ui-no-backdrop", this.option("backdrop") === "false");
    dialog.classList.toggle("dialog-swap-in", Boolean(options.swap));
    // Start from the closed look, so the opening animates (the dialog was display: none before).
    dialog.classList.add("ui-opening");
    if (modal) {
      dialog.showModal();
      if (this.locksScroll) {
        openModals.add(this);
        this.#syncRootClass();
      }
    } else {
      dialog.show();
    }
    this.#reflect(true);
    // Apply the closed look once (reading the style forces it), then the open one: the transition runs between them.
    getComputedStyle(dialog).opacity;
    dialog.classList.remove("ui-opening");
    this.#busy = new Promise((resolve) => {
      afterTransition(dialog, () => {
        dialog.classList.remove("dialog-swap-in");
        this.emit("shown");
        resolve(true);
      });
    });
    return this.#busy;
  }

  /** Closes the dialog with its exit animation (.hiding keeps it in the top layer meanwhile). */
  async hide() {
    await this.#busy;
    if (!this.isOpen) {
      return true;
    }
    const allowed = this.emit("hide", true);
    if (!allowed) {
      return false;
    }
    const dialog = this.dialog;
    dialog.classList.add("hiding");
    this.#busy = new Promise((resolve) => {
      afterTransition(dialog, () => {
        dialog.close();
        dialog.classList.remove("hiding", "dialog-nonmodal", "ui-no-backdrop");
        openModals.delete(this);
        this.#syncRootClass();
        this.#options = {};
        this.#reflect(false);
        this.emit("hidden");
        resolve(true);
      });
    });
    return this.#busy;
  }

  toggle(options = {}) {
    return this.isOpen ? this.hide() : this.show(options);
  }
}

registerComponent("ui-dialog", UiDialog);

registerToggle("dialog", (target, trigger, options) => {
  if (target.localName === "dialog") {
    PlainDialog.for(target).toggle(options, trigger);
    return;
  }
  if (!(target instanceof UiDialog)) {
    return;
  }
  // A trigger inside an open dialog swaps: the new one opens before the current closes (the backdrop stays).
  const current = trigger.closest("ui-dialog");
  if (current && current !== target && current.isOpen) {
    target.show({ ...options, swap: true }).then(() => {});
    current.hide();
    return;
  }
  target.toggle(options);
});
