/**
 * Escape a value for safe interpolation into HTML text or attribute context.
 *
 * Every dynamic value (attributes, item data, labels) that ends up in a
 * template string passed to innerHTML must go through this helper.
 */
export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
