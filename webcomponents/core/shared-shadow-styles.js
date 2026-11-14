/**
 * Loads component stylesheets once and shares them across all shadow roots.
 *
 * Stylesheets are addressed by URL; components resolve theirs relative to
 * their own module (import.meta.url), so no base path configuration is needed.
 * A stylesheet is either a URL or `{ url, transform }`: the transform gets the
 * constructed CSSStyleSheet once (e.g. stripRootTokenRules for the shared
 * Bootstrap copy) and every shadow root adopts the transformed sheet.
 * Uses constructable stylesheets (adoptedStyleSheets) when available and
 * falls back to a <style> element per shadow root otherwise (without transforms).
 */
export class SharedShadowStyles {
  static cssTextPromises = new Map();
  static sheetPromises = new Map();
  static documentSheets = new Map();

  static async getCssText(stylesheetUrl) {
    if (!this.cssTextPromises.has(stylesheetUrl)) {
      this.cssTextPromises.set(stylesheetUrl, fetch(stylesheetUrl).then((response) => {
        if (!response.ok) {
          throw new Error(`Unable to load component stylesheet: ${response.status}`);
        }
        return response.text();
      }));
    }

    return this.cssTextPromises.get(stylesheetUrl);
  }

  static normalize(stylesheets) {
    const list = Array.isArray(stylesheets) ? stylesheets : [stylesheets];
    return list
      .filter(Boolean)
      .map((entry) => (typeof entry === "string" ? { url: entry, transform: null } : entry))
      .filter((entry) => entry.url);
  }

  static getSheet({ url, transform }) {
    const key = transform ? `${url}#${transform.name}` : url;
    if (!this.sheetPromises.has(key)) {
      this.sheetPromises.set(key, this.getCssText(url).then(async (cssText) => {
        const sheet = new CSSStyleSheet();
        await sheet.replace(cssText);
        transform?.(sheet);
        return sheet;
      }));
    }
    return this.sheetPromises.get(key);
  }

  static async apply(shadowRoot, stylesheets) {
    const entries = this.normalize(stylesheets);
    if (!entries.length) {
      return;
    }
    if ("adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype) {
      shadowRoot.adoptedStyleSheets = await Promise.all(entries.map((entry) => this.getSheet(entry)));
      return;
    }

    for (const { url } of [...entries].reverse()) {
      if (!shadowRoot.querySelector(`style[data-shared-shadow-style="${url}"]`)) {
        const style = document.createElement("style");
        style.dataset.sharedShadowStyle = url;
        style.textContent = await this.getCssText(url);
        shadowRoot.prepend(style);
      }
    }
  }

  /**
   * Adopt a stylesheet into the document once (for light-DOM components).
   * Appended after the page's own sheets, so it wins at equal specificity.
   */
  static applyToDocument(stylesheetUrl) {
    if (!stylesheetUrl) {
      return Promise.resolve();
    }
    if (!this.documentSheets.has(stylesheetUrl)) {
      this.documentSheets.set(stylesheetUrl, this.getCssText(stylesheetUrl).then(async (cssText) => {
        if ("adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype) {
          const sheet = new CSSStyleSheet();
          await sheet.replace(cssText);
          document.adoptedStyleSheets = [...document.adoptedStyleSheets, sheet];
          return;
        }
        const style = document.createElement("style");
        style.dataset.sharedDocumentStyle = stylesheetUrl;
        style.textContent = cssText;
        document.head.append(style);
      }));
    }
    return this.documentSheets.get(stylesheetUrl);
  }
}
