import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { afterTransition } from "../../../core/transitions.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";

/**
 * <ui-collapse> (Bootstrap 6 collapse): shows and hides its content; the CSS animates the size
 * (interpolate-size; browsers without it switch at once).
 *
 * Attributes: open (shown; reflected), horizontal (animates the width; give the content a width).
 * Triggers anywhere: data-bs-toggle="collapse" with data-bs-target / href — a selector, also matching
 * several targets; several triggers may control one target. They get aria-expanded (and .collapsed while
 * closed). The data API also works on Bootstrap's plain .collapse elements.
 *
 * Methods: show(), hide(), toggle() — promises that resolve after the transition (false if cancelled).
 * Events (bubble): ui-collapse:show and ui-collapse:hide (cancelable), ui-collapse:shown, ui-collapse:hidden.
 * Part: collapse.
 */
export class UiCollapse extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-collapse.css", import.meta.url).href];
  static observedAttributes = ["open", "horizontal"];

  #reflecting = false;

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "open" && this.hasRendered) {
      if (!this.#reflecting) {
        (newValue === null ? this.hide() : this.show());
      }
      return;
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  get shown() {
    return this.hasAttribute("open");
  }

  get panel() {
    return this.shadowRoot.querySelector(".collapse");
  }

  render() {
    const classes = ["collapse", this.hasAttribute("horizontal") ? "collapse-horizontal" : "", this.shown ? "show" : ""];
    return `<div class="${classes.filter(Boolean).join(" ")}" part="collapse"><slot></slot></div>`;
  }

  afterRender() {
    syncTriggers(this);
  }

  show() {
    return setShown(this, true);
  }

  hide() {
    return setShown(this, false);
  }

  toggle() {
    return setShown(this, !this.shown);
  }

  reflect(open) {
    this.#reflecting = true;
    this.toggleAttribute("open", open);
    this.#reflecting = false;
  }
}

/** The element that carries .collapse / .show: the shadow panel of a <ui-collapse>, or a plain .collapse. */
function panelOf(target) {
  return target instanceof UiCollapse ? target.panel : target;
}

function isShown(target) {
  return target instanceof UiCollapse ? target.shown : target.classList.contains("show");
}

/** Shows or hides a <ui-collapse> or a plain .collapse; resolves after the transition. */
export function setShown(target, show) {
  if (isShown(target) === show) {
    return Promise.resolve(true);
  }
  const allowed = target.dispatchEvent(new CustomEvent(`ui-collapse:${show ? "show" : "hide"}`, { bubbles: true, cancelable: true }));
  if (!allowed) {
    return Promise.resolve(false);
  }
  if (target instanceof UiCollapse) {
    target.reflect(show);
  }
  const panel = panelOf(target);
  panel?.classList.toggle("show", show);
  syncTriggers(target);
  return new Promise((resolve) => {
    const done = () => {
      target.dispatchEvent(new CustomEvent(`ui-collapse:${show ? "shown" : "hidden"}`, { bubbles: true }));
      resolve(true);
    };
    if (panel) {
      afterTransition(panel, done);
    } else {
      done();
    }
  });
}

/** The targets of a trigger: every element matching its data-bs-target or href. */
function targetsOf(trigger) {
  const selector = trigger.getAttribute("data-bs-target") || trigger.getAttribute("href");
  if (!selector || selector === "#") {
    return [];
  }
  try {
    return [...document.querySelectorAll(selector)];
  } catch {
    return [];
  }
}

/** aria-expanded / .collapsed on every trigger of a target. */
function syncTriggers(target) {
  document.querySelectorAll('[data-bs-toggle="collapse"]').forEach((trigger) => {
    const targets = targetsOf(trigger);
    if (!targets.includes(target)) {
      return;
    }
    const expanded = targets.some(isShown);
    trigger.setAttribute("aria-expanded", String(expanded));
    trigger.classList.toggle("collapsed", !expanded);
  });
}

registerComponent("ui-collapse", UiCollapse);

document.addEventListener("click", (event) => {
  const trigger = event.target instanceof Element ? event.target.closest('[data-bs-toggle="collapse"]') : null;
  if (!trigger || trigger.hasAttribute("disabled")) {
    return;
  }
  if (trigger.localName === "a") {
    event.preventDefault();
  }
  targetsOf(trigger).forEach((target) => setShown(target, !isShown(target)));
});
