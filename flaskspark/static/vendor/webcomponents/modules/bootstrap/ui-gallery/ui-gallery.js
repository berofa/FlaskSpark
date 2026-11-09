import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";

/**
 * <ui-gallery>: images and videos as tiles of their thumbnails; a click opens the lightbox (a modal <dialog> in the
 * top layer) with the full image or the video player, title and description, previous/next (buttons, arrow keys,
 * swipe) and Escape to close. Not a Bootstrap component: styled with Bootstrap's tokens.
 *
 * Data: property `items` = [{id, kind: "image" | "video", thumb, src, title, description}] (thumb: URL or null,
 * then the tile shows the kind; src: what the lightbox shows). Setting it renders the tiles again.
 *
 * Attributes:
 * - captions: the title under every tile.
 * - editable: a pencil on every tile and in the lightbox fires ui-gallery:edit.
 * - sortable: tiles can be dragged to another place (pointer with a mouse; fires ui-gallery:reorder).
 * - empty: text without items (default: nothing is shown).
 *
 * Events (bubble, composed): ui-gallery:open {item, index}, ui-gallery:edit {item}, ui-gallery:reorder {ids}.
 * Methods: show(index), close().
 * CSS parts: grid, tile, thumb, caption, lightbox, media, lightbox-caption.
 * Custom properties: --ui-gallery-tile-size (min. width, default 8rem), --ui-gallery-gap, --ui-gallery-radius,
 *   --ui-gallery-backdrop.
 */
export class UiGallery extends ShadowComponentElement {
  static stylesheet = new URL("./ui-gallery.css", import.meta.url).href;
  static observedAttributes = ["captions", "editable", "sortable", "empty"];

  #items = [];
  #index = -1;
  #dragFrom = -1;
  #touchX = null;

  get items() {
    return this.#items;
  }

  set items(value) {
    this.#items = Array.isArray(value) ? value : [];
    if (this.#index >= this.#items.length) this.close();
    this.requestRender();
  }

  #tile(item, index) {
    const label = item.kind === "video" ? "Video" : "Bild";
    const media = item.thumb
      ? `<img part="thumb" src="${escapeHtml(item.thumb)}" alt="${escapeHtml(item.title || label)}" loading="lazy" draggable="false">`
      : `<span class="ui-gallery__kind">${label}</span>`;
    return `
      <figure class="ui-gallery__item" data-index="${index}"${this.hasAttribute("sortable") ? ' draggable="true"' : ""}>
        <button type="button" part="tile" class="ui-gallery__tile" data-open="${index}" aria-label="${escapeHtml(item.title || label)} öffnen">
          ${media}
          ${item.kind === "video" ? '<span class="ui-gallery__play" aria-hidden="true"></span>' : ""}
        </button>
        ${this.hasAttribute("editable") ? `<button type="button" class="ui-gallery__edit" data-edit="${index}" aria-label="Bearbeiten" title="Bearbeiten">${PENCIL}</button>` : ""}
        ${this.hasAttribute("captions") ? `<figcaption part="caption" class="ui-gallery__caption">${escapeHtml(item.title || "")}</figcaption>` : ""}
      </figure>`;
  }

  render() {
    const empty = this.getAttribute("empty");
    return `
      ${this.#items.length
        ? `<div part="grid" class="ui-gallery">${this.#items.map((item, i) => this.#tile(item, i)).join("")}</div>`
        : empty ? `<p class="ui-gallery__empty">${escapeHtml(empty)}</p>` : ""}
      <dialog part="lightbox" class="ui-gallery__lightbox" aria-label="Ansicht">
        <div class="ui-gallery__stage" data-stage></div>
        <div part="lightbox-caption" class="ui-gallery__bar">
          <div class="ui-gallery__text" data-text></div>
          <div class="ui-gallery__controls">
            ${this.hasAttribute("editable") ? `<button type="button" class="ui-gallery__btn" data-lb="edit" aria-label="Bearbeiten" title="Bearbeiten">${PENCIL}</button>` : ""}
            <button type="button" class="ui-gallery__btn" data-lb="prev" aria-label="Vorheriges" title="Vorheriges">&#8249;</button>
            <span class="ui-gallery__count" data-count></span>
            <button type="button" class="ui-gallery__btn" data-lb="next" aria-label="Nächstes" title="Nächstes">&#8250;</button>
            <button type="button" class="ui-gallery__btn" data-lb="close" aria-label="Schliessen" title="Schliessen">&times;</button>
          </div>
        </div>
      </dialog>`;
  }

  afterRender() {
    const root = this.shadowRoot;
    root.querySelector(".ui-gallery")?.addEventListener("click", (event) => {
      const edit = event.target.closest("[data-edit]");
      if (edit) return this.#emit("ui-gallery:edit", { item: this.#items[Number(edit.dataset.edit)] });
      const open = event.target.closest("[data-open]");
      if (open) this.show(Number(open.dataset.open));
      return undefined;
    });
    const dialog = root.querySelector("dialog");
    dialog.addEventListener("click", (event) => {
      const action = event.target.closest("[data-lb]")?.dataset.lb;
      if (action === "prev") this.#step(-1);
      else if (action === "next") this.#step(1);
      else if (action === "close" || event.target === dialog) this.close();
      else if (action === "edit") this.#emit("ui-gallery:edit", { item: this.#items[this.#index] });
    });
    dialog.addEventListener("keydown", (event) => {
      if (event.key === "ArrowLeft") this.#step(-1);
      else if (event.key === "ArrowRight") this.#step(1);
    });
    dialog.addEventListener("close", () => this.#stop());
    dialog.addEventListener("touchstart", (event) => { this.#touchX = event.touches[0]?.clientX ?? null; }, { passive: true });
    dialog.addEventListener("touchend", (event) => {
      const x = event.changedTouches[0]?.clientX;
      if (this.#touchX !== null && x !== undefined && Math.abs(x - this.#touchX) > 60) this.#step(x < this.#touchX ? 1 : -1);
      this.#touchX = null;
    });
    if (this.hasAttribute("sortable")) this.#sorting(root.querySelector(".ui-gallery"));
    if (this.#index >= 0) this.show(this.#index);
  }

  #sorting(grid) {
    if (!grid) return;
    grid.addEventListener("dragstart", (event) => {
      const item = event.target.closest?.(".ui-gallery__item");
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
    });
    grid.addEventListener("drop", (event) => {
      const target = event.target.closest?.(".ui-gallery__item");
      if (this.#dragFrom < 0 || !target) return;
      event.preventDefault();
      const to = Number(target.dataset.index);
      const items = [...this.#items];
      const [moved] = items.splice(this.#dragFrom, 1);
      items.splice(to, 0, moved);
      this.#dragFrom = -1;
      if (items.every((item, i) => item === this.#items[i])) return this.requestRender();
      this.items = items;
      this.#emit("ui-gallery:reorder", { ids: items.map((item) => item.id) });
      return undefined;
    });
    grid.addEventListener("dragend", () => {
      this.#dragFrom = -1;
      grid.querySelectorAll(".is-dragging").forEach((el) => el.classList.remove("is-dragging"));
    });
  }

  show(index) {
    const item = this.#items[index];
    const dialog = this.shadowRoot.querySelector("dialog");
    if (!item || !dialog) return;
    this.#stop();
    this.#index = index;
    const title = escapeHtml(item.title || "");
    this.shadowRoot.querySelector("[data-stage]").innerHTML = item.kind === "video"
      ? `<video part="media" class="ui-gallery__media" src="${escapeHtml(item.src)}" controls autoplay playsinline preload="metadata"></video>`
      : `<img part="media" class="ui-gallery__media" src="${escapeHtml(item.src)}" alt="${title}">`;
    this.shadowRoot.querySelector("[data-text]").innerHTML = `
      ${title ? `<div class="ui-gallery__title">${title}</div>` : ""}
      ${item.description ? `<div class="ui-gallery__description">${escapeHtml(item.description)}</div>` : ""}`;
    this.shadowRoot.querySelector("[data-count]").textContent = this.#items.length > 1 ? `${index + 1} / ${this.#items.length}` : "";
    this.shadowRoot.querySelectorAll('[data-lb="prev"], [data-lb="next"]').forEach((b) => { b.hidden = this.#items.length < 2; });
    if (!dialog.open) dialog.showModal();
    this.#emit("ui-gallery:open", { item, index });
  }

  close() {
    const dialog = this.shadowRoot?.querySelector("dialog");
    this.#index = -1;
    if (dialog?.open) dialog.close();
  }

  #step(delta) {
    if (this.#items.length < 2 || this.#index < 0) return;
    this.show((this.#index + delta + this.#items.length) % this.#items.length);
  }

  #stop() {
    const video = this.shadowRoot?.querySelector("[data-stage] video");
    if (video) {
      video.pause();
      video.removeAttribute("src");
      video.load();
    }
    if (!this.shadowRoot?.querySelector("dialog")?.open) this.#index = -1;
  }

  #emit(type, detail) {
    this.dispatchEvent(new CustomEvent(type, { bubbles: true, composed: true, detail }));
  }
}

const PENCIL = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true"><path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293z"/></svg>';

registerComponent("ui-gallery", UiGallery);
