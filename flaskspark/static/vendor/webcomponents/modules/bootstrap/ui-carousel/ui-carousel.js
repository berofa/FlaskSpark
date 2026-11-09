import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { afterTransition } from "../../../core/transitions.js";

/**
 * <ui-carousel>.
 *
 * The slide choreography toggles Bootstrap's carousel-item-* classes on the
 * <ui-carousel-item> host elements: the hosts share one formatting context
 * inside .carousel-inner, so the float/transform dance works across the
 * shadow boundaries. The matching styles live in :host(...) rules of the
 * item stylesheet.
 *
 * Attributes:
 * - controls / indicators: render prev/next controls and indicator buttons.
 * - interval: autoplay in milliseconds (pauses on hover).
 * - fade: cross-fade instead of sliding (mirrored onto the items).
 * - prev-label / next-label: aria-labels of the controls.
 *
 * Methods / events:
 * - next(), prev(), to(index)
 * - ui-carousel:slid (bubbles) with detail { index, direction }.
 */
export class UiCarousel extends ShadowComponentElement {
  static stylesheet = new URL("./ui-carousel.css", import.meta.url).href;
  static observedAttributes = ["controls", "indicators", "interval", "fade", "prev-label", "next-label"];

  #sliding = false;
  #cycleTimer = null;
  #hovered = false;
  #knownItems = [];

  constructor() {
    super();
    this.addEventListener("mouseenter", () => {
      this.#hovered = true;
      this.#stopCycle();
    });
    this.addEventListener("mouseleave", () => {
      this.#hovered = false;
      this.#startCycle();
    });
    this.addEventListener("keydown", (event) => {
      if (event.key === "ArrowRight") {
        event.preventDefault();
        this.next();
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        this.prev();
      }
    });
  }

  disconnectedCallback() {
    this.#stopCycle();
  }

  render() {
    const items = this.getItems();
    const activeIndex = Math.max(items.findIndex((item) => item.hasAttribute("active")), 0);
    const indicators = this.hasAttribute("indicators")
      ? `
        <div class="carousel-indicators">
          ${items.map((item, index) => `
            <button
              type="button"
              class="${index === activeIndex ? "active" : ""}"
              data-index="${index}"
              aria-label="Slide ${index + 1}"
              ${index === activeIndex ? 'aria-current="true"' : ""}
            ></button>
          `).join("")}
        </div>
      `
      : "";
    const controls = this.hasAttribute("controls")
      ? `
        <button class="carousel-control-prev" type="button" data-slide="prev" aria-label="${escapeHtml(this.getAttribute("prev-label") || "Previous")}">
          <span class="carousel-control-prev-icon" aria-hidden="true"></span>
        </button>
        <button class="carousel-control-next" type="button" data-slide="next" aria-label="${escapeHtml(this.getAttribute("next-label") || "Next")}">
          <span class="carousel-control-next-icon" aria-hidden="true"></span>
        </button>
      `
      : "";
    return `
      <div class="carousel slide">
        ${indicators}
        <div class="carousel-inner">
          <slot></slot>
        </div>
        ${controls}
      </div>
    `;
  }

  afterRender() {
    this.shadowRoot.querySelector("[data-slide='prev']")?.addEventListener("click", () => this.prev());
    this.shadowRoot.querySelector("[data-slide='next']")?.addEventListener("click", () => this.next());
    this.shadowRoot.querySelector(".carousel-indicators")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-index]");
      if (button) {
        this.to(Number.parseInt(button.dataset.index, 10));
      }
    });
    // Re-rendering recreates the slot, which fires slotchange again — only
    // re-render when the item set actually changed, or this would loop.
    this.#knownItems = this.getItems();
    this.shadowRoot.querySelector("slot").addEventListener("slotchange", () => {
      if (this.#itemsChanged()) {
        this.requestRender();
      }
    });
    this.#syncItems();
    this.#startCycle();
  }

  getItems() {
    return Array.from(this.querySelectorAll(":scope > ui-carousel-item"));
  }

  getActiveIndex() {
    return this.getItems().findIndex((item) => item.hasAttribute("active"));
  }

  next() {
    this.#slide("next");
  }

  prev() {
    this.#slide("prev");
  }

  to(index) {
    const activeIndex = this.getActiveIndex();
    if (index === activeIndex) {
      return;
    }
    this.#slide(index > activeIndex ? "next" : "prev", index);
  }

  #itemsChanged() {
    const items = this.getItems();
    const unchanged = items.length === this.#knownItems.length
      && items.every((item, index) => item === this.#knownItems[index]);
    if (unchanged) {
      return false;
    }
    this.#knownItems = items;
    return true;
  }

  #syncItems() {
    const items = this.getItems();
    if (!items.length) {
      return;
    }
    const fade = this.hasAttribute("fade");
    items.forEach((item) => item.toggleAttribute("fade", fade));
    if (!items.some((item) => item.hasAttribute("active"))) {
      items[0].setAttribute("active", "");
    }
  }

  #slide(direction, targetIndex = null) {
    if (this.#sliding) {
      return;
    }
    const items = this.getItems();
    if (items.length < 2) {
      return;
    }
    const activeIndex = Math.max(this.getActiveIndex(), 0);
    const nextIndex = targetIndex ?? (direction === "next"
      ? (activeIndex + 1) % items.length
      : (activeIndex - 1 + items.length) % items.length);
    const activeItem = items[activeIndex];
    const nextItem = items[nextIndex];
    if (!nextItem || nextItem === activeItem) {
      return;
    }

    this.#sliding = true;
    const directionalClass = direction === "next" ? "carousel-item-next" : "carousel-item-prev";
    const orderClass = direction === "next" ? "carousel-item-start" : "carousel-item-end";

    nextItem.classList.add(directionalClass);
    nextItem.offsetHeight; // force reflow so the slide transition runs
    activeItem.classList.add(orderClass);
    nextItem.classList.add(orderClass);

    afterTransition(nextItem, () => {
      nextItem.classList.remove(directionalClass, orderClass);
      nextItem.setAttribute("active", "");
      activeItem.classList.remove(orderClass);
      activeItem.removeAttribute("active");
      this.#sliding = false;
      this.#syncIndicators(nextIndex);
      this.dispatchEvent(new CustomEvent("ui-carousel:slid", {
        bubbles: true,
        detail: { index: nextIndex, direction },
      }));
    });
  }

  #syncIndicators(activeIndex) {
    this.shadowRoot?.querySelectorAll(".carousel-indicators [data-index]").forEach((button) => {
      const active = Number.parseInt(button.dataset.index, 10) === activeIndex;
      button.classList.toggle("active", active);
      if (active) {
        button.setAttribute("aria-current", "true");
      } else {
        button.removeAttribute("aria-current");
      }
    });
  }

  #startCycle() {
    this.#stopCycle();
    const interval = Number.parseInt(this.getAttribute("interval") || "0", 10);
    if (interval > 0 && !this.#hovered && this.isConnected) {
      this.#cycleTimer = window.setInterval(() => this.next(), interval);
    }
  }

  #stopCycle() {
    if (this.#cycleTimer !== null) {
      window.clearInterval(this.#cycleTimer);
      this.#cycleTimer = null;
    }
  }
}

/**
 * <ui-carousel-item>.
 *
 * Attributes:
 * - active: current slide (managed by the carousel).
 *
 * Slots: default. Direct children with class "carousel-caption" get the
 * Bootstrap caption placement.
 */
export class UiCarouselItem extends ShadowComponentElement {
  static stylesheet = new URL("./ui-carousel.css", import.meta.url).href;
  // "active" and "fade" are intentionally not observed: the carousel drives
  // them (plus the transient carousel-item-* classes) purely through CSS.
  static observedAttributes = [];

  render() {
    return "<slot></slot>";
  }
}

registerComponent("ui-carousel", UiCarousel);
registerComponent("ui-carousel-item", UiCarouselItem);
