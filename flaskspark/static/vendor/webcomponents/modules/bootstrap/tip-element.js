import { HOST_TOKENS_CLASS } from "../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../core/shadow-component-element.js";
import { SharedShadowStyles } from "../../core/shared-shadow-styles.js";
import { Tip } from "../../core/tip.js";

const TIP_STYLES = new URL("../../core/tip.css", import.meta.url).href;
const FOCUSABLE = "a[href], button, input, select, textarea, [tabindex], ui-button, ui-input, ui-check, ui-select";

/**
 * Base of <ui-tooltip> and <ui-popover>: the host wraps its trigger content; the box (core/tip.js) lives in the
 * host's shadow root, so the slots "content" / "heading" can hold rich content and the shared Bootstrap copy
 * styles it. Options come from attributes: placement (responsive "top md:right"), trigger ("hover focus",
 * "click", "manual"), delay (ms or {"show":…, "hide":…}), offset ("x,y"), html, custom-class,
 * animation="false", disabled.
 */
export class TipElement extends ShadowComponentElement {
  static kind = "tooltip";

  tip = null;

  attributeChangedCallback(name, oldValue, newValue) {
    if (this.tip) {
      if (name === "disabled") {
        (newValue === null ? this.tip.enable() : this.tip.disable());
      } else if (this.tip.isShown) {
        this.tip.setContent({});
      }
      return;
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  render() {
    return '<span class="ui-tip-trigger" part="trigger"><slot></slot></span>';
  }

  afterRender() {
    if (this.tip) return;
    // Plain-text triggers (an info icon, a word) become reachable by keyboard.
    if (!this.hasAttribute("tabindex") && !this.querySelector(FOCUSABLE)) {
      this.setAttribute("tabindex", "0");
    }
    this.tip = new Tip(this, { kind: this.constructor.kind, root: this.shadowRoot, events: this, options: () => this.tipOptions() });
    if (this.hasAttribute("disabled")) this.tip.disable();
  }

  /** Options for core/tip.js; subclasses add title / content. */
  tipOptions() {
    return {
      placement: this.getAttribute("placement") || undefined,
      trigger: this.getAttribute("trigger") || undefined,
      delay: this.getAttribute("delay") || undefined,
      offset: this.getAttribute("offset") || undefined,
      html: this.hasAttribute("html"),
      customClass: [HOST_TOKENS_CLASS, this.getAttribute("custom-class") || ""].filter(Boolean).join(" "),
      animation: this.getAttribute("animation") !== "false",
    };
  }

  show() { return this.tip?.show(); }

  hide() { return this.tip?.hide(); }

  toggle() { return this.tip?.toggle(); }

  update() { this.tip?.update(); }

  enable() { this.removeAttribute("disabled"); }

  disable() { this.setAttribute("disabled", ""); }

  setContent(content) { this.tip?.setContent(content); }
}

/**
 * Bootstrap's data API for plain markup: data-bs-toggle="tooltip" / "popover" on any element, options as
 * data-bs-* (title, content, placement, trigger, delay, offset, html, custom-class, animation). The box is
 * created on the first hover, focus or click and lives in the page (document.body).
 */
export function installTipDataApi(kind) {
  const selector = `[data-bs-toggle="${kind}"]`;
  const tips = new WeakMap();
  const tipFor = (element) => {
    if (!tips.has(element)) {
      SharedShadowStyles.applyToDocument(TIP_STYLES);
      if (element.hasAttribute("title")) {
        element.dataset.bsOriginalTitle = element.getAttribute("title");
        element.removeAttribute("title"); // no native tooltip besides ours
      }
      const data = element.dataset;
      tips.set(element, new Tip(element, {
        kind,
        root: document.body,
        events: element,
        options: () => ({
          title: data.bsTitle ?? data.bsOriginalTitle ?? "",
          content: data.bsContent ?? "",
          placement: data.bsPlacement,
          trigger: data.bsTrigger,
          delay: data.bsDelay,
          offset: data.bsOffset,
          html: data.bsHtml === "true",
          sanitize: data.bsSanitize !== "false",
          customClass: data.bsCustomClass,
          animation: data.bsAnimation !== "false",
        }),
      }));
    }
    return tips.get(element);
  };
  const triggersOf = (element) => String(element.dataset.bsTrigger || (kind === "popover" ? "click" : "hover focus")).split(/\s+/);
  document.addEventListener("pointerover", (event) => {
    const element = event.target instanceof Element ? event.target.closest(selector) : null;
    if (element && !tips.has(element) && event.pointerType !== "touch" && triggersOf(element).includes("hover")) {
      tipFor(element).show();
    }
  });
  document.addEventListener("focusin", (event) => {
    const element = event.target instanceof Element ? event.target.closest(selector) : null;
    if (element && !tips.has(element) && triggersOf(element).includes("focus")) {
      tipFor(element).show();
    }
  });
  document.addEventListener("click", (event) => {
    const element = event.target instanceof Element ? event.target.closest(selector) : null;
    if (element && !tips.has(element) && triggersOf(element).includes("click")) {
      const tip = tipFor(element);
      tip.pinned = true;
      tip.show();
    }
  });
  return (element) => tipFor(element);
}
