/**
 * The locale of <ui-calendar>: the full language tag for the date formats (e.g. "en-CH": days as 04.11. or 04/11,
 * not the US order) and the first day of the week. Pure functions, without the DOM (tested with node).
 */

/** Weekday names for the attribute first-day (0 = Sunday, as FullCalendar's firstDay). */
const WEEKDAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];

/** Regions that start the week on Sunday, for browsers without Intl.Locale week info (CLDR, the common ones). */
const SUNDAY_REGIONS = new Set(["US", "CA", "MX", "BR", "JP", "KR", "TW", "HK", "IL", "PH", "IN", "ZA", "SA",
  "PE", "CO", "VE", "GT", "HN", "NI", "PA", "SV", "DO", "PR", "PY", "BO", "KE", "ZW", "TH", "ID", "PK", "BD"]);

/** `tag` as a canonical BCP 47 language tag ("en_ch" -> "en-CH"), "en" when it is empty or invalid. */
export function canonicalLocale(tag) {
  const text = String(tag || "").trim().replace(/_/g, "-");
  if (!text) return "en";
  try {
    return Intl.getCanonicalLocales(text)[0] || "en";
  } catch {
    return "en";
  }
}

/** The first day of the week of `locale` (0 = Sunday, 1 = Monday, …): from Intl.Locale's week info where the browser
 *  has it, else by the region (a language without one: "en" -> Sunday as en-US, the others Monday). */
export function localeFirstDay(locale) {
  const tag = canonicalLocale(locale);
  try {
    const loc = new Intl.Locale(tag);
    const info = typeof loc.getWeekInfo === "function" ? loc.getWeekInfo() : loc.weekInfo;
    if (info && Number.isInteger(info.firstDay)) return info.firstDay % 7; // Intl: 1 = Monday … 7 = Sunday
  } catch {
    // fall through to the table
  }
  const [language, ...rest] = tag.split("-");
  const region = rest.find((part) => /^([A-Z]{2}|\d{3})$/.test(part));
  if (!region) return language === "en" ? 0 : 1;
  return SUNDAY_REGIONS.has(region) ? 0 : 1;
}

/** The attribute first-day as 0 (Sunday) … 6 (Saturday): a number (7 is Sunday too) or an English weekday name
 *  ("monday", "mon"); null when it is missing or invalid (then the locale decides). */
export function parseFirstDay(value) {
  const text = String(value ?? "").trim().toLowerCase();
  if (!text) return null;
  if (/^\d+$/.test(text)) {
    const n = Number(text);
    return n <= 7 ? n % 7 : null;
  }
  const index = WEEKDAYS.findIndex((day) => day === text || (text.length >= 3 && day.startsWith(text)));
  return index >= 0 ? index : null;
}

/** The first day of the week: the attribute first-day, else that of the locale. */
export function firstDayOf(attribute, locale) {
  return parseFirstDay(attribute) ?? localeFirstDay(locale);
}
