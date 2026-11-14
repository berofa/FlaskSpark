/**
 * Sharing of an item (flaskspark.core.shares), the same for every module:
 *
 * <ui-share-editor>: per role «not shared», «read» or «write», below it who is invited now and their answer. Set
 * `data` to a sharing as the API gives it ({roles, shares: {role id: permission}, joins, members}); value() returns
 * {role id: permission} for the API, changed() whether it differs from `data`. The attribute `hint` adds what reading
 * and writing mean for this item.
 *
 * <ui-share-dialog>: the dialog «Share …» around the editor. open(type, id, {name, hint}) reads the sharing from
 * /api/shares/<type>/<id> (or open({src, name, hint}) from any URL) and saves it there (POST {shares}). Fires
 * "share-dialog:saved" (bubbles) with the API's answer (message, the new sharing) after a save.
 *
 *   import "flaskspark/ui-share-dialog.js";
 *   document.querySelector("ui-share-dialog").open("note", 7, { name: "Shopping" });
 *
 * Texts through the app's translations (flaskspark/i18n.js).
 */
import { registerComponent } from "webcomponents/core/registry.js";
import { LightComponentElement } from "webcomponents/core/light-component-element.js";
import { escapeHtml as esc } from "webcomponents/core/escape.js";
import { icon } from "flaskspark/icons.js";
import { notice, request } from "flaskspark/ui.js";
import { preload, t } from "flaskspark/i18n.js";

const N_ = (text) => text; // marks a text for the catalogue (scripts/core-i18n)

const TEXTS = [
  N_("not shared"), N_("read"), N_("write"), N_("invited"), N_("joined"), N_("declined"), N_("Invited"), N_("Loading…"), N_("Cancel"), N_("Save"), N_("Share"),
  N_("Share «{name}»"), N_("No role to share this with."), N_("Shared with every user of a role (also later ones), never with yourself."),
  N_("Only who joins sees it."), N_("When a share ends, who had joined sees a notice once."), N_("Sharing saved."),
];
const ready = preload(TEXTS);

function statusOf(status) {
  return { invited: ["info", t("invited")], joined: ["success", t("joined")], declined: ["secondary", t("declined")] }[status]
    || ["info", t("invited")];
}

export class UiShareEditor extends LightComponentElement {
  static stylesheet = new URL("../css/ui-share-dialog.css", import.meta.url).href;

  #data = null;

  set data(value) {
    this.#data = value;
    ready.then(() => this.#paint());
  }

  get data() {
    return this.#data;
  }

  render() {
    return "<div data-share-body></div>";
  }

  afterRender() {
    ready.then(() => this.#paint());
  }

  /** {role id: "read"|"write"} as chosen now (roles not shared are left out). */
  value() {
    const out = {};
    for (const el of this.querySelectorAll("[data-share-role]")) {
      if (el.value) out[el.dataset.shareRole] = el.value;
    }
    return out;
  }

  changed() {
    const was = Object.entries(this.#data?.shares || {}).map(([k, v]) => `${k}:${v}`).sort().join();
    return was !== Object.entries(this.value()).map(([k, v]) => `${k}:${v}`).sort().join();
  }

  #paint() {
    const box = this.querySelector("[data-share-body]");
    const d = this.#data;
    if (!box || !d) return;
    const shares = d.shares || {};
    const hint = this.getAttribute("hint");
    const permissions = [["", t("not shared")], ["read", t("read")], ["write", t("write")]];
    box.innerHTML = `
      <div class="ui-share-roles">
        ${(d.roles || []).map((r) => `
          <span class="ui-share-role">${esc(r.name)}</span>
          <ui-select size="sm" data-share-role="${esc(r.id)}" aria-label="${esc(r.name)}" value="${esc(shares[String(r.id)] || "")}">
            ${permissions.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join("")}</ui-select>`).join("")
          || `<p class="small app-muted mb-0">${esc(t("No role to share this with."))}</p>`}
      </div>
      ${(d.members || []).length ? `
        <div class="ui-share-members-head">${esc(t("Invited"))}</div>
        <ul class="ui-share-people">${d.members.map((m) => {
          const [variant, label] = statusOf(m.status);
          return `<li><span>${esc(m.username)}</span><ui-badge variant="secondary">${esc(t(m.permission === "read" ? "read" : "write"))}</ui-badge>${
            d.joins ? `<ui-badge variant="${variant}">${esc(label)}</ui-badge>` : ""}</li>`;
        }).join("")}</ul>` : ""}
      <small class="d-block app-muted mt-2">${esc(t("Shared with every user of a role (also later ones), never with yourself."))}${
        d.joins ? ` ${esc(t("Only who joins sees it."))}` : ""} ${esc(t("When a share ends, who had joined sees a notice once."))}${
        hint ? ` ${esc(hint)}` : ""}</small>`;
  }
}

export class UiShareDialog extends LightComponentElement {
  #src = null;
  #busy = false;

  render() {
    return `
      <ui-dialog size="lg" scrollable>
        <span slot="heading" class="d-flex align-items-center gap-2" data-heading></span>
        <div data-notice></div>
        <div data-body></div>
        <ui-share-editor></ui-share-editor>
        <ui-button-group slot="footer" size="sm" data-footer>
          <ui-button size="sm" variant="secondary" outline data-bs-dismiss="dialog" data-cancel></ui-button>
          <ui-button size="sm" data-share-save></ui-button>
        </ui-button-group>
      </ui-dialog>`;
  }

  afterRender() {
    ready.then(() => {
      this.querySelector("[data-cancel]").textContent = t("Cancel");
      this.querySelector("[data-share-save]").textContent = t("Save");
      this.querySelector("[data-footer]").setAttribute("label", t("Share"));
    });
    this.querySelector("ui-dialog").addEventListener("click", (e) => {
      if (e.composedPath().some((n) => n instanceof Element && n.hasAttribute?.("data-share-save")) && !this.#busy) this.#save();
    });
  }

  /**
   * Open the dialog for an item: open(type, id, {name, hint}) for /api/shares/<type>/<id>, or open({src, name, hint})
   * for a sharing at another URL. hint: what reading and writing mean for this item.
   */
  async open(type, id, options = {}) {
    if (typeof type === "object") {
      options = type;
      this.#src = options.src;
    } else {
      this.#src = `/api/shares/${encodeURIComponent(type)}/${Number(id)}`;
    }
    await ready;
    const editor = this.querySelector("ui-share-editor");
    editor.toggleAttribute("hidden", true);
    if (options.hint) editor.setAttribute("hint", options.hint);
    else editor.removeAttribute("hint");
    const heading = this.querySelector("[data-heading]");
    heading.innerHTML = `${icon("people")} ${esc(options.name ? t("Share «{name}»", { name: options.name }) : t("Share"))}`;
    this.querySelector("[data-notice]").innerHTML = "";
    const body = this.querySelector("[data-body]");
    body.textContent = t("Loading…");
    this.querySelector("ui-dialog").show();
    try {
      const data = await request(this.#src);
      if (!options.name && data.name) heading.innerHTML = `${icon("people")} ${esc(t("Share «{name}»", { name: data.name }))}`;
      editor.data = data;
      body.innerHTML = "";
      editor.toggleAttribute("hidden", false);
    } catch (error) {
      body.innerHTML = `<ui-alert variant="warning">${esc(error.message)}</ui-alert>`;
    }
  }

  async #save() {
    const editor = this.querySelector("ui-share-editor");
    if (!editor.data) return;
    this.#busy = true;
    try {
      const result = await request(this.#src, "POST", { shares: editor.value() });
      this.querySelector("ui-dialog").hide();
      notice(result.message || t("Sharing saved."));
      this.dispatchEvent(new CustomEvent("share-dialog:saved", { bubbles: true, detail: result }));
    } catch (error) {
      notice(error.message, "danger", this.querySelector("[data-notice]"));
    } finally {
      this.#busy = false;
    }
  }
}

registerComponent("ui-share-editor", UiShareEditor);
registerComponent("ui-share-dialog", UiShareDialog);
