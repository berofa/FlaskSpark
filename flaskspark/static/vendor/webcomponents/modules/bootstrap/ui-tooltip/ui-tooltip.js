import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { computePlacement } from "../../../core/placement.js";

const PLACEMENTS = new Set(["top", "bottom", "left", "right"]);
const BS_SIDE = { top: "top", bottom: "bottom", left: "start", right: "end" };
const FOCUSABLE = "a[href], button, input, select, textarea, [tabindex], ui-button, ui-input, ui-select, ui-textarea, ui-check";
const SUPPORTS_POPOVER = typeof HTMLElement !== "undefined" && Object.prototype.hasOwnProperty.call(HTMLElement.prototype, "popover");

/**
 * <ui-tooltip>: Bootstrap tooltip around its trigger content, without Bootstrap's JS.
 *
 * The bubble is a popover="manual" element (top layer), so it escapes
 * overflow:hidden containers like cards; browsers without the Popover API
 * fall back to position: fixed.
 *
 * Shows on hover and keyboard focus, toggles on tap (touch), hides on Escape,
 * on a tap outside; it follows the trigger while the page scrolls. Plain-text triggers (e.g. an
 * info icon) get tabindex="0" so keyboard users can reach them.
 *
 * Attributes:
 * - text: tooltip text (use the "content" slot for rich content).
 * - placement: "top" (default), "bottom", "left" or "right"; flips when there
 *   is no room.
 *
 * Slots: default (trigger), "content".
 * CSS parts: trigger, tooltip, arrow, inner. Bootstrap's --bs-tooltip-* are
 * declared on .tooltip, so override them via ::part(tooltip).
 * Events: ui-tooltip:shown / ui-tooltip:hidden (bubble).
 */
export class UiTooltip extends ShadowComponentElement {
  static stylesheet = new URL("./ui-tooltip.css", import.meta.url).href;
  static observedAttributes = ["text", "placement"];

  #hover = false;
  #focus = false;
  #pinned = false;
  #lastTouch = 0;
  #visible = false;
  #onOutside = (event) => {
    if (!event.composedPath().includes(this)) {
      this.#pinned = false;
      this.#update();
    }
  };
  #frame = 0;
  // Follow the trigger while scrolling (focus moves often scroll the trigger into view).
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
    this.addEventListener("pointerenter", (event) => {
      if (event.pointerType !== "touch") {
        this.#hover = true;
        this.#update();
      }
    });
    this.addEventListener("pointerleave", (event) => {
      if (event.pointerType !== "touch") {
        this.#hover = false;
        this.#update();
      }
    });
    this.addEventListener("pointerdown", (event) => {
      if (event.pointerType === "touch") {
        this.#lastTouch = Date.now();
        this.#pinned = !this.#visible;
        this.#focus = false;
        this.#update();
      }
    });
    this.addEventListener("focusin", () => {
      // A tap also focuses the trigger; the tap toggle above already decided.
      if (Date.now() - this.#lastTouch > 600) {
        this.#focus = true;
        this.#update();
      }
    });
    this.addEventListener("focusout", () => {
      this.#focus = false;
      this.#pinned = false;
      this.#update();
    });
    this.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        this.hide();
      }
    });
  }

  disconnectedCallback() {
    this.hide();
  }

  get #tip() {
    return this.shadowRoot.querySelector("[data-tooltip]");
  }

  render() {
    const text = this.getAttribute("text") || "";
    return `
      <span class="ui-tooltip-trigger" part="trigger"><slot></slot></span>
      <div class="tooltip" role="tooltip" part="tooltip" data-tooltip ${SUPPORTS_POPOVER ? 'popover="manual"' : "hidden"}>
        <div class="tooltip-arrow" part="arrow" data-arrow></div>
        <div class="tooltip-inner" part="inner"><slot name="content">${escapeHtml(text)}</slot></div>
      </div>
    `;
  }

  afterRender() {
    if (!this.hasAttribute("tabindex") && !this.querySelector(FOCUSABLE)) {
      this.setAttribute("tabindex", "0");
    }
    if (this.#visible) {
      this.#visible = false;
      this.show();
    }
  }

  show() {
    const tip = this.#tip;
    const hasContent = this.getAttribute("text") || this.querySelector('[slot="content"]');
    if (!tip || !hasContent || this.#visible) {
      return;
    }
    this.#visible = true;
    if (SUPPORTS_POPOVER) {
      if (!tip.matches(":popover-open")) tip.showPopover();
    } else {
      tip.hidden = false;
    }
    this.#position();
    tip.classList.add("show");
    document.addEventListener("pointerdown", this.#onOutside, true);
    window.addEventListener("scroll", this.#onScroll, { capture: true, passive: true });
    window.addEventListener("resize", this.#onScroll, { passive: true });
    this.dispatchEvent(new CustomEvent("ui-tooltip:shown", { bubbles: true }));
  }

  hide() {
    this.#hover = false;
    this.#focus = false;
    this.#pinned = false;
    this.#hideTip();
  }

  #update() {
    if (this.#hover || this.#focus || this.#pinned) {
      this.show();
    } else {
      this.#hideTip();
    }
  }

  #hideTip() {
    document.removeEventListener("pointerdown", this.#onOutside, true);
    window.removeEventListener("scroll", this.#onScroll, { capture: true });
    window.removeEventListener("resize", this.#onScroll);
    if (!this.#visible) {
      return;
    }
    this.#visible = false;
    const tip = this.#tip;
    if (tip) {
      tip.classList.remove("show");
      if (SUPPORTS_POPOVER) {
        if (tip.matches(":popover-open")) tip.hidePopover();
      } else {
        tip.hidden = true;
      }
    }
    this.dispatchEvent(new CustomEvent("ui-tooltip:hidden", { bubbles: true }));
  }

  #position() {
    const tip = this.#tip;
    const trigger = this.shadowRoot.querySelector(".ui-tooltip-trigger");
    const anchor = (trigger.getClientRects().length ? trigger : this).getBoundingClientRect();
    const raw = this.getAttribute("placement");
    const preferred = PLACEMENTS.has(raw) ? raw : "top";

    // Measure with the arrow side of the preferred placement, then place.
    tip.style.left = "0px";
    tip.style.top = "0px";
    tip.className = `tooltip bs-tooltip-${BS_SIDE[preferred]}`;
    const rect = tip.getBoundingClientRect();
    const arrowSize = parseFloat(getComputedStyle(tip).getPropertyValue("--bs-tooltip-arrow-height")) || 0;
    const rootFont = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
    const result = computePlacement(
      anchor,
      { width: rect.width, height: rect.height },
      { width: document.documentElement.clientWidth, height: document.documentElement.clientHeight },
      preferred,
      { gap: arrowSize * rootFont + 2 },
    );

    tip.className = `tooltip bs-tooltip-${BS_SIDE[result.placement]} show`;
    tip.style.left = `${Math.round(result.left)}px`;
    tip.style.top = `${Math.round(result.top)}px`;
    const arrow = tip.querySelector("[data-arrow]");
    const arrowRect = arrow.getBoundingClientRect();
    if (result.placement === "top" || result.placement === "bottom") {
      arrow.style.top = "";
      arrow.style.left = `${Math.round(result.arrow - arrowRect.width / 2)}px`;
    } else {
      arrow.style.left = "";
      arrow.style.top = `${Math.round(result.arrow - arrowRect.height / 2)}px`;
    }
  }
}

registerComponent("ui-tooltip", UiTooltip);
