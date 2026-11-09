import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";

const VARIANTS = new Set([
  "primary",
  "secondary",
  "success",
  "danger",
  "warning",
  "info",
  "light",
  "dark",
  "link",
]);

/**
 * <ui-button>.
 *
 * Attributes:
 * - variant: Bootstrap variant (primary … dark, link) or "ghost".
 * - outline: outline style of the variant.
 * - size: "sm" or "lg".
 * - disabled, active, block: state and layout modifiers.
 * - type: "button" (default), "submit", or "reset" — submit/reset are
 *   forwarded to the surrounding light-DOM form via ElementInternals.
 * - href (+ target, rel): renders an <a> styled as a button instead.
 * - label: accessible name of the inner control (icon-only buttons).
 * - current: aria-current value for navigation links (e.g. "page").
 * - toggle: toggle button; `active` is exposed as aria-pressed. The page
 *   switches `active` itself (e.g. in a click handler); state changes update
 *   the inner button in place, so it keeps the focus.
 *
 * CSS part: button (the inner <button> / <a>), for page-level theming.
 */
export class UiButton extends ShadowComponentElement {
  static stylesheet = new URL("./ui-button.css", import.meta.url).href;
  static formAssociated = true;
  static observedAttributes = [
    "href",
    "target",
    "rel",
    "type",
    "variant",
    "outline",
    "size",
    "disabled",
    "active",
    "label",
    "current",
    "toggle",
  ];

  #internals;

  constructor() {
    super();
    this.#internals = this.attachInternals();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    // Pressed-state changes of a toggle button: update in place instead of re-rendering.
    const control = this.hasRendered && this.shadowRoot.querySelector('[part="button"]');
    if (name === "active" && control && oldValue !== newValue) {
      control.className = this.resolveClassName() + (this.hasAttribute("disabled") && control.tagName === "A" ? " disabled" : "");
      if (this.hasAttribute("toggle")) control.setAttribute("aria-pressed", String(this.hasAttribute("active")));
      return;
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  render() {
    const href = this.getAttribute("href");
    const disabled = this.hasAttribute("disabled");
    const className = this.resolveClassName();
    const label = this.getAttribute("label");
    const aria = (label ? ` aria-label="${escapeHtml(label)}"` : "")
      + (this.hasAttribute("toggle") ? ` aria-pressed="${this.hasAttribute("active")}"` : "");

    if (href) {
      const target = this.getAttribute("target") || "";
      const rel = this.getAttribute("rel") || "";
      return `
        <a
          class="${escapeHtml(className)}${disabled ? " disabled" : ""}"
          part="button"
          href="${escapeHtml(href)}"
          target="${escapeHtml(target)}"
          rel="${escapeHtml(rel)}"
          ${disabled ? 'aria-disabled="true" tabindex="-1"' : ""}
          ${this.hasAttribute("current") ? `aria-current="${escapeHtml(this.getAttribute("current") || "page")}"` : ""}${aria}
        >
          <slot></slot>
        </a>
      `;
    }

    const type = this.getAttribute("type") || "button";
    return `
      <button class="${escapeHtml(className)}" part="button" type="${escapeHtml(type)}" ${disabled ? "disabled" : ""}${aria}>
        <slot></slot>
      </button>
    `;
  }

  afterRender() {
    const button = this.shadowRoot.querySelector("button");
    if (!button) {
      return;
    }
    button.addEventListener("click", () => {
      // The internal button cannot submit a light-DOM form across the
      // shadow boundary; forward through ElementInternals instead.
      const type = this.getAttribute("type");
      if (type === "submit") {
        this.#internals.form?.requestSubmit();
      } else if (type === "reset") {
        this.#internals.form?.reset();
      }
    });
  }

  resolveClassName() {
    const variant = this.getAttribute("variant") || "primary";
    const classes = ["btn"];

    if (variant === "ghost") {
      // Custom extension, styled via :host([variant="ghost"]) in SCSS.
    } else if (VARIANTS.has(variant)) {
      classes.push(`btn-${this.hasAttribute("outline") ? "outline-" : ""}${variant}`);
    } else {
      classes.push("btn-primary");
    }

    const size = this.getAttribute("size");
    if (size === "sm" || size === "lg") {
      classes.push(`btn-${size}`);
    }
    if (this.hasAttribute("active")) {
      classes.push("active");
    }

    return classes.join(" ");
  }
}

registerComponent("ui-button", UiButton);
