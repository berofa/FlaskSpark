import { hoistComponentTokens, stripRootTokenRules } from "../../core/shadow-sheet-transforms.js";

/**
 * Component token defaults moved from the Bootstrap class to the host element,
 * so a page themes a component with `ui-x { --bs-x-…: … }` (see
 * hoistComponentTokens). Only base rules and rules with additional defaults
 * (e.g. .btn-styled) belong here, never modifiers that override the base
 * (.badge-outline, .btn-sm): those must keep winning on the inner element.
 */
export const TOKEN_HOISTS = Object.freeze([
  { selector: ".alert", prefix: "--bs-alert-", host: "ui-alert" },
  { selector: ".badge", prefix: "--bs-badge-", host: "ui-badge" },
  { selector: ".btn", prefix: "--bs-btn-", host: "ui-button" },
  { selector: ".btn-styled", prefix: "--bs-btn-", host: "ui-button" },
  { selector: ".btn-close", prefix: "--bs-btn-close-", host: "ui-close-button" },
  { selector: ".breadcrumb", prefix: "--bs-breadcrumb-", host: "ui-breadcrumb" },
  { selector: ".card", prefix: "--bs-card-", host: "ui-card" },
  { selector: ".list-group", prefix: "--bs-list-group-", host: "ui-list-group" },
].map((entry) => Object.freeze(entry)));

export function prepareBootstrapSheet(sheet) {
  stripRootTokenRules(sheet);
  hoistComponentTokens(sheet, TOKEN_HOISTS);
}

/**
 * Stylesheets every Bootstrap 6 component adopts before its own:
 * the full Bootstrap CSS (one shared sheet for all shadow roots, prepared once
 * by prepareBootstrapSheet) and the :host baseline. Usage:
 *
 *   static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-x.css", import.meta.url).href];
 */
export const BOOTSTRAP_SHADOW_STYLES = Object.freeze([
  Object.freeze({
    url: new URL("../../vendor/bootstrap6/css/bootstrap.min.css", import.meta.url).href,
    transform: prepareBootstrapSheet,
  }),
  new URL("../../core/ui-shadow-base.css", import.meta.url).href,
]);

/** Theme colours of Bootstrap 6 (.theme-*), in the order of its docs. */
export const THEME_COLORS = Object.freeze([
  "primary",
  "accent",
  "success",
  "danger",
  "warning",
  "info",
  "inverse",
  "secondary",
]);

/** The theme colour named by `value`, or "" (no .theme-* class). Bootstrap 5's "dark" maps to inverse. */
export function themeColor(value) {
  const name = String(value || "").trim().toLowerCase();
  const mapped = name === "dark" ? "inverse" : name;
  return THEME_COLORS.includes(mapped) ? mapped : "";
}
