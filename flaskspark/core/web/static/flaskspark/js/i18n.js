/*
 * Translations for scripts, in the page's language (the catalogues of the core, the modules and the app, merged):
 *
 *   import { t, nt, preload, preloadCatalog } from "flaskspark/i18n.js";
 *   t("Saved");                                   // the page's module's texts are there at once (the layout)
 *   t("{n} of {total}", { n: 3, total: 7 });      // {name} placeholders
 *   nt("{n} file", "{n} files", count);           // the plural for count ({n} and {num} are count)
 *   await preloadCatalog("calendar");             // every text of another module ("core", "app" too)
 *   await preload(["Saved", ["{n} file", "{n} files"]]);   // single texts and plurals ([singular, plural])
 *
 * The layout puts the catalogue of the page's module into the page (<script type="application/json"
 * id="flaskspark-i18n">, a page names others with {% set i18n_modules = [...] %}); t() and nt() use it without asking
 * the server. Other texts come through POST /api/i18n (texts may contain commas) and /api/i18n/catalog, once each.
 * A text without a translation stays the English source text.
 */
const cache = new Map();          // source text -> translation
const pluralForms = new Map();    // singular -> [form for index 0, 1, ...]
const loadedParts = new Set();    // catalogues fetched or found in the page
let pluralIndex = (n) => (n === 1 ? 0 : 1);   // English's rule until a catalogue names the page's


/*
 * A gettext plural expression ("(n != 1)", "n%10==1 && n%100!=11 ? 0 : …") as a function n -> index, parsed (no
 * eval: the page's content security policy may forbid it). An expression it can't read gives English's rule.
 */
export function compilePlural(expression) {
  const tokens = String(expression).match(/\d+|n|&&|\|\||[=!<>]=|[-+*/%<>!?:()]/g) || [];
  const rest = String(expression).replace(/\d+|n|&&|\|\||[=!<>]=|[-+*/%<>!?:()]|\s+/g, "");
  if (rest || !tokens.length) return (n) => (n === 1 ? 0 : 1);
  let position = 0;
  const peek = () => tokens[position];
  const next = () => tokens[position++];
  const binary = (operators, lower) => () => {
    let left = lower();
    while (operators.includes(peek())) {
      const operator = next();
      const right = lower();
      const l = left;
      left = (n) => {
        const a = l(n);
        const b = right(n);
        switch (operator) {
          case "||": return a || b ? 1 : 0;
          case "&&": return a && b ? 1 : 0;
          case "==": return a === b ? 1 : 0;
          case "!=": return a !== b ? 1 : 0;
          case "<": return a < b ? 1 : 0;
          case ">": return a > b ? 1 : 0;
          case "<=": return a <= b ? 1 : 0;
          case ">=": return a >= b ? 1 : 0;
          case "+": return a + b;
          case "-": return a - b;
          case "*": return a * b;
          case "/": return b ? Math.trunc(a / b) : 0;
          default: return b ? a % b : 0;
        }
      };
    }
    return left;
  };
  let ternary;
  const primary = () => {
    const token = next();
    if (token === "n") return (n) => n;
    if (token === "(") {
      const inner = ternary();
      if (next() !== ")") throw new Error("plural: ) expected");
      return inner;
    }
    if (token === "!") {
      const operand = primary();
      return (n) => (operand(n) ? 0 : 1);
    }
    if (token === "-") {
      const operand = primary();
      return (n) => -operand(n);
    }
    if (/^\d+$/.test(token ?? "")) {
      const value = Number(token);
      return () => value;
    }
    throw new Error(`plural: unexpected ${token}`);
  };
  const multiplicative = binary(["*", "/", "%"], primary);
  const additive = binary(["+", "-"], multiplicative);
  const relational = binary(["<", ">", "<=", ">="], additive);
  const equality = binary(["==", "!="], relational);
  const and = binary(["&&"], equality);
  const or = binary(["||"], and);
  ternary = () => {
    const condition = or();
    if (peek() !== "?") return condition;
    next();
    const yes = ternary();
    if (next() !== ":") throw new Error("plural: : expected");
    const no = ternary();
    return (n) => (condition(n) ? yes(n) : no(n));
  };
  try {
    const parsed = ternary();
    if (position !== tokens.length) throw new Error("plural: trailing tokens");
    return (n) => Number(parsed(Math.abs(Math.trunc(Number(n) || 0))));
  } catch {
    return (n) => (n === 1 ? 0 : 1);
  }
}

/* A catalogue ({language, plural, texts, plurals}, from the page or the server) into the cache. */
export function absorb(data) {
  if (!data || typeof data !== "object") return;
  for (const [key, value] of Object.entries(data.texts || {})) cache.set(key, value ?? key);
  for (const [key, forms] of Object.entries(data.plurals || {})) if (Array.isArray(forms)) pluralForms.set(key, forms);
  if (data.plural) pluralIndex = compilePlural(data.plural);
}

function fromPage() {
  if (typeof document === "undefined") return;
  const element = document.getElementById("flaskspark-i18n");
  if (!element) return;
  try {
    absorb(JSON.parse(element.textContent || "{}"));
  } catch {
    // a broken catalogue: the texts ask the server
  }
}
fromPage();

async function post(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${url}: ${response.status}`);
  return response.json();
}

/* Texts (strings) and plurals ([singular, plural]) the page needs, fetched once each. */
export async function preload(keys) {
  const texts = keys.filter((k) => typeof k === "string" && !cache.has(k));
  const pairs = keys.filter((k) => Array.isArray(k) && k.length === 2 && !pluralForms.has(k[0]));
  if (!texts.length && !pairs.length) return;
  try {
    if (pairs.length) {
      absorb(await post("/api/i18n/catalog", { keys: texts, plurals: pairs }));
      for (const key of texts) if (!cache.has(key)) cache.set(key, key);
    } else {
      const data = await post("/api/i18n", { keys: texts });
      for (const key of texts) cache.set(key, data[key] ?? key);
    }
  } catch {
    for (const key of texts) cache.set(key, key);
  }
}

/* Every text of the catalogues of these parts (module names, "core", "app"), fetched once each. */
export async function preloadCatalog(...parts) {
  const missing = parts.flat().filter((p) => p && !loadedParts.has(p));
  if (!missing.length) return;
  try {
    const query = encodeURIComponent(missing.join(","));
    const response = await fetch(`/api/i18n/catalog?modules=${query}`, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(String(response.status));
    absorb(await response.json());
    for (const part of missing) loadedParts.add(part);
  } catch {
    // not reachable: the source texts (t() and nt() never fail)
  }
}

function fill(text, params) {
  for (const [name, value] of Object.entries(params)) text = text.replaceAll(`{${name}}`, String(value));
  return text;
}

export function t(key, params = {}) {
  return fill(cache.has(key) ? cache.get(key) : key, params);
}

/* The singular or plural text for n in the page's language; {n} and {num} are n unless params name them. */
export function nt(singular, plural, n, params = {}) {
  const forms = pluralForms.get(singular);
  let text;
  if (forms && forms.length) {
    const index = pluralIndex(n);
    text = forms[Math.min(Math.max(index, 0), forms.length - 1)];
  } else {
    text = n === 1 ? singular : plural;
  }
  return fill(text, { n, num: n, ...params });
}
