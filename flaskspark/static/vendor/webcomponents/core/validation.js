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
