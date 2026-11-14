/**
 * The trend of a key figure from an attribute value: "up", "down", "flat" or "" (none).
 *
 * Accepts the words (up, down, flat; also rising/falling/unchanged), signs ("+", "-", "=") and numbers (the sign of
 * a change: 2.5 is up, -1 down, 0 flat). Anything else is no trend.
 */
const WORDS = new Map([
  ["up", "up"], ["rising", "up"], ["+", "up"],
  ["down", "down"], ["falling", "down"], ["-", "down"], ["−", "down"],
  ["flat", "flat"], ["unchanged", "flat"], ["=", "flat"], ["0", "flat"],
]);

export function trendOf(value) {
  const text = String(value ?? "").trim().toLowerCase();
  if (!text) return "";
  if (WORDS.has(text)) return WORDS.get(text);
  const number = Number(text.replace("−", "-"));
  if (Number.isFinite(number)) return number > 0 ? "up" : number < 0 ? "down" : "flat";
  return "";
}

/** The theme colour of a trend: up is success, down is danger (inverse: the other way round), flat none. */
export function trendVariant(trend, inverse = false) {
  if (trend === "up") return inverse ? "danger" : "success";
  if (trend === "down") return inverse ? "success" : "danger";
  return "";
}
