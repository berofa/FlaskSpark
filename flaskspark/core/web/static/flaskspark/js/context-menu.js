/**
 * Context menus: the actions of an entry on a right click, on a touch screen by resting a finger on it, with the
 * context menu key. The menu is ui-context-menu of webcomponents (Bootstrap 6's menu with icons).
 *
 *   import { contextMenu, quietRightClick, fromButtons, copyText } from "flaskspark/context-menu.js";
 *   const detach = contextMenu(root, { selector: ".entry", items: (el) => [...] });
 *   // root gets the class "has-context-menu": a page may hide the buttons the menu repeats
 *   quietRightClick();  // opt-in, once per page: a right click without a menu does nothing
 *
 * quietRightClick() keeps the browser's own menu where it is needed (text fields, selected text, links, media).
 */
import { UiContextMenu } from "webcomponents/modules/bootstrap/ui-context-menu/ui-context-menu.js";

/** The context menus for the elements matching options.selector in root; returns the function that removes them. */
export function contextMenu(root, options) {
  root.classList.add("has-context-menu");
  const detach = UiContextMenu.attach(root, options);
  return () => {
    detach();
    root.classList.remove("has-context-menu");
  };
}

/** Where the browser's own menu stays: text fields (paste), links and media (open, save), selected text (copy). */
export const NATIVE = "input, textarea, select, [contenteditable=''], [contenteditable='true'], a[href], img, video, audio";

/** Does a right click on `target` keep the browser's menu? (selected: the page has selected text) */
export function keepsNative(target, selected = false) {
  return selected || Boolean(target?.closest?.(NATIVE));
}

/** A right click without a menu of the page does nothing (once per page). */
export function quietRightClick(doc = document) {
  if (doc.documentElement.dataset.quietRightClick) return;
  doc.documentElement.dataset.quietRightClick = "1";
  doc.addEventListener("contextmenu", (event) => {
    if (event.defaultPrevented) return; // a menu of the page opened
    const target = event.composedPath().find((n) => n instanceof Element) || event.target;
    if (keepsNative(target, String(doc.getSelection?.() || "").trim().length > 0)) return;
    event.preventDefault();
  });
}

/**
 * Items that press the entry's own buttons (their handlers, confirmations and dialogs stay as they are): specs
 * [{selector, label, icon, danger, description}] or {divider: true} / {header}; an item only where its button is in
 * the entry and enabled (label: the button's title, label or text when not given).
 */
export function fromButtons(entry, specs) {
  return specs.map((spec) => {
    if (spec.divider || spec.header) return spec;
    const button = entry?.querySelector?.(spec.selector);
    if (!button || button.disabled || button.hasAttribute?.("disabled")) return null;
    const label = spec.label || button.getAttribute("title") || button.getAttribute("label") || button.textContent.trim();
    return { label, icon: spec.icon, danger: spec.danger, description: spec.description, action: () => button.click() };
  });
}

/** Copy a text to the clipboard; false where the browser refuses. */
export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
