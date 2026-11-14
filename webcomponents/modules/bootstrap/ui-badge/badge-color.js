/**
 * Colour arithmetic of <ui-badge color="…"> (pure functions, tested with node --test):
 * parse a resolved CSS colour, WCAG relative luminance and contrast, the text colour on a filled badge, and how much
 * black (light mode) or white (dark mode) a free colour needs as text or line on the page's background.
 */

/** WCAG relative luminance of white and of a dark page (Bootstrap's dark body, about #121318). */
export const LIGHT_PAGE = 1;
export const DARK_PAGE = 0.0065;
/** Minimum contrast: text (WCAG AA) and lines (non-text, WCAG 1.4.11). */
export const TEXT_CONTRAST = 4.5;
export const LINE_CONTRAST = 3;

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

function channel(text, max = 255) {
  const value = String(text).trim();
  if (value === "none") return 0;
  return value.endsWith("%") ? (parseFloat(value) / 100) * max : parseFloat(value);
}

function alpha(text) {
  if (text === undefined || text === null || text === "") return 1;
  return clamp(channel(text, 1), 0, 1);
}

/** OKLab (L 0..1) -> sRGB 0..255 (CSS Color 4). */
function oklabToRgb(l, a, b) {
  const l1 = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m1 = (l - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s1 = (l - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const linear = [
    4.0767416621 * l1 - 3.3077115913 * m1 + 0.2309699292 * s1,
    -1.2684380046 * l1 + 2.6097574011 * m1 - 0.3413193965 * s1,
    -0.0041960863 * l1 - 0.7034186147 * m1 + 1.707614701 * s1,
  ];
  return linear.map((c) => {
    const v = clamp(c, 0, 1);
    return 255 * (v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055);
  });
}

/**
 * A colour as getComputedStyle() gives it (also hex): [r, g, b, a] with r, g, b in 0..255 and a in 0..1, or null
 * for what it does not read (e.g. lab(); the component then asks a canvas).
 */
export function parseColor(text) {
  const value = String(text ?? "").trim().toLowerCase();
  if (!value) return null;
  if (value === "transparent") return [0, 0, 0, 0];
  let m = value.match(/^#([0-9a-f]{3,8})$/);
  if (m) {
    let hex = m[1];
    if (hex.length === 3 || hex.length === 4) hex = [...hex].map((c) => c + c).join("");
    if (hex.length !== 6 && hex.length !== 8) return null;
    const n = (i) => parseInt(hex.slice(i, i + 2), 16);
    return [n(0), n(2), n(4), hex.length === 8 ? n(6) / 255 : 1];
  }
  m = value.match(/^(rgba?|color|oklch|oklab)\((.*)\)$/);
  if (!m) return null;
  const [, fn, body] = m;
  const [main, slash] = body.split("/");
  const parts = main.replace(/,/g, " ").trim().split(/\s+/);
  const a = alpha(slash ?? (parts.length === 4 && fn.startsWith("rgb") ? parts[3] : undefined));
  if (fn === "rgb" || fn === "rgba") {
    if (parts.length < 3) return null;
    return [...parts.slice(0, 3).map((p) => clamp(channel(p), 0, 255)), a];
  }
  if (fn === "color") {
    const [space, ...rest] = parts;
    if (!["srgb", "display-p3", "srgb-linear"].includes(space) || rest.length < 3) return null;
    const rgb = rest.slice(0, 3).map((p) => clamp(channel(p, 1), 0, 1));
    const encoded = space === "srgb-linear"
      ? rgb.map((v) => (v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055)) : rgb;
    return [...encoded.map((v) => v * 255), a];
  }
  if (parts.length < 3) return null;
  const l = channel(parts[0], 1);
  if (fn === "oklab") return [...oklabToRgb(l, channel(parts[1], 0.4), channel(parts[2], 0.4)), a];
  const c = channel(parts[1], 0.4);
  const h = (parseFloat(parts[2]) || 0) * (Math.PI / 180);
  return [...oklabToRgb(l, c * Math.cos(h), c * Math.sin(h)), a];
}

/** WCAG 2 relative luminance of [r, g, b] (0..255). */
export function luminance([r, g, b]) {
  const lin = (v) => {
    const s = v / 255;
    return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

/** WCAG 2 contrast ratio of two luminances (1..21). */
export function contrastRatio(a, b) {
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

/** The text on a badge filled with `rgb`: "light" (white) or "dark", whichever contrasts more (WCAG). */
export function contrastText(rgb) {
  const l = luminance(rgb);
  return contrastRatio(l, 1) >= contrastRatio(l, 0) ? "light" : "dark";
}

/** `rgb` mixed with `toward` (0..255 each) by `amount` (0..1) in sRGB, as color-mix(in srgb, …) does. */
export function mix(rgb, toward, amount) {
  return rgb.slice(0, 3).map((v, i) => v + (toward[i] - v) * amount);
}

/**
 * How much (0..1, in steps of 0.05) black or white `rgb` needs before it contrasts `ratio` with a page of luminance
 * `page` (0: it does already).
 */
export function mixFor(rgb, toward, page, ratio) {
  for (let step = 0; step <= 20; step += 1) {
    const amount = step / 20;
    if (contrastRatio(luminance(mix(rgb, toward, amount)), page) >= ratio) return amount;
  }
  return 1;
}

const BLACK = [0, 0, 0];
const WHITE = [255, 255, 255];

/**
 * Everything a freely coloured badge needs from its colour: the text on the fill ("light"/"dark") and the share of
 * black (light mode) or white (dark mode) for its text and its line on the page, as CSS percentages. In dark mode the
 * line always gets a little white (a dark label stays visible on a dark page); edgeTint: only as much as the edge of a
 * filled badge needs (0% for most colours).
 */
export function badgeShades(rgb) {
  const pct = (amount) => `${Math.round(amount * 100)}%`;
  return {
    contrast: contrastText(rgb),
    textShade: pct(mixFor(rgb, BLACK, LIGHT_PAGE, TEXT_CONTRAST)),
    lineShade: pct(mixFor(rgb, BLACK, LIGHT_PAGE, LINE_CONTRAST)),
    textTint: pct(mixFor(rgb, WHITE, DARK_PAGE, TEXT_CONTRAST)),
    lineTint: pct(Math.max(0.15, mixFor(rgb, WHITE, DARK_PAGE, LINE_CONTRAST))),
    edgeTint: pct(mixFor(rgb, WHITE, DARK_PAGE, LINE_CONTRAST)),
  };
}
