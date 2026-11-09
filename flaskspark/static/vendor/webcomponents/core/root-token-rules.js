/**
 * Removes the root token blocks (`:root, :host { --bs-…: … }`) from a stylesheet.
 *
 * Bootstrap 6 declares its tokens for `:root, :host`. Inside a shadow tree the
 * `:host` part resets every token to its default, so values the page sets
 * (e.g. its primary colour) would not reach the components anymore. The copy
 * adopted into shadow roots therefore drops these blocks; the tokens inherit
 * from the page, which loads Bootstrap (or ui-tokens.css) itself.
 *
 * Works on any CSSOM-like object (cssRules + deleteRule), so it is testable
 * without a browser.
 */

const ROOT_SELECTORS = new Set([":root", ":host"]);

export function isRootTokenRule(rule) {
  const selectorText = rule?.selectorText;
  if (typeof selectorText !== "string" || !selectorText.trim()) {
    return false;
  }
  return selectorText.split(",").every((selector) => ROOT_SELECTORS.has(selector.trim()));
}

/** Removes root token rules recursively (also inside @media, @layer, @supports); returns how many. */
export function stripRootTokenRules(container) {
  const rules = container?.cssRules;
  if (!rules) {
    return 0;
  }
  let removed = 0;
  for (let index = rules.length - 1; index >= 0; index -= 1) {
    const rule = rules[index];
    if (isRootTokenRule(rule)) {
      container.deleteRule(index);
      removed += 1;
      continue;
    }
    if (rule.cssRules && !rule.selectorText) {
      removed += stripRootTokenRules(rule);
      if (rule.cssRules.length === 0 && typeof rule.conditionText === "string") {
        // An @media / @supports block left empty.
        container.deleteRule(index);
      }
    }
  }
  return removed;
}
