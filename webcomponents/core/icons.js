/**
 * Icons by name for components that take an `icon` attribute (e.g. <ui-card icon="graph-up">): inline SVG from an
 * icon sprite (one <symbol id="name"> per icon, like bootstrap-icons.svg), so they work inside shadow trees, where an
 * icon font's classes do not reach.
 *
 * The page names its sprite once, either in its <head>:
 *
 *   <meta name="ui-icon-sprite" content="/static/vendor/bootstrap-icons/bootstrap-icons.svg">
 *
 * or by script: setIconSprite(url). Without a sprite an `icon` attribute renders nothing (the component's "icon" slot
 * still takes any markup).
 */
import { escapeHtml } from "./escape.js";

let sprite = null;

/** Use `url` as the icon sprite (overrides the page's <meta name="ui-icon-sprite">). */
export function setIconSprite(url) {
  sprite = url || "";
}

/** The sprite's URL ("" when the page names none). */
export function iconSprite() {
  if (sprite !== null) return sprite;
  if (typeof document === "undefined") return "";
  return document.querySelector('meta[name="ui-icon-sprite"]')?.getAttribute("content") || "";
}

/** The markup of icon `name` (decorative: aria-hidden), "" without a name or a sprite. */
export function spriteIcon(name, className = "ui-icon") {
  const url = iconSprite();
  const id = String(name || "").trim();
  if (!url || !id) return "";
  return `<svg class="${escapeHtml(className)}" width="1em" height="1em" fill="currentColor" aria-hidden="true" focusable="false">`
    + `<use href="${escapeHtml(url)}#${escapeHtml(id)}"></use></svg>`;
}
