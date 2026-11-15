/**
 * <ui-service-status>: the status of the application's services in the sidebar (flaskspark.core.status), for admins.
 *
 *   <ui-service-status src="/api/status/services" interval="30" topic="ev.all.services"></ui-service-status>
 *
 * Collapsed (default) it shows a one-line summary, a tile for each service with a warning or a problem and a row of
 * small dots for the services that run fine. Expanded (a click on the heading, remembered per browser) it shows a
 * tile per service: a coloured dot (ok, warning, error), the name and a short summary. A tile with a page of its own
 * (href) links there. Hovering or focusing a tile or a dot shows the details (instances, version, memory, findings);
 * an error row shows the error shortened, a click on it the whole message in a dialog.
 *
 * Data: GET `src` (default /api/status/services) every `interval` seconds while the page is visible, and at once
 * when the server announces a change on the live channel (`topic`, default ev.all.services; the guardian sends it
 * after each run). Texts through the app's translations (flaskspark/i18n.js).
 */
import { registerComponent } from "webcomponents/core/registry.js";
import { LightComponentElement } from "webcomponents/core/light-component-element.js";
import { preload, t } from "flaskspark/i18n.js";
import { pushChannel } from "flaskspark/push-channel.js";

const STORE = "flaskspark.services.open";
const TEXTS = [
  "OK", "Warning", "Problem", "Services", "Status of the services", "{n} running", "1 warning", "{n} warnings",
  "1 problem", "{n} problems", "Show problems only", "Show all services", "Close", "Error", "Show the whole message",
  "Status not available",
];

function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

/** The opening tag's name and attributes of a tile or dot: a link to the tile's page (href), else a button. */
function trigger(s) {
  return s.href ? `a href="${esc(s.href)}"` : `button type="button"`;
}

function level(name) {
  return { ok: t("OK"), warning: t("Warning"), error: t("Problem") }[name] || name;
}

export class UiServiceStatus extends LightComponentElement {
  static observedAttributes = ["src", "interval", "topic"];
  static stylesheet = new URL("../css/ui-service-status.css", import.meta.url).href;

  data = null;
  error = false;
  #timer = null;
  #off = null;
  #loading = false;
  #deferred = false;
  #ready = false;
  #open = (() => {
    try {
      return localStorage.getItem(STORE) === "1";
    } catch {
      return false;
    }
  })();

  constructor() {
    super();
    this.addEventListener("click", (event) => {
      const error = event.target.closest(".ui-service-status__error");
      if (error) {
        UiServiceStatus.#showError(error.dataset.label, error.dataset.full);
        return;
      }
      if (!event.target.closest(".ui-service-status__toggle")) return;
      this.#open = !this.#open;
      try {
        localStorage.setItem(STORE, this.#open ? "1" : "0");
      } catch {
        // Not remembered (private window, blocked storage).
      }
      this.requestRender();
    });
    this.onVisible = () => {
      if (document.visibilityState === "visible") this.refresh();
    };
  }

  get src() {
    return this.getAttribute("src") || "/api/status/services";
  }

  connectedCallback() {
    super.connectedCallback();
    preload(TEXTS).then(() => {
      this.#ready = true;
      this.requestRender();
    });
    this.refresh();
    const seconds = Math.max(5, Number(this.getAttribute("interval")) || 30);
    this.#timer = setInterval(() => {
      if (document.visibilityState === "visible") this.refresh();
    }, seconds * 1000);
    document.addEventListener("visibilitychange", this.onVisible);
    const channel = pushChannel();
    const off = channel.subscribe(this.getAttribute("topic") || "ev.all.services", () => this.refresh());
    const resync = () => this.refresh();
    channel.addEventListener("resync", resync);
    this.#off = () => {
      off();
      channel.removeEventListener("resync", resync);
    };
  }

  disconnectedCallback() {
    clearInterval(this.#timer);
    this.#timer = null;
    document.removeEventListener("visibilitychange", this.onVisible);
    this.#off?.();
    this.#off = null;
  }

  /** Load the status now (a load already running is not started twice). */
  async refresh() {
    if (this.#loading) return;
    this.#loading = true;
    try {
      const response = await fetch(this.src, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(String(response.status));
      this.data = await response.json();
      this.error = false;
    } catch {
      this.error = true;
    } finally {
      this.#loading = false;
    }
    this.requestRender();
  }

  requestRender() {
    // An open popover would vanish with the re-render: wait until it closes.
    if (this.querySelector("ui-popover[aria-describedby]")) {
      if (!this.#deferred) {
        this.#deferred = true;
        this.addEventListener("ui-popover:hidden", () => {
          this.#deferred = false;
          this.requestRender();
        }, { once: true });
      }
      return;
    }
    super.requestRender();
  }

  /** The whole message of an error row in a dialog (one for the page, outside the tiles: they are drawn anew). */
  static #showError(label, text) {
    let dialog = document.getElementById("ui-service-status-error");
    if (!dialog) {
      dialog = document.createElement("ui-dialog");
      dialog.id = "ui-service-status-error";
      dialog.setAttribute("size", "lg");
      dialog.innerHTML = `<span slot="heading" data-heading></span>
        <pre class="ui-service-status__full" data-text></pre>
        <ui-button slot="footer" variant="secondary" outline data-bs-dismiss="dialog">${esc(t("Close"))}</ui-button>`;
      document.body.append(dialog);
    }
    dialog.querySelector("[data-heading]").textContent = label || t("Error");
    dialog.querySelector("[data-text]").textContent = text || "";
    dialog.show();
  }

  #popover(s, trigger, attrs = "") {
    // Texts outside the template literals: the extraction of the core's catalogue (scripts/core-i18n) finds them there.
    const whole = t("Show the whole message");
    return `
      <ui-popover class="ui-service-status__pop" trigger="hover focus" ${attrs || `placement="right"`}>
        ${trigger}
        <span slot="heading" class="ui-service-status__heading">
          <span class="ui-service-status__title">${esc(s.name)}
            <span class="ui-service-status__level ui-service-status__level--${esc(s.level)}">${esc(level(s.level))}</span></span>
          ${s.process || s.service ? `<code class="ui-service-status__unit">${esc(s.process || s.service)}</code>` : ""}
        </span>
        <div slot="content" class="ui-service-status__body">
          ${s.summary ? `<p class="ui-service-status__lead">${esc(s.summary)}</p>` : ""}
          ${(s.details || []).length ? `<dl class="ui-service-status__details">
            ${s.details.map(([label, text, full]) => `<dt>${esc(label)}</dt><dd>${full === undefined ? esc(text)
              : `<button type="button" class="ui-service-status__error" data-label="${esc(`${s.name} · ${label}`)}" data-full="${esc(full)}"
                  title="${esc(whole)}">${esc(text)}</button>`}</dd>`).join("")}
          </dl>` : ""}
        </div>
      </ui-popover>`;
  }

  #tile(s) {
    return this.#popover(s, `
        <${trigger(s)} class="ui-service-status__tile ui-service-status__tile--${esc(s.level)}" aria-label="${esc(s.name)}: ${esc(level(s.level))}, ${esc(s.summary)}">
          <span class="ui-service-status__dot" aria-hidden="true"></span>
          <span class="ui-service-status__name">${esc(s.name)}</span>
          <span class="ui-service-status__summary">${esc(s.summary)}</span>
        </${s.href ? "a" : "button"}>`);
  }

  // The box sits above the whole row of dots at its width (only the arrow follows the dot), so it covers none of
  // the other dots and they stay reachable by hover.
  #dot(s) {
    return this.#popover(s, `
        <${trigger(s)} class="ui-service-status__chip ui-service-status__tile--${esc(s.level)}" title="${esc(s.name)}" aria-label="${esc(s.name)}: ${esc(level(s.level))}, ${esc(s.summary)}">
          <span class="ui-service-status__dot" aria-hidden="true"></span>
        </${s.href ? "a" : "button"}>`, ` placement="top" anchor=".ui-service-status__dots" fit-anchor`);
  }

  // "12 running" or "10 running · 1 warning · 1 problem"
  #counts(services) {
    const n = (name) => services.filter((s) => s.level === name).length;
    const parts = [t("{n} running", { n: n("ok") })];
    if (n("warning")) parts.push(n("warning") === 1 ? t("1 warning") : t("{n} warnings", { n: n("warning") }));
    if (n("error")) parts.push(n("error") === 1 ? t("1 problem") : t("{n} problems", { n: n("error") }));
    return parts.join(" · ");
  }

  render() {
    if (!this.#ready || (!this.data && !this.error)) return "";
    const services = this.data?.services || [];
    const text = {
      none: t("Status not available"),
      group: t("Status of the services"),
      toggle: this.#open ? t("Show problems only") : t("Show all services"),
      services: t("Services"),
    };
    const body = this.error && !this.data
      ? `<p class="ui-service-status__none">${esc(text.none)}</p>`
      : this.#open
        ? services.map((s) => this.#tile(s)).join("")
        : services.filter((s) => s.level !== "ok").map((s) => this.#tile(s)).join("")
          + `<div class="ui-service-status__dots">${services.filter((s) => s.level === "ok").map((s) => this.#dot(s)).join("")}</div>`;
    return `<div class="ui-service-status" role="group" aria-label="${esc(text.group)}">
      <button type="button" class="ui-service-status__toggle" aria-expanded="${this.#open}"
              title="${esc(text.toggle)}">
        <span class="ui-service-status__group">${esc(text.services)}</span>
        <span class="ui-service-status__count">${this.data ? esc(this.#counts(services)) : ""}</span>
        <svg class="ui-service-status__chevron" xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708"/></svg>
      </button>${body}</div>`;
  }
}

registerComponent("ui-service-status", UiServiceStatus);
