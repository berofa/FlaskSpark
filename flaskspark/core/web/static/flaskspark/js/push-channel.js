/**
 * pushChannel(): live data the server pushes (flaskspark.core push service), as Server-Sent Events.
 *
 *   import { pushChannel } from "flaskspark/push-channel.js";
 *   const channel = pushChannel();                 // same origin: GET /events, POST /events/sub
 *   const off = channel.subscribe("notes.state", (data, topic) => …);
 *   channel.addEventListener("resync", () => reloadMyData());  // after a reconnect: events may be missing
 *   channel.addEventListener("status", (e) => show(e.detail.state));
 *
 * - One event stream per tab (EventSource): plain HTTP, over HTTP/2 inside the page's connection. No connection
 *   of its own, so nothing a browser queues or throttles the way it does with WebSockets.
 * - Topics are shared: ten components on one topic make one subscription; the last unsubscribe ends it.
 *   Subscriptions go to the server with POST /events/sub (collected, one request per task). A new subscription
 *   gets the topic's latest update at once.
 * - The server greets every stream with "hello" {user, stream}; on every hello (a reconnect too) the channel
 *   subscribes all its topics again, and after a reconnect it fires "resync" (events may be missing).
 * - Reconnects: the browser reconnects a broken stream by itself; a stream refused outright (no 200) is tried
 *   again with a growing pause (1 s … 30 s), unless the session URL says the user is signed out. A stream silent
 *   for longer than SILENT ms (the server pings every 15 s) is opened anew.
 * - Signed out ("signed-out" from the server, or a refused stream and the session URL answers 401): state
 *   "signed-out", no more reconnects (the page has to sign in again).
 * - States: "connecting", "open", "closed" (reconnecting), "signed-out", "stopped" (close()). The current
 *   one: channel.state.
 * - Who is signed in: channel.user (from the hello, null before), event "hello". Topics may name the user as
 *   {user} (e.g. "ev.user.{user}.notes"): subscribe() waits for the hello to fill it in.
 * - Leaving the page (pagehide) closes the stream; back from the back-forward cache (pageshow) it opens again.
 * - Diagnosis: a stream refused before it opened is a console warning; attempts and openings are console.debug.
 *
 * Options of pushChannel(options) (the first call of a page decides): url (default /events), sessionUrl (default
 * /api/push/session: asked when a stream is refused, to tell a lost session from an outage).
 */

const SILENT = 45000;
const channels = new Map();
const inPage = typeof window !== "undefined" && typeof document !== "undefined";

export function pushChannel(options = {}) {
  const url = options.url || "/events";
  if (!channels.has(url)) channels.set(url, new PushChannel(url, options));
  return channels.get(url);
}

export class PushChannel extends EventTarget {
  #url;
  #sessionUrl;
  #source = null;
  #stream = null; // id of the open stream (from its hello), for /events/sub
  #listeners = new Map(); // topic -> Set(callback)
  #pending = { sub: new Set(), unsub: new Set() };
  #flushQueued = false;
  #state = "connecting";
  #user = null;
  #pause = 1000;
  #everOpened = false;
  #retryTimer = null;
  #watchdog = null;
  #heard = 0;
  #started = 0;
  #stopped = false;
  #suspended = false;

  constructor(url = "/events", { sessionUrl = "/api/push/session", page = inPage } = {}) {
    super();
    this.#url = url;
    this.#sessionUrl = sessionUrl;
    if (page) {
      window.addEventListener("pagehide", () => this.#suspend());
      window.addEventListener("pageshow", (event) => {
        if (event.persisted) this.#resume();
      });
    }
    this.#connect();
  }

  get state() {
    return this.#state;
  }

  get user() {
    return this.#user;
  }

  /** Ends the channel for good: no reconnects. */
  close() {
    this.#stopped = true;
    this.#drop();
    this.#setState("stopped");
  }

  subscribe(topic, callback) {
    if (topic.includes("{user}")) {
      // Wait for the hello that names the user, then subscribe the topic it gives.
      let off = null;
      let cancelled = false;
      const go = () => {
        if (!cancelled && !off) off = this.subscribe(topic.replaceAll("{user}", this.#user), callback);
      };
      if (this.#user !== null) go();
      else this.addEventListener("hello", go, { once: true });
      return () => {
        cancelled = true;
        this.removeEventListener("hello", go);
        off?.();
      };
    }
    let set = this.#listeners.get(topic);
    if (!set) {
      set = new Set();
      this.#listeners.set(topic, set);
      this.#want("sub", topic);
    }
    set.add(callback);
    return () => {
      set.delete(callback);
      if (!set.size && this.#listeners.get(topic) === set) {
        this.#listeners.delete(topic);
        this.#want("unsub", topic);
      }
    };
  }

  // --- subscriptions ----------------------------------------------------------------------------------------

  #want(op, topic) {
    const other = op === "sub" ? "unsub" : "sub";
    if (this.#pending[other].has(topic)) this.#pending[other].delete(topic);
    else this.#pending[op].add(topic);
    if (!this.#flushQueued) {
      this.#flushQueued = true;
      queueMicrotask(() => this.#flush());
    }
  }

  /** The collected (un)subscriptions in one request; nothing while there is no stream (the hello sends all). */
  async #flush() {
    this.#flushQueued = false;
    const stream = this.#stream;
    if (!stream || (!this.#pending.sub.size && !this.#pending.unsub.size)) return;
    const body = { stream, sub: [...this.#pending.sub], unsub: [...this.#pending.unsub] };
    this.#pending = { sub: new Set(), unsub: new Set() };
    try {
      const response = await fetch(`${this.#url}/sub`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(body),
      });
      if (response.status === 404 && stream === this.#stream) this.#reconnect(); // the server forgot the stream
    } catch {
      // the stream breaks too and its next hello subscribes everything again
    }
  }

  // --- the stream -------------------------------------------------------------------------------------------

  #setState(state) {
    if (state === this.#state) return;
    this.#state = state;
    this.dispatchEvent(new CustomEvent("status", { detail: { state } }));
  }

  #deliver(topic, data) {
    for (const callback of [...(this.#listeners.get(topic) || [])]) {
      try {
        callback(data, topic);
      } catch (error) {
        console.error("push-channel listener", error);
      }
    }
  }

  #drop() {
    clearTimeout(this.#retryTimer);
    clearInterval(this.#watchdog);
    this.#source?.close();
    this.#source = null;
    this.#stream = null;
  }

  #reconnect() {
    this.#drop();
    this.#connect();
  }

  #suspend() {
    if (this.#stopped) return;
    this.#suspended = true;
    this.#drop();
  }

  #resume() {
    if (this.#stopped || !this.#suspended) return;
    this.#suspended = false;
    this.#pause = 1000;
    this.#connect();
  }

  #connect() {
    this.#setState("connecting");
    this.#started = performance.now();
    console.debug(`push-channel: connecting at ${Math.round(this.#started)} ms`);
    const source = new EventSource(this.#url, { withCredentials: true });
    this.#source = source;
    this.#heard = Date.now();
    const heard = () => {
      this.#heard = Date.now();
    };
    source.addEventListener("hello", (event) => {
      heard();
      let hello;
      try {
        hello = JSON.parse(event.data);
      } catch {
        return;
      }
      console.debug(`push-channel: open at ${Math.round(performance.now())} ms (took ${Math.round(performance.now() - this.#started)} ms)`);
      this.#pause = 1000;
      this.#stream = hello.stream;
      if (hello.user !== this.#user) {
        this.#user = hello.user;
        this.dispatchEvent(new CustomEvent("hello", { detail: { user: hello.user } }));
      }
      // A new stream knows nothing: every topic again (the pending ones are part of it).
      this.#pending = { sub: new Set(this.#listeners.keys()), unsub: new Set() };
      this.#flush();
      this.#setState("open");
      if (this.#everOpened) this.dispatchEvent(new CustomEvent("resync"));
      this.#everOpened = true;
    });
    source.addEventListener("message", (event) => {
      heard();
      let message;
      try {
        message = JSON.parse(event.data);
      } catch {
        return;
      }
      if (message.topic !== undefined) this.#deliver(message.topic, message.data);
    });
    source.addEventListener("ping", heard);
    source.addEventListener("refused", (event) => {
      try {
        const { error, topics } = JSON.parse(event.data);
        console.warn("push-channel:", error, topics || "");
      } catch {
        // nothing to tell
      }
    });
    source.addEventListener("signed-out", () => {
      this.#drop();
      this.#setState("signed-out");
    });
    source.onerror = () => {
      if (this.#source !== source) return;
      this.#stream = null;
      if (source.readyState === EventSource.CLOSED) {
        // Refused (no 200): the browser gives up, we try again unless the session is gone.
        console.warn(`push-channel: refused after ${Math.round(performance.now() - this.#started)} ms`);
        this.#drop();
        this.#setState("closed");
        this.#retry();
      } else {
        this.#setState("closed"); // the browser reconnects by itself; the next hello resubscribes and resyncs
      }
    };
    clearInterval(this.#watchdog);
    this.#watchdog = setInterval(() => {
      if (Date.now() - this.#heard > SILENT) {
        console.warn("push-channel: stream silent, opening it anew");
        this.#reconnect();
      }
    }, SILENT / 3);
  }

  async #retry() {
    try {
      const response = await fetch(this.#sessionUrl, { headers: { Accept: "application/json" }, credentials: "same-origin" });
      if (response.status === 401) {
        this.#setState("signed-out");
        return;
      }
    } catch {
      // offline: keep trying
    }
    if (this.#stopped || this.#suspended) return;
    console.debug(`push-channel: next attempt in ${this.#pause} ms`);
    this.#retryTimer = setTimeout(() => this.#connect(), this.#pause);
    this.#pause = Math.min(this.#pause * 2, 30000);
  }
}
