/**
 * The messages of invalid form values (FormControlElement): German, short, from the native validity and the
 * stricter email rule (a domain with a dot: «a@b» is no address one can write to).
 */

const MESSAGES = {
  valueMissing: "Pflichtfeld",
  typeMismatch: { email: "Keine gültige E-Mail-Adresse", url: "Keine gültige Adresse (https://…)", default: "Ungültige Eingabe" },
  patternMismatch: "Ungültige Eingabe",
  tooShort: "Zu kurz",
  tooLong: "Zu lang",
  rangeUnderflow: "Zu klein",
  rangeOverflow: "Zu gross",
  stepMismatch: "Ungültiger Wert",
  badInput: "Ungültige Eingabe",
};

export const EMAIL = /^[^\s@]+@[^\s@.]+(\.[^\s@.]+)*\.[^\s@.]{2,}$/;

/** "" when valid, else the message (validity: a ValidityState or a plain object with its flags). */
export function validationMessage(validity, type = "text", value = "") {
  for (const key of Object.keys(MESSAGES)) {
    if (validity?.[key]) {
      const m = MESSAGES[key];
      return typeof m === "string" ? m : m[type] || m.default;
    }
  }
  if (type === "email" && String(value || "").trim() && !EMAIL.test(String(value).trim())) return MESSAGES.typeMismatch.email;
  return "";
}

/**
 * Bootstrap 6's validation opt-in: client-side feedback only inside an element with data-bs-validate (usually
 * the form; the attribute may also sit on the control or any ancestor). "valid" in its value (data-bs-validate=
 * "valid") also shows valid fields. Returns null without opt-in, else { valid }.
 * `element`: the control's host (in the page); `form`: its form, also when the form is not an ancestor.
 */
export function validationMode(element, form = null) {
  const scope = element?.closest?.("[data-bs-validate]") || (form?.matches?.("[data-bs-validate]") ? form : null);
  if (!scope) return null;
  const tokens = String(scope.getAttribute("data-bs-validate") || "").split(/\s+/);
  return { valid: tokens.includes("valid") };
}

/**
 * Calls `onAttempt` when someone tries to submit `form` (like :user-invalid, the feedback then shows on every
 * control): on submit (also with novalidate) and on the invalid event of a blocked submission. Returns a function
 * that stops listening.
 */
export function onSubmitAttempt(form, element, onAttempt) {
  if (!form) return () => {};
  const submit = () => onAttempt();
  form.addEventListener("submit", submit, true);
  element.addEventListener("invalid", submit);
  return () => {
    form.removeEventListener("submit", submit, true);
    element.removeEventListener("invalid", submit);
  };
}
