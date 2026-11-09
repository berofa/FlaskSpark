import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

const APPEARANCES = new Set(["solid", "outline", "subtle", "text", "link"]);
const SIZES = new Set(["xs", "sm", "lg"]);

/**
 * <ui-button> (Bootstrap 6 button).
 *
 * Attributes:
 * - variant: theme colour (primary, accent, success, danger, warning, info,
 *   inverse, secondary). Bootstrap 5 names: "link" = appearance link,
 *   "ghost" = appearance text.
 * - appearance: solid (default with a variant), outline, subtle, text or link;
 *   without variant and appearance the neutral base button (.btn).
 *   "outline" as a boolean attribute works too (Bootstrap 5 API).
 * - styled: gradient and shadow on solid buttons (.btn-styled).
 * - size: xs, sm or lg.
 * - icon: square icon-only button (.btn-icon); give it a label.
 * - disabled, active: state. A disabled <fieldset> disables the button too.
 * - toggle: on/off button like Bootstrap's button plugin: a click switches
 *   `active` (exposed as aria-pressed) and fires ui-button:toggle.
 * - block: fills the width of its container (in a d-grid it does anyway).
 * - type: button (default), submit or reset — forwarded to the surrounding form.
 * - href (+ target, rel, download): renders an <a> styled as a button.
 * - label: accessible name (icon-only buttons). current: aria-current (links).
 * - button-class: further Bootstrap classes for the inner control.
 *
 * In a <ui-button-group> the group sets grouped, group-first, group-last and
 * group-divider (styled by ../grouped.css).
 *
 * Methods: toggle(), focus(), click(). Part: button.
 */
export class UiButton extends ShadowComponentElement {
  static stylesheets = [
    ...BOOTSTRAP_SHADOW_STYLES,
    new URL("../grouped.css", import.meta.url).href,
    new URL("./ui-button.css", import.meta.url).href,
  ];
  static formAssociated = true;
  static observedAttributes = [
    "href",
    "target",
    "rel",
    "download",
    "type",
    "variant",
    "appearance",
    "outline",
    "styled",
    "size",
    "icon",
    "disabled",
    "active",
    "label",
    "current",
    "toggle",
    "button-class",
  ];

  #internals;
  #formDisabled = false;

  constructor() {
    super();
    this.#internals = this.attachInternals();
    this.shadowRoot.addEventListener("click", (event) => this.#onClick(event));
  }

  get disabled() {
    return this.hasAttribute("disabled") || this.#formDisabled;
  }

  set disabled(value) {
    this.toggleAttribute("disabled", Boolean(value));
  }

  get active() {
    return this.hasAttribute("active");
  }

  set active(value) {
    this.toggleAttribute("active", Boolean(value));
  }

  get form() {
    return this.#internals.form;
  }

  formDisabledCallback(disabled) {
    this.#formDisabled = disabled;
    this.requestRender();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    // State changes of a toggle button: update in place instead of re-rendering, so it keeps the focus.
    const control = this.hasRendered && this.shadowRoot.querySelector('[part="button"]');
    if (name === "active" && control && oldValue !== newValue) {
      control.className = this.classNames();
      if (this.hasAttribute("toggle")) {
        control.setAttribute("aria-pressed", String(this.active));
      }
      return;
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  toggle() {
    this.active = !this.active;
    this.dispatchEvent(new CustomEvent("ui-button:toggle", { bubbles: true, detail: { active: this.active } }));
    return this.active;
  }

  focus(options) {
    this.shadowRoot.querySelector('[part="button"]')?.focus(options);
  }

  click() {
    this.shadowRoot.querySelector('[part="button"]')?.click();
  }

  appearance() {
    const raw = (this.getAttribute("appearance") || "").trim().toLowerCase();
    if (APPEARANCES.has(raw)) {
      return raw;
    }
    const legacy = (this.getAttribute("variant") || "").trim().toLowerCase();
    if (legacy === "link") {
      return "link";
    }
    if (legacy === "ghost") {
      return "text";
    }
    if (this.hasAttribute("outline")) {
      return "outline";
    }
    return themeColor(legacy) ? "solid" : "";
  }

  classNames() {
    const appearance = this.appearance();
    const variant = themeColor(this.getAttribute("variant"));
    const size = (this.getAttribute("size") || "").trim().toLowerCase();
    const classes = [
      // .btn-link keeps .btn like in Bootstrap's docs; the other appearances replace it.
      appearance === "link" ? "btn btn-link" : appearance ? `btn-${appearance}` : "btn",
      HOST_TOKENS_CLASS,
      variant ? `theme-${variant}` : "",
      this.hasAttribute("styled") ? "btn-styled" : "",
      SIZES.has(size) ? `btn-${size}` : "",
      this.hasAttribute("icon") ? "btn-icon" : "",
      this.active ? "active" : "",
      this.getAttribute("button-class") || "",
    ];
    if (this.disabled && this.hasAttribute("href")) {
      classes.push("disabled");
    }
    return classes.filter(Boolean).join(" ");
  }

  render() {
    const className = escapeHtml(this.classNames());
    const disabled = this.disabled;
    const label = this.getAttribute("label");
    const aria = (label ? ` aria-label="${escapeHtml(label)}"` : "")
      + (this.hasAttribute("toggle") ? ` aria-pressed="${this.active}"` : "");

    const href = this.getAttribute("href");
    if (href) {
      const optional = ["target", "rel", "download"]
        .filter((name) => this.hasAttribute(name))
        .map((name) => ` ${name}="${escapeHtml(this.getAttribute(name))}"`)
        .join("");
      const current = this.hasAttribute("current") ? ` aria-current="${escapeHtml(this.getAttribute("current") || "page")}"` : "";
      return `<a class="${className}" part="button" href="${escapeHtml(href)}"${optional}${current}${aria}`
        + `${disabled ? ' aria-disabled="true" tabindex="-1"' : ""}${this.hasAttribute("toggle") ? ' role="button"' : ""}><slot></slot></a>`;
    }

    const type = ["submit", "reset"].includes(this.getAttribute("type")) ? this.getAttribute("type") : "button";
    return `<button class="${className}" part="button" type="${type}"${disabled ? " disabled" : ""}${aria}><slot></slot></button>`;
  }

  #onClick(event) {
    if (this.disabled) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    if (this.hasAttribute("toggle")) {
      if (this.hasAttribute("href")) {
        event.preventDefault();
      }
      this.toggle();
    }
    // The inner button cannot submit a light-DOM form across the shadow boundary; forward through ElementInternals.
    const type = this.getAttribute("type");
    if (type === "submit") {
      this.#internals.form?.requestSubmit();
    } else if (type === "reset") {
      this.#internals.form?.reset();
    }
  }
}

registerComponent("ui-button", UiButton);
