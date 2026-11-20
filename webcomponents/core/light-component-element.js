import { morph } from "./morph.js";
import { SharedShadowStyles } from "./shared-shadow-styles.js";

/**
 * Base class for components that render into the light DOM (no shadow root).
 *
 * Use it for components that compose other components and must stay
 * reachable for page styles, e.g. app-specific cards built from ui-card /
 * ui-table that the page theme styles via ::part() (::part() selectors of the
 * page do not reach into a nested shadow tree).
 *
 * Rendering is scheduled like ShadowComponentElement: attribute changes and
 * connection coalesce into one render per microtask. render() returns HTML
 * that replaces the element's children, so it is meant for data-driven
 * components without author content. The stylesheet (static stylesheet, an
 * absolute URL) is adopted into the document once.
 *
 * `static morph = true`: the children are patched with morph() (core/morph.js)
 * instead of replaced, for components rendered again on every live update:
 * unchanged nodes stay, so the height does not jump for a moment (the page
 * keeps its scroll position, also on iOS Safari without scroll anchoring) and
 * focus and open states stay. Listeners belong on the component (delegation),
 * not on rendered elements bound again in afterRender().
 */
export class LightComponentElement extends HTMLElement {
  static observedAttributes = [];
  static stylesheet = "";
  static morph = false;

  #renderScheduled = false;

  constructor() {
    super();
    this.hasRendered = false;
  }

  connectedCallback() {
    SharedShadowStyles.applyToDocument(this.constructor.stylesheet);
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
      if (!this.isConnected) {
        return;
      }
      const html = this.render();
      if (this.constructor.morph && this.hasRendered) {
        morph(this, html);
      } else {
        this.innerHTML = html;
      }
      this.hasRendered = true;
      this.afterRender();
    });
  }

  afterRender() {}

  render() {
    return "";
  }
}
