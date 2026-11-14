/**
 * Bootstrap Icons as inline SVG from the sprite (works inside shadow trees too, unlike the icon font):
 *
 *   import { icon } from "flaskspark/icons.js";
 *   cell.innerHTML = icon("trash");                  // markup
 *   button.append(iconElement("pencil", "Edit"));    // an element; a label makes it visible to screen readers
 */
const SPRITE = new URL("../vendor/bootstrap-icons/bootstrap-icons.svg", import.meta.url).href;

export function icon(name, label = "") {
  const a11y = label ? `role="img" aria-label="${label.replace(/"/g, "&quot;")}"` : 'aria-hidden="true"';
  return `<svg class="bi-svg" width="1em" height="1em" fill="currentColor" ${a11y}><use href="${SPRITE}#${name}"></use></svg>`;
}

export function iconElement(name, label = "") {
  const template = document.createElement("template");
  template.innerHTML = icon(name, label);
  return template.content.firstElementChild;
}
