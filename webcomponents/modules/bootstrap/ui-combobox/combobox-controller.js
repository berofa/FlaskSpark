import { MenuController } from "../ui-menu/ui-menu.js";
import { searchText } from "./search.js";

export { searchText };

/**
 * Bootstrap 6's combobox (js/src/combobox.ts, MIT): a toggle button (.combobox-toggle with a .combobox-value) and a
 * .menu of .menu-item[data-bs-value] options, on the menu plugin (top layer, placement, keyboard). Single or multiple
 * selection (.selected, aria-selected), placeholder, live search (.combobox-search-input, .combobox-no-results).
 *
 * Options: multiple, placeholder, search, searchNormalize, placement ("bottom-start"), offset ("0,2"),
 * name (plain markup: a hidden input of that name gets the value), labelOf(item) (text shown in the toggle),
 * countLabel(n) ("{n} selected"), emit(name, detail, cancelable) (default: ui-combobox:<name> on the toggle).
 */
const ITEM = ".menu-item[data-bs-value]";
const VISIBLE_ITEM = ".menu-item[data-bs-value]:not(.disabled):not(:disabled)";

export class ComboboxController {
  constructor(toggle, menu, options = {}) {
    this.toggle = toggle;
    this.menu = menu;
    this.options = { placement: "bottom-start", offset: "0,2", ...options };
    this.valueDisplay = toggle.querySelector(".combobox-value");
    this.searchInput = menu.querySelector(".combobox-search-input");
    this.noResults = menu.querySelector(".combobox-no-results");
    this.hiddenInput = null;
    this.toggle.setAttribute("aria-haspopup", "listbox");
    this.menu.setAttribute("role", "listbox");
    if (this.options.multiple) this.menu.setAttribute("aria-multiselectable", "true");
    if (this.options.name) {
      this.hiddenInput = document.createElement("input");
      this.hiddenInput.type = "hidden";
      this.hiddenInput.name = this.options.name;
      this.toggle.before(this.hiddenInput);
    }
    this.menuController = new MenuController(toggle, menu, () => ({
      placement: this.options.placement,
      offset: this.options.offset,
      autoClose: this.options.multiple ? "outside" : "true",
    }), toggle);
    this.items().forEach((item) => {
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", String(item.classList.contains("selected")));
      if (item.matches(".disabled, :disabled")) item.setAttribute("aria-disabled", "true");
    });
    this.#sync();
    this.#listen();
  }

  #emit(name, detail = {}, cancelable = false) {
    if (this.options.emit) return this.options.emit(name, detail, cancelable);
    return this.toggle.dispatchEvent(new CustomEvent(`ui-combobox:${name}`, { bubbles: true, cancelable, detail }));
  }

  get isShown() {
    return this.menu.classList.contains("show");
  }

  items() {
    return [...this.menu.querySelectorAll(ITEM)];
  }

  selectedItems() {
    return this.items().filter((item) => item.classList.contains("selected"));
  }

  /** The value: the selected item's data-bs-value, or an array of them (multiple). */
  get value() {
    const values = this.selectedItems().map((item) => item.dataset.bsValue);
    return this.options.multiple ? values : (values[0] ?? "");
  }

  toggleMenu() {
    return this.isShown ? this.hide() : this.show();
  }

  show() {
    if (this.toggle.disabled || this.toggle.classList.contains("disabled") || this.isShown) return;
    if (!this.#emit("show", {}, true)) return;
    this.menuController.show();
    if (this.searchInput) {
      this.searchInput.value = "";
      this.filter("");
      setTimeout(() => this.searchInput.focus());
    }
    this.#emit("shown");
  }

  hide() {
    if (!this.isShown) return;
    if (!this.#emit("hide", {}, true)) return;
    this.menuController.hide();
    this.#emit("hidden");
  }

  /** Selects the items with these values (and only those), without events. */
  select(values) {
    const wanted = new Set([values].flat().map(String));
    this.items().forEach((item) => {
      const on = wanted.has(item.dataset.bsValue);
      item.classList.toggle("selected", on);
      item.setAttribute("aria-selected", String(on));
    });
    this.#sync();
  }

  #listen() {
    this.menu.addEventListener("click", (event) => {
      const item = event.target instanceof Element ? event.target.closest(ITEM) : null;
      if (!item || !this.menu.contains(item) || item.matches(".disabled, :disabled")) return;
      event.preventDefault();
      this.#choose(item);
    });
    this.toggle.addEventListener("keydown", (event) => {
      if ((event.key === "Enter" || event.key === " ") && !this.isShown) {
        event.preventDefault();
        this.show();
      }
    });
    this.menu.addEventListener("keydown", (event) => {
      if (event.key === "Escape") this.toggle.focus();
    });
    if (this.searchInput) {
      this.searchInput.addEventListener("input", () => this.filter(this.searchInput.value));
      this.searchInput.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          this.hide();
          this.toggle.focus();
        }
      });
    }
  }

  #choose(item) {
    if (this.options.multiple) {
      item.classList.toggle("selected");
      item.setAttribute("aria-selected", String(item.classList.contains("selected")));
    } else {
      this.items().forEach((other) => {
        other.classList.toggle("selected", other === item);
        other.setAttribute("aria-selected", String(other === item));
      });
    }
    this.#sync();
    this.#emit("change", { value: this.value, item });
    if (!this.options.multiple) {
      this.hide();
      this.toggle.focus();
    }
  }

  #sync() {
    const selected = this.selectedItems();
    if (this.valueDisplay) {
      if (!selected.length) {
        this.valueDisplay.textContent = this.options.placeholder || "";
        this.valueDisplay.classList.toggle("combobox-placeholder", Boolean(this.options.placeholder));
      } else {
        this.valueDisplay.classList.remove("combobox-placeholder");
        this.valueDisplay.textContent = this.options.multiple && selected.length > 1
          ? (this.options.countLabel ? this.options.countLabel(selected.length) : `${selected.length} selected`)
          : this.#labelOf(selected[0]);
      }
    }
    if (this.hiddenInput) {
      const values = selected.map((item) => item.dataset.bsValue);
      this.hiddenInput.value = this.options.multiple ? values.join(",") : (values[0] || "");
    }
  }

  #labelOf(item) {
    if (this.options.labelOf) return this.options.labelOf(item);
    const label = item.querySelector(".menu-item-content > span:first-child");
    return (label ? label.textContent : item.textContent).trim();
  }

  /** Shows only the items whose text contains the query. */
  filter(query) {
    const wanted = searchText(query, this.options.searchNormalize);
    let visible = 0;
    this.items().forEach((item) => {
      const text = searchText(this.options.textOf ? this.options.textOf(item) : item.textContent, this.options.searchNormalize);
      const match = !wanted || text.includes(wanted);
      item.style.display = match ? "" : "none";
      if (match) visible += 1;
    });
    this.noResults?.classList.toggle("d-none", visible > 0);
    return visible;
  }

  visibleItems() {
    return [...this.menu.querySelectorAll(VISIBLE_ITEM)].filter((item) => item.style.display !== "none");
  }
}

const plain = new WeakMap();

/** The controller of a plain [data-bs-toggle="combobox"] toggle (options from its data-bs-* attributes). */
export function plainCombobox(toggle) {
  let controller = plain.get(toggle);
  if (!controller) {
    let menu = toggle.nextElementSibling;
    while (menu && !menu.classList.contains("menu")) menu = menu.nextElementSibling;
    if (!menu) return null;
    const d = toggle.dataset;
    controller = new ComboboxController(toggle, menu, {
      multiple: d.bsMultiple === "true",
      placeholder: d.bsPlaceholder || "",
      search: d.bsSearch === "true",
      searchNormalize: d.bsSearchNormalize === "true",
      name: d.bsName || null,
      ...(d.bsPlacement ? { placement: d.bsPlacement } : {}),
      ...(d.bsOffset ? { offset: d.bsOffset } : {}),
    });
    plain.set(toggle, controller);
  }
  return controller;
}

let installed = false;

/** Bootstrap's data API: every [data-bs-toggle="combobox"] on load (also later ones on first click). */
export function installComboboxDataApi() {
  if (installed || typeof document === "undefined") return;
  installed = true;
  document.addEventListener("click", (event) => {
    const toggle = event.target instanceof Element ? event.target.closest('[data-bs-toggle="combobox"]') : null;
    if (!toggle) return;
    event.preventDefault();
    plainCombobox(toggle)?.toggleMenu();
  });
  const start = () => document.querySelectorAll('[data-bs-toggle="combobox"]').forEach((toggle) => plainCombobox(toggle));
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
}
