/**
 * Bootstrap's data API for components with shadow trees: one delegated click listener on the document for
 * `data-bs-toggle="<kind>"` triggers. The target is `data-bs-target` (a selector) or the trigger's `href`
 * ("#id"); `data-bs-*` options on the trigger are passed on (data-bs-backdrop="static" → { backdrop: "static" }).
 */

const handlers = new Map();
let installed = false;

/** The options a trigger passes on: its data-bs-* attributes except toggle and target. */
export function triggerOptions(trigger) {
  const options = {};
  for (const [key, value] of Object.entries(trigger.dataset)) {
    if (key.startsWith("bs") && key !== "bsToggle" && key !== "bsTarget") {
      const name = key.slice(2, 3).toLowerCase() + key.slice(3);
      options[name] = value;
    }
  }
  return options;
}

/** The element a trigger controls, or null. */
export function triggerTarget(trigger) {
  const selector = trigger.getAttribute("data-bs-target") || trigger.getAttribute("href") || "";
  if (!selector || selector === "#") {
    return null;
  }
  try {
    return trigger.getRootNode().querySelector(selector) || document.querySelector(selector);
  } catch {
    return null;
  }
}

/** Calls handler(target, trigger, options, event) for clicks on data-bs-toggle="<kind>" triggers. */
export function registerToggle(kind, handler) {
  handlers.set(kind, handler);
  if (installed) {
    return;
  }
  installed = true;
  document.addEventListener("click", (event) => {
    const trigger = event.target instanceof Element ? event.target.closest("[data-bs-toggle]") : null;
    const handle = trigger && handlers.get(trigger.getAttribute("data-bs-toggle"));
    if (!handle || trigger.hasAttribute("disabled")) {
      return;
    }
    const target = triggerTarget(trigger);
    if (target) {
      if (trigger.localName === "a") {
        event.preventDefault();
      }
      handle(target, trigger, triggerOptions(trigger), event);
    }
  });
}
