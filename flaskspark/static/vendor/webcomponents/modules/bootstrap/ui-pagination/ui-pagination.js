import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { morph } from "../../../core/morph.js";
import { pageWindow } from "../../../core/pages.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

/**
 * <ui-pagination> (Bootstrap 6 pagination): page links for `total` pages with the current one active
 * (aria-current="page"), previous / next, and "…" gaps when there are more pages than `max`.
 *
 * Attributes: total, current (1), max (entries for page numbers incl. gaps, default 7), href (a link pattern,
 * "{page}" is the number, e.g. "?page={page}"; without it the entries are buttons and ui-pagination:change tells
 * the page), size (sm, lg), variant (theme colour), align (start, center, end), arrows ("icons": « », "none"),
 * prev-label ("Previous"), next-label ("Next"), label (the nav's name, default "Pagination").
 * Event ui-pagination:change {page} (cancelable; then current stays). Property current.
 * Parts: nav, list, item, link.
 */
export class UiPagination extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-pagination.css", import.meta.url).href];
  static observedAttributes = ["total", "current", "max", "href", "size", "variant", "align", "arrows", "prev-label", "next-label", "label"];

  constructor() {
    super();
    this.shadowRoot.addEventListener("click", (event) => {
      const link = event.target.closest?.("[data-page]");
      if (!link || link.closest(".disabled, .active")) {
        if (link) event.preventDefault();
        return;
      }
      const page = Number(link.dataset.page);
      if (!this.dispatchEvent(new CustomEvent("ui-pagination:change", { bubbles: true, cancelable: true, detail: { page } }))) {
        event.preventDefault();
        return;
      }
      if (!this.getAttribute("href")) event.preventDefault();
      this.current = page;
    });
  }

  get total() {
    return Math.max(1, Number.parseInt(this.getAttribute("total"), 10) || 1);
  }

  get current() {
    return Math.min(Math.max(1, Number.parseInt(this.getAttribute("current"), 10) || 1), this.total);
  }

  set current(page) {
    this.setAttribute("current", String(page));
  }

  renderShadow() {
    morph(this.shadowRoot, this.render());
  }

  #entry(page, content, { label = "", disabled = false, active = false } = {}) {
    const pattern = this.getAttribute("href");
    const aria = label ? ` aria-label="${escapeHtml(label)}"` : "";
    const current = active ? ' aria-current="page"' : "";
    const link = pattern && !disabled
      ? `<a class="page-link" part="link" href="${escapeHtml(pattern.replaceAll("{page}", String(page)))}" data-page="${page}"${aria}${current}>${content}</a>`
      : `<button type="button" class="page-link" part="link" data-page="${page}"${aria}${current}${disabled ? " disabled" : ""}>${content}</button>`;
    return `<li class="page-item${active ? " active" : ""}${disabled ? " disabled" : ""}" part="item">${link}</li>`;
  }

  render() {
    const total = this.total;
    const current = this.current;
    const max = Number.parseInt(this.getAttribute("max"), 10) || 7;
    const variant = themeColor(this.getAttribute("variant"));
    const size = ["sm", "lg"].includes(this.getAttribute("size")) ? `pagination-${this.getAttribute("size")}` : "";
    const align = { center: "justify-content-center", end: "justify-content-end" }[this.getAttribute("align")] || "";
    const classes = ["pagination", HOST_TOKENS_CLASS, size, variant ? `theme-${variant}` : "", align].filter(Boolean).join(" ");
    const arrows = this.getAttribute("arrows");
    const prevLabel = this.getAttribute("prev-label") || "Previous";
    const nextLabel = this.getAttribute("next-label") || "Next";
    const items = pageWindow(current, total, max).map((page) => (page === "gap"
      ? '<li class="page-item disabled" part="item"><span class="page-link" part="link" aria-hidden="true">…</span></li>'
      : this.#entry(page, String(page), { active: page === current })));
    if (arrows !== "none") {
      const icons = arrows === "icons";
      items.unshift(this.#entry(current - 1, icons ? '<span aria-hidden="true">&laquo;</span>' : escapeHtml(prevLabel),
        { label: icons ? prevLabel : "", disabled: current <= 1 }));
      items.push(this.#entry(current + 1, icons ? '<span aria-hidden="true">&raquo;</span>' : escapeHtml(nextLabel),
        { label: icons ? nextLabel : "", disabled: current >= total }));
    }
    return `<nav part="nav" aria-label="${escapeHtml(this.getAttribute("label") || "Pagination")}"><ul class="${classes}" part="list">${items.join("")}</ul></nav>`;
  }
}

registerComponent("ui-pagination", UiPagination);
