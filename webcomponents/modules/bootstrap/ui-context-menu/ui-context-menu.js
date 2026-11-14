import { registerComponent } from "../../../core/registry.js";
import { SharedShadowStyles } from "../../../core/shared-shadow-styles.js";
import { escapeHtml } from "../../../core/escape.js";

const DOCUMENT_STYLES = new URL("./ui-context-menu.document.css", import.meta.url).href;
const documentStyles = typeof document === "undefined" ? Promise.resolve() : SharedShadowStyles.applyToDocument(DOCUMENT_STYLES);
const LONG_PRESS = 500; // ms a finger rests on an element until its menu opens
const MOVE_TOLERANCE = 10; // px a resting finger may move (else it scrolls)
const MARGIN = 4; // px between the menu and the edge of the window
const ITEM = ".menu-item:not(.disabled, :disabled)";

/**
 * Where a menu of size `box` opens at the point x, y (viewport pixels): to the right and below it, else to the
 * left or above it where it does not fit, always inside the viewport (MARGIN). Pure, for the tests.
 */
export function atPoint(x, y, box, viewport, margin = MARGIN) {
  let left = x + box.width + margin > viewport.width ? x - box.width : x;
  let top = y + box.height + margin > viewport.height ? y - box.height : y;
  left = Math.max(margin, Math.min(left, viewport.width - box.width - margin));
  top = Math.max(margin, Math.min(top, viewport.height - box.height - margin));
  return { left: Math.round(left), top: Math.round(top) };
}

/** The markup of the items: Bootstrap 6's menu (.menu-item with .menu-item-icon, .menu-divider, .menu-header). */
export function itemsHtml(items) {
  return items.map((item, i) => {
    if (item.divider) return '<hr class="menu-divider">';
    if (item.header) return `<h6 class="menu-header">${escapeHtml(item.header)}</h6>`;
    const classes = ["menu-item", item.danger ? "theme-danger" : "", item.disabled ? "disabled" : ""].filter(Boolean);
    const icon = item.icon ? `<span class="menu-item-icon" aria-hidden="true">${item.icon}</span>` : "";
    const content = item.description
      ? `<span class="menu-item-content"><span>${escapeHtml(item.label)}</span><small class="menu-item-description">${escapeHtml(item.description)}</small></span>`
      : `<span>${escapeHtml(item.label)}</span>`;
    return `<button type="button" class="${classes.join(" ")}" role="menuitem" data-index="${i}"${item.disabled ? " disabled" : ""}>${icon}${content}</button>`;
  }).join("");
}

/** Is `el` inside `root`, also across shadow roots (e.g. the rows a ui-table moves into its shadow tree)? */
export function within(root, el) {
  for (let n = el; n; n = n.parentNode || n.host) {
    if (n === root) return true;
  }
  return false;
}

/** The items without dividers at the start, the end or twice in a row (items left out by a condition). */
export function tidy(items) {
  const out = [];
  for (const item of items.filter(Boolean)) {
    if (item.divider && (!out.length || out[out.length - 1].divider)) continue;
    out.push(item);
  }
  while (out.length && out[out.length - 1].divider) out.pop();
  return out;
}

/**
 * <ui-context-menu> (Bootstrap 6 menu as a context menu): the menu of an element on a right click, on a touch
 * screen when a finger rests on it (LONG_PRESS), and with the keyboard's context menu key (Shift+F10). One element
 * for the page, added by attach(); the markup is Bootstrap's own (.menu, .menu-item with .menu-item-icon,
 * .menu-divider, .menu-header, .theme-danger), styled by the page's Bootstrap CSS, opened in the top layer.
 *
 *   const detach = UiContextMenu.attach(root, {
 *     selector: ".message",                      // the elements with a menu (inside root)
 *     items: (target, event) => [                // null or [] : the browser's own menu
 *       { label: "Antworten", icon: "<svg…>", action: (target) => reply(target) },
 *       { divider: true },
 *       { label: "Löschen", icon: "<svg…>", danger: true, action: … },
 *     ],
 *     enabled: () => true,                       // false: the browser's own menu (e.g. switched off for an area)
 *   });
 *
 * An item: label, icon (SVG markup, trusted), description, danger, disabled, action(target, event); or {divider:
 * true}, {header: "…"}. Falsy items are left out (conditions inline), dividers tidied. Keyboard in the menu: ↓ ↑
 * Home End, Enter or Space, Esc (back to the element), Tab. It closes on a click outside, scrolling, resizing and
 * when the window loses focus. A long press does not also click the element (the click after it is swallowed).
 * Events (bubble from the element): ui-context-menu:show (cancelable, detail.items), ui-context-menu:hidden.
 */
export class UiContextMenu extends HTMLElement {
  static #instance = null;

  #menu = null;
  #items = [];
  #target = null;
  #event = null;
  #returnFocus = null;
  #openedAt = 0;

  /** The page's one menu element (made on first use). */
  static get instance() {
    if (!UiContextMenu.#instance || !UiContextMenu.#instance.isConnected) {
      UiContextMenu.#instance = document.createElement("ui-context-menu");
      document.body.append(UiContextMenu.#instance);
    }
    return UiContextMenu.#instance;
  }

  /** Context menus for the elements matching options.selector inside root; returns the function that removes them. */
  static attach(root, options) {
    const { selector, items, enabled = () => true } = options;
    let timer = null;
    let start = null;
    let swallowClick = false;
    const targetOf = (event) => {
      const el = event.composedPath().find((n) => n instanceof Element && n.matches?.(selector));
      return el && within(root, el) ? el : null;
    };
    const open = (target, event, x, y) => {
      if (!enabled(target)) return false;
      const list = tidy(items(target, event) || []);
      if (!list.length) return false;
      return UiContextMenu.instance.open(list, { target, event, x, y });
    };
    const onContextMenu = (event) => {
      const target = targetOf(event);
      if (!target) return;
      if (Date.now() - UiContextMenu.instance.#openedAt < 800) {
        event.preventDefault(); // a long press opened it already (Android also sends contextmenu)
        return;
      }
      const keyboard = event.button !== 2 && event.clientX === 0 && event.clientY === 0;
      const rect = target.getBoundingClientRect();
      const x = keyboard ? rect.left + Math.min(24, rect.width / 2) : event.clientX;
      const y = keyboard ? rect.top + Math.min(24, rect.height / 2) : event.clientY;
      if (open(target, event, x, y)) event.preventDefault();
    };
    const cancel = () => {
      clearTimeout(timer);
      timer = null;
    };
    const onPointerDown = (event) => {
      if (event.pointerType === "mouse") return;
      const target = targetOf(event);
      if (!target) return;
      start = { x: event.clientX, y: event.clientY };
      cancel();
      timer = setTimeout(() => {
        timer = null;
        if (open(target, event, start.x, start.y)) {
          swallowClick = true;
          navigator.vibrate?.(10);
        }
      }, LONG_PRESS);
    };
    const onPointerMove = (event) => {
      if (timer && start && Math.hypot(event.clientX - start.x, event.clientY - start.y) > MOVE_TOLERANCE) cancel();
    };
    const onClick = (event) => {
      if (!swallowClick) return;
      swallowClick = false;
      event.preventDefault();
      event.stopPropagation();
    };
    const onPointerUp = () => {
      cancel();
      if (swallowClick) setTimeout(() => { swallowClick = false; }, 400);
    };
    root.addEventListener("contextmenu", onContextMenu);
    root.addEventListener("pointerdown", onPointerDown);
    root.addEventListener("pointermove", onPointerMove);
    root.addEventListener("pointerup", onPointerUp);
    root.addEventListener("pointercancel", cancel);
    root.addEventListener("click", onClick, true);
    return () => {
      cancel();
      root.removeEventListener("contextmenu", onContextMenu);
      root.removeEventListener("pointerdown", onPointerDown);
      root.removeEventListener("pointermove", onPointerMove);
      root.removeEventListener("pointerup", onPointerUp);
      root.removeEventListener("pointercancel", cancel);
      root.removeEventListener("click", onClick, true);
    };
  }

  connectedCallback() {
    if (this.#menu) return;
    this.#menu = document.createElement("div");
    this.#menu.className = "menu ui-context-menu";
    this.#menu.setAttribute("role", "menu");
    this.#menu.setAttribute("popover", "manual");
    this.append(this.#menu);
    this.#menu.addEventListener("click", (e) => {
      const el = e.target.closest?.("[data-index]");
      if (!el || el.disabled) return;
      const item = this.#items[Number(el.dataset.index)];
      const target = this.#target;
      const event = this.#event;
      this.hide(false);
      item?.action?.(target, event);
    });
    this.#menu.addEventListener("keydown", (e) => this.#key(e));
  }

  get isOpen() {
    return this.#menu?.classList.contains("show") ?? false;
  }

  /** Open the menu with these items at x, y (viewport pixels) for target; false if a listener cancelled it. */
  open(items, { target = null, event = null, x = 0, y = 0 } = {}) {
    if (this.isOpen) this.hide(false);
    const show = new CustomEvent("ui-context-menu:show", { bubbles: true, composed: true, cancelable: true, detail: { items } });
    if (target && !target.dispatchEvent(show)) return false;
    this.#items = items;
    this.#target = target;
    this.#event = event;
    this.#returnFocus = document.activeElement;
    this.#menu.innerHTML = itemsHtml(items);
    this.#menu.classList.add("show");
    if ("showPopover" in this.#menu && !this.#menu.matches(":popover-open")) this.#menu.showPopover();
    const box = { width: this.#menu.offsetWidth, height: this.#menu.offsetHeight };
    const viewport = { width: document.documentElement.clientWidth, height: window.innerHeight };
    const { left, top } = atPoint(x, y, box, viewport);
    this.#menu.style.left = `${left}px`;
    this.#menu.style.top = `${top}px`;
    this.#openedAt = Date.now();
    this.#menu.querySelector(ITEM)?.focus({ preventScroll: true });
    this.#listen(true);
    return true;
  }

  /** Close it; focus goes back to where it was (not when an item was chosen: the action decides). */
  hide(restoreFocus = true) {
    if (!this.isOpen) return;
    this.#listen(false);
    this.#menu.classList.remove("show");
    if ("hidePopover" in this.#menu && this.#menu.matches(":popover-open")) this.#menu.hidePopover();
    const target = this.#target;
    if (restoreFocus) this.#returnFocus?.focus?.({ preventScroll: true });
    this.#target = null;
    this.#event = null;
    target?.dispatchEvent(new CustomEvent("ui-context-menu:hidden", { bubbles: true, composed: true }));
  }

  #outside = (e) => {
    if (!e.composedPath().includes(this.#menu)) this.hide(false);
  };

  #close = () => this.hide(false);

  #listen(on) {
    const method = on ? "addEventListener" : "removeEventListener";
    document[method]("pointerdown", this.#outside, true);
    window[method]("scroll", this.#close, true);
    window[method]("resize", this.#close);
    window[method]("blur", this.#close);
  }

  #key(e) {
    const items = [...this.#menu.querySelectorAll(ITEM)];
    const index = items.indexOf(document.activeElement);
    const go = (i) => items[(i + items.length) % items.length]?.focus();
    if (e.key === "ArrowDown") go(index + 1);
    else if (e.key === "ArrowUp") go(index - 1);
    else if (e.key === "Home") go(0);
    else if (e.key === "End") go(items.length - 1);
    else if (e.key === "Escape") this.hide(true);
    else if (e.key === "Tab") this.hide(false);
    else return;
    e.preventDefault();
  }
}

documentStyles.catch(() => {});
registerComponent("ui-context-menu", UiContextMenu);
