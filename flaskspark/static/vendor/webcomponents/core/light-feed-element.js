import { LightComponentElement } from "./light-component-element.js";
import { findFeed } from "./feeds.js";

/**
 * Light-DOM component bound to a feed element of the app (anything with subscribe(callback) -> unsubscribe) via
 * its "feed" attribute (element id). Every feed update stores the data in
 * `this.data` and re-renders; subclasses implement renderData(data).
 */
export class LightFeedElement extends LightComponentElement {
  static observedAttributes = ["feed"];

  data = undefined;
  #unsubscribe = null;
  #feedId = null;

  connectedCallback() {
    super.connectedCallback();
    this.#connect();
  }

  disconnectedCallback() {
    this.#unsubscribe?.();
    this.#unsubscribe = null;
    this.#feedId = null;
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "feed" && this.isConnected) {
      this.#connect();
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  async #connect() {
    const id = this.getAttribute("feed");
    if (id === this.#feedId) return;
    this.#feedId = id;
    this.#unsubscribe?.();
    this.#unsubscribe = null;
    const feed = await findFeed(id);
    if (!feed || this.#feedId !== id || !this.isConnected) return;
    this.#unsubscribe = feed.subscribe((data) => {
      this.data = data;
      this.requestRender();
    });
  }

  render() {
    return this.data == null ? this.renderEmpty() : this.renderData(this.data);
  }

  renderEmpty() {
    return "";
  }

  renderData() {
    return "";
  }
}
