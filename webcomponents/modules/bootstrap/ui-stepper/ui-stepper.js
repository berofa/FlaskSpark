import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { morph } from "../../../core/morph.js";
import { assignItemSlots, observeItems } from "../../../core/slotted-items.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

const BREAKPOINTS = new Set(["sm", "md", "lg", "xl", "2xl"]);

/**
 * <ui-stepper> (Bootstrap 6 stepper, new in v6): numbered steps for timelines, wizards and progress, with the
 * connecting track; <ui-step> children (their content slotted: a label, or descriptions, badges …).
 *
 * Attributes: horizontal (always, or from a container width: sm, md, lg, xl, 2xl), current (the steps up to this
 * one, counted from 1, are active; or `active` per step), overflow (scrolls horizontally when too wide), full
 * (full width), align (start, center, end), clickable (steps are buttons: ui-stepper:select {index, step}).
 * <ui-step>: active, variant (theme colour), href (a link step), disabled.
 * Property current. Parts: stepper, step.
 */
export class UiStepper extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-stepper.css", import.meta.url).href];
  static observedAttributes = ["horizontal", "current", "overflow", "full", "align", "clickable"];

  #stopObserving = null;
  #steps = [];

  constructor() {
    super();
    this.shadowRoot.addEventListener("click", (event) => {
      const item = event.target.closest?.("button.stepper-item");
      if (!item || item.disabled) return;
      const index = Number(item.dataset.index);
      this.dispatchEvent(new CustomEvent("ui-stepper:select", { bubbles: true, detail: { index, step: this.#steps[index] } }));
    });
  }

  connectedCallback() {
    super.connectedCallback();
    this.#stopObserving ??= observeItems(this, ["active", "variant", "href", "disabled"], () => this.requestRender());
  }

  disconnectedCallback() {
    this.#stopObserving?.();
    this.#stopObserving = null;
  }

  get current() {
    return Number.parseInt(this.getAttribute("current"), 10) || 0;
  }

  set current(value) {
    this.setAttribute("current", String(value));
  }

  get steps() {
    return [...this.#steps];
  }

  renderShadow() {
    morph(this.shadowRoot, this.render());
  }

  render() {
    this.#steps = assignItemSlots(this, "ui-step", "step");
    const horizontal = this.getAttribute("horizontal");
    const breakpoint = BREAKPOINTS.has(horizontal) ? horizontal : null;
    const align = { center: "text-center", end: "text-end" }[this.getAttribute("align")] || "";
    const current = this.hasAttribute("current") ? this.current : null;
    const clickable = this.hasAttribute("clickable");
    const anyLink = clickable || this.#steps.some((step) => step.hasAttribute("href"));
    const listTag = anyLink ? "div" : "ol";
    const classes = ["stepper", HOST_TOKENS_CLASS, horizontal !== null ? (breakpoint ? `${breakpoint}:stepper-horizontal` : "stepper-horizontal") : "",
      this.hasAttribute("full") ? "w-100" : ""].filter(Boolean).join(" ");
    const items = this.#steps.map((step, index) => {
      const active = current !== null ? index < current : step.hasAttribute("active");
      const variant = themeColor(step.getAttribute("variant"));
      const itemClasses = ["stepper-item", active ? "active" : "", variant ? `theme-${variant}` : ""].filter(Boolean).join(" ");
      const currentStep = current !== null && index === current - 1 ? ' aria-current="step"' : "";
      const content = `<slot name="step-${index}"></slot>`;
      const href = step.getAttribute("href");
      const disabled = step.hasAttribute("disabled");
      if (href && !disabled) {
        return `<a class="${itemClasses}" part="step" href="${escapeHtml(href)}" data-index="${index}"${currentStep}>${content}</a>`;
      }
      if (clickable) {
        return `<button type="button" class="${itemClasses}" part="step" data-index="${index}"${currentStep}${disabled ? " disabled" : ""}>${content}</button>`;
      }
      return anyLink ? `<div class="${itemClasses}" part="step"${currentStep}>${content}</div>` : `<li class="${itemClasses}" part="step"${currentStep}>${content}</li>`;
    });
    const list = `<${listTag} class="${classes}" part="stepper">${items.join("")}</${listTag}>`;
    const wrapper = ["ui-stepper", this.hasAttribute("overflow") ? "stepper-overflow" : "", breakpoint ? "contains-inline" : "", align].filter(Boolean).join(" ");
    return `<div class="${wrapper}">${list}</div>`;
  }
}

/** One step of a <ui-stepper> (active, variant, href, disabled; content: the label). */
export class UiStep extends HTMLElement {}

registerComponent("ui-stepper", UiStepper);
registerComponent("ui-step", UiStep);
