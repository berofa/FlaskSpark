/**
 * <ui-attachments owner-type="note" owner-id="12">: the images, videos and documents of an item
 * (flaskspark.core.attachments), for every module that names an AttachmentOwner in its manifest.
 *
 * - Images and videos in a <ui-gallery> (lightbox; sort by dragging, pencil to edit), documents as a list (open in
 *   the browser, e.g. PDFs; download; edit).
 * - <ui-dropzone> uploads one file after the other with a progress bar each (the server streams them to the
 *   storage); the title is the file name without its extension and can be changed afterwards. Without the storage
 *   the drop zone is disabled and says so; files above the limit are refused before they are sent.
 * - Edit: title (required) and description, delete with a second click.
 * Attribute `readonly`: no upload, no changes. Fires "attachments:changed" (bubbles, detail {count}) after every
 * change. Texts through the app's translations (flaskspark/i18n.js).
 *
 *   <script type="module" src="{{ url_for('static', filename='flaskspark/js/ui-attachments.js') }}"></script>
 */
import { registerComponent } from "webcomponents/core/registry.js";
import { LightComponentElement } from "webcomponents/core/light-component-element.js";
import { escapeHtml as esc } from "webcomponents/core/escape.js";
import { icon } from "flaskspark/icons.js";
import { notice } from "flaskspark/ui.js";
import { preload, t } from "flaskspark/i18n.js";
import * as api from "flaskspark/attachments.js";

const N_ = (text) => text; // marks a text for the catalogue (scripts/core-i18n)

const MEDIA = new Set(["image", "video"]);
const ready = preload([
  N_("No files."), N_("Download"), N_("Edit"), N_("Open in the browser"), N_("Title"), N_("Description"), N_("Delete"), N_("Really delete?"), N_("Cancel"),
  N_("Save"), N_("waiting"), N_("{percent} of {size}"), N_("Dismiss"), N_("Storage not available"), N_("Uploading works again once the storage is back."),
  N_("Drop images, videos or documents here or click"), N_("Several at once, at most {size} each"), N_("Several at once"),
  N_("The file is too large."), N_("Upload failed ({status})."), N_("Connection lost."), N_("Cancelled."), N_("Saved"), N_("File deleted."),
  N_("Open {title}"), N_("Previous"), N_("Next"), N_("Close"), N_("Image"), N_("Video"),
]);

export class UiAttachments extends LightComponentElement {
  static stylesheet = new URL("../css/ui-attachments.css", import.meta.url).href;
  static observedAttributes = ["owner-type", "owner-id", "readonly"];

  #items = [];
  #ready = false;
  #maxSize = 0;
  #loaded = false;
  #editing = null; // id of the file being edited
  #confirmDelete = null;
  #queue = []; // [{id, file, loaded, total, started, done, error}]
  #jobs = 0;
  #uploading = false;
  #key = "";

  get #owner() {
    return [this.getAttribute("owner-type") || "", Number(this.getAttribute("owner-id") || 0)];
  }

  get #writable() {
    return !this.hasAttribute("readonly");
  }

  render() {
    return `
      <div data-notice></div>
      <ui-gallery captions${this.#writable ? " editable sortable" : ""}></ui-gallery>
      <div data-edit></div>
      <div data-docs></div>
      <div data-queue></div>
      ${this.#writable ? '<ui-dropzone multiple class="mt-2" data-drop></ui-dropzone>' : ""}`;
  }

  afterRender() {
    const gallery = this.querySelector("ui-gallery");
    gallery.addEventListener("ui-gallery:edit", (e) => this.#edit(e.detail.item.id));
    gallery.addEventListener("ui-gallery:reorder", (e) => this.#reorder(e.detail.ids));
    this.querySelector("[data-drop]")?.addEventListener("ui-dropzone:files", (e) => this.#enqueue(e.detail.files));
    this.addEventListener("click", (e) => {
      const el = e.target.closest?.("[data-att]");
      if (el && !el.hasAttribute("disabled")) this.#action(el.dataset.att, Number(el.dataset.id || 0));
    });
    const [type, id] = this.#owner;
    const key = `${type}:${id}`;
    if (key !== this.#key) {
      this.#key = key;
      this.#loaded = false;
      this.#items = [];
      this.#queue = [];
      this.#editing = null;
    }
    ready.then(() => {
      for (const [attr, text] of [["open-label", t("Open {title}")], ["edit-label", t("Edit")], ["prev-label", t("Previous")],
        ["next-label", t("Next")], ["close-label", t("Close")], ["image-label", t("Image")], ["video-label", t("Video")]]) {
        gallery.setAttribute(attr, text);
      }
      if (this.#loaded) this.#paint();
      else this.load();
    });
  }

  /** Read the item's files again (e.g. after the event "attachments" of the live channel). */
  async load() {
    const [type, id] = this.#owner;
    if (!type || !id) return;
    try {
      const data = await api.list(type, id);
      this.#items = data.attachments;
      this.#ready = data.ready;
      this.#maxSize = data.max_size || 0;
      this.#loaded = true;
    } catch (error) {
      notice(error.message, "warning");
    }
    this.#paint();
  }

  #paint() {
    const media = this.#items.filter((a) => MEDIA.has(a.kind));
    const docs = this.#items.filter((a) => !MEDIA.has(a.kind));
    const gallery = this.querySelector("ui-gallery");
    if (!gallery) return;
    gallery.items = media.map((a) => ({
      id: a.id, kind: a.kind, thumb: a.thumb, title: a.title, description: a.description,
      src: a.kind === "image" ? `${a.url}&display=1` : a.url,
    }));
    gallery.hidden = !media.length;
    this.querySelector("[data-docs]").innerHTML = docs.length
      ? `<div class="ui-att-docs">${docs.map((a) => this.#docRow(a)).join("")}</div>` : "";
    this.querySelector("[data-edit]").innerHTML = this.#editHtml();
    this.#paintQueue();
    const drop = this.querySelector("[data-drop]");
    if (drop) {
      const away = this.#loaded && !this.#ready;
      drop.toggleAttribute("disabled", away);
      drop.setAttribute("text", away ? t("Storage not available") : t("Drop images, videos or documents here or click"));
      drop.setAttribute("hint", away ? t("Uploading works again once the storage is back.")
        : this.#maxSize ? t("Several at once, at most {size} each", { size: api.fileSize(this.#maxSize) }) : t("Several at once"));
      if (this.#maxSize) drop.setAttribute("max-size", String(this.#maxSize));
      else drop.removeAttribute("max-size");
    }
    if (this.#loaded && !this.#items.length && !this.#writable) {
      this.querySelector("[data-docs]").innerHTML = `<p class="app-muted small mb-0">${esc(t("No files."))}</p>`;
    }
  }

  #docRow(a) {
    const preview = a.thumb
      ? `<img src="${esc(a.thumb)}" alt="" class="ui-att-doc-thumb" loading="lazy">`
      : `<span class="ui-att-doc-thumb ui-att-doc-type">${esc((a.name.split(".").pop() || "?").slice(0, 4).toUpperCase())}</span>`;
    return `
      <div class="ui-att-doc" data-id="${a.id}">
        <a href="${esc(a.url)}" target="_blank" rel="noopener" class="ui-att-doc-link" title="${esc(t("Open in the browser"))}">${preview}</a>
        <div class="ui-att-doc-main">
          <a href="${esc(a.url)}" target="_blank" rel="noopener" class="fw-semibold">${esc(a.title)}</a>
          ${a.description ? `<div class="small app-muted">${esc(a.description)}</div>` : ""}
          <div class="small app-muted">${esc(a.name)} · ${api.fileSize(a.size)}</div>
        </div>
        <div class="ui-att-doc-actions">
          <ui-button size="sm" variant="secondary" outline href="${esc(a.url)}&amp;download=1" label="${esc(t("Download"))}" title="${esc(t("Download"))}">${icon("download")}</ui-button>
          ${this.#writable ? `<ui-button size="sm" variant="secondary" outline data-att="edit" data-id="${a.id}" label="${esc(t("Edit"))}" title="${esc(t("Edit"))}">${icon("pencil")}</ui-button>` : ""}
        </div>
      </div>`;
  }

  #editHtml() {
    const a = this.#items.find((x) => x.id === this.#editing);
    if (!a) return "";
    const remove = this.#confirmDelete === a.id
      ? `<ui-button size="sm" variant="danger" data-att="delete" data-id="${a.id}">${esc(t("Really delete?"))}</ui-button>`
      : `<ui-button size="sm" variant="danger" outline data-att="delete" data-id="${a.id}">${icon("trash")} ${esc(t("Delete"))}</ui-button>`;
    return `
      <div class="ui-att-edit">
        <div class="small app-muted mb-2">${esc(a.name)} · ${api.fileSize(a.size)}</div>
        <div class="row g-2">
          <div class="col-12"><ui-input size="sm" data-field="title" prefix="${esc(t("Title"))}" required maxlength="200" value="${esc(a.title)}"></ui-input></div>
          <div class="col-12"><ui-textarea size="sm" data-field="description" prefix="${esc(t("Description"))}" rows="2" value="${esc(a.description)}"></ui-textarea></div>
        </div>
        <div class="d-flex gap-2 mt-2">
          ${remove}
          <span class="ms-auto"></span>
          <ui-button size="sm" variant="secondary" outline data-att="cancel">${esc(t("Cancel"))}</ui-button>
          <ui-button size="sm" data-att="save" data-id="${a.id}">${esc(t("Save"))}</ui-button>
        </div>
      </div>`;
  }

  #paintQueue() {
    const box = this.querySelector("[data-queue]");
    if (!box) return;
    const rows = this.#queue.filter((q) => !q.done || q.error);
    box.innerHTML = rows.map((q) => {
      const pct = q.total ? Math.round((q.loaded / q.total) * 100) : 0;
      const state = q.error ? esc(q.error) : q.started ? esc(t("{percent} of {size}", { percent: `${pct} %`, size: api.fileSize(q.file.size) })) : esc(t("waiting"));
      return `
        <div class="ui-att-upload">
          <div class="d-flex justify-content-between small gap-2">
            <span class="text-truncate">${esc(q.file.name)}</span>
            <span class="text-nowrap ${q.error ? "text-danger" : "app-muted"}">${state}</span>
          </div>
          <div class="progress" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100" style="height: 0.35rem">
            <div class="progress-bar${q.error ? " bg-danger" : ""}" style="width: ${q.error ? 100 : pct}%"></div>
          </div>
          ${q.error ? `<button type="button" class="btn btn-link btn-sm p-0" data-att="dismiss" data-id="${q.id}">${esc(t("Dismiss"))}</button>` : ""}
        </div>`;
    }).join("");
  }

  #enqueue(files) {
    this.#queue.push(...files.map((file) => ({
      id: ++this.#jobs, file, loaded: 0, total: file.size, started: false, done: false, error: null,
    })));
    this.#paintQueue();
    this.#next();
  }

  async #next() {
    if (this.#uploading) return;
    const job = this.#queue.find((q) => !q.started);
    if (!job) {
      this.#queue = this.#queue.filter((q) => q.error);
      this.#paintQueue();
      return;
    }
    this.#uploading = true;
    job.started = true;
    const [type, id] = this.#owner;
    let last = 0;
    try {
      if (this.#maxSize && job.file.size > this.#maxSize) throw new Error(t("The file is too large."));
      const { attachment } = await api.upload(type, id, job.file, (loaded, total) => {
        Object.assign(job, { loaded, total });
        if (Date.now() - last > 200) {
          last = Date.now();
          this.#paintQueue();
        }
      }).promise;
      job.done = true;
      this.#items.push(attachment);
      this.#paint();
      this.#changed();
    } catch (error) {
      job.done = true;
      job.error = error.message;
      this.#paintQueue();
    } finally {
      this.#uploading = false;
    }
    this.#next();
  }

  #edit(id) {
    this.#editing = id;
    this.#confirmDelete = null;
    this.querySelector("ui-gallery")?.close?.();
    this.querySelector("[data-edit]").innerHTML = this.#editHtml();
    this.querySelector("[data-edit] ui-input")?.focus?.();
  }

  async #reorder(ids) {
    const [type, id] = this.#owner;
    const docs = this.#items.filter((a) => !MEDIA.has(a.kind)).map((a) => a.id);
    try {
      this.#items = (await api.reorder(type, id, [...ids, ...docs])).attachments;
      this.#changed();
    } catch (error) {
      notice(error.message, "danger");
      this.load();
    }
  }

  async #action(action, id) {
    if (action === "edit") return this.#edit(id);
    if (action === "cancel") {
      this.#editing = null;
      this.querySelector("[data-edit]").innerHTML = "";
      return undefined;
    }
    if (action === "dismiss") {
      this.#queue = this.#queue.filter((q) => q.id !== id);
      this.#paintQueue();
      return undefined;
    }
    if (action === "delete" && this.#confirmDelete !== id) {
      this.#confirmDelete = id;
      this.querySelector("[data-edit]").innerHTML = this.#editHtml();
      return undefined;
    }
    try {
      if (action === "save") {
        const field = (name) => this.querySelector(`[data-edit] [data-field="${name}"]`)?.value ?? "";
        const { attachment } = await api.update(id, { title: field("title").trim(), description: field("description") });
        this.#items = this.#items.map((a) => (a.id === id ? attachment : a));
        notice(t("Saved"));
      } else if (action === "delete") {
        await api.remove(id);
        this.#items = this.#items.filter((a) => a.id !== id);
        notice(t("File deleted."));
      }
      this.#editing = null;
      this.#confirmDelete = null;
      this.#paint();
      this.#changed();
    } catch (error) {
      notice(error.message, "danger");
    }
    return undefined;
  }

  #changed() {
    this.dispatchEvent(new CustomEvent("attachments:changed", { bubbles: true, detail: { count: this.#items.length } }));
  }
}

registerComponent("ui-attachments", UiAttachments);
