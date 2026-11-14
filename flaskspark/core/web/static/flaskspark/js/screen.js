/**
 * flaskspark.core: the script of an info screen (layouts/screen.html, <html data-screen="<key>">), a page on a display
 * nobody operates.
 *
 * - Display only: right clicks open no menu (neither the browser's nor ui-context-menu's), clicks, double clicks,
 *   presses and the activating keys (Enter, Space) do nothing; inside [data-screen-keep] everything works as usual.
 *   (frame.css and the web components hide the buttons; this keeps the rest from reacting.)
 * - Head row: the clock ([data-screen-clock], date and time in the page's language) and the live state
 *   ([data-screen-live] data-state="open" | "connecting" | "closed" | …, the push channel's).
 * - Recovery: the push channel reconnects by itself and the sections load their data again on "resync". Should it stay
 *   down for DOWN_RELOAD ms, the page loads itself anew, but only once the server answers again (a reload against a
 *   server that is away would leave the browser's error page on the wall); after every such reload the wait doubles
 *   (up to DOWN_RELOAD_MAX), back to the start once the channel is open. Once a day at <html data-screen-reload-at>
 *   ("04:00") the page reloads too (new code after a deployment, a fresh start).
 * - onNewDay(callback): for sections that show something of today (e.g. the current milestone): called when the local
 *   date changes (checked every minute, also after the computer slept).
 *
 *   import { onNewDay } from "flaskspark/screen.js";
 *   onNewDay(() => reload());
 */
import { pushChannel } from "./push-channel.js";
import { t, preload } from "./i18n.js";

export const DOWN_RELOAD = 5 * 60000; // ms the push channel may be down before the page reloads
export const DOWN_RELOAD_MAX = 60 * 60000;
const TICK = 30000; // ms between two checks (recovery, daily reload)
const DAY_TICK = 60000; // ms between two looks at the date
const RELOADS_KEY = "flaskspark.screen.reloads"; // sessionStorage: reloads in a row because the channel was down
const BLOCKED = ["contextmenu", "click", "dblclick", "auxclick", "mousedown", "pointerdown", "submit"];
const ACTIVATING = new Set(["Enter", " ", "Spacebar"]);
const TEXTS = ["Live: changes appear at once.", "Reconnecting…"];

const inPage = typeof window !== "undefined" && typeof document !== "undefined";

// ---- pure helpers (tests/webcomponents/js/screen.test.js) ----------------------------------------------------------

/** "YYYY-MM-DD" of a date in local time. */
export function dayKey(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** The next moment (a Date, local time) at "HH:MM" after `now`; null for anything else. */
export function nextAt(now, hhmm) {
  const match = /^([01]\d|2[0-3]):([0-5]\d)$/.exec(String(hhmm || ""));
  if (!match) return null;
  const next = new Date(now.getFullYear(), now.getMonth(), now.getDate(), Number(match[1]), Number(match[2]), 0, 0);
  if (next <= now) next.setDate(next.getDate() + 1);
  return next;
}

/** How long the channel may be down after `reloads` reloads in a row for that reason. */
export function downDelay(reloads = 0, base = DOWN_RELOAD, max = DOWN_RELOAD_MAX) {
  const n = Math.max(0, Math.floor(Number(reloads) || 0));
  return Math.min(base * 2 ** Math.min(n, 30), max);
}

/** Is it time to reload? downSince: when the channel went down (ms), null while it is open. */
export function shouldReload(downSince, now, delay = DOWN_RELOAD) {
  return downSince !== null && downSince !== undefined && now - downSince >= delay;
}

/** Does an event inside `path` (event.composedPath()) belong to an element the screen keeps working? */
export function keeps(path) {
  return (path || []).some((node) => typeof node?.hasAttribute === "function" && node.hasAttribute("data-screen-keep"));
}

// ---- a new day -----------------------------------------------------------------------------------------------------

const dayListeners = new Set();
let dayTimer = null;

/** Calls `callback` when the local date changes; returns the function that stops it. */
export function onNewDay(callback) {
  dayListeners.add(callback);
  if (!dayTimer && inPage) {
    let today = dayKey(new Date());
    dayTimer = setInterval(() => {
      const now = dayKey(new Date());
      if (now === today) return;
      today = now;
      for (const listener of [...dayListeners]) {
        try {
          listener(now);
        } catch (error) {
          console.error("screen: new day", error);
        }
      }
    }, DAY_TICK);
  }
  return () => dayListeners.delete(callback);
}

// ---- the page ------------------------------------------------------------------------------------------------------

function storedReloads() {
  try {
    return Number(sessionStorage.getItem(RELOADS_KEY)) || 0;
  } catch {
    return 0;
  }
}

function storeReloads(count) {
  try {
    if (count) sessionStorage.setItem(RELOADS_KEY, String(count));
    else sessionStorage.removeItem(RELOADS_KEY);
  } catch {
    // no storage: every wait is the first
  }
}

/** Reloads the page once the server answers (else nothing: the next check tries again). */
async function reloadWhenReachable(reason) {
  try {
    const response = await fetch(location.href, { cache: "no-store", headers: { Accept: "text/html" } });
    if (!response.ok) return false;
  } catch {
    return false;
  }
  console.info(`screen: reloading (${reason})`);
  location.reload();
  return true;
}

function blockInteraction(root) {
  const swallow = (event) => {
    if (keeps(event.composedPath())) return;
    if (event.type === "keydown" && !ACTIVATING.has(event.key)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
  };
  for (const type of [...BLOCKED, "keydown"]) window.addEventListener(type, swallow, { capture: true });
  root.classList.add("is-screen");
}

function startClock(root) {
  const clock = document.querySelector("[data-screen-clock]");
  if (!clock) return;
  const lang = root.lang || undefined;
  const date = new Intl.DateTimeFormat(lang, { weekday: "long", day: "numeric", month: "long" });
  const time = new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit" });
  const show = () => {
    const now = new Date();
    clock.dateTime = now.toISOString();
    clock.replaceChildren(
      Object.assign(document.createElement("span"), { className: "app-screen-date", textContent: date.format(now) }),
      Object.assign(document.createElement("span"), { className: "app-screen-time", textContent: time.format(now) }));
  };
  show();
  setTimeout(() => {
    show();
    setInterval(show, 60000);
  }, 60000 - (Date.now() % 60000) + 50); // on the minute
}

function watchChannel(root) {
  const live = document.querySelector("[data-screen-live]");
  let channel = null;
  try {
    channel = pushChannel();
  } catch (error) {
    console.warn("screen: no push channel", error);
  }
  let downSince = Date.now(); // not open yet
  let reloads = storedReloads();
  const show = (state) => {
    if (state === "open") {
      downSince = null;
      if (reloads) storeReloads((reloads = 0));
    } else if (downSince === null) {
      downSince = Date.now();
    }
    if (live) {
      live.dataset.state = state;
      live.title = t(state === "open" ? "Live: changes appear at once." : "Reconnecting…");
    }
  };
  channel?.addEventListener("status", (event) => show(event.detail.state));
  show(channel?.state || "closed");

  const daily = nextAt(new Date(), root.dataset.screenReloadAt);
  setInterval(async () => {
    const now = Date.now();
    if (daily && now >= daily.getTime()) {
      if (await reloadWhenReachable("daily")) return;
    }
    if (shouldReload(downSince, now, downDelay(reloads))) {
      storeReloads(reloads + 1);
      if (!(await reloadWhenReachable("live channel down"))) storeReloads(reloads);
    }
  }, TICK);
}

async function install() {
  const root = document.documentElement;
  blockInteraction(root);
  startClock(root);
  try {
    await preload(TEXTS);
  } catch {
    // the source texts then
  }
  watchChannel(root);
}

if (inPage && document.documentElement.hasAttribute("data-screen")) install();
