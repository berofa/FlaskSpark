import { hoistComponentTokens, stripRootTokenRules } from "../../core/shadow-sheet-transforms.js";

// Text fields share Bootstrap's .form-control (and input group, floating label) tokens.
const FIELD_HOSTS = ":is(ui-input, ui-select, ui-textarea, ui-datepicker, ui-combobox)";

/**
 * Component token defaults moved from the Bootstrap class to the host element,
 * so a page themes a component with `ui-x { --bs-x-…: … }` (see
 * hoistComponentTokens). Only base rules and rules with additional defaults
 * (e.g. .btn-styled) belong here, never modifiers that override the base
 * (.badge-outline, .btn-sm): those must keep winning on the inner element.
 */
export const TOKEN_HOISTS = Object.freeze([
  { selector: ".accordion", prefix: "--bs-accordion-", host: "ui-accordion" },
  { selector: ".alert", prefix: "--bs-alert-", host: "ui-alert" },
  { selector: ".badge", prefix: "--bs-badge-", host: "ui-badge" },
  { selector: ".btn", prefix: "--bs-btn-", host: "ui-button" },
  { selector: ".btn-styled", prefix: "--bs-btn-", host: "ui-button" },
  { selector: ".btn-close", prefix: "--bs-btn-close-", host: "ui-close-button" },
  { selector: ".breadcrumb", prefix: "--bs-breadcrumb-", host: "ui-breadcrumb" },
  { selector: ".carousel", prefix: "--bs-carousel-", host: "ui-carousel" },
  { selector: ".chip", prefix: "--bs-chip-", host: ":is(ui-chip, ui-chip-input)" },
  { selector: ".chip-input", prefix: "--bs-chip-input-", host: "ui-chip-input" },
  { selector: ".collapse", prefix: "--bs-transition-collapse-", host: "ui-collapse" },
  { selector: ".card", prefix: "--bs-card-", host: "ui-card" },
  { selector: ".table", prefix: "--bs-table-", host: "ui-table" },
  { selector: ".list-group", prefix: "--bs-list-group-", host: ":is(ui-list-group, ui-tabs)" },
  { selector: ".nav", prefix: "--bs-nav-", host: "ui-tabs" },
  { selector: ".nav-tabs", prefix: "--bs-nav-tabs-", host: "ui-tabs" },
  { selector: ".nav-pills", prefix: "--bs-nav-pills-", host: "ui-tabs" },
  { selector: ".nav-underline", prefix: "--bs-nav-underline-", host: "ui-tabs" },
  { selector: ".tab-content > .tab-pane", prefix: "--bs-tab-pane-", host: "ui-tabs" },
  { selector: ".dialog", prefix: "--bs-dialog-", host: "ui-dialog" },
  { selector: ".drawer", prefix: "--bs-drawer-", host: "ui-drawer" },
  { selector: ".tooltip", prefix: "--bs-tooltip-", host: "ui-tooltip" },
  { selector: ".popover", prefix: "--bs-popover-", host: "ui-popover" },
  { selector: ".toast", prefix: "--bs-toast-", host: "ui-toast" },
  { selector: ".check", prefix: "--bs-check-", host: "ui-check" },
  { selector: ".radio", prefix: "--bs-radio-", host: "ui-check" },
  { selector: ".switch", prefix: "--bs-switch-", host: "ui-check" },
  { selector: ".form-control", prefix: "--bs-control-", host: FIELD_HOSTS },
  { selector: ".input-group", prefix: "--bs-input-group-", host: FIELD_HOSTS },
  { selector: ".form-floating", prefix: "--bs-form-floating-", host: FIELD_HOSTS },
  { selector: ".form-adorn", prefix: "--bs-form-adorn-", host: FIELD_HOSTS },
  { selector: ".strength", prefix: "--bs-strength-", host: "ui-input" },
  { selector: ".strength-bar", prefix: "--bs-strength-", host: "ui-input" },
  { selector: "[data-vc=calendar]", prefix: "--bs-datepicker-", host: "ui-datepicker" },
  { selector: ".menu", prefix: "--bs-menu-", host: "ui-combobox" },
  { selector: ".avatar", prefix: "--bs-avatar-", host: "ui-avatar" },
  { selector: ".pagination", prefix: "--bs-pagination-", host: "ui-pagination" },
  { selector: ".stepper", prefix: "--bs-stepper-", host: "ui-stepper" },
  { selector: ".spinner-border", prefix: "--bs-spinner-", host: "ui-spinner" },
  // Same token names as the border spinner: the grow defaults only on grow spinners.
  { selector: ".spinner-grow", prefix: "--bs-spinner-", host: "ui-spinner[type=grow]" },
  { selector: ".placeholder", prefix: "--bs-placeholder-", host: "ui-placeholder" },
  { selector: ".progress", prefix: "--bs-progress-", host: "ui-progress" },
  { selector: ".otp", prefix: "--bs-otp-", host: "ui-otp" },
  { selector: ".form-range", prefix: "--bs-range-", host: "ui-range" },
  { selector: ".form-text", prefix: "--bs-form-text-", host: ":is(ui-input, ui-select, ui-textarea, ui-check, ui-range, ui-otp, ui-datepicker, ui-combobox)" },
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
