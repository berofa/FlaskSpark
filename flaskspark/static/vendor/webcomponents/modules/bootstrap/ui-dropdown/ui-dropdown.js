import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";

const DIRECTIONS = { down: "dropdown", up: "dropup", start: "dropstart", end: "dropend" };

/**
 * <ui-dropdown>.
 *
 * Attributes:
 * - label: toggle button text (use the "toggle" slot for rich content).
 * - variant / outline / size: styling of the toggle button.
 * - direction: "down" (default), "up", "start", or "end".
 * - align: "end" aligns the menu to the right edge.
 * - open: visible state; reflected.
 *
 * Slots: default (ui-dropdown-item children), "toggle".
 *
 * CSS parts: toggle (the .btn), menu (the .dropdown-menu); style the toggle like ui-button's
 * ::part(button), e.g. through the --bs-btn-* variables.
 *
 * Events: ui-dropdown:shown / ui-dropdown:hidden (bubble).
 */
export class UiDropdown extends ShadowComponentElement {
  static stylesheet = new URL("./ui-dropdown.css", import.meta.url).href;
  static observedAttributes = ["label", "variant", "outline", "size", "direction", "align", "open"];

  #suppressOpenAttribute = false;

  constructor() {
    super();
    // Clicking an actionable item closes the menu (light-DOM click bubbles
    // to the host).
    this.addEventListener("click", (event) => {
      const item = event.target.closest?.("ui-dropdown-item");
      if (item && !item.hasAttribute("disabled") && !item.hasAttribute("header") && !item.hasAttribute("divider")) {
        this.close();
      }
    });
    this.addEventListener("keydown", (event) => this.#onKeydown(event));
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "open") {
      if (this.#suppressOpenAttribute) {
        return;
      }
      if (this.hasRendered) {
        if (newValue !== null) {
          this.open();
        } else {
          this.close();
        }
        return;
      }
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  disconnectedCallback() {
    this.#removeDocumentListener();
  }

  get shown() {
    return this.hasAttribute("open");
  }

  render() {
    const label = this.getAttribute("label") || "";
    const open = this.hasAttribute("open");
    const direction = DIRECTIONS[this.getAttribute("direction")] || "dropdown";
    const alignEnd = this.getAttribute("align") === "end";
    return `
      <div class="${direction}">
        <button class="${escapeHtml(this.#toggleClasses(open))}" part="toggle" type="button" aria-expanded="${open ? "true" : "false"}">
          <slot name="toggle">${escapeHtml(label)}</slot>
        </button>
        <div class="dropdown-menu${alignEnd ? " dropdown-menu-end" : ""}${open ? " show" : ""}" part="menu" data-bs-popper="static">
          <slot></slot>
        </div>
      </div>
    `;
  }

  afterRender() {
    this.shadowRoot.querySelector("button").addEventListener("click", () => this.toggle());
    if (this.hasAttribute("open")) {
      this.#addDocumentListener();
    }
  }

  open() {
    if (this.shown) {
      return;
    }
    this.#reflectOpen(true);
    this.#setMenuShown(true);
    this.#addDocumentListener();
    this.dispatchEvent(new CustomEvent("ui-dropdown:shown", { bubbles: true }));
  }

  close() {
    if (!this.shown) {
      return;
    }
    this.#reflectOpen(false);
    this.#setMenuShown(false);
    this.#removeDocumentListener();
    this.dispatchEvent(new CustomEvent("ui-dropdown:hidden", { bubbles: true }));
  }

  toggle() {
    if (this.shown) {
      this.close();
    } else {
      this.open();
    }
  }

  getItems() {
    return Array.from(this.querySelectorAll(":scope > ui-dropdown-item")).filter((item) => (
      !item.hasAttribute("disabled") && !item.hasAttribute("divider") && !item.hasAttribute("header")
    ));
  }

  #toggleClasses(open) {
    const classes = ["btn", "dropdown-toggle"];
    const variant = this.getAttribute("variant") || "primary";
    classes.splice(1, 0, `btn-${this.hasAttribute("outline") ? "outline-" : ""}${variant}`);
    const size = this.getAttribute("size");
    if (size === "sm" || size === "lg") {
      classes.push(`btn-${size}`);
    }
    if (open) {
      classes.push("show");
    }
    return classes.join(" ");
  }

  #setMenuShown(shown) {
    const menu = this.shadowRoot?.querySelector(".dropdown-menu");
    const button = this.shadowRoot?.querySelector("button");
    menu?.classList.toggle("show", shown);
    button?.classList.toggle("show", shown);
    button?.setAttribute("aria-expanded", shown ? "true" : "false");
  }

  #onKeydown(event) {
    if (event.key === "Escape") {
      this.close();
      this.shadowRoot?.querySelector("button")?.focus();
      return;
    }
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
      return;
    }
    event.preventDefault();
    if (!this.shown) {
      this.open();
    }
    const items = this.getItems();
    if (!items.length) {
      return;
    }
    const activeItem = items.find((item) => item.contains(document.activeElement) || item === event.target.closest?.("ui-dropdown-item"));
    let index = items.indexOf(activeItem);
    index = event.key === "ArrowDown"
      ? Math.min(index + 1, items.length - 1)
      : Math.max(index - 1, 0);
    items[index]?.focusItem();
  }

  #onDocumentClick = (event) => {
    if (!event.composedPath().includes(this)) {
      this.close();
    }
  };

  #addDocumentListener() {
    document.addEventListener("click", this.#onDocumentClick);
  }

  #removeDocumentListener() {
    document.removeEventListener("click", this.#onDocumentClick);
  }

  #reflectOpen(open) {
    this.#suppressOpenAttribute = true;
    this.toggleAttribute("open", open);
    this.#suppressOpenAttribute = false;
  }
}

/**
 * <ui-dropdown-item>.
 *
 * Attributes:
 * - href: renders a link item (otherwise a button).
 * - active / disabled: item state.
 * - header: renders a non-interactive .dropdown-header.
 * - divider: renders a .dropdown-divider rule.
 */
export class UiDropdownItem extends ShadowComponentElement {
  static stylesheet = new URL("./ui-dropdown.css", import.meta.url).href;
  static observedAttributes = ["href", "active", "disabled", "header", "divider"];

  render() {
    if (this.hasAttribute("divider")) {
      return '<hr class="dropdown-divider" />';
    }
    if (this.hasAttribute("header")) {
      return '<span class="dropdown-header"><slot></slot></span>';
    }

    const href = this.getAttribute("href");
    const active = this.hasAttribute("active");
    const disabled = this.hasAttribute("disabled");
    const classes = `dropdown-item${active ? " active" : ""}${disabled ? " disabled" : ""}`;

    if (href) {
      return `
        <a
          class="${escapeHtml(classes)}"
          href="${escapeHtml(href)}"
          ${active ? 'aria-current="true"' : ""}
          ${disabled ? 'aria-disabled="true" tabindex="-1"' : ""}
        ><slot></slot></a>
      `;
    }
    return `
      <button class="${escapeHtml(classes)}" type="button" ${disabled ? "disabled" : ""}>
        <slot></slot>
      </button>
    `;
  }

  focusItem() {
    this.shadowRoot?.querySelector("a, button")?.focus();
  }
}

registerComponent("ui-dropdown", UiDropdown);
registerComponent("ui-dropdown-item", UiDropdownItem);
