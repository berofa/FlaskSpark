/**
 * <hidden-push-fragment push-topics="demo.state" target="#notes">: keeps a part of a server-rendered page current
 * without reloading it. When the server pushes one of the topics (and after the live channel reconnected), it loads
 * the page's URL in the background and replaces the content of `target` with that of the same element in the answer
 * (morph: only what changed). Everything outside `target` (forms, scroll position, open dialogs) stays untouched.
 *
 *   import "flaskspark/hidden-push-fragment.js";
 *
 * Attributes:
 * - push-topics: space-separated topics (see flaskspark/push-channel.js; "{user}" is the signed-in user).
 * - target: CSS selector of the part to replace (an element with an id is best).
 * - src: URL to load (default: the page's own URL).
 * - push-delay: ms to wait for more events before loading (default 300).
 *
 * Skips the update while the focus is inside the target (someone is typing there) and does it once the focus leaves.
 * Script API: refresh(). Event: hidden-push-fragment:update (detail: { target }). Never displayed.
 */
import { registerComponent } from "webcomponents/core/registry.js";
import { morph } from "webcomponents/core/morph.js";
import { pushChannel } from "flaskspark/push-channel.js";

export class HiddenPushFragment extends HTMLElement {
  #offs = [];
  #timer = null;
  #loading = null;
  #again = false;
  #onResync = () => this.refresh();

  connectedCallback() {
    this.hidden = true;
    if (this.#offs.length) return;
    const channel = pushChannel();
    const topics = (this.getAttribute("push-topics") || "").split(/\s+/).filter(Boolean);
    this.#offs = topics.map((topic) => channel.subscribe(topic, () => this.#pushed()));
    channel.addEventListener("resync", this.#onResync);
    this.#offs.push(() => channel.removeEventListener("resync", this.#onResync));
  }

  disconnectedCallback() {
    clearTimeout(this.#timer);
    this.#offs.forEach((off) => off());
    this.#offs = [];
  }

  #pushed() {
    clearTimeout(this.#timer);
    this.#timer = setTimeout(() => this.refresh(), Number(this.getAttribute("push-delay") ?? 300));
  }

  async refresh() {
    if (this.#loading) {
      this.#again = true;
      return this.#loading;
    }
    const selector = this.getAttribute("target");
    const target = selector && document.querySelector(selector);
    if (!target) return undefined;
    if (target.contains(document.activeElement) && document.activeElement !== document.body) {
      // Someone is typing in there: once the focus leaves.
      target.addEventListener("focusout", () => this.#pushed(), { once: true });
      return undefined;
    }
    this.#loading = fetch(this.getAttribute("src") || location.href, { headers: { Accept: "text/html" }, credentials: "same-origin" })
      .then((response) => (response.ok ? response.text() : Promise.reject(new Error(`HTTP ${response.status}`))))
      .then((html) => {
        const fresh = new DOMParser().parseFromString(html, "text/html").querySelector(selector);
        if (!fresh) return;
        morph(target, fresh.innerHTML);
        this.dispatchEvent(new CustomEvent("hidden-push-fragment:update", { detail: { target } }));
      })
      .catch((error) => console.warn(`hidden-push-fragment ${selector}:`, error))
      .finally(() => {
        this.#loading = null;
        if (this.#again) {
          this.#again = false;
          this.refresh();
        }
      });
    return this.#loading;
  }
}

registerComponent("hidden-push-fragment", HiddenPushFragment);
