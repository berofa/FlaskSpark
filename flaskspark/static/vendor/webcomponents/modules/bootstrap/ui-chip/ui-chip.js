import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { morph } from "../../../core/morph.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";
import { DISMISS_ICON, installChipsDataApi } from "./chips-controller.js";
import "./ui-chip-input.js";

/**
 * <ui-chip> (Bootstrap 6 .chip): a small interactive element for a person, place, tag or value.
 *
 * Attributes:
 * - variant: theme colour (subtle; active: solid).
 * - active: the solid appearance. toggle: a click (Enter, Space) toggles it and fires `change` (bubbles);
 *   the chip is a button with aria-pressed. name / value ("on"): form-associated, submits while active.
 * - href (+ target, rel): a link chip.
 * - dismissible: a remove button; fires the cancelable ui-chip:remove (bubbles), then removes the chip.
 * - img (+ img-alt): an avatar in front (.chip-img); slot "icon": an icon (.chip-icon).
 * - color: a coloured dot in front (any CSS colour; dimmed while a toggle chip is not active).
 * - disabled; label: accessible name; remove-label: name of the remove button ("Remove").
 * Parts: chip, img, icon, dot, dismiss.
 */
export class UiChip extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-chip.css", import.meta.url).href];
  static formAssociated = true;
  static observedAttributes = ["variant", "active", "toggle", "href", "target", "rel", "dismissible", "img", "img-alt", "color",
    "disabled", "label", "remove-label", "name", "value"];

  #internals;
  #defaultActive = null;
  #formDisabled = false;

  constructor() {
    super();
    this.#internals = this.attachInternals();
    this.shadowRoot.addEventListener("click", (event) => {
      if (this.#disabled) {
        return;
      }
      if (event.target.closest?.(".chip-dismiss")) {
        event.stopPropagation();
        this.dismiss();
      } else if (this.hasAttribute("toggle") && event.target.closest?.(".chip")) {
        this.#toggle();
      }
    });
    this.shadowRoot.addEventListener("keydown", (event) => {
      if (this.hasAttribute("toggle") && !this.#disabled && (event.key === "Enter" || event.key === " ")
        && event.target.classList?.contains("chip")) {
        event.preventDefault();
        this.#toggle();
      }
    });
  }

  connectedCallback() {
    this.#defaultActive ??= this.hasAttribute("active");
    super.connectedCallback();
  }

  get #disabled() {
    return this.hasAttribute("disabled") || this.#formDisabled;
  }

  get active() {
    return this.hasAttribute("active");
  }

  set active(value) {
    this.toggleAttribute("active", Boolean(value));
  }

  get value() {
    return this.getAttribute("value") ?? "on";
  }

  set value(value) {
    this.setAttribute("value", value);
  }

  get name() {
    return this.getAttribute("name") || "";
  }

  get form() {
    return this.#internals.form;
  }

  focus(options) {
    this.shadowRoot.querySelector(".chip[tabindex], a.chip, .chip-dismiss")?.focus(options);
  }

  #toggle() {
    this.active = !this.active;
    this.dispatchEvent(new Event("change", { bubbles: true }));
  }

  /** Removes the chip unless ui-chip:remove is cancelled; true when removed. */
  dismiss() {
    if (!this.dispatchEvent(new CustomEvent("ui-chip:remove", { bubbles: true, cancelable: true }))) {
      return false;
    }
    this.remove();
    return true;
  }

  renderShadow() {
    morph(this.shadowRoot, this.render());
    this.#internals.setFormValue(this.name && this.hasAttribute("toggle") && this.active ? this.value : null);
  }

  render() {
    const variant = themeColor(this.getAttribute("variant"));
    const disabled = this.#disabled;
    const toggle = this.hasAttribute("toggle");
    const classes = ["chip", HOST_TOKENS_CLASS, variant ? `theme-${variant}` : "", this.active ? "active" : "",
      disabled ? "disabled" : "", toggle && this.getAttribute("color") ? "chip-toggle" : ""].filter(Boolean).join(" ");
    const label = this.getAttribute("label");
    const aria = (label ? ` aria-label="${escapeHtml(label)}"` : "") + (disabled ? ' aria-disabled="true"' : "");
    const img = this.getAttribute("img");
    const color = this.getAttribute("color");
    const content = [
      img ? `<img class="chip-img" part="img" src="${escapeHtml(img)}" alt="${escapeHtml(this.getAttribute("img-alt") || "")}" width="16" height="16">` : "",
      color ? `<span class="chip-icon" part="dot"><span class="chip-dot" style="--ui-chip-dot-color: ${escapeHtml(color)}"></span></span>` : "",
      this.querySelector(':scope > [slot="icon"]') ? '<span class="chip-icon" part="icon"><slot name="icon"></slot></span>' : "",
      "<slot></slot>",
    ].join("");
    const href = this.getAttribute("href");
    if (href && !disabled) {
      const target = this.getAttribute("target");
      const rel = this.getAttribute("rel");
      return `<a class="${classes}" part="chip" href="${escapeHtml(href)}"${target ? ` target="${escapeHtml(target)}"` : ""}`
        + `${rel ? ` rel="${escapeHtml(rel)}"` : ""}${aria}>${content}</a>`;
    }
    const dismiss = this.hasAttribute("dismissible")
      ? `<button type="button" class="chip-dismiss" part="dismiss" aria-label="${escapeHtml(this.getAttribute("remove-label") || "Remove")}"`
        + `${disabled ? " disabled" : ""}>${DISMISS_ICON}</button>` : "";
    const role = toggle ? ` role="button" aria-pressed="${this.active}" tabindex="${disabled ? -1 : 0}"` : "";
    return `<span class="${classes}" part="chip"${role}${aria}>${content}${dismiss}</span>`;
  }

  formResetCallback() {
    this.active = Boolean(this.#defaultActive);
  }

  formDisabledCallback(disabled) {
    this.#formDisabled = disabled;
    this.requestRender();
  }
}

registerComponent("ui-chip", UiChip);
installChipsDataApi();
