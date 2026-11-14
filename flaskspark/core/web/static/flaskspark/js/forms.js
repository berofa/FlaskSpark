/**
 * Forms on top of the fields of webcomponents (ui-input, ui-select, ui-textarea, ui-check), sent as JSON.
 *
 *   import { validateForm, formJson, submitForm, refreshPage } from "flaskspark/forms.js";
 *
 * - validateForm(root): every visible field shows its feedback; false (and the first invalid one focused) when one
 *   is invalid (required and empty, an e-mail that is none, out of its bounds, …).
 * - formJson(form): the form's fields as an object (several values of a name: a list; an unchecked ui-check: false
 *   when it has data-bool, else left out like a native checkbox).
 * - submitForm(form, options): checked, sent as JSON (request() of flaskspark/ui.js) to form.action with the form's
 *   method (default POST); the answer's "message" (or data-success, or «Saved») as a notice; data-reset empties the
 *   form; in a <ui-dialog> it closes after success and an error shows inside the dialog above the form, elsewhere as
 *   a toast; then the page's content again from the server, only what changed (data-no-refresh: not). Returns the
 *   answer, or null on failure.
 * - <form data-fetch>: submitForm() on submit, for every such form of the page (this module only has to be loaded).
 * - refreshPage(selector = "main"): the content of `selector` as the server renders the page now (morph: no reload,
 *   no flicker, focus and scroll positions stay).
 */
import { morph } from "webcomponents/core/morph.js";
import { notice, request } from "flaskspark/ui.js";
import { preload, t } from "flaskspark/i18n.js";

preload(["Saved"]);

const FIELDS = "ui-input, ui-select, ui-textarea, ui-check, ui-combobox, ui-datepicker";

/** Every field of `root` checked (their feedback shown); false, and the first invalid one focused, if one is. */
export function validateForm(root) {
  const fields = [...root.querySelectorAll(FIELDS)].filter((f) => !f.hasAttribute("disabled") && f.offsetParent !== null);
  const invalid = fields.filter((f) => typeof f.validate === "function" && !f.validate());
  invalid[0]?.focus();
  return invalid.length === 0;
}

/** The fields of a form as a plain object for a JSON body. */
export function formJson(form) {
  const out = {};
  for (const [name, value] of new FormData(form)) {
    if (value instanceof File) continue; // files go with FormData, not JSON
    if (name in out) out[name] = [].concat(out[name], value);
    else out[name] = value;
  }
  for (const check of form.querySelectorAll("ui-check[data-bool][name]")) {
    out[check.getAttribute("name")] = Boolean(check.checked);
  }
  return out;
}

/** The content of `selector` (default the page's <main>) as the server renders the page now, only what changed. */
export async function refreshPage(selector = "main") {
  const response = await fetch(location.href, { headers: { Accept: "text/html" }, credentials: "same-origin" });
  if (!response.ok) return;
  const page = new DOMParser().parseFromString(await response.text(), "text/html");
  const fresh = page.querySelector(selector);
  const current = document.querySelector(selector);
  if (fresh && current) morph(current, fresh.innerHTML);
}

/** Where a form's error shows: in a dialog a box above the form (made once), else the form (a toast). */
function errorBox(form) {
  if (!form.closest("ui-dialog")) return form;
  let box = form.previousElementSibling;
  if (!box?.hasAttribute("data-form-notice")) {
    box = document.createElement("div");
    box.setAttribute("data-form-notice", "");
    form.before(box);
  }
  return box;
}

/** Check and send a form as JSON (see above); options: body (instead of formJson), refresh (default true). */
export async function submitForm(form, options = {}) {
  if (!validateForm(form)) return null;
  const button = form.querySelector('[type="submit"]');
  button?.setAttribute("disabled", "");
  try {
    const method = (form.getAttribute("method") || "post").toUpperCase();
    const data = await request(form.getAttribute("action") || location.href, method, options.body ?? formJson(form));
    notice(data.message || form.dataset.success || t("Saved"), "success");
    if (form.hasAttribute("data-reset")) form.reset();
    const dialog = form.closest("ui-dialog");
    if (dialog) {
      if (form.previousElementSibling?.hasAttribute("data-form-notice")) form.previousElementSibling.replaceChildren();
      dialog.hide?.();
    }
    if (options.refresh !== false && !form.hasAttribute("data-no-refresh")) await refreshPage();
    return data;
  } catch (error) {
    notice(error.message, "danger", errorBox(form));
    return null;
  } finally {
    button?.removeAttribute("disabled");
  }
}

if (typeof document !== "undefined" && !document.documentElement.dataset.fetchForms) {
  document.documentElement.dataset.fetchForms = "1";
  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.hasAttribute("data-fetch")) return;
    event.preventDefault();
    submitForm(form);
  });
}
