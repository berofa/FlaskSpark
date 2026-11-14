import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";

const DATA = new URL("./emoji.json", import.meta.url).href;
const RECENT_MAX = 32;
let loaded = null; // the emoji list, loaded once per page: [{group, emojis: [[emoji, name], …]}]

/** The categories: Unicode's group -> its tab icon and labels (de, en). */
const GROUPS = {
  "Smileys & Emotion": ["😀", "Smileys & Emotionen", "Smileys & Emotion"],
  "People & Body": ["👋", "Menschen & Körper", "People & Body"],
  "Animals & Nature": ["🐻", "Tiere & Natur", "Animals & Nature"],
  "Food & Drink": ["🍔", "Essen & Trinken", "Food & Drink"],
  "Travel & Places": ["🚗", "Reisen & Orte", "Travel & Places"],
  Activities: ["⚽", "Aktivitäten", "Activities"],
  Objects: ["💡", "Objekte", "Objects"],
  Symbols: ["🔣", "Symbole", "Symbols"],
  Flags: ["🏁", "Flaggen", "Flags"],
};
const TEXT = {
  de: { recent: "Zuletzt verwendet", search: "Emoji suchen (englisch)", none: "Kein Emoji gefunden." },
  en: { recent: "Recently used", search: "Search emoji", none: "No emoji found." },
};

/** Words of a query that all occur in a name (Unicode's English names). Exported for the tests. */
export function matches(name, query) {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  const hay = name.toLowerCase();
  return words.every((w) => hay.includes(w));
}

/** The recently used list after picking `emoji` (newest first, no duplicates, at most `max`). */
export function remember(recent, emoji, max = RECENT_MAX) {
  return [emoji, ...recent.filter((e) => e !== emoji)].slice(0, max);
}

/**
 * <ui-emoji-picker>: all emojis of Unicode (fully qualified, without skin tone variants) in categories like a phone's
 * keyboard: a tab per category, «recently used» first (kept in localStorage), a search over the English names.
 *
 * Attributes:
 * - storage-key: the localStorage key of the recently used ones (default "ui-emoji-picker:recent"; a page with
 *   several pickers for different purposes may give each its own).
 * - lang (or the closest [lang]): "de" for German labels, else English.
 *
 * Event: ui-emoji-picker:pick (bubbles, composed) with detail.emoji. The list (emoji.json, generated from Unicode's
 * emoji-test.txt) loads on first use. Parts: picker, tabs, search, grid.
 */
export class UiEmojiPicker extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-emoji-picker.css", import.meta.url).href];
  static observedAttributes = ["lang"];

  #groups = null;
  #group = "recent";
  #query = "";
  #wired = false;

  get #text() {
    const lang = (this.closest("[lang]")?.getAttribute("lang") || "en").slice(0, 2).toLowerCase();
    return TEXT[lang] ? { ...TEXT[lang], de: lang === "de" } : { ...TEXT.en, de: false };
  }

  get #key() {
    return this.getAttribute("storage-key") || "ui-emoji-picker:recent";
  }

  #recent() {
    try {
      const list = JSON.parse(localStorage.getItem(this.#key) || "[]");
      return Array.isArray(list) ? list.filter((e) => typeof e === "string") : [];
    } catch {
      return []; // private mode, blocked storage
    }
  }

  render() {
    const t = this.#text;
    return `
      <div class="emoji-picker" part="picker">
        <input class="form-control form-control-sm emoji-search" part="search" type="search" placeholder="${escapeHtml(t.search)}"
          aria-label="${escapeHtml(t.search)}" value="${escapeHtml(this.#query)}">
        <div class="emoji-tabs" part="tabs" role="tablist" data-tabs></div>
        <div class="emoji-grid" part="grid" data-grid aria-live="polite"></div>
      </div>`;
  }

  async afterRender() {
    if (!this.#wired) {
      this.#wired = true;
      this.shadowRoot.addEventListener("click", (e) => {
        const el = e.composedPath().find((n) => n instanceof Element && (n.dataset?.emoji || n.dataset?.group));
        if (!el) return;
        if (el.dataset.group) {
          this.#group = el.dataset.group;
          this.#query = "";
          this.#paint();
          return;
        }
        this.#pick(el.dataset.emoji);
      });
      this.shadowRoot.addEventListener("input", (e) => {
        if (!e.target.matches?.(".emoji-search")) return;
        this.#query = e.target.value.trim();
        this.#paint();
      });
    }
    this.#groups = await (loaded ??= fetch(DATA).then((r) => r.json()).catch(() => []));
    if (this.#group === "recent" && !this.#recent().length) this.#group = this.#groups[0]?.group || "recent";
    this.#paint();
  }

  #pick(emoji) {
    try {
      localStorage.setItem(this.#key, JSON.stringify(remember(this.#recent(), emoji)));
    } catch { /* no storage: nothing remembered */ }
    this.dispatchEvent(new CustomEvent("ui-emoji-picker:pick", { bubbles: true, composed: true, detail: { emoji } }));
  }

  #label(group) {
    const t = this.#text;
    if (group === "recent") return t.recent;
    const g = GROUPS[group];
    return g ? g[t.de ? 1 : 2] : group;
  }

  #paint() {
    const tabs = this.shadowRoot.querySelector("[data-tabs]");
    const grid = this.shadowRoot.querySelector("[data-grid]");
    if (!tabs || !grid || !this.#groups) return;
    const recent = this.#recent();
    const groups = [...(recent.length ? ["recent"] : []), ...this.#groups.map((g) => g.group)];
    tabs.innerHTML = groups.map((g) => {
      const active = !this.#query && g === this.#group;
      const iconOf = g === "recent" ? "🕘" : GROUPS[g]?.[0] || "•";
      return `<button type="button" role="tab" class="emoji-tab${active ? " active" : ""}" aria-selected="${active}"
        data-group="${escapeHtml(g)}" title="${escapeHtml(this.#label(g))}" aria-label="${escapeHtml(this.#label(g))}">${iconOf}</button>`;
    }).join("");
    let list;
    let heading;
    if (this.#query) {
      list = this.#groups.flatMap((g) => g.emojis).filter(([, name]) => matches(name, this.#query));
      heading = "";
    } else if (this.#group === "recent") {
      list = recent.map((e) => [e, ""]);
      heading = this.#label("recent");
    } else {
      list = this.#groups.find((g) => g.group === this.#group)?.emojis || [];
      heading = this.#label(this.#group);
    }
    grid.innerHTML = (heading ? `<div class="emoji-heading">${escapeHtml(heading)}</div>` : "")
      + (list.map(([e, name]) => `<button type="button" class="emoji" data-emoji="${escapeHtml(e)}" title="${escapeHtml(name)}"
        aria-label="${escapeHtml(name || e)}">${e}</button>`).join("")
      || `<div class="emoji-none">${escapeHtml(this.#text.none)}</div>`);
    grid.scrollTop = 0;
  }
}

registerComponent("ui-emoji-picker", UiEmojiPicker);
