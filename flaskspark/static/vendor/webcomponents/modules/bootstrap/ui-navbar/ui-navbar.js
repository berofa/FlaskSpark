import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { collapseElement, expandElement } from "../../../core/collapse-transition.js";

const EXPAND_BREAKPOINTS = new Set(["sm", "md", "lg", "xl", "xxl"]);

/**
 * <ui-navbar>.
 *
 * Attributes:
 * - brand / brand-href: brand text and link (use the "brand" slot for rich
 *   content).
 * - expand: breakpoint ("sm"–"xxl") above which the navbar is horizontal;
 *   empty value means always expanded. Without the attribute the navbar
 *   always collapses behind the toggler.
 * - theme: "dark" renders the dark navbar color scheme.
 * - container: "fluid" (default) or "fixed".
 * - fixed: "top" or "bottom"; sticky: "top".
 * - label: aria-label of the nav landmark.
 *
 * Slots: default (ui-nav-item children), "brand", "end" (right-aligned
 * content).
 */
export class UiNavbar extends ShadowComponentElement {
  static stylesheet = new URL("./ui-navbar.css", import.meta.url).href;
  static observedAttributes = ["brand", "brand-href", "expand", "theme", "container", "fixed", "sticky", "label"];

  #navOpen = false;
  #animating = false;

  render() {
    const classes = ["navbar"];
    const expand = this.getAttribute("expand");
    if (expand !== null) {
      classes.push(EXPAND_BREAKPOINTS.has(expand) ? `navbar-expand-${expand}` : "navbar-expand");
    }
    const fixed = this.getAttribute("fixed");
    if (fixed === "top" || fixed === "bottom") {
      classes.push(`fixed-${fixed}`);
    }
    if (this.getAttribute("sticky") === "top") {
      classes.push("sticky-top");
    }
    const theme = this.getAttribute("theme") === "dark" ? ' data-bs-theme="dark"' : "";
    const label = this.getAttribute("label") || "Main navigation";
    const brand = this.getAttribute("brand") || "";
    const brandHref = this.getAttribute("brand-href") || "#";
    const containerClass = this.getAttribute("container") === "fixed" ? "container" : "container-fluid";

    return `
      <nav class="${escapeHtml(classes.join(" "))}"${theme} aria-label="${escapeHtml(label)}">
        <div class="${containerClass}">
          <a class="navbar-brand" href="${escapeHtml(brandHref)}" data-slot-wrapper="brand" hidden>
            <slot name="brand">${escapeHtml(brand)}</slot>
          </a>
          <button class="navbar-toggler" type="button" aria-label="Toggle navigation" aria-expanded="${this.#navOpen ? "true" : "false"}">
            <span class="navbar-toggler-icon"></span>
          </button>
          <div class="collapse navbar-collapse${this.#navOpen ? " show" : ""}">
            <ul class="navbar-nav">
              <slot></slot>
            </ul>
            <slot name="end"></slot>
          </div>
        </div>
      </nav>
    `;
  }

  afterRender() {
    const toggler = this.shadowRoot.querySelector(".navbar-toggler");
    toggler.addEventListener("click", () => this.toggleNav());
    this.#syncBrandVisibility();
  }

  toggleNav() {
    if (this.#animating) {
      return;
    }
    const collapseNode = this.shadowRoot?.querySelector(".navbar-collapse");
    const toggler = this.shadowRoot?.querySelector(".navbar-toggler");
    if (!collapseNode) {
      return;
    }
    this.#animating = true;
    this.#navOpen = !this.#navOpen;
    toggler?.setAttribute("aria-expanded", this.#navOpen ? "true" : "false");
    const done = () => {
      this.#animating = false;
    };
    if (this.#navOpen) {
      expandElement(collapseNode, { onComplete: done });
    } else {
      collapseElement(collapseNode, { onComplete: done });
    }
  }

  #syncBrandVisibility() {
    const slot = this.shadowRoot.querySelector('slot[name="brand"]');
    const wrapper = this.shadowRoot.querySelector('[data-slot-wrapper="brand"]');
    const sync = () => {
      const hasContent = Boolean(this.getAttribute("brand")) || slot.assignedNodes().some((node) => (
        node.nodeType === Node.ELEMENT_NODE
        || (node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0)
      ));
      wrapper.hidden = !hasContent;
    };
    slot.addEventListener("slotchange", sync);
    sync();
  }
}

/**
 * <ui-nav-item> — a navbar navigation link.
 *
 * Attributes:
 * - href: link target.
 * - active / disabled: link state.
 */
export class UiNavItem extends ShadowComponentElement {
  static stylesheet = new URL("./ui-navbar.css", import.meta.url).href;
  static observedAttributes = ["href", "active", "disabled"];

  render() {
    const href = this.getAttribute("href") || "#";
    const active = this.hasAttribute("active");
    const disabled = this.hasAttribute("disabled");
    return `
      <a
        class="nav-link${active ? " active" : ""}${disabled ? " disabled" : ""}"
        href="${escapeHtml(href)}"
        ${active ? 'aria-current="page"' : ""}
        ${disabled ? 'aria-disabled="true" tabindex="-1"' : ""}
      ><slot></slot></a>
    `;
  }
}

registerComponent("ui-navbar", UiNavbar);
registerComponent("ui-nav-item", UiNavItem);
