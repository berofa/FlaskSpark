import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { morph } from "../../../core/morph.js";
import { assignItemSlots } from "../../../core/slotted-items.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";
import { CarouselController, installCarouselDataApi } from "./carousel-controller.js";

const ITEM = "ui-carousel-item:not([data-carousel-clone])";
const PLACEMENTS = new Set(["top", "bottom", "overlay"]);

/**
 * <ui-carousel> (Bootstrap 6 carousel on scroll snap) with <ui-carousel-item> children.
 *
 * The carousel renders Bootstrap's markup in its shadow tree: one .carousel-item per item (content slotted),
 * the controls and the indicators. Sliding, swiping and momentum come from the browser; CarouselController
 * adds the controls, active-slide syncing, autoplay and the ends.
 *
 * Attributes:
 * - controls, indicators, play-pause: render prev / next buttons, indicators, a play / pause button.
 * - placement: top (with the heading slot), bottom (default) or overlay (over the slides).
 * - fade (crossfade), center (snap the active slide to the centre), auto (variable width: size the items).
 * - autoplay, interval (ms, default 5000), ends (loop | wrap | stop), keyboard="false", pause="false".
 * - prev-label, next-label, play-label, pause-label, indicator-label ("Slide {n}"): accessible names.
 * Visible slides, gap and peek are CSS: --bs-carousel-items, --bs-carousel-items-gap, --bs-carousel-items-peek.
 *
 * <ui-carousel-item>: active (start slide), interval (ms, own autoplay interval).
 * Methods: next(), prev(), to(index), cycle(), pause(), nextWhenVisible(), togglePlayPause(),
 * activeIndex, items. Events (bubble): ui-carousel:slide (cancelable) and ui-carousel:slid with
 * detail { from, to, direction, relatedTarget } (relatedTarget: the <ui-carousel-item>).
 * Parts: carousel, inner, item, controls, control, prev, next, play-pause, indicators, indicator, heading.
 */
export class UiCarousel extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-carousel.css", import.meta.url).href];
  static documentStylesheet = new URL("./ui-carousel.document.css", import.meta.url).href;
  static observedAttributes = ["controls", "indicators", "play-pause", "placement", "fade", "center", "auto", "autoplay",
    "interval", "ends", "keyboard", "pause", "prev-label", "next-label", "play-label", "pause-label", "indicator-label"];

  #controller = null;
  #items = [];
  #observer = null;

  connectedCallback() {
    super.connectedCallback();
    this.#observer ??= new MutationObserver((records) => {
      const relevant = records.some((record) => (record.type === "childList"
        ? [...record.addedNodes, ...record.removedNodes].some((node) => node.nodeType === 1 && !node.hasAttribute("data-carousel-clone"))
        : record.target.parentElement === this && !record.target.hasAttribute("data-carousel-clone")));
      if (relevant) {
        this.requestRender();
      }
    });
    this.#observer.observe(this, { childList: true, subtree: true, attributes: true, attributeFilter: ["interval", "active"] });
  }

  disconnectedCallback() {
    this.#observer?.disconnect();
    this.#controller?.dispose();
    this.#controller = null;
  }

  renderShadow() {
    morph(this.shadowRoot, this.render());
    const root = this.shadowRoot.querySelector(".carousel");
    if (this.#controller && this.#controller.root !== root) {
      this.#controller.dispose();
      this.#controller = null;
    }
    if (this.#controller) {
      this.#controller.refresh();
    } else {
      this.#controller = new CarouselController(root, {
        config: () => ({
          autoplay: this.hasAttribute("autoplay"),
          ends: this.getAttribute("ends") || undefined,
          interval: this.getAttribute("interval") || undefined,
          keyboard: this.getAttribute("keyboard") ?? undefined,
          pause: this.getAttribute("pause") ?? undefined,
        }),
        emit: (name, detail, cancelable) => this.dispatchEvent(new CustomEvent(`ui-carousel:${name}`, { bubbles: true, cancelable, detail })),
        relatedTarget: (item) => this.#items[Number(item?.dataset.index)],
        makeClone: (item) => this.#makeClone(item),
        removeClone: (clone) => this.querySelectorAll(`[slot="${clone.dataset.cloneSlot}"]`).forEach((node) => node.remove()),
      });
    }
  }

  /** A loop clone: a copy of the light item (styled by the page) in a slot of a clone slide. */
  #makeClone(item) {
    const source = this.#items[Number(item.dataset.index)];
    const name = `clone-${Date.now()}`;
    const copy = source.cloneNode(true);
    copy.setAttribute("data-carousel-clone", "");
    copy.removeAttribute("id");
    copy.querySelectorAll("[id]").forEach((node) => node.removeAttribute("id"));
    copy.setAttribute("aria-hidden", "true");
    copy.inert = true;
    copy.slot = name;
    this.append(copy);
    const slide = item.cloneNode(false);
    slide.dataset.cloneSlot = name;
    slide.removeAttribute("data-index");
    slide.innerHTML = `<slot name="${name}"></slot>`;
    return slide;
  }

  get items() {
    return [...this.#items];
  }

  get activeIndex() {
    return this.#controller?.activeIndex ?? 0;
  }

  #label(name, fallback) {
    return escapeHtml(this.getAttribute(name) || fallback);
  }

  #controls(overlay) {
    const style = overlay ? " btn-subtle theme-secondary" : "";
    const buttons = [];
    if (this.hasAttribute("play-pause")) {
      buttons.push(`<button class="btn-icon btn-sm${style} carousel-control-play-pause" type="button" part="control play-pause" `
        + `data-bs-pause-label="${this.#label("pause-label", "Pause")}" data-bs-play-label="${this.#label("play-label", "Play")}" `
        + `aria-label="${this.#label("pause-label", "Pause")}"><span class="carousel-icon-pause" aria-hidden="true"></span>`
        + '<span class="carousel-icon-play" aria-hidden="true"></span></button>');
    }
    if (this.hasAttribute("controls")) {
      for (const [direction, label] of [["prev", "Previous"], ["next", "Next"]]) {
        buttons.push(`<button class="btn-icon btn-sm${style}" type="button" part="control ${direction}" data-bs-slide="${direction}" `
          + `aria-label="${this.#label(`${direction}-label`, label)}"><span class="carousel-icon-${direction}" aria-hidden="true"></span></button>`);
      }
    }
    return buttons.length ? `<div part="controls">${buttons.join("")}</div>` : "";
  }

  #indicators() {
    if (!this.hasAttribute("indicators")) {
      return "";
    }
    const label = this.getAttribute("indicator-label") || "Slide {n}";
    const active = this.#controller?.activeIndex ?? this.#initialIndex();
    const buttons = this.#items.map((_, index) => `<button type="button" part="indicator" data-bs-target data-bs-slide-to="${index}"`
      + `${index === active ? ' class="active" aria-current="true"' : ""} aria-label="${escapeHtml(label.replace("{n}", String(index + 1)))}"></button>`);
    return `<div class="carousel-indicators" part="indicators">${buttons.join("")}</div>`;
  }

  #initialIndex() {
    return Math.max(this.#items.findIndex((item) => item.hasAttribute("active")), 0);
  }

  render() {
    this.#items = assignItemSlots(this, ITEM, "item");
    const placement = PLACEMENTS.has(this.getAttribute("placement")) ? this.getAttribute("placement") : "bottom";
    const overlay = placement === "overlay";
    const active = this.#controller?.activeIndex ?? this.#initialIndex();
    const playing = this.#controller?.timer != null;
    const classes = ["carousel", "slide", HOST_TOKENS_CLASS, this.hasAttribute("fade") ? "carousel-fade" : "",
      this.hasAttribute("center") ? "carousel-center" : "", this.hasAttribute("auto") ? "carousel-auto" : "",
      overlay ? "carousel-overlay" : "", playing ? "carousel-playing" : ""].filter(Boolean).join(" ");
    const slides = this.#items.map((item, index) => {
      const interval = item.getAttribute("interval");
      return `<div class="carousel-item${index === active ? " active" : ""}" part="item" data-index="${index}"`
        + `${interval ? ` data-bs-interval="${escapeHtml(interval)}"` : ""}><slot name="item-${index}"></slot></div>`;
    });
    const inner = `<div class="carousel-inner" part="inner">${slides.join("")}</div>`;
    const controls = this.#controls(overlay);
    const indicators = this.#indicators();
    let markup;
    if (overlay) {
      const bar = controls || indicators ? `<div class="carousel-overlay-controls">${controls}${indicators}</div>` : "";
      markup = inner + bar;
    } else if (placement === "top") {
      const heading = '<div class="carousel-heading" part="heading"><slot name="heading"></slot></div>';
      markup = `<div class="carousel-bar">${heading}${controls}</div>${inner}`
        + (indicators ? `<div class="carousel-bar justify-content-center">${indicators}</div>` : "");
    } else {
      const bar = controls || indicators
        ? `<div class="carousel-bar${controls && indicators ? "" : controls ? "" : " justify-content-center"}">${controls}${indicators}</div>` : "";
      markup = inner + bar;
    }
    return `<div class="${classes}" part="carousel">${markup}</div>`;
  }

  #wire() {
    if (this.wired) {
      return;
    }
    this.wired = true;
    this.shadowRoot.addEventListener("click", (event) => {
      const control = event.target.closest?.("[data-bs-slide], [data-bs-slide-to], .carousel-control-play-pause");
      if (!control || control.disabled || !this.#controller) {
        return;
      }
      if (control.classList.contains("carousel-control-play-pause")) {
        this.#controller.togglePlayPause();
        return;
      }
      this.#controller.pauseFromInteraction();
      if (control.hasAttribute("data-bs-slide-to")) {
        this.#controller.to(control.getAttribute("data-bs-slide-to"));
      } else if (control.getAttribute("data-bs-slide") === "next") {
        this.#controller.next();
      } else {
        this.#controller.prev();
      }
    });
  }

  constructor() {
    super();
    this.#wire();
  }

  next() { this.#controller?.next(); }

  prev() { this.#controller?.prev(); }

  to(index) { this.#controller?.to(index); }

  cycle() { this.#controller?.cycle(); }

  pause() { this.#controller?.pause(); }

  nextWhenVisible() { this.#controller?.nextWhenVisible(); }

  togglePlayPause() { this.#controller?.togglePlayPause(); }

  /** Autoplay off for good (what a control click does); used by external data-bs-slide triggers. */
  pauseFromInteraction() { this.#controller?.pauseFromInteraction(); }
}

/** One slide of a <ui-carousel>; its content is slotted into the rendered .carousel-item. */
export class UiCarouselItem extends HTMLElement {}

registerComponent("ui-carousel", UiCarousel);
registerComponent("ui-carousel-item", UiCarouselItem);
installCarouselDataApi();
