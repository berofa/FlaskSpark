import { sanitizeHtml } from "../../core/sanitize.js";
import { menuControllerOf } from "./ui-menu/ui-menu.js";

/**
 * Bootstrap 6's nav overflow (js/src/nav-overflow.ts, MIT), the "Priority+" pattern, for Bootstrap's own markup:
 * a `.nav-overflow[data-bs-toggle="nav-overflow"]` wrapper around a `.nav`. Items that do not fit the wrapper's
 * width (ResizeObserver, so container- not viewport-based) move into a "More" menu (the menu plugin of ui-menu);
 * an item with its own menu becomes a submenu there. `.nav-overflow-keep` items stay, active and disabled states
 * are kept.
 *
 * Options (or data-bs-* on the wrapper): moreText ("More"; false or "": icon only, aria-label "More"),
 * moreIcon (HTML; an element with data-bs-overflow-icon in the wrapper wins), iconPlacement ("start" / "end"),
 * menuPlacement ("bottom-end"), threshold (items always visible), collapseBelow (a breakpoint name or pixels:
 * below that width every item goes into the menu). Events on the wrapper: ui-nav-overflow:overflow
 * {overflowCount, visibleCount} and ui-nav-overflow:update. Method update().
 */
const MORE_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">'
  + '<path d="M3 9.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3m5 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3m5 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3"/></svg>';
const ICON_ALLOW_LIST = {
  svg: ["xmlns", "width", "height", "viewbox", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "class", "aria-hidden"],
  path: ["d", "fill", "fill-rule", "clip-rule"], circle: ["cx", "cy", "r"], rect: ["x", "y", "width", "height", "rx"], g: [], span: ["class"], i: ["class"],
};
const BREAKPOINTS = { sm: 576, md: 768, lg: 1024, xl: 1280, "2xl": 1536 };

export class NavOverflowController {
  constructor(element, options = {}) {
    this.element = element;
    this.options = { moreText: "More", moreIcon: MORE_ICON, iconPlacement: "start", menuPlacement: "bottom-end", threshold: 0, collapseBelow: 0, ...options };
    this.nav = element.querySelector(".nav");
    if (!this.nav) throw new TypeError("nav overflow: the wrapper has no .nav");
    this.itemMenus = new Map();
    this.relocated = new Map();
    element.classList.add("nav-overflow");
    this.items = [...this.nav.querySelectorAll(".nav-item")].filter((item) => !item.querySelector(".nav-overflow-toggle"));
    this.items.forEach((item, index) => {
      item.dataset.bsNavOrder = String(index);
      const link = item.querySelector(".nav-link");
      if (link?.matches('[data-bs-toggle="menu"]')) this.#itemMenu(item, link);
    });
    this.collapseBelow = this.#resolveCollapseBelow();
    this.#createMenu();
    this.observer = new ResizeObserver(() => this.update());
    this.observer.observe(element);
    this.update();
    element.classList.add("nav-overflow-initialized");
  }

  #emit(name, detail = {}) {
    this.element.dispatchEvent(new CustomEvent(`ui-nav-overflow:${name}`, { bubbles: true, detail }));
  }

  #resolveCollapseBelow() {
    const value = this.options.collapseBelow;
    if (typeof value === "number") return value;
    if (/^\d+(\.\d+)?$/.test(String(value))) return Number(value);
    if (value) {
      const css = Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue(`--bs-breakpoint-${value}`));
      return css || BREAKPOINTS[value] || 0;
    }
    return 0;
  }

  #createMenu() {
    this.toggle = this.element.querySelector(".nav-overflow-toggle");
    if (this.toggle) {
      this.menu = this.element.querySelector(".nav-overflow-menu");
      return;
    }
    const text = this.options.moreText === false || this.options.moreText === "false" ? "" : String(this.options.moreText ?? "");
    const item = document.createElement("li");
    item.className = "nav-item nav-overflow-item";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "nav-link nav-overflow-toggle";
    button.dataset.bsToggle = "menu";
    button.dataset.bsPlacement = this.options.menuPlacement;
    button.setAttribute("aria-expanded", "false");
    if (!text) button.setAttribute("aria-label", "More");
    const icon = document.createElement("span");
    icon.className = "nav-overflow-icon";
    icon.innerHTML = sanitizeHtml(this.#icon(), ICON_ALLOW_LIST);
    if (!text) {
      button.append(icon);
    } else {
      const label = document.createElement("span");
      label.className = "nav-overflow-text";
      label.textContent = text;
      (this.options.iconPlacement === "end" ? button.append(label, icon) : button.append(icon, label));
    }
    const menu = document.createElement("div");
    menu.className = "nav-overflow-menu menu";
    item.append(button, menu);
    this.nav.append(item);
    this.toggle = button;
    this.menu = menu;
  }

  #icon() {
    const custom = this.element.querySelector("[data-bs-overflow-icon]");
    if (!custom) return this.options.moreIcon;
    const copy = custom.cloneNode(true);
    copy.removeAttribute("data-bs-overflow-icon");
    custom.remove();
    return copy.outerHTML;
  }

  #available() {
    const style = getComputedStyle(this.element);
    return this.element.clientWidth - (Number.parseFloat(style.paddingInlineStart) || 0) - (Number.parseFloat(style.paddingInlineEnd) || 0);
  }

  /** Moves the items that do not fit into the menu (again). */
  update() {
    this.#restore();
    const available = this.#available();
    const overflowItem = this.toggle?.closest(".nav-item") ?? null;
    const candidates = this.items.filter((item) => !item.classList.contains("nav-overflow-keep"));
    if (this.collapseBelow > 0 && available < this.collapseBelow) {
      this.#apply(candidates, overflowItem);
    } else {
      const gap = Number.parseFloat(getComputedStyle(this.nav).columnGap) || 0;
      const keep = this.items.filter((item) => item.classList.contains("nav-overflow-keep")).reduce((sum, item) => sum + item.offsetWidth + gap, 0);
      const limit = available - keep - (overflowItem ? overflowItem.offsetWidth + gap : 0);
      let used = 0;
      let overflow = [];
      for (const item of candidates) {
        used += item.offsetWidth + gap;
        if (used > limit + 1) overflow.push(item);
      }
      const threshold = Number(this.options.threshold) || 0;
      if (this.items.length - overflow.length < threshold && this.items.length > threshold) {
        overflow = this.items.slice(threshold).filter((item) => !item.classList.contains("nav-overflow-keep"));
      }
      this.#apply(overflow, overflowItem);
    }
    this.#emit("update");
  }

  #apply(items, overflowItem) {
    this.menu.replaceChildren();
    items.forEach((item) => {
      const link = item.querySelector(".nav-link");
      if (!link) return;
      const menu = this.#itemMenu(item, link);
      this.menu.append(menu && link.matches('[data-bs-toggle="menu"]') ? this.#asSubmenu(item, link, menu) : this.#asItem(link));
      item.classList.add("d-none");
      item.dataset.bsNavOverflow = "true";
    });
    overflowItem?.classList.toggle("d-none", items.length === 0);
    if (items.length) this.#emit("overflow", { overflowCount: items.length, visibleCount: this.items.length - items.length });
  }

  #asSubmenu(item, link, menu) {
    this.#resetMenu(link, menu);
    item.classList.remove("show");
    this.relocated.set(item, { menu, parent: menu.parentNode, next: menu.nextSibling });
    const submenu = document.createElement("div");
    submenu.className = "submenu";
    submenu.append(this.#asItem(link, true), menu);
    return submenu;
  }

  #asItem(link, submenu = false) {
    const copy = link.cloneNode(true);
    copy.className = "menu-item";
    copy.removeAttribute("id");
    if (link.classList.contains("active")) copy.classList.add("active");
    if (link.classList.contains("disabled") || link.hasAttribute("disabled")) copy.classList.add("disabled");
    if (submenu) {
      copy.getAttributeNames().filter((name) => name.startsWith("data-bs-") && name !== "data-bs-theme").forEach((name) => copy.removeAttribute(name));
      copy.removeAttribute("href");
      copy.setAttribute("aria-haspopup", "true");
      copy.setAttribute("aria-expanded", "false");
      if (copy.tagName === "A") {
        copy.setAttribute("role", "button");
        if (!copy.hasAttribute("tabindex")) copy.setAttribute("tabindex", "0");
      }
    }
    return copy;
  }

  #itemMenu(item, link) {
    let sibling = link.nextElementSibling;
    while (sibling && !sibling.classList.contains("menu")) sibling = sibling.nextElementSibling;
    const found = (sibling && !sibling.classList.contains("nav-overflow-menu") ? sibling : null)
      || [...item.querySelectorAll(".menu")].find((menu) => !menu.classList.contains("nav-overflow-menu"));
    if (found) {
      this.itemMenus.set(item, found);
      return found;
    }
    const cached = this.itemMenus.get(item);
    return cached?.isConnected ? cached : null;
  }

  #resetMenu(toggle, menu) {
    menuControllerOf(toggle)?.hide();
    toggle.classList.remove("show");
    toggle.setAttribute("aria-expanded", "false");
    toggle.parentElement?.classList.remove("show");
    menu.classList.remove("show");
  }

  #restore() {
    if (this.toggle && this.menu) {
      this.#resetMenu(this.toggle, this.menu);
      this.toggle.closest(".nav-item")?.classList.remove("show");
    }
    this.relocated.forEach(({ menu, parent, next }) => (next ? next.before(menu) : parent.append(menu)));
    this.relocated.clear();
    this.items.forEach((item) => {
      item.classList.remove("d-none");
      delete item.dataset.bsNavOverflow;
    });
    this.toggle?.closest(".nav-item")?.classList.remove("d-none");
    this.menu?.replaceChildren();
  }

  dispose() {
    this.observer?.disconnect();
    this.#restore();
    this.toggle?.closest(".nav-overflow-item")?.remove();
  }
}

const plain = new WeakMap();

export function plainNavOverflow(element) {
  let controller = plain.get(element);
  if (!controller) {
    const d = element.dataset;
    const options = {};
    if (d.bsMoreText !== undefined) options.moreText = d.bsMoreText === "false" ? false : d.bsMoreText;
    if (d.bsMoreIcon) options.moreIcon = d.bsMoreIcon;
    if (d.bsIconPlacement) options.iconPlacement = d.bsIconPlacement;
    if (d.bsMenuPlacement) options.menuPlacement = d.bsMenuPlacement;
    if (d.bsThreshold) options.threshold = Number(d.bsThreshold);
    if (d.bsCollapseBelow) options.collapseBelow = d.bsCollapseBelow;
    controller = new NavOverflowController(element, options);
    plain.set(element, controller);
  }
  return controller;
}

let installed = false;

/** Bootstrap's data API: every [data-bs-toggle="nav-overflow"] wrapper of the page (also ones added later). */
export function installNavOverflowDataApi() {
  if (installed || typeof document === "undefined" || typeof ResizeObserver === "undefined") return;
  installed = true;
  const scan = (root) => root.querySelectorAll?.('[data-bs-toggle="nav-overflow"]').forEach((element) => plainNavOverflow(element));
  const start = () => {
    scan(document);
    new MutationObserver((records) => records.forEach((record) => record.addedNodes.forEach((node) => {
      if (node.nodeType !== 1) return;
      if (node.matches('[data-bs-toggle="nav-overflow"]')) plainNavOverflow(node);
      scan(node);
    }))).observe(document.documentElement, { childList: true, subtree: true });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
}

installNavOverflowDataApi();
