/**
 * Transforms for the Bootstrap copy that shadow roots adopt (run once per sheet).
 *
 * Both work on any CSSOM-like object (cssRules, deleteRule, insertRule, style),
 * so they are testable without a browser.
 */

const ROOT_SELECTORS = new Set([":root", ":host"]);

const isGroupingRule = (rule) => Boolean(rule?.cssRules) && typeof rule.selectorText !== "string";

/** Selector list of a style rule, trimmed. */
function selectorsOf(rule) {
  return typeof rule?.selectorText === "string" ? rule.selectorText.split(",").map((s) => s.trim()) : [];
}

export function isRootTokenRule(rule) {
  const selectors = selectorsOf(rule);
  return selectors.length > 0 && selectors.every((selector) => ROOT_SELECTORS.has(selector));
}

/**
 * Removes the root token blocks (`:root, :host { --bs-…: … }`).
 *
 * Bootstrap 6 declares its tokens for `:root, :host`. Inside a shadow tree the
 * `:host` part resets every token to its default, so values the page sets
 * (e.g. its primary colour) would not reach the components anymore. The tokens
 * inherit from the page instead, which loads Bootstrap itself.
 * Recurses into @layer, @media and @supports; returns how many rules it removed.
 */
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
    if (isGroupingRule(rule)) {
      removed += stripRootTokenRules(rule);
      if (rule.cssRules.length === 0 && typeof rule.conditionText === "string") {
        // An @media / @supports block left empty.
        container.deleteRule(index);
      }
    }
  }
  return removed;
}

/** Class a component puts on its own inner element, so it inherits its tokens from the host. */
export const HOST_TOKENS_CLASS = "ui-host-tokens";

/**
 * Makes a component's token defaults themeable on its host element.
 *
 * Bootstrap declares component tokens on the component class
 * (`.badge { --bs-badge-padding-x: … }`). Inside a shadow tree a page rule like
 * `ui-badge { --bs-badge-padding-x: 1em }` would never win against that. So for
 * each qualifying rule this inserts
 * - `:host(ui-badge) { <the tokens> }` before it: defaults on the host, where
 *   every page rule for the host wins (the outer tree beats :host), and
 * - `:where(.ui-host-tokens):is(<the rule's selectors>) { <token>: inherit }`
 *   right after it: the component's own inner element (which carries
 *   HOST_TOKENS_CLASS) inherits the host's values. Same specificity and before
 *   the modifiers, so .badge-outline or .btn-sm still win as in Bootstrap.
 * The rule itself stays untouched: the same class used inside other components
 * (a .btn-close in an alert) keeps Bootstrap's defaults.
 *
 * `hoists`: [{ selector: ".badge", prefix: "--bs-badge-", host: "ui-badge" }].
 * A rule qualifies when the first selector of its list is `selector`; only
 * properties starting with `prefix` count, and none that read `--bs-theme-*`
 * (those must be computed on the element that carries the .theme-* class).
 * Returns how many tokens became themeable.
 */
export function hoistComponentTokens(container, hoists) {
  const rules = container?.cssRules;
  if (!rules || !hoists?.length) {
    return 0;
  }
  let hoisted = 0;
  for (let index = rules.length - 1; index >= 0; index -= 1) {
    const rule = rules[index];
    if (isGroupingRule(rule)) {
      hoisted += hoistComponentTokens(rule, hoists);
      continue;
    }
    const first = selectorsOf(rule)[0];
    const hoist = first && hoists.find((entry) => entry.selector === first);
    if (!hoist || !rule.style) {
      continue;
    }
    const declarations = [];
    for (let i = 0; i < rule.style.length; i += 1) {
      const name = rule.style.item(i);
      const value = rule.style.getPropertyValue(name);
      if (name.startsWith(hoist.prefix) && !value.includes("--bs-theme-")) {
        declarations.push([name, value.trim()]);
      }
    }
    if (!declarations.length) {
      continue;
    }
    const defaults = declarations.map(([name, value]) => `${name}: ${value};`).join(" ");
    const inherit = declarations.map(([name]) => `${name}: inherit;`).join(" ");
    container.insertRule(`:where(.${HOST_TOKENS_CLASS}):is(${rule.selectorText}) { ${inherit} }`, index + 1);
    container.insertRule(`:host(${hoist.host}) { ${defaults} }`, index);
    hoisted += declarations.length;
  }
  return hoisted;
}
