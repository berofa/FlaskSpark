import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";

/**
 * <ui-chip>: compact pill for toggles, filters and tags (Bootstrap has no chip;
 * styled with Bootstrap's tokens). Renders a native <button> (or <a>) inside.
 *
 * Attributes:
 * - active: selected state. A click toggles it and fires `change` (bubbles);
 *   exposed as aria-pressed. Changing it from script updates the chip in place
 *   (keeps the focus) and does not fire `change`.
 * - color: colour of the leading dot (any CSS colour); no dot without it.
 *   The dot is dimmed while the chip is not active.
 * - size: "sm" or "lg".
 * - disabled.
 * - removable: adds a × button; it fires the cancelable `ui-chip:remove`
 *   (bubbles) and removes the chip unless the event is cancelled.
 * - href (+ target, rel): link chip instead of a toggle.
 * - static: display only (no button, no toggling), e.g. for tags.
 * - name, value (default "on"): form-associated; submits value while active.
 * - label: accessible name (icon-only chips).
 *
 * Slot: default (chip text).
 * CSS parts: chip (the pill), dot, remove.
 * Custom properties (set on the element or any ancestor):
 *   --ui-chip-color, --ui-chip-bg, --ui-chip-border-color,
 *   --ui-chip-hover-color, --ui-chip-hover-bg, --ui-chip-hover-border-color,
 *   --ui-chip-active-color, --ui-chip-active-bg, --ui-chip-active-border-color,
 *   --ui-chip-font-size, --ui-chip-font-weight, --ui-chip-padding-y, --ui-chip-padding-x,
 *   --ui-chip-radius, --ui-chip-dot-size, --ui-chip-dot-inactive-opacity.
 */
export class UiChip extends ShadowComponentElement {
  static stylesheet = new URL("./ui-chip.css", import.meta.url).href;
  static formAssociated = true;
  static observedAttributes = [
    "active", "color", "size", "disabled", "removable", "href", "target", "rel", "static", "name", "value", "label",
  ];

  #internals;
  #defaultActive = null;
  #formDisabled = false;

  constructor() {
    super();
    this.#internals = this.attachInternals();
  }

  connectedCallback() {
    if (this.#defaultActive === null) {
      this.#defaultActive = this.hasAttribute("active");
    }
    super.connectedCallback();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "active" && this.hasRendered && oldValue !== newValue) {
      // State change only: update in place instead of re-rendering (keeps the focus).
      this.#chip?.setAttribute("aria-pressed", String(this.active));
      this.#syncFormValue();
      return;
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  get #chip() {
    return this.shadowRoot.querySelector('[part~="chip"]');
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
    this.shadowRoot.querySelector("button, a")?.focus(options);
  }

  render() {
    const color = this.getAttribute("color");
    const dot = color ? `<span class="ui-chip__dot" part="dot" style="--ui-chip-dot-color: ${escapeHtml(color)}"></span>` : "";
    const label = this.getAttribute("label");
    const aria = label ? ` aria-label="${escapeHtml(label)}"` : "";
    const disabled = this.hasAttribute("disabled") || this.#formDisabled;
    const remove = this.hasAttribute("removable") && !disabled
      ? '<button type="button" class="ui-chip__remove" part="remove" aria-label="Entfernen" data-remove>×</button>'
      : "";
    const content = `${dot}<span class="ui-chip__text"><slot></slot></span>`;
    const href = this.getAttribute("href");

    let chip;
    if (this.hasAttribute("static")) {
      chip = `<span class="ui-chip" part="chip"${aria}>${content}</span>`;
    } else if (href && !disabled) {
      chip = `<a class="ui-chip" part="chip" href="${escapeHtml(href)}" target="${escapeHtml(this.getAttribute("target") || "")}" rel="${escapeHtml(this.getAttribute("rel") || "")}"${aria}>${content}</a>`;
    } else {
      chip = `<button type="button" class="ui-chip" part="chip" aria-pressed="${this.active}" ${disabled ? "disabled" : ""}${aria}>${content}</button>`;
    }
    return `<span class="ui-chip__wrap${remove ? " ui-chip__wrap--removable" : ""}">${chip}${remove}</span>`;
  }

  afterRender() {
    const chip = this.#chip;
    if (chip?.tagName === "BUTTON") {
      chip.addEventListener("click", () => {
        this.active = !this.active;
        this.dispatchEvent(new Event("change", { bubbles: true }));
      });
    }
    this.shadowRoot.querySelector("[data-remove]")?.addEventListener("click", () => {
      const event = new CustomEvent("ui-chip:remove", { bubbles: true, cancelable: true });
      if (this.dispatchEvent(event)) {
        this.remove();
      }
    });
    this.#syncFormValue();
  }

  #syncFormValue() {
    this.#internals.setFormValue(this.name && this.active ? this.value : null);
  }

  formResetCallback() {
    this.active = Boolean(this.#defaultActive);
  }

  formDisabledCallback(disabled) {
    this.#formDisabled = disabled;
    this.requestRender();
  }

  formStateRestoreCallback(state) {
    this.active = state !== null;
  }
}

registerComponent("ui-chip", UiChip);
