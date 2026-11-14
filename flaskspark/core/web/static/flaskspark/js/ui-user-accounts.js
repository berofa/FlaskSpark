/**
 * <ui-user-accounts src="/api/accounts">: the profile's «Accounts» (flaskspark.core.accounts). The signed-in user's
 * accounts: one login (user name and password at a provider) with the services it offers (the account types the
 * application's modules use, e.g. mail over IMAP, sending over SMTP, calendars over CalDAV). Connect one (a preset
 * of a provider sets what it can; an own server asks for its addresses), switch services on and off, change the name
 * or the password, test the connection, switch the account off and on, share it with roles (<ui-share-dialog>),
 * remove it. Connecting and editing happen in a dialog; a new account is kept only if every service signs in. Below
 * them the accounts others shared with the user's role. The form is built from the types' fields (kinds text, int,
 * bool, choice, url, host); the login asks for what the chosen types need (a user name, a password or e.g. an access
 * token: the types' username and secret_label). With src="/api/settings/accounts" it keeps the application's
 * accounts (the admins' tab «Accounts» in «Settings»: no sharing). Texts through the app's translations
 * (flaskspark/i18n.js).
 */
import { registerComponent } from "webcomponents/core/registry.js";
import { LightComponentElement } from "webcomponents/core/light-component-element.js";
import { escapeHtml as esc } from "webcomponents/core/escape.js";
import { icon } from "flaskspark/icons.js";
import { notice, request } from "flaskspark/ui.js";
import { validateForm } from "flaskspark/forms.js";
import { preload, t } from "flaskspark/i18n.js";
import "flaskspark/ui-share-dialog.js";

const N_ = (text) => text; // marks a text for the catalogue (scripts/core-i18n)

const ready = preload([
  N_("Accounts"), N_("Connect account"), N_("No account connected yet."), N_("Loading…"), N_("Test the connection"), N_("Share"), N_("Edit"),
  N_("Switch off"), N_("Switch on"), N_("Remove"), N_("Really remove?"), N_("No"), N_("switched off"), N_("connected"), N_("sign-in failed"),
  N_("not tested"), N_("Used by"), N_("Shared with you"), N_("shared by {owner}"), N_("read"), N_("write"), N_("Provider"), N_("Name"),
  N_("User name"), N_("Password"), N_("Leave empty to keep the password."), N_("Services"), N_("Cancel"), N_("Save"), N_("Connect"),
  N_("Edit «{name}»"), N_("An account is one sign-in (user name and password) with everything its server offers. The password is stored encrypted; the data stays on the servers. A new account is kept only if every chosen service signs in."),
  N_("Choose at least one service."), N_("Testing…"), N_("Connecting…"), N_("Saving…"), N_("The user name is the one you signed in with: {user}."),
  N_("Default: {value}"), N_("Leave empty to keep it."),
  N_("These accounts belong to the application, not to a person: the modules' services use them for everyone. Only admins see and change them."),
]);

function btn(name, tooltip, action, id, variant = "secondary") {
  return `<ui-button size="sm" variant="${variant}" outline data-acc-action="${action}" data-id="${id}" label="${esc(tooltip)}" title="${esc(tooltip)}">${icon(name)}</ui-button>`;
}

export class UiUserAccounts extends LightComponentElement {
  static stylesheet = new URL("../css/ui-user-accounts.css", import.meta.url).href;

  #data = null;
  #error = null;
  #busy = false;
  #confirm = null; // the account whose removal waits for a second click
  // the dialog's form: null, or {id (0: new), provider, values: {name: value}, types: {key: bool}}
  #form = null;

  get #src() {
    return this.getAttribute("src") || "/api/accounts";
  }

  render() {
    return `<div data-body></div><ui-share-dialog></ui-share-dialog>
      <ui-dialog size="lg" scrollable data-acc-dialog>
        <span slot="heading" data-acc-heading></span>
        <div data-modal-notice></div>
        <form data-modal-body novalidate></form>
        <ui-button-group slot="footer" size="sm" data-modal-footer></ui-button-group>
      </ui-dialog>`;
  }

  afterRender() {
    this.addEventListener("click", (e) => {
      const el = e.composedPath().find((n) => n instanceof Element && n.dataset?.accAction);
      if (el && !el.hasAttribute("disabled") && !this.#busy) this.#action(el.dataset.accAction, Number(el.dataset.id), el);
    });
    this.addEventListener("change", (e) => this.#changed(e));
    this.querySelector("[data-acc-dialog]").addEventListener("ui-dialog:hidden", () => { this.#form = null; });
    this.addEventListener("share-dialog:saved", () => this.load());
    this.querySelector("[data-body]").textContent = "…";
    ready.then(() => this.load());
  }

  async load() {
    try {
      this.#data = await request(this.#src);
      this.#error = null;
    } catch (error) {
      this.#error = error.message;
    }
    this.#paint();
  }

  // --- the list ---------------------------------------------------------------------------------------------------
  #paint() {
    const body = this.querySelector("[data-body]");
    if (!body) return;
    if (this.#error) {
      body.innerHTML = `<ui-alert variant="warning">${esc(this.#error)}</ui-alert>`;
      return;
    }
    const d = this.#data;
    if (!d) return;
    body.innerHTML = `
      <section class="ui-acc-section">
        <div class="ui-acc-section__head">
          <h2 class="h5 mb-0 d-flex align-items-center gap-2">${icon("plug")} ${esc(t("Accounts"))}</h2>
          <ui-button size="sm" data-acc-action="add" data-id="0">${icon("plus")} ${esc(t("Connect account"))}</ui-button>
        </div>
        ${d.accounts.length ? `<div class="ui-acc-list">${d.accounts.map((a) => this.#accountHtml(a)).join("")}</div>`
          : `<p class="app-muted mb-0">${esc(t("No account connected yet."))}</p>`}
        ${d.shared?.length ? `
          <h3 class="h6 mt-4 mb-2">${esc(t("Shared with you"))}</h3>
          <div class="ui-acc-list">${d.shared.map((a) => this.#sharedHtml(a)).join("")}</div>` : ""}
        ${d.app ? `<p class="ui-acc-notes">${esc(t("These accounts belong to the application, not to a person: the modules' services use them for everyone. Only admins see and change them."))}</p>` : ""}
        <p class="ui-acc-notes">${esc(t("An account is one sign-in (user name and password) with everything its server offers. The password is stored encrypted; the data stays on the servers. A new account is kept only if every chosen service signs in."))}</p>
      </section>`;
  }

  #providerLabel(key) {
    return this.#data.providers.find((p) => p.key === key)?.label || key;
  }

  #typeBadge(key, c) {
    const variant = c.verified ? "success" : c.error ? "danger" : "secondary";
    const title = c.verified ? t("connected") : c.error ? t("sign-in failed") : t("not tested");
    return `<ui-badge variant="${variant}" title="${esc(title)}">${icon(c.icon || "plug")} ${esc(c.label)}</ui-badge>`;
  }

  #accountHtml(a) {
    const types = Object.entries(a.types || {});
    const roles = Object.entries(a.shares || {}).map(([id, p]) =>
      `${this.#data.roles.find((r) => r.id === Number(id))?.name || `#${id}`} (${t(p === "read" ? "read" : "write")})`);
    const actions = this.#confirm === a.id ? `
        <span class="small me-1">${esc(t("Really remove?"))}</span>
        <ui-button size="sm" variant="danger" data-acc-action="delete" data-id="${a.id}">${esc(t("Remove"))}</ui-button>
        <ui-button size="sm" variant="secondary" outline data-acc-action="cancel-confirm" data-id="0">${esc(t("No"))}</ui-button>` : `
        ${btn("arrow-repeat", t("Test the connection"), "test", a.id)}
        ${this.#data.roles?.length ? btn("people", t("Share"), "share", a.id) : ""}
        ${btn("pencil", t("Edit"), "edit", a.id)}
        ${btn("power", a.is_active ? t("Switch off") : t("Switch on"), a.is_active ? "deactivate" : "activate", a.id)}
        ${btn("trash", t("Remove"), "confirm", a.id, "danger")}`;
    return `
      <div class="ui-acc-item${a.is_active ? "" : " is-inactive"}" data-account="${a.id}">
        <div class="ui-acc-main">
          <div class="d-flex flex-wrap align-items-center gap-2"><span class="fw-semibold">${esc(a.name)}</span>
            ${a.is_active ? "" : `<ui-badge variant="secondary">${esc(t("switched off"))}</ui-badge>`}</div>
          <small class="app-muted">${esc(this.#providerLabel(a.provider))}${a.username ? ` · ${esc(a.username)}` : ""}</small>
          <div class="ui-acc-types">${types.map(([k, c]) => this.#typeBadge(k, c)).join("")}</div>
          ${types.map(([, c]) => `${c.describe ? `<small class="d-block app-muted">${esc(c.label)}: ${esc(c.describe)}</small>` : ""}${
            c.error ? `<small class="d-block text-danger">${esc(c.label)}: ${esc(c.error)}</small>` : ""}`).join("")}
          ${a.modules?.length ? `<small class="d-block app-muted">${esc(t("Used by"))}: ${a.modules.map(esc).join(", ")}</small>` : ""}
          ${roles.length ? `<small class="d-block app-muted">${icon("people")} ${roles.map(esc).join(", ")}</small>` : ""}
        </div>
        <div class="ui-acc-actions">${actions}</div>
      </div>`;
  }

  #sharedHtml(a) {
    return `
      <div class="ui-acc-item${a.is_active ? "" : " is-inactive"}">
        <div class="ui-acc-main">
          <div class="d-flex flex-wrap align-items-center gap-2"><span class="fw-semibold">${esc(a.name)}</span>
            <ui-badge variant="info">${esc(t(a.permission === "read" ? "read" : "write"))}</ui-badge></div>
          <small class="app-muted">${a.username ? `${esc(a.username)} · ` : ""}${esc(t("shared by {owner}", { owner: a.owner }))}</small>
          <small class="d-block app-muted">${(a.types || []).map(esc).join(", ")}</small>
        </div>
      </div>`;
  }

  // --- actions ----------------------------------------------------------------------------------------------------
  async #action(action, id, el) {
    if (action === "add") return this.#open({ id: 0, provider: this.#data.providers[0]?.key || "custom", values: {}, types: {} });
    if (action === "edit") {
      const a = this.#data.accounts.find((x) => x.id === id);
      const values = { name: a.name, username: a.username };
      for (const [key, c] of Object.entries(a.types)) {
        for (const [field, value] of Object.entries(c.settings || {})) values[`${key}.${field}`] = value;
      }
      return this.#open({ id, provider: a.provider, values, types: Object.fromEntries(Object.keys(a.types).map((k) => [k, true])) });
    }
    if (action === "confirm" || action === "cancel-confirm") {
      this.#confirm = action === "confirm" ? id : null;
      return this.#paint();
    }
    if (action === "share") {
      const a = this.#data.accounts.find((x) => x.id === id);
      return this.querySelector("ui-share-dialog").open("account", id, { name: a?.name });
    }
    if (action === "save") return this.#save(el);
    if (["test", "activate", "deactivate", "delete"].includes(action)) {
      this.#busy = true;
      if (action === "test") notice(t("Testing…"), "info");
      try {
        const data = await request(`${this.#src}/${id}`, "POST", { action });
        this.#confirm = null;
        this.#data = data;
        notice(data.message);
      } catch (error) {
        if (error.data?.accounts) this.#data = error.data;
        notice(error.message, "danger");
      } finally {
        this.#busy = false;
        this.#paint();
      }
    }
    return undefined;
  }

  // --- the dialog -------------------------------------------------------------------------------------------------
  #provider() {
    return this.#data.providers.find((p) => p.key === this.#form.provider) || { key: "custom", types: {}, sso_user: false };
  }

  /** The types the form shows: those offered, and those the account has (also one no longer offered). */
  #types() {
    const offered = this.#data.types;
    const editing = this.#form.id ? this.#data.accounts.find((a) => a.id === this.#form.id) : null;
    const extra = Object.entries(editing?.types || {}).filter(([k]) => !offered.some((x) => x.key === k))
      .map(([key, c]) => ({ key, label: c.label, icon: c.icon, fields: [], modules: [] }));
    const provider = this.#provider();
    const all = [...offered, ...extra];
    // a preset offers only some types (an own server all)
    return provider.key === "custom" || this.#form.id ? all : all.filter((x) => x.key in (provider.types || {}));
  }

  #open(form) {
    this.#form = form;
    if (!form.id && !Object.keys(form.types).length) {
      const provider = this.#provider();
      const offered = Object.keys(provider.types || {});
      form.types = Object.fromEntries((offered.length ? offered : this.#data.types.slice(0, 1).map((x) => x.key)).map((k) => [k, true]));
    }
    const dialog = this.querySelector("[data-acc-dialog]");
    const editing = form.id ? this.#data.accounts.find((a) => a.id === form.id) : null;
    this.querySelector("[data-acc-heading]").innerHTML = `${icon("plug")} ${esc(editing ? t("Edit «{name}»", { name: editing.name }) : t("Connect account"))}`;
    this.querySelector("[data-modal-notice]").innerHTML = "";
    this.querySelector("[data-modal-footer]").innerHTML = `
      <ui-button size="sm" variant="secondary" outline data-bs-dismiss="dialog">${esc(t("Cancel"))}</ui-button>
      <ui-button size="sm" data-acc-action="save" data-id="${form.id}">${esc(form.id ? t("Save") : t("Connect"))}</ui-button>`;
    this.#paintForm();
    dialog.show();
  }

  #field(typeKey, f, preset) {
    const name = `${typeKey}.${f.key}`;
    const fixed = preset && f.key in preset;
    const value = fixed ? preset[f.key] : (this.#form.values[name] ?? f.default ?? "");
    const help = f.help || (f.default !== null && f.default !== undefined && f.kind !== "bool" ? t("Default: {value}", { value: f.default }) : "");
    if (fixed) return "";
    if (f.kind === "bool") {
      return `<div class="col-12"><ui-check switch name="${esc(name)}" data-bool label="${esc(f.label)}" description="${esc(f.help || "")}"${value ? " checked" : ""}></ui-check></div>`;
    }
    if (f.kind === "choice") {
      return `<div class="md:col-6"><ui-select name="${esc(name)}" label="${esc(f.label)}" value="${esc(value)}">
        ${f.choices.map((c) => `<option value="${esc(c.value)}"${String(c.value) === String(value) ? " selected" : ""}>${esc(c.label)}</option>`).join("")}</ui-select></div>`;
    }
    const number = f.kind === "int";
    const type = number ? "number" : f.kind === "url" ? "url" : "text";
    return `<div class="${f.kind === "url" ? "col-12" : "md:col-6"}"><ui-input name="${esc(name)}" type="${type}" label="${esc(f.label)}" help="${esc(help)}"
      value="${esc(value)}" placeholder="${esc(f.placeholder || "")}"${f.required && f.default == null ? " required" : ""}
      ${number && f.min != null ? `min="${f.min}"` : ""} ${number && f.max != null ? `max="${f.max}"` : ""}></ui-input></div>`;
  }

  /** What the login of the chosen types needs: a user name, a secret (and what it is called). */
  #login() {
    const chosen = this.#types().filter((x) => this.#form.types[x.key] && x.login !== false);
    const labels = [...new Set(chosen.map((x) => x.secret_label).filter(Boolean))];
    return {
      username: chosen.some((x) => x.username !== false),
      secret: chosen.length > 0,
      secretLabel: labels.length === 1 ? labels[0] : t("Password"),
      own: labels.length === 1 && labels[0] !== t("Password"),
    };
  }

  #paintForm() {
    const form = this.#form;
    const box = this.querySelector("[data-modal-body]");
    const provider = this.#provider();
    const providers = this.#data.providers;
    const sso = provider.sso_user;
    const login = this.#login();
    const v = (name) => form.values[name] ?? "";
    box.innerHTML = `
      <div class="row g-3">
        ${!form.id && providers.length > 1 ? `<div class="md:col-6"><ui-select name="provider" label="${esc(t("Provider"))}" value="${esc(form.provider)}" data-acc-provider>
          ${providers.map((p) => `<option value="${esc(p.key)}"${p.key === form.provider ? " selected" : ""}>${esc(p.label)}</option>`).join("")}</ui-select></div>` : ""}
        <div class="md:col-6"><ui-input name="name" label="${esc(t("Name"))}" maxlength="60" value="${esc(v("name"))}"></ui-input></div>
        ${!login.username ? "" : sso ? `<div class="col-12"><small class="app-muted">${esc(t("The user name is the one you signed in with: {user}.", { user: this.#data.user }))}</small></div>`
          : `<div class="md:col-6"><ui-input name="username" label="${esc(t("User name"))}" autocomplete="off" value="${esc(v("username"))}"${form.id ? "" : " required"}></ui-input></div>`}
        ${login.secret ? `<div class="md:col-6"><ui-input name="password" type="password" label="${esc(login.secretLabel)}" autocomplete="new-password"
          ${form.id ? `help="${esc(login.own ? t("Leave empty to keep it.") : t("Leave empty to keep the password."))}"` : " required"}></ui-input></div>` : ""}
      </div>
      <h3 class="h6 mt-4 mb-2">${esc(t("Services"))}</h3>
      <div class="ui-acc-form-types">
        ${this.#types().map((x) => `
          <div class="ui-acc-form-type">
            <ui-check switch data-acc-type="${esc(x.key)}" label="${esc(x.label)}"
              description="${esc(x.modules?.length ? `${t("Used by")}: ${x.modules.join(", ")}` : "")}"${form.types[x.key] ? " checked" : ""}></ui-check>
            ${form.types[x.key] ? `<div class="row g-2 mt-1">${(x.fields || []).map((f) => this.#field(x.key, f, (provider.types || {})[x.key])).join("")}</div>` : ""}
          </div>`).join("")}
      </div>`;
  }

  /** What the form holds now, into #form.values (before it is painted again). */
  #collect() {
    const box = this.querySelector("[data-modal-body]");
    for (const el of box.querySelectorAll("[name]")) {
      const name = el.getAttribute("name");
      if (name === "password" || name === "provider") continue;
      this.#form.values[name] = el.matches("ui-check") ? Boolean(el.checked) : el.value;
    }
  }

  #changed(e) {
    if (!this.#form) return;
    const provider = e.target.closest?.("[data-acc-provider]");
    const type = e.target.closest?.("[data-acc-type]");
    if (!provider && !type) return;
    this.#collect();
    if (provider) {
      this.#form.provider = provider.value;
      this.#form.types = {};
      const offered = Object.keys(this.#provider().types || {});
      this.#form.types = Object.fromEntries((offered.length ? offered : this.#data.types.slice(0, 1).map((x) => x.key)).map((k) => [k, true]));
    }
    if (type) this.#form.types[type.dataset.accType] = Boolean(type.checked);
    this.#paintForm();
  }

  async #save() {
    const form = this.#form;
    const box = this.querySelector("[data-modal-body]");
    const noticeBox = this.querySelector("[data-modal-notice]");
    if (!validateForm(box)) return;
    this.#collect();
    const editing = form.id ? this.#data.accounts.find((a) => a.id === form.id) : null;
    const types = {};
    for (const x of this.#types()) {
      if (form.types[x.key]) {
        const settings = {};
        for (const f of x.fields || []) {
          const value = form.values[`${x.key}.${f.key}`];
          if (value !== undefined && value !== "") settings[f.key] = value;
        }
        types[x.key] = settings;
      } else if (editing?.types?.[x.key]) {
        types[x.key] = null;
      }
    }
    if (!Object.values(types).some((x) => x !== null)) {
      notice(t("Choose at least one service."), "warning", noticeBox);
      return;
    }
    const body = {
      name: form.values.name || "",
      password: box.querySelector('[name="password"]')?.value || "",
      types,
    };
    if (!form.id) Object.assign(body, { provider: form.provider, username: form.values.username || "" });
    this.#busy = true;
    notice(form.id ? t("Saving…") : t("Connecting…"), "info");
    try {
      const data = await request(form.id ? `${this.#src}/${form.id}` : this.#src, form.id ? "PUT" : "POST", body);
      this.#data = data;
      this.querySelector("[data-acc-dialog]").hide();
      notice(data.message);
      this.#paint();
    } catch (error) {
      notice(error.message, "danger", noticeBox);
    } finally {
      this.#busy = false;
    }
  }
}

registerComponent("ui-user-accounts", UiUserAccounts);
