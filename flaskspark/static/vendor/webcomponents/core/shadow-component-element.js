import { SharedShadowStyles } from "./shared-shadow-styles.js";

/**
 * Base class for shadow DOM components.
 *
 * Rendering is scheduled instead of executed directly: attribute changes and
 * connection coalesce into a single mount per microtask, and a mount token
 * guards against interleaved async mounts (styles load asynchronously, so a
 * stale mount could otherwise overwrite a newer one).
 */
export class ShadowComponentElement extends HTMLElement {
  static observedAttributes = [];
  /**
   * Absolute URL of the component stylesheet, resolved next to the component
   * module: static stylesheet = new URL("./ui-x.css", import.meta.url).href
   */
  static stylesheet = "";
  /**
   * Several stylesheets in cascade order (URLs or { url, transform }), e.g. the
   * shared Bootstrap copy and the component's own CSS. Takes precedence over
   * `stylesheet`.
   */
  static stylesheets = null;
  /**
   * Stylesheet adopted into the document once (URL), for the component's
   * slotted content: Bootstrap styles direct children (`.alert > p`,
   * `.card-body > *`), which only a page-level rule like `ui-alert > p` can
   * mirror. Wrap the rules in `@layer components` so they rank like Bootstrap's.
   */
  static documentStylesheet = "";

  #renderScheduled = false;
  #mountToken = 0;

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.hasRendered = false;
  }

  connectedCallback() {
    SharedShadowStyles.applyToDocument(this.constructor.documentStylesheet);
    this.requestRender();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue === newValue) {
      return;
    }
    this.requestRender();
  }

  requestRender() {
    if (!this.isConnected || this.#renderScheduled) {
      return;
    }
    this.#renderScheduled = true;
    queueMicrotask(() => {
      this.#renderScheduled = false;
      this.mount();
    });
  }

  async mount() {
    if (!this.shadowRoot || !this.isConnected) {
      return;
    }

    const token = ++this.#mountToken;
    await SharedShadowStyles.apply(this.shadowRoot, this.constructor.stylesheets ?? this.constructor.stylesheet);
    if (token !== this.#mountToken || !this.isConnected) {
      return;
    }

    this.renderShadow();
    this.hasRendered = true;
    this.afterRender();
  }

  renderShadow() {
    // innerHTML wipes the <style> fallback used by browsers without
    // adoptedStyleSheets support, so re-attach it after rendering.
    const fallbackStyle = this.shadowRoot.querySelector("style[data-shared-shadow-style]");
    this.shadowRoot.innerHTML = this.render();
    if (fallbackStyle) {
      this.shadowRoot.prepend(fallbackStyle);
    }
  }

  afterRender() {}

  render() {
    return "";
  }
}
