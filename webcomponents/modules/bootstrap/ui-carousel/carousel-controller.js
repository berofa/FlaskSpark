import { triggerTarget } from "../../../core/triggers.js";

/**
 * Bootstrap 6's carousel behaviour (js/src/carousel.ts, MIT) for a `.carousel` element, in the document or in a
 * shadow tree. The browser does the sliding (scroll snap in `.carousel-inner`); the controller adds prev / next
 * / indicator controls, active-slide syncing, autoplay with per-slide intervals and the indicator progress,
 * play / pause, keyboard, pause on hover and the ends: `loop` (seamless, through a transient clone), `wrap`,
 * `stop` (end controls disabled). `.carousel-fade` swaps the active slide instead of scrolling.
 *
 * Options: config() → { autoplay, ends, interval, keyboard, pause } (read on every use, so attribute changes
 * apply at once), emit(name, detail, cancelable) → false when cancelled, relatedTarget(item) (the element
 * named in events), makeClone(item) (a loop clone, default a deep copy) and itemInterval(item).
 */

const SCROLL_DURATION = 300;
const ACTIVE_RATIO_TOLERANCE = 0.05;
const CLONE = "carousel-item-clone";
const ENDS = ["stop", "wrap", "loop"];
export const CAROUSEL_DEFAULTS = { autoplay: false, ends: "loop", interval: 5000, keyboard: true, pause: "hover" };

const easeInOutCubic = (p) => (p < 0.5 ? 4 * p * p * p : 1 - ((-2 * p + 2) ** 3) / 2);
const isFalse = (value) => value === false || value === "false";

export class CarouselController {
  constructor(root, options = {}) {
    this.root = root;
    this.options = options;
    this.timer = null;
    this.observer = null;
    this.scrollFrame = null;
    this.looping = false;
    this.visibility = new Map();
    this.playing = this.#config().autoplay;
    this.activeIndex = this.#initialActiveIndex();
    this.onKeydown = (event) => this.#keydown(event);
    this.onEnter = () => this.#config().pause === "hover" && this.pause();
    this.onLeave = () => this.#config().pause === "hover" && this.#maybeEnableCycle();
    this.onPointerdown = () => this.pauseFromInteraction();
    this.onScrollend = () => !this.looping && this.scrollFrame === null && this.#settle();
    root.addEventListener("keydown", this.onKeydown);
    root.addEventListener("mouseenter", this.onEnter);
    root.addEventListener("mouseleave", this.onLeave);
    this.refresh();
    if (this.playing) {
      this.cycle();
    }
  }

  #config() {
    const config = { ...CAROUSEL_DEFAULTS, ...(this.options.config?.() || {}) };
    config.autoplay = config.autoplay === true || config.autoplay === "true" || config.autoplay === "";
    config.keyboard = !isFalse(config.keyboard);
    config.pause = isFalse(config.pause) ? false : config.pause;
    config.interval = Number.parseInt(config.interval, 10) || CAROUSEL_DEFAULTS.interval;
    if (!ENDS.includes(config.ends)) {
      config.ends = CAROUSEL_DEFAULTS.ends;
    }
    return config;
  }

  #emit(name, detail, cancelable = false) {
    if (this.options.emit) {
      return this.options.emit(name, detail, cancelable);
    }
    return this.root.dispatchEvent(new CustomEvent(`ui-carousel:${name}`, { bubbles: true, cancelable, detail }));
  }

  #detail(from, to, direction) {
    const item = this.items()[to];
    return { from, to, direction, relatedTarget: this.options.relatedTarget ? this.options.relatedTarget(item) : item };
  }

  /** Re-reads the viewport, the controls and the slides (after the markup changed) and re-applies the state. */
  refresh() {
    const viewport = this.root.querySelector(".carousel-inner") || this.root;
    if (viewport !== this.viewport) {
      this.viewport?.removeEventListener("pointerdown", this.onPointerdown);
      this.viewport?.removeEventListener("scrollend", this.onScrollend);
      this.viewport = viewport;
      viewport.addEventListener("pointerdown", this.onPointerdown);
      viewport.addEventListener("scrollend", this.onScrollend);
    }
    this.indicators = this.root.querySelector(".carousel-indicators");
    this.playPause = this.root.querySelector(".carousel-control-play-pause");
    this.prevControls = [...this.root.querySelectorAll('[data-bs-slide="prev"]')];
    this.nextControls = [...this.root.querySelectorAll('[data-bs-slide="next"]')];
    this.activeIndex = Math.min(this.activeIndex, Math.max(this.items().length - 1, 0));
    this.#observeItems();
    this.#refreshActiveState();
    this.#updatePlayPause();
    this.root.classList.toggle("carousel-playing", this.timer !== null);
    if (this.timer !== null) {
      this.root.style.setProperty("--bs-carousel-interval", `${this.#itemInterval()}ms`);
    }
  }

  items() {
    return [...this.root.querySelectorAll(`.carousel-item:not(.${CLONE})`)];
  }

  next() {
    this.to(this.#navIndex() + 1);
  }

  nextWhenVisible() {
    const style = getComputedStyle(this.root);
    if (document.visibilityState === "visible" && this.root.getClientRects().length > 0 && style.visibility === "visible") {
      this.next();
    }
  }

  prev() {
    this.to(this.#navIndex() - 1);
  }

  pause() {
    this.#clearTimer();
    this.root.classList.remove("carousel-playing");
  }

  cycle() {
    this.#clearTimer();
    this.#scheduleAutoplay();
    this.root.classList.add("carousel-playing");
  }

  to(index) {
    if (this.looping) {
      return;
    }
    const items = this.items();
    const raw = Number.parseInt(index, 10);
    if (this.#config().ends === "loop" && !this.#reducedMotion() && this.#canLoop()) {
      if (raw > items.length - 1) {
        this.#loopTransition(true);
        return;
      }
      if (raw < 0) {
        this.#loopTransition(false);
        return;
      }
    }
    const target = this.#normalizeIndex(raw, items.length);
    const current = this.#navIndex();
    if (target === null || target === current) {
      return;
    }
    if (!this.#emit("slide", this.#detail(current, target, this.#direction(current, target)), true)) {
      return;
    }
    if (this.#isFade()) {
      this.#setActive(target);
      return;
    }
    this.#scrollToIndex(target);
  }

  /** Autoplay off for good once the user takes over (controls, keyboard, swipe, pause button). */
  pauseFromInteraction() {
    this.playing = false;
    this.pause();
    this.#updatePlayPause();
  }

  togglePlayPause() {
    if (this.playing) {
      this.pauseFromInteraction();
      return;
    }
    this.playing = true;
    this.cycle();
    this.#updatePlayPause();
  }

  dispose() {
    this.#clearTimer();
    this.observer?.disconnect();
    if (this.scrollFrame !== null) {
      cancelAnimationFrame(this.scrollFrame);
    }
    this.root.querySelectorAll(`.${CLONE}`).forEach((clone) => this.#removeClone(clone));
    this.viewport.style.scrollSnapType = "";
    this.root.removeEventListener("keydown", this.onKeydown);
    this.root.removeEventListener("mouseenter", this.onEnter);
    this.root.removeEventListener("mouseleave", this.onLeave);
    this.viewport.removeEventListener("pointerdown", this.onPointerdown);
    this.viewport.removeEventListener("scrollend", this.onScrollend);
  }

  #initialActiveIndex() {
    const index = this.items().findIndex((item) => item.classList.contains("active"));
    return Math.max(index, 0);
  }

  #keydown(event) {
    if (!this.#config().keyboard || /input|textarea|select/i.test(event.composedPath()[0]?.tagName || "")) {
      return;
    }
    const step = { ArrowLeft: -1, ArrowRight: 1 }[event.key];
    if (step) {
      event.preventDefault();
      this.pauseFromInteraction();
      ((step > 0) !== this.#isRTL() ? this.next() : this.prev());
    }
  }

  #observeItems() {
    this.observer?.disconnect();
    this.observer = null;
    this.visibility.clear();
    if (this.#isFade() || typeof IntersectionObserver === "undefined") {
      return;
    }
    this.observer = new IntersectionObserver((entries) => this.#intersection(entries),
      { root: this.viewport, threshold: [0, 0.25, 0.5, 0.75, 1] });
    this.items().forEach((item) => this.observer.observe(item));
  }

  #intersection(entries) {
    if (this.looping) {
      return;
    }
    entries.forEach((entry) => this.visibility.set(entry.target, entry.isIntersecting ? entry.intersectionRatio : 0));
    const ratios = this.items().map((item) => this.visibility.get(item) ?? 0);
    const max = Math.max(...ratios);
    // The left-most slide that is nearly fully visible (a programmatic scroll rests a sub-pixel off).
    this.#setActive(max > 0 ? ratios.findIndex((ratio) => ratio >= max - ACTIVE_RATIO_TOLERANCE) : this.activeIndex);
    this.#updateEndControls();
  }

  /** After a scroll came to rest: the active slide from the geometry (also without IntersectionObserver). */
  #settle() {
    if (!this.#isFade()) {
      this.#setActive(this.#navIndex());
    }
    this.#updateEndControls();
  }

  // The index a step starts from: the live scroll position (the observer updates the active index later).
  #navIndex() {
    if (this.#isFade() || this.viewport.scrollWidth - this.viewport.clientWidth <= 0) {
      return this.activeIndex;
    }
    let index = this.activeIndex;
    let smallest = Number.POSITIVE_INFINITY;
    this.items().forEach((item, itemIndex) => {
      const delta = Math.abs(this.#scrollDelta(item));
      if (delta < smallest) {
        smallest = delta;
        index = itemIndex;
      }
    });
    return index;
  }

  #scrollToIndex(index) {
    const item = this.items()[index];
    if (!item) {
      return;
    }
    const delta = this.#scrollDelta(item);
    if (Math.abs(delta) < 1) {
      return;
    }
    // Snap stop "always" would clamp a programmatic jump to one slide: no snapping while animating.
    this.viewport.style.scrollSnapType = "none";
    this.#animateScroll(this.viewport.scrollLeft + delta, () => {
      this.viewport.style.scrollSnapType = "";
      this.#settle();
    });
  }

  // Steps scrollLeft by hand (Safari overshoots programmatic smooth scrolls under page zoom).
  #animateScroll(targetLeft, done) {
    if (this.scrollFrame !== null) {
      cancelAnimationFrame(this.scrollFrame);
      this.scrollFrame = null;
    }
    const start = this.viewport.scrollLeft;
    const distance = targetLeft - start;
    if (this.#reducedMotion() || typeof requestAnimationFrame === "undefined") {
      this.viewport.scrollTo({ left: targetLeft, behavior: "instant" });
      done();
      return;
    }
    let startTime = null;
    const step = (now) => {
      startTime ??= now;
      const progress = Math.min((now - startTime) / SCROLL_DURATION, 1);
      this.viewport.scrollTo({ left: start + distance * easeInOutCubic(progress), behavior: "instant" });
      if (progress < 1) {
        this.scrollFrame = requestAnimationFrame(step);
        return;
      }
      this.viewport.scrollTo({ left: targetLeft, behavior: "instant" });
      this.scrollFrame = null;
      done();
    };
    this.scrollFrame = requestAnimationFrame(step);
  }

  // How far to scroll so `element` rests where the active slide sits (start or centre, peek respected).
  #scrollDelta(element) {
    const view = this.viewport.getBoundingClientRect();
    const rect = element.getBoundingClientRect();
    if (this.root.classList.contains("carousel-center")) {
      return rect.left + rect.width / 2 - (view.left + view.width / 2);
    }
    const pad = Number.parseFloat(getComputedStyle(this.viewport).scrollPaddingInlineStart) || 0;
    return this.#isRTL() ? rect.right - (view.right - pad) : rect.left - (view.left + pad);
  }

  // Seamless loop: scroll on into a clone of the destination, then jump to the real slide unseen.
  #loopTransition(isNext) {
    const items = this.items();
    const last = items.length - 1;
    const from = this.activeIndex;
    const to = isNext ? 0 : last;
    const direction = this.#loopDirection(isNext);
    if (!this.#emit("slide", this.#detail(from, to, direction), true)) {
      return;
    }
    this.looping = true;
    const clone = this.#makeClone(isNext ? items[0] : items[last]);
    this.viewport.style.scrollSnapType = "none";
    if (isNext) {
      this.viewport.append(clone);
    } else {
      this.viewport.prepend(clone);
      this.#jumpScroll(this.#scrollDelta(items[from]));
    }
    this.#animateScroll(this.viewport.scrollLeft + this.#scrollDelta(clone), () => {
      this.#removeClone(clone);
      this.#jumpScroll(this.#scrollDelta(items[to]));
      this.activeIndex = to;
      this.#refreshActiveState();
      this.#emit("slid", this.#detail(from, to, direction));
      this.viewport.style.scrollSnapType = "";
      this.looping = false;
    });
  }

  #makeClone(item) {
    const clone = this.options.makeClone ? this.options.makeClone(item) : item.cloneNode(true);
    clone.classList.add(CLONE);
    clone.classList.remove("active");
    clone.removeAttribute("id");
    clone.querySelectorAll("[id]").forEach((node) => node.removeAttribute("id"));
    clone.setAttribute("aria-hidden", "true");
    clone.inert = true;
    return clone;
  }

  #removeClone(clone) {
    this.options.removeClone?.(clone);
    clone.remove();
  }

  #loopDirection(isNext) {
    return isNext !== this.#isRTL() ? "left" : "right";
  }

  #jumpScroll(delta) {
    this.viewport.style.scrollSnapType = "none";
    this.viewport.scrollBy({ left: delta, top: 0, behavior: "instant" });
  }

  #setActive(index) {
    const items = this.items();
    if (index === this.activeIndex || !items[index]) {
      return;
    }
    const from = this.activeIndex;
    this.activeIndex = index;
    this.#refreshActiveState();
    this.#emit("slid", this.#detail(from, index, this.#direction(from, index)));
  }

  #refreshActiveState() {
    this.items().forEach((item, index) => item.classList.toggle("active", index === this.activeIndex));
    if (this.indicators) {
      this.indicators.querySelectorAll("[data-bs-slide-to]").forEach((indicator) => {
        const active = Number(indicator.getAttribute("data-bs-slide-to")) === this.activeIndex;
        indicator.classList.toggle("active", active);
        if (active) {
          indicator.setAttribute("aria-current", "true");
        } else {
          indicator.removeAttribute("aria-current");
        }
      });
    }
    this.#updateEndControls();
  }

  #updateEndControls() {
    if (this.#config().ends !== "stop") {
      [...this.prevControls, ...this.nextControls].forEach((control) => {
        control.disabled = false;
      });
      return;
    }
    const max = this.viewport.scrollWidth - this.viewport.clientWidth;
    let atStart;
    let atEnd;
    if (max > 0 && !this.#isFade()) {
      const progress = Math.abs(this.viewport.scrollLeft);
      atStart = progress <= 1;
      atEnd = progress >= max - 1;
    } else {
      atStart = this.activeIndex <= 0;
      atEnd = this.activeIndex >= this.items().length - 1;
    }
    this.#setDisabled(this.prevControls, atStart);
    this.#setDisabled(this.nextControls, atEnd);
  }

  #setDisabled(controls, disabled) {
    controls.forEach((control) => {
      // Do not lose the focus with the control: move it to the opposite one.
      if (disabled && control === control.getRootNode().activeElement) {
        const opposite = controls === this.prevControls ? this.nextControls : this.prevControls;
        (opposite[0] ?? this.viewport).focus({ preventScroll: true });
      }
      control.disabled = disabled;
    });
  }

  #normalizeIndex(index, length) {
    if (Number.isNaN(index) || length === 0) {
      return null;
    }
    const wraps = this.#config().ends !== "stop";
    if (index < 0) {
      return wraps ? length - 1 : null;
    }
    if (index > length - 1) {
      return wraps ? 0 : null;
    }
    return index;
  }

  // Seamless looping only in the single-slide scroll layout; the others wrap.
  #canLoop() {
    if (this.#isFade() || this.items().length < 2) {
      return false;
    }
    const style = getComputedStyle(this.root);
    const number = (name) => Number.parseFloat(style.getPropertyValue(name)) || 0;
    return (number("--bs-carousel-items") || 1) === 1 && number("--bs-carousel-items-peek") === 0
      && !this.root.classList.contains("carousel-center") && !this.root.classList.contains("carousel-auto");
  }

  #direction(from, to) {
    return (to > from) !== this.#isRTL() ? "left" : "right";
  }

  #scheduleAutoplay(index = this.activeIndex) {
    const interval = this.#itemInterval(index);
    this.root.style.setProperty("--bs-carousel-interval", `${interval}ms`);
    this.timer = setTimeout(() => {
      const upcoming = this.#normalizeIndex(this.#navIndex() + 1, this.items().length);
      this.nextWhenVisible();
      if (upcoming === null) {
        this.pause();
        return;
      }
      this.#scheduleAutoplay(upcoming);
    }, interval);
  }

  #itemInterval(index = this.activeIndex) {
    const item = this.items()[index];
    const own = item ? Number.parseInt(this.options.itemInterval ? this.options.itemInterval(item) : item.getAttribute("data-bs-interval"), 10) : Number.NaN;
    return Number.isNaN(own) ? this.#config().interval : own;
  }

  #maybeEnableCycle() {
    if (this.playing) {
      this.cycle();
    }
  }

  #updatePlayPause() {
    if (!this.playPause) {
      return;
    }
    this.playPause.classList.toggle("paused", !this.playing);
    const label = this.playPause.getAttribute(this.playing ? "data-bs-pause-label" : "data-bs-play-label");
    if (label) {
      this.playPause.setAttribute("aria-label", label);
    }
  }

  #isFade() {
    return this.root.classList.contains("carousel-fade");
  }

  #isRTL() {
    return getComputedStyle(this.root).direction === "rtl";
  }

  #reducedMotion() {
    return typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  #clearTimer() {
    if (this.timer !== null) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }
}

const plain = new WeakMap();

/** The controller of a plain `.carousel` element (options from its data-bs-* attributes). */
export function plainCarousel(element) {
  let controller = plain.get(element);
  if (!controller) {
    controller = new CarouselController(element, {
      config: () => {
        const { bsAutoplay, bsEnds, bsInterval, bsKeyboard, bsPause } = element.dataset;
        return Object.fromEntries(Object.entries({ autoplay: bsAutoplay, ends: bsEnds, interval: bsInterval, keyboard: bsKeyboard, pause: bsPause })
          .filter(([, value]) => value !== undefined));
      },
    });
    plain.set(element, controller);
  }
  return controller;
}

let installed = false;

/**
 * Bootstrap's carousel data API: [data-bs-slide], [data-bs-slide-to] and .carousel-control-play-pause triggers
 * (data-bs-target or href) for plain `.carousel` elements and for <ui-carousel>; autoplaying plain carousels
 * (data-bs-autoplay="true") start on load, the others on first contact (so swipes keep the indicators in sync).
 */
export function installCarouselDataApi() {
  if (installed || typeof document === "undefined") {
    return;
  }
  installed = true;
  document.addEventListener("click", (event) => {
    const trigger = event.target instanceof Element
      ? event.target.closest("[data-bs-slide], [data-bs-slide-to], .carousel-control-play-pause") : null;
    const target = trigger && triggerTarget(trigger);
    if (!target || trigger.disabled) {
      return;
    }
    const controller = target.localName === "ui-carousel" ? target : target.classList.contains("carousel") ? plainCarousel(target) : null;
    if (!controller) {
      return;
    }
    event.preventDefault();
    if (trigger.classList.contains("carousel-control-play-pause")) {
      controller.togglePlayPause();
      return;
    }
    controller.pauseFromInteraction();
    if (trigger.hasAttribute("data-bs-slide-to")) {
      controller.to(trigger.getAttribute("data-bs-slide-to"));
    } else if (trigger.getAttribute("data-bs-slide") === "next") {
      controller.next();
    } else {
      controller.prev();
    }
  });
  const contact = (event) => {
    const carousel = event.target instanceof Element ? event.target.closest(".carousel") : null;
    if (carousel) {
      plainCarousel(carousel);
    }
  };
  document.addEventListener("pointerover", contact);
  document.addEventListener("focusin", contact);
  const autoplay = () => document.querySelectorAll('.carousel[data-bs-autoplay="true"]').forEach((carousel) => plainCarousel(carousel));
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoplay, { once: true });
  } else {
    autoplay();
  }
}
