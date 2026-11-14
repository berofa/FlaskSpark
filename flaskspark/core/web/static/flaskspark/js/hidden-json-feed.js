/**
 * <hidden-json-feed>: loads JSON once and shares it with any number of components, so a page with ten consumers still
 * makes one request.
 *
 *   import "flaskspark/hidden-json-feed.js";
 *   <hidden-json-feed id="stats" src="/api/stats" push-topics="demo.state" interval="60"></hidden-json-feed>
 *   document.getElementById("stats").subscribe((data) => render(data));
 *
 * Attributes:
 * - src: URL (requested with Accept: application/json).
 * - interval: reload every n seconds (0 or missing: load once). With push-topics only while the live channel is not
 *   open (the fallback).
 * - push-topics: reload when the server pushes one of these topics (space-separated, see flaskspark/push-channel.js;
 *   "{user}" is the signed-in user), instead of polling. Events in quick succession make one reload (push-delay ms,
 *   default 300); an event during a load reloads once more after it; after the channel reconnects (events may be
 *   missing) it reloads once.
 * - select: dot path into the response (e.g. "summary"); subscribers get only that part.
 *
 * Initial data can be embedded to skip the first request (the same shape as the response; select applies):
 *   <hidden-json-feed src="/api/stats"><script type="application/json">{"…": …}</script></hidden-json-feed>
 *
 * Script API: subscribe(callback) -> unsubscribe (the callback runs at once when data is present), refresh(), data.
 * Event: hidden-json-feed:update (detail: { data }). Never displayed (hidden is set on connect).
 */
import { registerComponent } from "webcomponents/core/registry.js";
import { readEmbeddedJson } from "webcomponents/core/feeds.js";
import { pushChannel } from "flaskspark/push-channel.js";

export class HiddenJsonFeed extends HTMLElement {
  #data;
  #listeners = new Set();
  #timer = null;
  #loading = null;
  #again = false;
  #pushOff = [];
  #pushTimer = null;
  #onResync = () => this.refresh();

  connectedCallback() {
    this.hidden = true;
    const topics = (this.getAttribute("push-topics") || "").split(/\s+/).filter(Boolean);
    if (topics.length && !this.#pushOff.length) {
      const channel = pushChannel();
      this.#pushOff = topics.map((topic) => channel.subscribe(topic, () => this.#pushed()));
      channel.addEventListener("resync", this.#onResync);
      this.#pushOff.push(() => channel.removeEventListener("resync", this.#onResync));
    }
    const embedded = readEmbeddedJson(this);
    if (embedded !== undefined) {
      this.#set(embedded);
    } else {
      this.refresh();
    }
    const interval = Number(this.getAttribute("interval")) || 0;
    if (interval > 0 && !this.#timer) {
      this.#timer = setInterval(() => {
        if (!this.#pushOff.length || pushChannel().state !== "open") this.refresh();
      }, interval * 1000);
    }
  }

  disconnectedCallback() {
    clearInterval(this.#timer);
    this.#timer = null;
    clearTimeout(this.#pushTimer);
    this.#pushOff.forEach((off) => off());
    this.#pushOff = [];
  }

  #pushed() {
    clearTimeout(this.#pushTimer);
    this.#pushTimer = setTimeout(() => this.refresh(), Number(this.getAttribute("push-delay") ?? 300));
  }

  get data() {
    return this.#data;
  }

  subscribe(callback) {
    this.#listeners.add(callback);
    if (this.#data !== undefined) callback(this.#data);
    return () => this.#listeners.delete(callback);
  }

  refresh() {
    const src = this.getAttribute("src");
    if (this.#loading) {
      this.#again = true; // something changed while loading: the answer may be older, load again after it
      return this.#loading;
    }
    if (!src) return this.#loading;
    this.#loading = fetch(src, { headers: { Accept: "application/json" }, credentials: "same-origin" })
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`))))
      .then((json) => this.#set(json))
      .catch((error) => console.warn(`hidden-json-feed ${src}:`, error))
      .finally(() => {
        this.#loading = null;
        if (this.#again) {
          this.#again = false;
          this.refresh();
        }
      });
    return this.#loading;
  }

  #set(json) {
    const path = (this.getAttribute("select") || "").split(".").filter(Boolean);
    this.#data = path.reduce((value, key) => (value == null ? value : value[key]), json);
    for (const callback of this.#listeners) callback(this.#data);
    this.dispatchEvent(new CustomEvent("hidden-json-feed:update", { detail: { data: this.#data } }));
  }
}

registerComponent("hidden-json-feed", HiddenJsonFeed);
