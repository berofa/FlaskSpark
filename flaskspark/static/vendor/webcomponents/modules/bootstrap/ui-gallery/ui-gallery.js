import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";

const ICONS = {
  edit: '<path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293z"/>',
  prev: '<path d="M11.354 1.646a.5.5 0 0 1 0 .708L5.707 8l5.647 5.646a.5.5 0 0 1-.708.708l-6-6a.5.5 0 0 1 0-.708l6-6a.5.5 0 0 1 .708 0"/>',
  next: '<path d="M4.646 1.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1 0 .708l-6 6a.5.5 0 0 1-.708-.708L10.293 8 4.646 2.354a.5.5 0 0 1 0-.708"/>',
  close: '<path d="M2.146 2.854a.5.5 0 1 1 .708-.708L8 7.293l5.146-5.147a.5.5 0 0 1 .708.708L8.707 8l5.147 5.146a.5.5 0 0 1-.708.708L8 8.707l-5.146 5.147a.5.5 0 0 1-.708-.708L7.293 8z"/>',
};
const icon = (name) => `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">${ICONS[name]}</svg>`;
const LABELS = { open: "Open {title}", edit: "Edit", prev: "Previous", next: "Next", close: "Close", image: "Image", video: "Video", lightbox: "Viewer" };

/**
 * <ui-gallery>: images and videos as thumbnail tiles; a click opens the lightbox (a modal <dialog> in the top
 * layer) with the full image or the video player, title and description, previous / next (buttons, arrow keys,
 * Home / End, swipe) and Escape to close. Not a Bootstrap component: built from Bootstrap's tokens and buttons,
 * themed with its own --ui-gallery-* tokens.
 *
 * Items: <ui-gallery-item src thumb kind title description item-id> children, or the property `items`
 * = [{id, kind: "image" | "video", thumb, src, title, description}] (the property wins once set). thumb: URL or
 * empty (the tile shows the kind); src: what the lightbox shows.
 *
 * Attributes:
 * - captions: the title under every tile. empty: text without items.
 * - editable: an edit button on every tile and in the lightbox (fires ui-gallery:edit).
 * - sortable: tiles can be dragged to another place (fires ui-gallery:reorder; reorders the items).
 * - open-label ("Open {title}"), edit-label, prev-label, next-label, close-label, image-label, video-label,
 *   lightbox-label: texts.
 * Events (bubble, composed): ui-gallery:open {item, index}, ui-gallery:close, ui-gallery:edit {item},
 * ui-gallery:reorder {ids, items}. Methods: show(index), close(), next(), prev(). Property: index (open item or -1).
 * Parts: grid, item, tile, thumb, play, edit, caption, empty, lightbox, stage, media, bar, title, description,
 * count, control.
 */
export class UiGallery extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-gallery.css", import.meta.url).href];
  static observedAttributes = ["captions", "editable", "sortable", "empty", ...Object.keys(LABELS).map((key) => `${key}-label`)];

  #items = null; // set by the property; null: the children
  #index = -1;
  #dragFrom = -1;
  #touchX = null;
  #observer = null;

  connectedCallback() {
    this.#observer ??= new MutationObserver(() => this.#items === null && this.requestRender());
    this.#observer.observe(this, { childList: true, subtree: true, attributes: true });
    super.connectedCallback();
  }

  disconnectedCallback() {
    this.#observer?.disconnect();
  }

  get items() {
    if (this.#items) {
      return this.#items;
    }
    return [...this.querySelectorAll(":scope > ui-gallery-item")].map((element) => ({
      id: element.getAttribute("item-id") ?? element.id ?? "",
      kind: element.getAttribute("kind") === "video" ? "video" : "image",
      thumb: element.getAttribute("thumb") || (element.getAttribute("kind") === "video" ? "" : element.getAttribute("src") || ""),
      src: element.getAttribute("src") || "",
      title: element.getAttribute("title") || "",
      description: element.getAttribute("description") || "",
    }));
  }

  set items(value) {
    this.#items = Array.isArray(value) ? value : [];
    if (this.#index >= this.#items.length) {
      this.close();
    }
    this.requestRender();
  }

  get index() {
    return this.#index;
  }

  #label(key, title = "") {
    return (this.getAttribute(`${key}-label`) || LABELS[key]).replace("{title}", title);
  }

  #tile(item, index) {
    const kind = this.#label(item.kind === "video" ? "video" : "image");
    const name = item.title || kind;
    const media = item.thumb
      ? `<img part="thumb" class="ui-gallery-thumb" src="${escapeHtml(item.thumb)}" alt="" loading="lazy" draggable="false">`
      : `<span class="ui-gallery-kind">${escapeHtml(kind)}</span>`;
    const play = item.kind === "video" ? '<span class="ui-gallery-play" part="play" aria-hidden="true"></span>' : "";
    const edit = this.hasAttribute("editable")
      ? `<button type="button" class="btn-icon btn-sm btn-solid theme-inverse ui-gallery-edit" part="edit" data-edit="${index}" `
        + `aria-label="${escapeHtml(`${this.#label("edit")}: ${name}`)}" title="${escapeHtml(this.#label("edit"))}">${icon("edit")}</button>` : "";
    const caption = this.hasAttribute("captions") ? `<figcaption part="caption" class="ui-gallery-caption">${escapeHtml(item.title || "")}</figcaption>` : "";
    return `<figure class="ui-gallery-item" part="item" data-index="${index}"${this.hasAttribute("sortable") ? ' draggable="true"' : ""}>`
      + `<button type="button" part="tile" class="ui-gallery-tile" data-open="${index}" aria-label="${escapeHtml(this.#label("open", name))}">${media}${play}</button>`
      + `${edit}${caption}</figure>`;
  }

  render() {
    const items = this.items;
    const empty = this.getAttribute("empty");
    const control = (action) => `<button type="button" class="btn-icon btn-subtle theme-secondary" part="control" data-lb="${action}" `
      + `aria-label="${escapeHtml(this.#label(action))}" title="${escapeHtml(this.#label(action))}">${icon(action)}</button>`;
    const grid = items.length
      ? `<div part="grid" class="ui-gallery-grid">${items.map((item, index) => this.#tile(item, index)).join("")}</div>`
      : empty ? `<p class="ui-gallery-empty" part="empty">${escapeHtml(empty)}</p>` : "";
    return `${grid}<dialog part="lightbox" class="ui-gallery-lightbox" aria-label="${escapeHtml(this.#label("lightbox"))}" data-bs-theme="dark">`
      + '<div class="ui-gallery-stage" part="stage" data-stage></div>'
      + '<div class="ui-gallery-bar" part="bar"><div class="ui-gallery-text" data-text></div><div class="ui-gallery-controls">'
      + `${this.hasAttribute("editable") ? control("edit") : ""}${control("prev")}<span class="ui-gallery-count" part="count" data-count></span>`
      + `${control("next")}${control("close")}</div></div></dialog>`;
  }

  afterRender() {
    const root = this.shadowRoot;
    const grid = root.querySelector(".ui-gallery-grid");
    grid?.addEventListener("click", (event) => {
      const edit = event.target.closest("[data-edit]");
      if (edit) {
        this.#emit("ui-gallery:edit", { item: this.items[Number(edit.dataset.edit)] });
        return;
      }
      const open = event.target.closest("[data-open]");
      if (open) {
        this.show(Number(open.dataset.open));
      }
    });
    const dialog = root.querySelector("dialog");
    dialog.addEventListener("click", (event) => {
      const action = event.target.closest("[data-lb]")?.dataset.lb;
      if (action === "prev") this.prev();
      else if (action === "next") this.next();
      else if (action === "close" || event.target === dialog) this.close();
      else if (action === "edit") this.#emit("ui-gallery:edit", { item: this.items[this.#index] });
    });
    dialog.addEventListener("keydown", (event) => {
      const step = { ArrowLeft: () => this.prev(), ArrowRight: () => this.next(), Home: () => this.show(0),
        End: () => this.show(this.items.length - 1) }[event.key];
      if (step && !event.target.closest?.("video")) {
        event.preventDefault();
        step();
      }
    });
    dialog.addEventListener("close", () => this.#closed());
    dialog.addEventListener("touchstart", (event) => { this.#touchX = event.touches[0]?.clientX ?? null; }, { passive: true });
    dialog.addEventListener("touchend", (event) => {
      const x = event.changedTouches[0]?.clientX;
      if (this.#touchX !== null && x !== undefined && Math.abs(x - this.#touchX) > 60) {
        (x < this.#touchX ? this.next() : this.prev());
      }
      this.#touchX = null;
    });
    if (this.hasAttribute("sortable")) {
      this.#sorting(grid);
    }
    if (this.#index >= 0) {
      const index = this.#index;
      this.#index = -1;
      this.show(index);
    }
  }

  #sorting(grid) {
    if (!grid) {
      return;
    }
    grid.addEventListener("dragstart", (event) => {
      const item = event.target.closest?.(".ui-gallery-item");
      if (!item) return;
      this.#dragFrom = Number(item.dataset.index);
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", String(this.#dragFrom));
      item.classList.add("is-dragging");
    });
    grid.addEventListener("dragover", (event) => {
      if (this.#dragFrom < 0) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      grid.querySelectorAll(".is-target").forEach((el) => el.classList.remove("is-target"));
      event.target.closest?.(".ui-gallery-item")?.classList.add("is-target");
    });
    grid.addEventListener("drop", (event) => {
      const target = event.target.closest?.(".ui-gallery-item");
      if (this.#dragFrom < 0 || !target) return;
      event.preventDefault();
      this.move(this.#dragFrom, Number(target.dataset.index));
      this.#dragFrom = -1;
    });
    grid.addEventListener("dragend", () => {
      this.#dragFrom = -1;
      grid.querySelectorAll(".is-dragging, .is-target").forEach((el) => el.classList.remove("is-dragging", "is-target"));
    });
  }

  /** Moves the item at `from` to `to` (what dragging does): reorders the children or the items. */
  move(from, to) {
    const items = this.items;
    if (from === to || !items[from] || !items[to]) {
      this.requestRender();
      return;
    }
    if (this.#items) {
      const reordered = [...items];
      reordered.splice(to, 0, ...reordered.splice(from, 1));
      this.items = reordered;
    } else {
      const children = [...this.querySelectorAll(":scope > ui-gallery-item")];
      const moved = children[from];
      (to > from ? children[to].after(moved) : children[to].before(moved));
    }
    const now = this.#items || this.items;
    this.#emit("ui-gallery:reorder", { ids: now.map((item) => item.id), items: now });
  }

  show(index) {
    const items = this.items;
    const item = items[index];
    const dialog = this.shadowRoot.querySelector("dialog");
    if (!item || !dialog) return;
    this.#stopVideo();
    this.#index = index;
    const title = escapeHtml(item.title || "");
    this.shadowRoot.querySelector("[data-stage]").innerHTML = item.kind === "video"
      ? `<video part="media" class="ui-gallery-media" src="${escapeHtml(item.src)}" controls autoplay playsinline preload="metadata"></video>`
      : `<img part="media" class="ui-gallery-media" src="${escapeHtml(item.src)}" alt="${title}">`;
    this.shadowRoot.querySelector("[data-text]").innerHTML = (title ? `<div class="ui-gallery-title" part="title">${title}</div>` : "")
      + (item.description ? `<div class="ui-gallery-description" part="description">${escapeHtml(item.description)}</div>` : "");
    this.shadowRoot.querySelector("[data-count]").textContent = items.length > 1 ? `${index + 1} / ${items.length}` : "";
    this.shadowRoot.querySelectorAll('[data-lb="prev"], [data-lb="next"]').forEach((button) => { button.hidden = items.length < 2; });
    if (!dialog.open) dialog.showModal();
    this.#emit("ui-gallery:open", { item, index });
  }

  close() {
    const dialog = this.shadowRoot?.querySelector("dialog");
    if (dialog?.open) dialog.close();
  }

  next() {
    this.#step(1);
  }

  prev() {
    this.#step(-1);
  }

  #step(delta) {
    const count = this.items.length;
    if (count < 2 || this.#index < 0) return;
    this.show((this.#index + delta + count) % count);
  }

  #closed() {
    this.#stopVideo();
    if (this.#index >= 0) {
      this.#index = -1;
      this.#emit("ui-gallery:close", {});
    }
  }

  #stopVideo() {
    const video = this.shadowRoot?.querySelector("[data-stage] video");
    if (video) {
      video.pause();
      video.removeAttribute("src");
      video.load();
    }
  }

  #emit(type, detail) {
    this.dispatchEvent(new CustomEvent(type, { bubbles: true, composed: true, detail }));
  }
}

/** One item of a <ui-gallery> (attributes only: src, thumb, kind, title, description, item-id). */
export class UiGalleryItem extends HTMLElement {}

registerComponent("ui-gallery", UiGallery);
registerComponent("ui-gallery-item", UiGalleryItem);
