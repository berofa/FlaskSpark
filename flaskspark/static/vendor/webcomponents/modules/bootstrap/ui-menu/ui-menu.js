import { registerComponent } from "../../../core/registry.js";
import { SharedShadowStyles } from "../../../core/shared-shadow-styles.js";
import { placeAligned, resolvePlacement } from "../../../core/placement.js";
import { afterTransition } from "../../../core/transitions.js";

const DOCUMENT_STYLES = new URL("./ui-menu.document.css", import.meta.url).href;
// Loaded with the module: the popover rules must apply before a menu is measured.
const documentStyles = typeof document === "undefined" ? Promise.resolve() : SharedShadowStyles.applyToDocument(DOCUMENT_STYLES);
const BREAKPOINTS = { sm: 576, md: 768, lg: 1024, xl: 1280, "2xl": 1536 };
const STACK_BELOW = 576; // submenus stack inside their menu on narrow screens, like Bootstrap's
const HOVER_DELAY = 120;
const ITEM = ".menu-item:not(.disabled, :disabled)";
const controllers = new WeakMap();
const open = new Set();

/** The menu items of one menu level (not those of its submenus). */
function itemsOf(menu) {
  return [...menu.querySelectorAll(ITEM)].filter((item) => item.closest(".menu") === menu && item.offsetParent !== null);
}

const supportsPopover = typeof HTMLElement !== "undefined" && "showPopover" in HTMLElement.prototype;

function showLayer(menu) {
  if (!supportsPopover) {
    return;
  }
  if (!menu.hasAttribute("popover")) {
    menu.setAttribute("popover", "manual");
  }
  if (!menu.matches(":popover-open")) {
    menu.showPopover();
  }
}

function hideLayer(menu) {
  if (supportsPopover && menu.matches?.(":popover-open")) {
    menu.hidePopover();
  }
}

/**
 * Bootstrap 6's menu plugin for one toggle and its .menu (used by <ui-menu> and by the data API for
 * plain markup): opening in the top layer (never clipped), placement, auto close, keyboard, submenus.
 */
export class MenuController {
  constructor(toggle, menu, options, events) {
    this.toggle = toggle;
    this.menu = menu;
    this.options = options; // () => { placement, offset, reference, autoClose, display }
    this.events = events; // element the ui-menu:* events are fired on
    this.timers = new WeakMap();
    this.reposition = () => this.position();
    this.onDocumentClick = (event) => this.#documentClick(event);
    this.toggle.setAttribute("aria-expanded", "false");
    this.toggle.addEventListener("keydown", (event) => this.#toggleKeydown(event));
    this.menu.addEventListener("keydown", (event) => this.#menuKeydown(event));
    this.menu.addEventListener("click", (event) => this.#menuClick(event));
    this.#wireSubmenus();
    controllers.set(toggle, this);
  }

  get isOpen() {
    return this.menu.classList.contains("show");
  }

  #emit(name, cancelable = false, detail = {}) {
    return this.events.dispatchEvent(new CustomEvent(`ui-menu:${name}`, { bubbles: true, cancelable, detail }));
  }

  toggleMenu() {
    return this.isOpen ? this.hide() : this.show();
  }

  show() {
    if (this.isOpen || this.toggle.hasAttribute("disabled") || !this.#emit("show", true)) {
      return;
    }
    // One menu at a time (outside the one that contains this one).
    open.forEach((other) => other !== this && !other.menu.contains(this.toggle) && other.hide());
    this.menu.classList.add("show");
    this.toggle.setAttribute("aria-expanded", "true");
    this.toggle.classList.add("show");
    if (this.options().display !== "static") {
      showLayer(this.menu);
      this.position();
      documentStyles.then(() => this.position());
      window.addEventListener("resize", this.reposition);
      window.addEventListener("scroll", this.reposition, true);
    }
    open.add(this);
    document.addEventListener("click", this.onDocumentClick, true);
    afterTransition(this.menu, () => this.#emit("shown"));
  }

  hide(clickEvent = null) {
    if (!this.isOpen || !this.#emit("hide", true, { clickEvent })) {
      return;
    }
    this.menu.querySelectorAll(".submenu.show").forEach((submenu) => this.#closeSubmenu(submenu));
    this.menu.classList.remove("show");
    this.toggle.setAttribute("aria-expanded", "false");
    this.toggle.classList.remove("show");
    open.delete(this);
    document.removeEventListener("click", this.onDocumentClick, true);
    window.removeEventListener("resize", this.reposition);
    window.removeEventListener("scroll", this.reposition, true);
    afterTransition(this.menu, () => {
      if (!this.isOpen) {
        hideLayer(this.menu);
        this.#emit("hidden");
      }
    });
  }

  /** The element the menu is placed at: the toggle, its parent or a selector (option reference). */
  #reference() {
    const reference = this.options().reference || "toggle";
    if (reference === "toggle") return this.toggle;
    if (reference === "parent") return this.toggle.parentElement || this.toggle;
    return document.querySelector(reference) || this.toggle;
  }

  position() {
    if (!this.isOpen || this.options().display === "static") {
      return;
    }
    const options = this.options();
    const placement = resolvePlacement(options.placement || "bottom-start", window.innerWidth, BREAKPOINTS);
    const offset = String(options.offset || "0,2").split(",").map((value) => Number.parseFloat(value) || 0);
    const rtl = getComputedStyle(this.toggle).direction === "rtl";
    const anchor = this.#reference().getBoundingClientRect();
    // The layout size: the opening transition scales the menu, its bounding box would be smaller.
    const box = { width: this.menu.offsetWidth, height: this.menu.offsetHeight };
    const viewport = { width: document.documentElement.clientWidth, height: window.innerHeight };
    // No distance to the viewport edge (like Floating UI's shift): an anchor at the edge keeps its alignment.
    const result = placeAligned(anchor, box, viewport, placement, { offset: [offset[0], offset[1] ?? 2], rtl, margin: 0 });
    this.menu.style.left = `${result.left}px`;
    this.menu.style.top = `${result.top}px`;
    this.menu.setAttribute("data-bs-placement", result.placement);
  }

  #documentClick(event) {
    const path = event.composedPath();
    const inToggle = path.includes(this.toggle);
    const inMenu = path.includes(this.menu);
    const autoClose = String(this.options().autoClose ?? "true");
    if (inToggle) {
      return;
    }
    if (!inMenu && (autoClose === "true" || autoClose === "outside")) {
      this.hide(event);
    }
  }

  #menuClick(event) {
    const item = event.target instanceof Element ? event.target.closest(".menu-item") : null;
    if (!item || item.closest(".menu") === null) {
      return;
    }
    if (item.parentElement?.classList.contains("submenu")) {
      event.preventDefault();
      const submenu = item.parentElement;
      (submenu.classList.contains("show") ? this.#closeSubmenu(submenu) : this.#openSubmenu(submenu));
      return;
    }
    const autoClose = String(this.options().autoClose ?? "true");
    if ((autoClose === "true" || autoClose === "inside") && !item.closest("form") && !item.matches(".disabled, :disabled")) {
      this.hide(event);
    }
  }

  #toggleKeydown(event) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      this.show();
      const items = itemsOf(this.menu);
      (event.key === "ArrowDown" ? items[0] : items.at(-1))?.focus();
    } else if (event.key === "Escape" && this.isOpen) {
      this.hide();
    }
  }

  #menuKeydown(event) {
    const level = event.target instanceof Element ? event.target.closest(".menu") : null;
    if (!level) {
      return;
    }
    const items = itemsOf(level);
    const index = items.indexOf(event.target.closest(".menu-item"));
    const rtl = getComputedStyle(level).direction === "rtl";
    const into = rtl ? "ArrowLeft" : "ArrowRight";
    const back = rtl ? "ArrowRight" : "ArrowLeft";
    const submenu = event.target.parentElement?.classList.contains("submenu") ? event.target.parentElement : null;
    switch (event.key) {
      case "ArrowDown":
      case "ArrowUp": {
        event.preventDefault();
        const step = event.key === "ArrowDown" ? 1 : -1;
        items[(index + step + items.length) % items.length]?.focus();
        break;
      }
      case "Home":
      case "End":
        event.preventDefault();
        (event.key === "Home" ? items[0] : items.at(-1))?.focus();
        break;
      case into:
        if (submenu) {
          event.preventDefault();
          this.#openSubmenu(submenu);
          itemsOf(submenu.querySelector(":scope > .menu"))[0]?.focus();
        }
        break;
      case back: {
        const parent = level.parentElement?.classList.contains("submenu") ? level.parentElement : null;
        if (parent) {
          event.preventDefault();
          this.#closeSubmenu(parent);
          parent.querySelector(":scope > .menu-item")?.focus();
        }
        break;
      }
      case "Escape":
        event.preventDefault();
        this.hide();
        this.toggle.focus();
        break;
      case "Tab":
        this.hide();
        break;
      default:
    }
  }

  #wireSubmenus() {
    this.menu.querySelectorAll(".submenu").forEach((submenu) => {
      const trigger = submenu.querySelector(":scope > .menu-item");
      if (!trigger) return;
      trigger.setAttribute("aria-haspopup", "true");
      trigger.setAttribute("aria-expanded", "false");
      submenu.addEventListener("pointerenter", (event) => {
        if (event.pointerType === "mouse") this.#schedule(submenu, () => this.#openSubmenu(submenu));
      });
      submenu.addEventListener("pointerleave", (event) => {
        if (event.pointerType === "mouse") this.#schedule(submenu, () => this.#closeSubmenu(submenu));
      });
    });
  }

  #schedule(submenu, action) {
    clearTimeout(this.timers.get(submenu));
    this.timers.set(submenu, setTimeout(action, HOVER_DELAY));
  }

  #openSubmenu(submenu) {
    const panel = submenu.querySelector(":scope > .menu");
    const trigger = submenu.querySelector(":scope > .menu-item");
    if (!panel || submenu.classList.contains("show")) return;
    // Siblings close: one open submenu per level.
    [...submenu.parentElement.children].forEach((sibling) => sibling !== submenu && sibling.classList?.contains("show")
      && sibling.classList.contains("submenu") && this.#closeSubmenu(sibling));
    submenu.classList.add("show");
    panel.classList.add("show");
    trigger?.setAttribute("aria-expanded", "true");
    const stacked = window.innerWidth < STACK_BELOW || this.options().display === "static";
    panel.classList.toggle("ui-menu-stacked", stacked);
    if (!stacked) {
      showLayer(panel);
      const anchor = trigger.getBoundingClientRect();
      const box = { width: panel.offsetWidth, height: panel.offsetHeight };
      const viewport = { width: document.documentElement.clientWidth, height: window.innerHeight };
      const padding = Number.parseFloat(getComputedStyle(this.menu).paddingTop) || 0;
      const rtl = getComputedStyle(submenu).direction === "rtl";
      const result = placeAligned(anchor, box, viewport, "end-start", { offset: [-padding, 0], rtl, margin: 0 });
      panel.style.left = `${result.left}px`;
      panel.style.top = `${result.top}px`;
      panel.setAttribute("data-bs-placement", result.placement);
    }
  }

  #closeSubmenu(submenu) {
    const panel = submenu.querySelector(":scope > .menu");
    submenu.querySelectorAll(".submenu.show").forEach((inner) => inner !== submenu && this.#closeSubmenu(inner));
    submenu.classList.remove("show");
    panel?.classList.remove("show");
    submenu.querySelector(":scope > .menu-item")?.setAttribute("aria-expanded", "false");
    if (panel) {
      afterTransition(panel, () => !panel.classList.contains("show") && hideLayer(panel));
    }
  }
}

/** The option of a menu: the toggle's data-bs-* attribute, else the <ui-menu> attribute. */
function optionsOf(toggle, host) {
  return () => ({
    placement: toggle.dataset.bsPlacement ?? host?.getAttribute("placement") ?? undefined,
    offset: toggle.dataset.bsOffset ?? host?.getAttribute("offset") ?? undefined,
    reference: toggle.dataset.bsReference ?? host?.getAttribute("reference") ?? undefined,
    autoClose: toggle.dataset.bsAutoClose ?? host?.getAttribute("auto-close") ?? undefined,
    display: toggle.dataset.bsDisplay ?? host?.getAttribute("display") ?? undefined,
  });
}

/** The .menu a toggle opens: the next sibling .menu (Bootstrap's markup), or the first .menu of the wrapper. */
function menuFor(toggle, host) {
  let sibling = toggle.nextElementSibling;
  while (sibling && !sibling.classList.contains("menu")) {
    sibling = sibling.nextElementSibling;
  }
  return sibling || host?.querySelector(":scope .menu") || null;
}

/**
 * <ui-menu> (Bootstrap 6 menu): wraps Bootstrap's own markup — a toggle with data-bs-toggle="menu" and a
 * .menu with .menu-item links or buttons, .menu-header, .menu-divider, .menu-text, forms, .submenu — and
 * adds the behaviour. The page's Bootstrap CSS styles the markup (light DOM), so every class of Bootstrap's
 * docs works: .active, .disabled, .selected, .theme-*, .menu-item-icon, .menu-item-content /
 * .menu-item-description, .menu-scrollable, .menu-translucent, data-bs-theme="dark".
 *
 * Attributes (or data-bs-* on the toggle, which win): placement ("bottom-start" default; top, bottom, left,
 * right, start, end with -start / -end; responsive "bottom-start md:bottom-end"), offset ("x,y" px),
 * reference (toggle, parent or a selector), auto-close (true, inside, outside, false), display ("static":
 * no positioning).
 *
 * The menu opens in the top layer (never clipped by its container). Keyboard: ↓ ↑ Home End between items,
 * → ← into and out of submenus, Esc closes and returns to the toggle, Tab closes. Submenus open on hover or
 * click and stack inside their menu below 576px. Plain markup with data-bs-toggle="menu" works without the
 * wrapper, too.
 *
 * Methods: show(), hide(), toggle(), position(). Events (bubble): ui-menu:show and ui-menu:hide
 * (cancelable; hide has detail.clickEvent), ui-menu:shown, ui-menu:hidden.
 */
export class UiMenu extends HTMLElement {
  #controller = null;

  connectedCallback() {
    queueMicrotask(() => this.#setup());
  }

  #setup() {
    if (this.#controller || !this.isConnected) return;
    const toggle = this.querySelector('[data-bs-toggle="menu"]');
    const menu = toggle && menuFor(toggle, this);
    if (toggle && menu) {
      this.#controller = new MenuController(toggle, menu, optionsOf(toggle, this), this);
    }
  }

  get controller() {
    this.#setup();
    return this.#controller;
  }

  show() { this.controller?.show(); }

  hide() { this.controller?.hide(); }

  toggle() { this.controller?.toggleMenu(); }

  position() { this.controller?.position(); }
}

registerComponent("ui-menu", UiMenu);

// Bootstrap's data API: data-bs-toggle="menu" anywhere (also outside a <ui-menu>).
document.addEventListener("click", (event) => {
  const toggle = event.target instanceof Element ? event.target.closest('[data-bs-toggle="menu"]') : null;
  if (!toggle || toggle.hasAttribute("disabled")) return;
  const host = toggle.closest("ui-menu");
  let controller = host ? host.controller : controllers.get(toggle);
  if (!controller) {
    const menu = menuFor(toggle, null);
    if (!menu) return;
    controller = new MenuController(toggle, menu, optionsOf(toggle, null), toggle);
  }
  if (toggle.localName === "a") event.preventDefault();
  controller.toggleMenu();
});
