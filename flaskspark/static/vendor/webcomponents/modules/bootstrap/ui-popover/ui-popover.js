import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { computePlacement } from "../../../core/placement.js";

const PLACEMENTS = new Set(["top", "bottom", "left", "right"]);
const BS_SIDE = { top: "top", bottom: "bottom", left: "start", right: "end" };
const FOCUSABLE = "a[href], button, input, select, textarea, [tabindex], ui-button, ui-input, ui-select, ui-textarea, ui-check";
const SUPPORTS_POPOVER = typeof HTMLElement !== "undefined" && Object.prototype.hasOwnProperty.call(HTMLElement.prototype, "popover");
const HOVER_DELAY = 150; // ms before a hover-opened popover closes (time to move into it)
const OPEN = new Set(); // the visible popovers: opening one closes the others at once

/**
 * <ui-popover>: Bootstrap popover (title and body) around its trigger content, without Bootstrap's JS.
 *
 * Like ui-tooltip the box is a popover="manual" element (top layer), so it escapes overflow:hidden
 * containers; browsers without the Popover API fall back to position: fixed. Unlike a tooltip it
 * holds rich content (tables, links) and can be pinned:
 *
 * - trigger="hover" (default): opens on hover and keyboard focus; the pointer may move into the box.
 *   A click (or tap) pins it open until a click outside, Escape or another click on the trigger.
 * - trigger="click": opens and closes on click only.
 *
 * It follows the trigger while the page scrolls. Plain-text triggers get tabindex="0". Only one
 * popover is open at a time: opening one closes the others at once (also a pinned one; nested
 * popovers stay), so moving from trigger to trigger never shows two boxes above each other.
 *
 * Attributes:
 * - heading: title text (or the "heading" slot); without one the header is left out.
 * - text: body text (or the "content" slot for rich content).
 * - placement: "top" (default), "bottom", "left" or "right"; flips when there is no room.
 * - trigger: "hover" (default) or "click".
 * - anchor: selector of an ancestor the box is placed at instead of the trigger (e.g. the row or
 *   grid of several popovers, so the box keeps its place and covers none of them); the arrow still
 *   points at the trigger.
 * - fit-anchor: with anchor, the box takes the anchor's width (top/bottom) or height (left/right).
 *
 * Slots: default (trigger), "heading", "content".
 * CSS parts: trigger, popover, arrow, header, body. Bootstrap's --bs-popover-* are declared on
 * .popover, so override them via ::part(popover).
 * Events: ui-popover:shown / ui-popover:hidden (bubble).
 */
export class UiPopover extends ShadowComponentElement {
  static stylesheet = new URL("./ui-popover.css", import.meta.url).href;
  static observedAttributes = ["heading", "text", "placement", "trigger", "anchor", "fit-anchor"];

  #hover = false;
  #focus = false;
  #pinned = false;
  #visible = false;
  #leaveTimer = 0;
  #onOutside = (event) => {
    if (!event.composedPath().includes(this)) {
      this.hide();
    }
  };
  #frame = 0;
  #onScroll = () => {
    if (!this.#frame) {
      this.#frame = requestAnimationFrame(() => {
        this.#frame = 0;
        if (this.#visible) this.#position();
      });
    }
  };

  constructor() {
    super();
    // The box is part of the shadow tree: entering it keeps a hover-opened popover open.
    this.addEventListener("pointerenter", (event) => {
      if (event.pointerType !== "touch" && !this.#clickOnly) {
        clearTimeout(this.#leaveTimer);
        this.#hover = true;
        this.#update();
      }
    });
    this.addEventListener("pointerleave", (event) => {
      if (event.pointerType !== "touch" && !this.#clickOnly) {
        clearTimeout(this.#leaveTimer);
        this.#leaveTimer = setTimeout(() => {
          this.#hover = false;
          this.#update();
        }, HOVER_DELAY);
      }
    });
    this.addEventListener("click", (event) => {
      // Clicks inside the box (links, text selection) don't toggle.
      if (event.composedPath().includes(this.#box)) return;
      this.#pinned = !this.#pinned || !this.#visible;
      if (!this.#pinned) {
        this.#hover = false;
        this.#focus = false;
      }
      this.#update();
    });
    this.addEventListener("focusin", () => {
      if (!this.#clickOnly) {
        this.#focus = true;
        this.#update();
      }
    });
    this.addEventListener("focusout", (event) => {
      if (event.relatedTarget && this.contains(event.relatedTarget)) return;
      this.#focus = false;
      this.#update();
    });
    this.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        this.hide();
      } else if ((event.key === "Enter" || event.key === " ") && event.target === this) {
        event.preventDefault();
        this.click();
      }
    });
  }

  disconnectedCallback() {
    clearTimeout(this.#leaveTimer);
    this.hide();
  }

  get #clickOnly() {
    return this.getAttribute("trigger") === "click";
  }

  get #box() {
    return this.shadowRoot?.querySelector("[data-popover]");
  }

  render() {
    const heading = this.getAttribute("heading") || "";
    const text = this.getAttribute("text") || "";
    const hasHeading = heading || this.querySelector('[slot="heading"]');
    return `
      <span class="ui-popover-trigger" part="trigger"><slot></slot></span>
      <div class="popover" role="dialog" part="popover" data-popover ${SUPPORTS_POPOVER ? 'popover="manual"' : "hidden"}>
        <div class="popover-arrow" part="arrow" data-arrow></div>
        <div class="popover-header" part="header" ${hasHeading ? "" : "hidden"}><slot name="heading">${escapeHtml(heading)}</slot></div>
        <div class="popover-body" part="body"><slot name="content">${escapeHtml(text)}</slot></div>
      </div>
    `;
  }

  afterRender() {
    if (!this.hasAttribute("tabindex") && !this.querySelector(FOCUSABLE)) {
      this.setAttribute("tabindex", "0");
    }
    this.setAttribute("aria-haspopup", "dialog");
    if (this.#visible) {
      this.#visible = false;
      this.show();
    }
  }

  show() {
    const box = this.#box;
    const hasContent = this.getAttribute("text") || this.querySelector('[slot="content"]');
    if (!box || !hasContent || this.#visible) {
      return;
    }
    for (const other of [...OPEN]) {
      if (other !== this && !other.contains(this) && !this.contains(other)) other.hide();
    }
    OPEN.add(this);
    this.#visible = true;
    if (SUPPORTS_POPOVER) {
      if (!box.matches(":popover-open")) box.showPopover();
    } else {
      box.hidden = false;
    }
    this.#position();
    box.classList.add("show");
    this.setAttribute("aria-expanded", "true");
    document.addEventListener("pointerdown", this.#onOutside, true);
    window.addEventListener("scroll", this.#onScroll, { capture: true, passive: true });
    window.addEventListener("resize", this.#onScroll, { passive: true });
    this.dispatchEvent(new CustomEvent("ui-popover:shown", { bubbles: true }));
  }

  hide() {
    this.#hover = false;
    this.#focus = false;
    this.#pinned = false;
    this.#hideBox();
  }

  #update() {
    if (this.#hover || this.#focus || this.#pinned) {
      this.show();
    } else {
      this.#hideBox();
    }
  }

  #hideBox() {
    document.removeEventListener("pointerdown", this.#onOutside, true);
    window.removeEventListener("scroll", this.#onScroll, { capture: true });
    window.removeEventListener("resize", this.#onScroll);
    if (!this.#visible) {
      return;
    }
    this.#visible = false;
    OPEN.delete(this);
    const box = this.#box;
    if (box) {
      box.classList.remove("show");
      if (SUPPORTS_POPOVER) {
        if (box.matches(":popover-open")) box.hidePopover();
      } else {
        box.hidden = true;
      }
    }
    this.setAttribute("aria-expanded", "false");
    this.dispatchEvent(new CustomEvent("ui-popover:hidden", { bubbles: true }));
  }

  #position() {
    const box = this.#box;
    const trigger = this.shadowRoot.querySelector(".ui-popover-trigger");
    const target = (trigger.getClientRects().length ? trigger : this).getBoundingClientRect();
    const anchorEl = this.hasAttribute("anchor") ? this.parentElement?.closest(this.getAttribute("anchor")) : null;
    const anchor = anchorEl ? anchorEl.getBoundingClientRect() : target;
    const raw = this.getAttribute("placement");
    const preferred = PLACEMENTS.has(raw) ? raw : "top";
    const vertical = preferred === "top" || preferred === "bottom";

    box.style.left = "0px";
    box.style.top = "0px";
    for (const prop of ["width", "minWidth", "maxWidth", "height", "minHeight", "maxHeight"]) box.style[prop] = "";
    if (anchorEl && this.hasAttribute("fit-anchor")) {
      const [size, value] = vertical ? ["Width", anchor.width] : ["Height", anchor.height];
      for (const prop of [size.toLowerCase(), `min${size}`, `max${size}`]) box.style[prop] = `${Math.round(value)}px`;
    }
    box.className = `popover bs-popover-${BS_SIDE[preferred]}`;
    const rect = box.getBoundingClientRect();
    const arrow = box.querySelector("[data-arrow]");
    const arrowSize = preferred === "top" || preferred === "bottom" ? arrow.offsetHeight : arrow.offsetWidth;
    const result = computePlacement(
      anchor,
      { width: rect.width, height: rect.height },
      { width: document.documentElement.clientWidth, height: document.documentElement.clientHeight },
      preferred,
      { gap: (arrowSize || 8) + 2 },
    );

    box.className = `popover bs-popover-${BS_SIDE[result.placement]} show`;
    box.style.left = `${Math.round(result.left)}px`;
    box.style.top = `${Math.round(result.top)}px`;
    const arrowRect = arrow.getBoundingClientRect();
    // At a separate anchor the arrow points at the trigger, kept inside the box's rounded corners.
    const pointAt = (offset, size) => (anchorEl ? Math.max(12, Math.min(offset, size - 12)) : offset);
    if (result.placement === "top" || result.placement === "bottom") {
      const offset = pointAt(anchorEl ? target.left + target.width / 2 - result.left : result.arrow, rect.width);
      arrow.style.top = "";
      arrow.style.left = `${Math.round(offset - arrowRect.width / 2)}px`;
    } else {
      const offset = pointAt(anchorEl ? target.top + target.height / 2 - result.top : result.arrow, rect.height);
      arrow.style.left = "";
      arrow.style.top = `${Math.round(offset - arrowRect.height / 2)}px`;
    }
  }
}

registerComponent("ui-popover", UiPopover);
