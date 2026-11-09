import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { afterTransition } from "../../../core/transitions.js";

const PERSIST_STORAGE_PREFIX = "ui-tabs.";

/**
 * <ui-tabs> container.
 *
 * Renders the tab navigation in its shadow root from the headings of its
 * <ui-tab-panel> children and switches panels with Bootstrap's fade
 * transition. Supports the WAI-ARIA tabs keyboard pattern (arrow keys,
 * Home/End) with automatic activation.
 *
 * Attributes:
 * - variant: "tabs" (default), "pills", or "underline".
 * - fill / justified: Bootstrap nav-fill / nav-justified behavior.
 * - persist-key: restores the last active tab from localStorage.
 * - card: Bootstrap card with the tabs in its header (.card-header-tabs) and the panels in its
 *   body, so the tabs close cleanly with the content below.
 *
 * Slots: the panels; "actions" for content right of the tabs (e.g. filters), on the same line.
 *
 * CSS parts: nav (the .nav list), tab (each .nav-link), content (.tab-content), actions; with card
 * also card, header and body (style them like ui-card's parts).
 *
 * Events:
 * - ui-tabs:change (bubbles) with detail { index, name, panel } after a
 *   panel became active.
 */
export class UiTabs extends ShadowComponentElement {
  static stylesheet = new URL("./ui-tabs.css", import.meta.url).href;
  static observedAttributes = ["variant", "fill", "justified", "persist-key", "card"];

  #persistRestored = false;
  #switching = false;
  #renderedActiveIndex = -1;
  #knownPanels = [];

  render() {
    const panels = this.getPanels();
    // Resolve once per render pass; afterRender syncs the panel attributes
    // to the same index (persist restoration is only consulted once).
    const activeIndex = this.#resolveActiveIndex(panels);
    this.#renderedActiveIndex = activeIndex;
    const buttons = panels.map((panel, index) => {
      const heading = panel.getAttribute("heading") || `Tab ${index + 1}`;
      const active = index === activeIndex;
      const disabled = panel.hasAttribute("disabled");
      return `
        <li class="nav-item" role="presentation">
          <button
            class="nav-link${active ? " active" : ""}${disabled ? " disabled" : ""}"
            part="tab${active ? " tab-active" : ""}"
            type="button"
            role="tab"
            data-index="${index}"
            aria-selected="${active ? "true" : "false"}"
            ${disabled ? "disabled" : ""}
          >${escapeHtml(heading)}</button>
        </li>
      `;
    }).join("");

    if (this.hasAttribute("card")) {
      return `
        <div class="ui-tabs card" part="card">
          <div class="card-header ui-tabs__header" part="header">
            <ul class="${this.#navClass()} card-header-${this.getAttribute("variant") === "pills" ? "pills" : "tabs"}" role="tablist" part="nav">
              ${buttons}
            </ul>
            <div class="ui-tabs__actions" part="actions"><slot name="actions"></slot></div>
          </div>
          <div class="card-body tab-content" part="body content">
            <slot></slot>
          </div>
        </div>
      `;
    }
    return `
      <div class="ui-tabs">
        <div class="ui-tabs__header">
          <ul class="${this.#navClass()}" role="tablist" part="nav">
            ${buttons}
          </ul>
          <div class="ui-tabs__actions" part="actions"><slot name="actions"></slot></div>
        </div>
        <div class="tab-content" part="content">
          <slot></slot>
        </div>
      </div>
    `;
  }

  afterRender() {
    const tablist = this.shadowRoot.querySelector("[role='tablist']");
    tablist.addEventListener("click", (event) => {
      const button = event.target.closest("[data-index]");
      if (button && !button.disabled) {
        this.select(Number.parseInt(button.dataset.index, 10));
      }
    });
    tablist.addEventListener("keydown", (event) => this.#onKeydown(event));
    // Re-rendering recreates the slot, which fires slotchange again — only
    // re-render when the panel set actually changed, or this would loop.
    this.#knownPanels = this.getPanels();
    this.shadowRoot.querySelector("slot:not([name])").addEventListener("slotchange", () => {
      if (this.#panelsChanged()) {
        this.requestRender();
      }
    });
    this.#syncPanelAttributes();
  }

  #panelsChanged() {
    const panels = this.getPanels();
    const unchanged = panels.length === this.#knownPanels.length
      && panels.every((panel, index) => panel === this.#knownPanels[index]);
    if (unchanged) {
      return false;
    }
    this.#knownPanels = panels;
    return true;
  }

  getPanels() {
    return Array.from(this.querySelectorAll(":scope > ui-tab-panel"));
  }

  getActiveIndex() {
    return this.getPanels().findIndex((panel) => panel.hasAttribute("active"));
  }

  async select(index, { focus = false } = {}) {
    const panels = this.getPanels();
    const target = panels[index];
    if (!target || target.hasAttribute("disabled") || this.#switching) {
      return;
    }
    const currentIndex = this.getActiveIndex();
    if (index === currentIndex) {
      return;
    }

    this.#switching = true;
    this.#syncNavState(index, { focus });
    const current = panels[currentIndex];
    if (current) {
      await current.deactivate();
    }
    target.activate();
    this.#switching = false;

    this.#persistActive(target, index);
    this.dispatchEvent(new CustomEvent("ui-tabs:change", {
      bubbles: true,
      detail: { index, name: target.getAttribute("name") || null, panel: target },
    }));
  }

  #navClass() {
    const variant = this.getAttribute("variant");
    const classes = ["nav"];
    if (variant === "pills") {
      classes.push("nav-pills");
    } else if (variant === "underline") {
      classes.push("nav-underline");
    } else {
      classes.push("nav-tabs");
    }
    if (this.hasAttribute("fill")) {
      classes.push("nav-fill");
    }
    if (this.hasAttribute("justified")) {
      classes.push("nav-justified");
    }
    return classes.join(" ");
  }

  #resolveActiveIndex(panels) {
    if (!panels.length) {
      return -1;
    }
    const enabled = (index) => index >= 0 && !panels[index].hasAttribute("disabled");

    if (!this.#persistRestored) {
      this.#persistRestored = true;
      const storedIndex = this.#restorePersisted(panels);
      if (enabled(storedIndex)) {
        return storedIndex;
      }
    }

    const markupIndex = panels.findIndex(
      (panel) => panel.hasAttribute("active") && !panel.hasAttribute("disabled"),
    );
    if (markupIndex !== -1) {
      return markupIndex;
    }
    return panels.findIndex((panel) => !panel.hasAttribute("disabled"));
  }

  // The nav lives in this component's shadow root; the panels reflect the
  // active state as attributes so both stay in sync after a switch.
  #syncNavState(activeIndex, { focus = false } = {}) {
    this.shadowRoot.querySelectorAll("[data-index]").forEach((button) => {
      const active = Number.parseInt(button.dataset.index, 10) === activeIndex;
      button.classList.toggle("active", active);
      button.setAttribute("part", active ? "tab tab-active" : "tab");
      button.setAttribute("aria-selected", active ? "true" : "false");
      if (active && focus) {
        button.focus();
      }
    });
  }

  #syncPanelAttributes() {
    const panels = this.getPanels();
    const activeIndex = this.#renderedActiveIndex;
    panels.forEach((panel, index) => {
      if (index === activeIndex && !panel.hasAttribute("active")) {
        panel.setAttribute("active", "");
      } else if (index !== activeIndex && panel.hasAttribute("active")) {
        panel.removeAttribute("active");
      }
    });
  }

  #onKeydown(event) {
    const steps = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
    const panels = this.getPanels();
    const enabledIndexes = panels
      .map((panel, index) => (panel.hasAttribute("disabled") ? null : index))
      .filter((index) => index !== null);
    if (!enabledIndexes.length) {
      return;
    }

    let targetIndex = null;
    if (event.key === "Home") {
      targetIndex = enabledIndexes[0];
    } else if (event.key === "End") {
      targetIndex = enabledIndexes[enabledIndexes.length - 1];
    } else if (event.key in steps) {
      const current = this.getActiveIndex();
      const position = Math.max(enabledIndexes.indexOf(current), 0);
      const nextPosition = (position + steps[event.key] + enabledIndexes.length) % enabledIndexes.length;
      targetIndex = enabledIndexes[nextPosition];
    } else {
      return;
    }

    event.preventDefault();
    this.select(targetIndex, { focus: true });
  }

  #persistKey() {
    const key = (this.getAttribute("persist-key") || "").trim();
    return key ? `${PERSIST_STORAGE_PREFIX}${key}` : null;
  }

  #persistActive(panel, index) {
    const key = this.#persistKey();
    if (!key) {
      return;
    }
    try {
      window.localStorage.setItem(key, panel.getAttribute("name") || String(index));
    } catch {
      // Storage may be unavailable (private mode, quota); persistence is optional.
    }
  }

  #restorePersisted(panels) {
    const key = this.#persistKey();
    if (!key) {
      return -1;
    }
    let stored = null;
    try {
      stored = window.localStorage.getItem(key);
    } catch {
      return -1;
    }
    if (stored === null) {
      return -1;
    }
    const namedIndex = panels.findIndex((panel) => panel.getAttribute("name") === stored);
    if (namedIndex !== -1) {
      return namedIndex;
    }
    const numeric = Number.parseInt(stored, 10);
    return Number.isInteger(numeric) && numeric >= 0 && numeric < panels.length ? numeric : -1;
  }
}

/**
 * <ui-tab-panel> content pane.
 *
 * Attributes:
 * - heading: plain-text label rendered in the parent's tab navigation.
 * - name: stable identifier, used for persistence and the change event.
 * - active: current state; reflected when the user switches tabs.
 * - disabled: excludes the tab from selection.
 */
export class UiTabPanel extends ShadowComponentElement {
  static stylesheet = new URL("./ui-tabs.css", import.meta.url).href;
  static observedAttributes = ["heading", "name", "active", "disabled"];

  #suppressActiveAttribute = false;

  attributeChangedCallback(name, oldValue, newValue) {
    // Internal switches animate the pane directly and only reflect the
    // state; re-rendering here would cut the fade transition short.
    if (name === "active" && this.#suppressActiveAttribute) {
      return;
    }
    super.attributeChangedCallback(name, oldValue, newValue);
    if (oldValue !== newValue && (name === "heading" || name === "disabled" || name === "active")) {
      // The tab navigation lives in the parent's shadow root.
      this.closest("ui-tabs")?.requestRender();
    }
  }

  get active() {
    return this.hasAttribute("active");
  }

  render() {
    const active = this.active;
    return `
      <div class="tab-pane fade${active ? " show active" : ""}" role="tabpanel">
        <slot></slot>
      </div>
    `;
  }

  activate() {
    this.#reflectActive(true);
    const pane = this.shadowRoot?.querySelector(".tab-pane");
    if (!pane) {
      return;
    }
    pane.classList.add("active");
    pane.offsetHeight; // force reflow so the fade-in transition runs
    pane.classList.add("show");
  }

  deactivate() {
    this.#reflectActive(false);
    const pane = this.shadowRoot?.querySelector(".tab-pane");
    if (!pane) {
      return Promise.resolve();
    }
    return new Promise((resolve) => {
      pane.classList.remove("show");
      afterTransition(pane, () => {
        pane.classList.remove("active");
        resolve();
      });
    });
  }

  #reflectActive(active) {
    this.#suppressActiveAttribute = true;
    this.toggleAttribute("active", active);
    this.#suppressActiveAttribute = false;
  }
}

registerComponent("ui-tabs", UiTabs);
registerComponent("ui-tab-panel", UiTabPanel);
