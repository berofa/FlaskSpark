import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { escapeHtml } from "../../../core/escape.js";
import { registerToggle } from "../../../core/triggers.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";
import { UiDialog } from "../ui-dialog/ui-dialog.js";

const PLACEMENTS = new Set(["start", "end", "top", "bottom", "fullscreen"]);
const BREAKPOINTS = new Map([["sm", 576], ["md", 768], ["lg", 1024], ["xl", 1280], ["2xl", 1536]]);
const SWIPE_DISTANCE = 50;

/**
 * <ui-drawer> (Bootstrap 6 drawer: a sidebar panel on the native <dialog>, built on <ui-dialog>).
 *
 * Attributes:
 * - open: shown; reflected. heading (or slot "heading"): title with a close button (no-close, close-label).
 * - placement: start (default), end, top, bottom or fullscreen.
 * - responsive: breakpoint (sm, md, lg, xl, 2xl) from which the content sits in the page layout instead
 *   (e.g. a navbar's links); below it a drawer. The host has `docked` while it is in the layout.
 * - backdrop: "static" (outside clicks don't close it) or "false" (no backdrop).
 * - keyboard="false": Escape does not close it.
 * - scroll: the page stays scrollable; with backdrop="false" the drawer is non-modal (no focus trap).
 * - animation="instant": no slide. translucent: blurred, translucent panel. sheet: flush to the edge.
 * - data-bs-theme="dark": a dark drawer.
 *
 * Swipe towards its edge to close it. Only one drawer opens at a time through triggers
 * (data-bs-toggle="drawer" data-bs-target="#id", options data-bs-backdrop / -keyboard / -scroll).
 * Slots: default (body), heading, footer. Elements inside with data-bs-dismiss="drawer" close it.
 * Methods: show(options), hide(), toggle(options) as on <ui-dialog>. Events (bubble): ui-drawer:show and
 * ui-drawer:hide (cancelable), ui-drawer:shown, ui-drawer:hidden, ui-drawer:hide-prevented, ui-drawer:cancel,
 * ui-drawer:dock (detail.docked).
 * Parts: drawer, header, title, close, body, footer.
 */
export class UiDrawer extends UiDialog {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-drawer.css", import.meta.url).href];
  static observedAttributes = [
    "open", "heading", "no-close", "close-label", "placement", "responsive", "backdrop", "keyboard", "scroll",
    "animation", "translucent", "sheet",
  ];
  static eventPrefix = "ui-drawer";
  static staticClass = "drawer-static";

  #media = null;
  #onMedia = () => this.#syncDocked();

  constructor() {
    super();
    this.addEventListener("click", (event) => {
      if (event.target instanceof Element && event.target.closest('[data-bs-dismiss="drawer"]')) {
        event.preventDefault();
        this.hide();
      }
    });
  }

  connectedCallback() {
    super.connectedCallback();
    this.#watchBreakpoint();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.#media?.removeEventListener("change", this.#onMedia);
    this.#media = null;
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "responsive" && oldValue !== newValue) {
      this.#watchBreakpoint();
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  get breakpoint() {
    const value = (this.getAttribute("responsive") || "").trim().toLowerCase();
    return BREAKPOINTS.has(value) ? value : "";
  }

  get docked() {
    return this.hasAttribute("docked");
  }

  #watchBreakpoint() {
    this.#media?.removeEventListener("change", this.#onMedia);
    this.#media = null;
    const breakpoint = this.breakpoint;
    if (breakpoint && this.isConnected) {
      this.#media = window.matchMedia(`(width >= ${BREAKPOINTS.get(breakpoint)}px)`);
      this.#media.addEventListener("change", this.#onMedia);
    }
    this.#syncDocked();
  }

  /** Above its breakpoint the drawer is part of the layout: an open panel closes at once. */
  #syncDocked() {
    const docked = Boolean(this.#media?.matches);
    if (docked === this.docked) {
      return;
    }
    this.toggleAttribute("docked", docked);
    if (docked && this.dialog?.open) {
      this.dialog.close();
      this.dialog.classList.remove("hiding", "ui-opening");
      this.toggleAttribute("open", false);
    }
    this.dispatchEvent(new CustomEvent("ui-drawer:dock", { bubbles: true, detail: { docked } }));
  }

  /** The page stays scrollable: the scroll attribute (boolean) or data-bs-scroll="true". */
  get scrolls() {
    const value = this.option("scroll");
    return value !== null && value !== undefined && value !== "false";
  }

  get modal() {
    return !(this.scrolls && this.option("backdrop") === "false");
  }

  get locksScroll() {
    return this.modal && !this.scrolls;
  }

  async show(options = {}) {
    if (this.docked) {
      return false;
    }
    return super.show(options);
  }

  render() {
    const raw = (this.getAttribute("placement") || "start").trim().toLowerCase();
    const placement = PLACEMENTS.has(raw) ? raw : "start";
    const breakpoint = this.breakpoint;
    const classes = [
      breakpoint ? `${breakpoint}:drawer` : "drawer",
      HOST_TOKENS_CLASS,
      `drawer-${placement}`,
      this.getAttribute("animation") === "instant" ? "drawer-instant" : "",
      this.hasAttribute("translucent") ? "drawer-translucent" : "",
      this.hasAttribute("sheet") ? "drawer-sheet" : "",
    ].filter(Boolean).join(" ");
    const filled = new Set([...this.children].map((child) => child.slot));
    const heading = this.getAttribute("heading");
    const hasHeader = heading !== null || filled.has("heading");
    const close = this.hasAttribute("no-close")
      ? ""
      : `<button type="button" class="btn-close" part="close" data-close aria-label="${escapeHtml(this.getAttribute("close-label") || "Close")}"></button>`;
    const { stateClasses, openAttribute } = this.currentState();
    return `
      <dialog class="${classes}${stateClasses}" part="drawer" tabindex="-1"${hasHeader ? ' aria-labelledby="title"' : ""}${openAttribute}>
        ${hasHeader ? `<div class="drawer-header" part="header"><h5 class="drawer-title" id="title" part="title"><slot name="heading">${escapeHtml(heading || "")}</slot></h5>${close}</div>` : ""}
        <div class="drawer-body" part="body"><slot></slot></div>
        ${filled.has("footer") ? '<div class="drawer-footer" part="footer"><slot name="footer"></slot></div>' : ""}
      </dialog>
    `;
  }

  afterRender() {
    const wasWired = this.dialog?.__uiDrawerSwipe;
    super.afterRender();
    const dialog = this.dialog;
    if (!dialog || wasWired) {
      return;
    }
    dialog.__uiDrawerSwipe = true;
    let start = null;
    dialog.addEventListener("pointerdown", (event) => {
      start = event.pointerType === "mouse" ? null : { x: event.clientX, y: event.clientY };
    });
    dialog.addEventListener("pointerup", (event) => {
      if (!start || this.docked) {
        return;
      }
      const dx = event.clientX - start.x;
      const dy = event.clientY - start.y;
      start = null;
      if (this.#swipeCloses(dx, dy)) {
        this.hide();
      }
    });
  }

  /** A swipe towards the drawer's edge (placement-aware, also right-to-left). */
  #swipeCloses(dx, dy) {
    const rtl = getComputedStyle(this).direction === "rtl";
    const placement = (this.getAttribute("placement") || "start").trim().toLowerCase();
    const horizontal = Math.abs(dx) > Math.abs(dy);
    switch (placement) {
      case "end":
        return horizontal && (rtl ? -dx : dx) > SWIPE_DISTANCE;
      case "top":
        return !horizontal && -dy > SWIPE_DISTANCE;
      case "bottom":
      case "fullscreen":
        return !horizontal && dy > SWIPE_DISTANCE;
      default:
        return horizontal && (rtl ? dx : -dx) > SWIPE_DISTANCE;
    }
  }
}

registerComponent("ui-drawer", UiDrawer);

registerToggle("drawer", (target, trigger, options) => {
  if (!(target instanceof UiDrawer)) {
    return;
  }
  // Only one drawer at a time.
  document.querySelectorAll("ui-drawer[open]").forEach((other) => other !== target && other.hide());
  target.toggle(options);
});
