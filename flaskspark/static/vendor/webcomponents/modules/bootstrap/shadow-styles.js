import { stripRootTokenRules } from "../../core/root-token-rules.js";

/**
 * Stylesheets every Bootstrap 6 component adopts before its own:
 * the full Bootstrap CSS (one shared sheet for all shadow roots, without its
 * `:root, :host` token blocks, so the page's tokens inherit) and the :host
 * baseline. Usage:
 *
 *   static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-x.css", import.meta.url).href];
 */
export const BOOTSTRAP_SHADOW_STYLES = Object.freeze([
  Object.freeze({
    url: new URL("../../vendor/bootstrap6/css/bootstrap.min.css", import.meta.url).href,
    transform: stripRootTokenRules,
  }),
  new URL("../../core/ui-shadow-base.css", import.meta.url).href,
]);
