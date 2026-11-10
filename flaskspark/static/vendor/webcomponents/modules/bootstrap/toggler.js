/**
 * Bootstrap 6's toggler (js/src/toggler.ts, MIT): a click on [data-bs-toggle="toggler"] toggles an attribute or
 * a class of the trigger itself, or of every element data-bs-target selects. The toggled element names what:
 * data-bs-attribute (default "class") and data-bs-value (a class name, or the attribute's value; without a value
 * nothing happens). `id` is never toggled. Events on the toggled element: ui-toggler:toggle (cancelable) and
 * ui-toggler:toggled. Works for components too (<ui-button data-bs-toggle="toggler" …>).
 */

/** Toggles the element's configured attribute or class; false when cancelled or not configured. */
export function toggle(element) {
  const attribute = element.getAttribute("data-bs-attribute") || "class";
  const value = element.getAttribute("data-bs-value");
  if (!element.dispatchEvent(new CustomEvent("ui-toggler:toggle", { bubbles: true, cancelable: true }))) {
    return false;
  }
  if (attribute === "id" || value === null) {
    return false;
  }
  if (attribute === "class") {
    element.classList.toggle(value);
  } else if (element.getAttribute(attribute) === value) {
    element.removeAttribute(attribute);
  } else {
    element.setAttribute(attribute, value);
  }
  element.dispatchEvent(new CustomEvent("ui-toggler:toggled", { bubbles: true }));
  return true;
}

let installed = false;

export function installTogglerDataApi() {
  if (installed || typeof document === "undefined") {
    return;
  }
  installed = true;
  document.addEventListener("click", (event) => {
    const trigger = event.target instanceof Element ? event.target.closest('[data-bs-toggle="toggler"]') : null;
    if (!trigger || trigger.hasAttribute("disabled")) {
      return;
    }
    const selector = trigger.getAttribute("data-bs-target");
    let targets = [trigger];
    if (selector) {
      try {
        targets = [...document.querySelectorAll(selector)];
      } catch {
        targets = [];
      }
    }
    if (trigger.localName === "a") {
      event.preventDefault();
    }
    targets.forEach((target) => toggle(target));
  });
}

installTogglerDataApi();
