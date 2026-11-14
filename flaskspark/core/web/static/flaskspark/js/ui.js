/**
 * Helpers of every page: JSON requests, messages and activity logs.
 *
 *   import { request, notice, activityLog } from "flaskspark/ui.js";
 *   const data = await request("/api/x", "POST", { id: 1 });   // throws Error(server's "error") on failure
 *   notice(t("Saved"));                                       // a toast at the top right
 *   notice(t("Not found"), "danger", dialogBox);              // inside a ui-dialog: a ui-alert in `box`
 *   const log = activityLog("my-log");                        // <div class="app-log" id="my-log">
 *   log.add("Connected", "success"); log.separator(); log.clear();
 */

/** fetch() with a JSON body and JSON answer; throws an Error with the server's message ("error" or "message"). */
export async function request(url, method = "GET", body = undefined, options = {}) {
  const response = await fetch(url, {
    method,
    headers: {
      Accept: "application/json",
      "X-Requested-With": "XMLHttpRequest",
      ...(body !== undefined && !(body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
    body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    signal: options.signal,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    const error = new Error(data.error || data.message || `Request failed (${response.status}).`);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

/** A message: a toast at the top right (never moves the page). With `box` inside a ui-dialog, warnings and errors
 *  become a dismissible ui-alert there instead (they belong to the dialog's form). Success goes after 4 s, the rest
 *  after 8 s. variant: success, info, warning, danger (also "error"). */
export function notice(message, variant = "success", box = null) {
  if (variant === "error") variant = "danger";
  if (box?.closest?.("ui-dialog") && variant !== "success" && variant !== "info") {
    box.innerHTML = "";
    const el = document.createElement("ui-alert");
    el.setAttribute("variant", variant);
    el.setAttribute("dismissible", "");
    el.textContent = message;
    box.append(el);
    return el;
  }
  import("webcomponents/modules/bootstrap/ui-toast/ui-toast.js")
    .then(({ showToast }) => showToast(message, { variant, delay: variant === "success" ? 4000 : 8000 }));
  return null;
}

const pad2 = (value) => String(value).padStart(2, "0");

function logTime(value) {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) return "??:??:??";
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}:${pad2(date.getSeconds())}`;
}

/** An activity log in an element (id or element, class "app-log"): lines with time and level. */
export function activityLog(target) {
  const el = typeof target === "string" ? document.getElementById(target) : target;
  return {
    element: el,
    /** add(message, level = "info") or add({message, level, timestamp}); an empty message adds a separator. */
    add(entry, level = "info") {
      if (!el) return;
      const item = typeof entry === "object" && entry !== null ? entry : { message: String(entry ?? ""), level };
      const message = String(item.message || "");
      const line = document.createElement("div");
      if (!message.trim()) {
        line.className = "app-log-line app-log-separator";
        line.setAttribute("aria-hidden", "true");
      } else {
        const lvl = String(item.level || level || "info");
        line.className = `app-log-line app-log-${lvl}`;
        const time = document.createElement("span");
        time.className = "app-log-time";
        time.textContent = `[${logTime(item.timestamp)}]`;
        const text = document.createElement("span");
        text.className = "app-log-text";
        text.textContent = message;
        line.append(time, " ", text);
      }
      el.append(line);
      el.scrollTop = el.scrollHeight;
    },
    separator() {
      this.add("");
    },
    clear() {
      if (el) el.replaceChildren();
    },
  };
}
