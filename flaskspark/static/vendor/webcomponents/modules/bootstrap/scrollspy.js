/**
 * Bootstrap 6's scrollspy (js/src/scrollspy.ts, MIT): marks the link of the section being read as active, in a
 * nav, list group, menu or any set of links. `data-bs-spy="scroll"` on the scrolling element (often <body>) and
 * `data-bs-target` (the links' container). An IntersectionObserver watches an activation line near the top
 * (topMargin, "12%" or pixels like "96px"; rootMargin overrides it): the deepest section past the line is active,
 * the last one at the very bottom; links of nested navs activate their parents, menu items their toggle.
 * Components with an href (e.g. <ui-list-group-item href="#a">) are links too; they get the attribute `active`.
 *
 * Options (or data-bs-*): target, topMargin, rootMargin, threshold ("0,0.5"), smoothScroll. Event on the
 * spied element: ui-scrollspy:activate {relatedTarget}. Methods: refresh() (after the content changed), update()
 * (recompute from the scroll position), dispose().
 */
const LINK_ITEMS = ".nav-link, .nav-item > .nav-link, .list-group-item";

const isComponent = (element) => element.localName.includes("-");
const isActive = (element) => (isComponent(element) ? element.hasAttribute("active") : element.classList.contains("active"));
const setActive = (element, on) => (isComponent(element) ? element.toggleAttribute("active", on) : element.classList.toggle("active", on));

function visible(element) {
  return element.getClientRects().length > 0 && getComputedStyle(element).visibility !== "hidden";
}

function decodeFragment(hash) {
  try {
    return decodeURIComponent(hash);
  } catch {
    return hash;
  }
}

export class ScrollSpyController {
  constructor(element, options = {}) {
    this.element = element;
    this.options = { topMargin: "12%", rootMargin: null, threshold: [0], smoothScroll: false, ...options };
    const target = this.options.target;
    this.target = (typeof target === "string" ? document.querySelector(target) : target) || document.body;
    if (typeof this.options.threshold === "string") this.options.threshold = this.options.threshold.split(",").map(Number.parseFloat);
    this.root = getComputedStyle(element).overflowY === "visible" ? null : element;
    this.intersecting = new Set();
    this.activeTarget = null;
    this.lastActive = null;
    this.atBottom = false;
    this.onClick = (event) => this.#smoothClick(event);
    this.onScrollEnd = () => this.update();
    (this.root || document).addEventListener("scrollend", this.onScrollEnd);
    this.refresh();
  }

  /** The links: elements with an href in the target (also custom elements with an href attribute). */
  #links() {
    return [...this.target.querySelectorAll("[href]")];
  }

  refresh() {
    this.sections = [];
    this.linkBySection = new Map();
    this.sectionByLink = new Map();
    const seen = new Set();
    for (const link of this.#links()) {
      const href = link.getAttribute("href") || "";
      const hash = href.startsWith("#") ? href : (link.hash || "");
      if (!hash || hash === "#" || link.hasAttribute("disabled") || link.classList.contains("disabled")) continue;
      const section = document.getElementById(decodeFragment(hash.slice(1)));
      if (!section || !this.element.contains(section) || !visible(section)) continue;
      this.sectionByLink.set(link, section);
      this.linkBySection.set(section, link);
      if (!seen.has(section)) {
        seen.add(section);
        this.sections.push(section);
      }
    }
    this.sections.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
    this.target.removeEventListener("click", this.onClick);
    if (this.options.smoothScroll === true || this.options.smoothScroll === "true") this.target.addEventListener("click", this.onClick);
    this.observer?.disconnect();
    this.intersecting.clear();
    this.observer = new IntersectionObserver((entries) => this.#intersect(entries), {
      root: this.root, threshold: this.options.threshold, rootMargin: this.options.rootMargin ?? this.#rootMargin(),
    });
    this.sections.forEach((section) => this.observer.observe(section));
    this.#sentinel();
  }

  /**
   * The active section from the geometry (what the observer reports, computed directly): after a scroll came to
   * rest, and for pages that change the scroll position from script.
   */
  update() {
    const scroller = this.root || document.scrollingElement || document.documentElement;
    const rootRect = this.root ? this.root.getBoundingClientRect() : { top: 0, height: document.documentElement.clientHeight || window.innerHeight };
    const text = String(this.options.topMargin);
    const value = Number.parseFloat(text) || 0;
    const line = rootRect.top + (text.endsWith("%") ? (rootRect.height * value) / 100 : value);
    this.intersecting.clear();
    this.sections.forEach((section) => {
      const rect = section.getBoundingClientRect();
      if (rect.top <= line && rect.bottom > rootRect.top) this.intersecting.add(section);
    });
    this.atBottom = scroller.scrollHeight > scroller.clientHeight && scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 1;
    this.#compute();
  }

  #rootMargin() {
    const text = String(this.options.topMargin);
    let percent = Number.parseFloat(text) || 0;
    if (!text.endsWith("%")) {
      const height = this.root ? this.root.clientHeight : (document.documentElement.clientHeight || window.innerHeight);
      percent = height ? (percent / height) * 100 : 12;
    }
    return `0px 0px -${Math.min(Math.max(100 - percent, 0), 100)}% 0px`;
  }

  #sentinel() {
    this.sentinelObserver?.disconnect();
    this.sentinel?.remove();
    this.atBottom = false;
    if (!this.sections.length) return;
    this.sentinel = document.createElement("div");
    this.sentinel.setAttribute("aria-hidden", "true");
    this.sentinel.style.cssText = "position:relative;width:0;height:0;margin:0;padding:0;border:0;visibility:hidden;";
    this.element.append(this.sentinel);
    this.sentinelObserver = new IntersectionObserver((entries) => {
      const scroller = this.root || document.scrollingElement || document.documentElement;
      this.atBottom = Boolean(entries.at(-1)?.isIntersecting) && scroller.scrollHeight > scroller.clientHeight;
      this.#compute();
    }, { root: this.root, threshold: [0] });
    this.sentinelObserver.observe(this.sentinel);
  }

  #intersect(entries) {
    entries.forEach((entry) => (entry.isIntersecting ? this.intersecting.add(entry.target) : this.intersecting.delete(entry.target)));
    this.#compute();
  }

  #compute() {
    if (!this.element.isConnected || !this.sections.length) return;
    let active = null;
    if (this.atBottom) {
      active = this.sections.at(-1);
    } else {
      this.sections.forEach((section) => {
        if (this.intersecting.has(section)) active = section;
      });
      active ||= this.lastActive ?? this.sections[0];
    }
    this.lastActive = active;
    const link = this.linkBySection.get(active);
    if (link) this.#activate(link);
  }

  #activate(link) {
    if (this.activeTarget === link) return;
    setActive(this.target, false);
    this.#links().filter(isActive).forEach((other) => setActive(other, false));
    this.target.querySelectorAll(`${LINK_ITEMS}, [data-bs-toggle="menu"]`).forEach((item) => item.classList.remove("active"));
    this.activeTarget = link;
    setActive(link, true);
    if (link.classList.contains("menu-item")) {
      const toggle = link.closest(".menu")?.previousElementSibling;
      if (toggle?.matches('[data-bs-toggle="menu"]')) toggle.classList.add("active");
    } else {
      // Nested navs: the links in front of each enclosing nav / list group are its parents.
      for (let group = link.parentElement?.closest(".nav, .list-group"); group; group = group.parentElement?.closest(".nav, .list-group")) {
        for (let sibling = group.previousElementSibling; sibling; sibling = sibling.previousElementSibling) {
          if (sibling.matches(LINK_ITEMS)) sibling.classList.add("active");
        }
      }
    }
    this.element.dispatchEvent(new CustomEvent("ui-scrollspy:activate", { bubbles: true, detail: { relatedTarget: link } }));
  }

  #smoothClick(event) {
    const link = event.target.closest?.("[href]");
    const section = link && this.sectionByLink.get(link);
    if (!section) return;
    event.preventDefault();
    const top = section.offsetTop - this.element.offsetTop;
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    (this.root || window).scrollTo({ top, behavior: reduce ? "auto" : "smooth" });
    const hash = `#${section.id}`;
    const settle = () => {
      history.replaceState?.(null, "", hash);
      if (!section.hasAttribute("tabindex")) section.setAttribute("tabindex", "-1");
      section.focus({ preventScroll: true });
    };
    if (reduce) settle();
    else (this.root || document).addEventListener("scrollend", settle, { once: true });
  }

  dispose() {
    (this.root || document).removeEventListener("scrollend", this.onScrollEnd);
    this.observer?.disconnect();
    this.sentinelObserver?.disconnect();
    this.sentinel?.remove();
    this.target.removeEventListener("click", this.onClick);
  }
}

const plain = new WeakMap();

export function plainScrollSpy(element) {
  let controller = plain.get(element);
  if (!controller) {
    const d = element.dataset;
    const options = {};
    if (d.bsTarget) options.target = d.bsTarget;
    if (d.bsTopMargin) options.topMargin = d.bsTopMargin;
    if (d.bsRootMargin) options.rootMargin = d.bsRootMargin;
    if (d.bsThreshold) options.threshold = d.bsThreshold;
    if (d.bsSmoothScroll) options.smoothScroll = d.bsSmoothScroll;
    controller = new ScrollSpyController(element, options);
    plain.set(element, controller);
  }
  return controller;
}

let installed = false;

/** Bootstrap's data API: every [data-bs-spy="scroll"] on load (components render by then). */
export function installScrollSpyDataApi() {
  if (installed || typeof document === "undefined" || typeof IntersectionObserver === "undefined") return;
  installed = true;
  const start = () => document.querySelectorAll('[data-bs-spy="scroll"]').forEach((element) => plainScrollSpy(element));
  if (document.readyState === "complete") start();
  else window.addEventListener("load", start, { once: true });
}

installScrollSpyDataApi();
