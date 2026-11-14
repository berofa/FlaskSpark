import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";
import { badgeShades, parseColor } from "./badge-color.js";

const APPEARANCES = new Set(["solid", "subtle", "outline"]);

/**
 * <ui-badge> (Bootstrap 6 badge).
 *
 * Attributes:
 * - variant: theme colour (primary, accent, success, danger, warning, info,
 *   inverse, secondary); without one the badge is neutral.
 * - appearance: solid (default), subtle or outline.
 * - pill: fully rounded (rounded-pill).
 * - href (+ target, rel): renders the badge as a link.
 * - badge-class: further Bootstrap classes for the badge itself (utilities
 *   such as "border border-bg"); classes on <ui-badge> style the host
 *   (e.g. position-absolute top-0 start-100 translate-middle).
 * - color: a free CSS colour (e.g. a label's "#428fdc"); wins over variant.
 *   Solid: filled with it, the text white or dark by WCAG contrast; subtle and
 *   outline: its text and line darkened (light mode) or lightened (dark mode)
 *   as far as the page needs.
 * - scope: a scoped (split) badge as GitLab shows scoped labels: the scope on
 *   the left filled with the colour (color, else the variant's, else neutral),
 *   the value (the content) on the right on the page's background, framed and
 *   written in the colour. Screen readers hear "Scope: value".
 *
 * Scales with the font size of its parent (em units). Empty badges are hidden.
 * Parts: badge; with scope also scope and value.
 */
export class UiBadge extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-badge.css", import.meta.url).href];
  static observedAttributes = ["variant", "appearance", "pill", "href", "target", "rel", "badge-class", "scope", "color"];

  get #color() {
    return (this.getAttribute("color") || "").trim();
  }

  get #scope() {
    return this.getAttribute("scope") || "";
  }

  classNames() {
    const variant = themeColor(this.getAttribute("variant"));
    const appearance = (this.getAttribute("appearance") || "solid").trim().toLowerCase();
    const scoped = Boolean(this.#scope);
    return [
      "badge",
      HOST_TOKENS_CLASS,
      !scoped && APPEARANCES.has(appearance) && appearance !== "solid" ? `badge-${appearance}` : "",
      variant && !this.#color ? `theme-${variant}` : "",
      this.#color ? "ui-badge-color" : "",
      scoped ? "ui-badge-scoped" : "",
      this.hasAttribute("pill") ? "rounded-pill" : "",
      this.getAttribute("badge-class") || "",
    ].filter(Boolean).join(" ");
  }

  render() {
    const classes = escapeHtml(this.classNames());
    const scope = this.#scope;
    const content = scope
      ? `<span class="ui-badge-scope" part="scope">${escapeHtml(scope)}<span class="visually-hidden">: </span></span>`
        + `<span class="ui-badge-value" part="value"><slot></slot></span>`
      : "<slot></slot>";
    const href = this.getAttribute("href");
    if (href) {
      const target = this.hasAttribute("target") ? ` target="${escapeHtml(this.getAttribute("target"))}"` : "";
      const rel = this.hasAttribute("rel") ? ` rel="${escapeHtml(this.getAttribute("rel"))}"` : "";
      return `<a class="${classes}" part="badge" href="${escapeHtml(href)}"${target}${rel}>${content}</a>`;
    }
    return `<span class="${classes}" part="badge">${content}</span>`;
  }

  afterRender() {
    const color = this.#color;
    const badge = this.shadowRoot.querySelector(".badge");
    if (!color || !badge || (globalThis.CSS?.supports && !CSS.supports("color", color))) return;
    badge.style.setProperty("--ui-badge-color", color);
    const rgb = this.#resolve(badge, color);
    if (!rgb) return;
    const shades = badgeShades(rgb);
    badge.style.setProperty("--ui-badge-contrast", shades.contrast === "light" ? "var(--bs-white, #fff)" : "var(--bs-gray-975, #121318)");
    badge.style.setProperty("--ui-badge-text-shade", shades.textShade);
    badge.style.setProperty("--ui-badge-line-shade", shades.lineShade);
    badge.style.setProperty("--ui-badge-text-tint", shades.textTint);
    badge.style.setProperty("--ui-badge-line-tint", shades.lineTint);
    badge.style.setProperty("--ui-badge-edge-tint", shades.edgeTint);
  }

  /** The colour as [r, g, b, a] (0..255): resolved in place (var(), currentColor), read, else drawn on a canvas. */
  #resolve(badge, color) {
    const probe = document.createElement("span");
    probe.style.color = color;
    probe.hidden = true;
    badge.append(probe);
    const resolved = getComputedStyle(probe).color;
    probe.remove();
    const parsed = parseColor(resolved);
    if (parsed) return parsed;
    try {
      const context = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
      context.fillStyle = resolved;
      context.fillRect(0, 0, 1, 1);
      const [r, g, b, a] = context.getImageData(0, 0, 1, 1).data;
      return [r, g, b, a / 255];
    } catch {
      return null;
    }
  }
}

registerComponent("ui-badge", UiBadge);
