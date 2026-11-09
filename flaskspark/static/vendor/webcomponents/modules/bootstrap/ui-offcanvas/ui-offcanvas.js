import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { afterTransition } from "../../../core/transitions.js";

const PLACEMENTS = new Set(["start", "end", "top", "bottom"]);
// Bootstrap's grid breakpoints (media-breakpoint-up).
const BREAKPOINTS = { sm: 576, md: 768, lg: 992, xl: 1200, xxl: 1400 };

/**
 * <ui-offcanvas>.
 *
 * Attributes:
 * - open: visible state; reflected, can be set declaratively.
 * - heading: plain-text title (use the "heading" slot for rich content).
 * - placement: "start" (default), "end", "top" or "bottom".
 * - responsive: breakpoint ("sm"–"xxl") from which the panel is docked into
 *   the page layout (always visible, no header, no backdrop) — e.g. a sidebar
 *   that becomes an offcanvas behind a hamburger on small screens. While
 *   docked the host carries the `docked` attribute.
 * - backdrop: "static" keeps the panel open on backdrop click and Escape,
 *   "false" renders no backdrop.
 * - scroll: keep the page scrollable while open.
 * - label: accessible name of the panel (default: the heading).
 *
 * Slots: default (body), "heading". Slotted elements carrying
 * data-ui-offcanvas-close close the panel on click.
 *
 * Triggers: any element with data-ui-offcanvas-toggle="<id>" toggles the
 * offcanvas with that id and gets aria-expanded/aria-controls.
 *
 * Methods / events:
 * - open(), close(), toggle()
 * - ui-offcanvas:shown / ui-offcanvas:hidden (bubble) after the transition;
 *   ui-offcanvas:dock (bubbles, detail.docked) when docking changes.
 */
export class UiOffcanvas extends ShadowComponentElement {
  static stylesheet = new URL("./ui-offcanvas.css", import.meta.url).href;
  static observedAttributes = ["open", "heading", "placement", "responsive", "backdrop", "scroll", "label"];

  #shown = false;
  #transitioning = false;
  #suppressOpenAttribute = false;
  #previousFocus = null;
  #previousBodyOverflow = null;
  #media = null;

  constructor() {
    super();
    this.addEventListener("click", (event) => {
      if (event.target.closest?.("[data-ui-offcanvas-close]")) {
        this.close();
      }
    });
  }

  connectedCallback() {
    this.#watchBreakpoint();
    super.connectedCallback();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "open") {
      if (this.#suppressOpenAttribute) {
        return;
      }
      if (this.hasRendered) {
        if (newValue !== null) {
          this.open();
        } else {
          this.close();
        }
        return;
      }
    }
    if (name === "responsive" && this.isConnected) {
      this.#watchBreakpoint();
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  disconnectedCallback() {
    this.#media?.removeEventListener("change", this.#onMediaChange);
    this.#media = null;
    this.#removeDocumentListeners();
    if (this.#shown) {
      this.#unlockBodyScroll();
      this.#shown = false;
    }
  }

  render() {
    const placement = PLACEMENTS.has(this.getAttribute("placement")) ? this.getAttribute("placement") : "start";
    const responsive = this.getAttribute("responsive");
    const base = responsive in BREAKPOINTS ? `offcanvas-${responsive}` : "offcanvas";
    const heading = this.getAttribute("heading") || "";
    const label = this.getAttribute("label") || heading;
    const shown = this.#shown && !this.docked;
    const backdrop = this.getAttribute("backdrop") !== "false";
    return `
      <div
        part="panel"
        class="${base} offcanvas-${placement}${shown ? " show" : ""}"
        tabindex="-1"
        ${label ? `aria-label="${escapeHtml(label)}"` : ""}
        ${shown ? 'role="dialog" aria-modal="true"' : ""}
      >
        <div class="offcanvas-header" part="header">
          <h5 class="offcanvas-title" part="title"><slot name="heading">${escapeHtml(heading)}</slot></h5>
          <button type="button" class="btn-close" aria-label="Close"></button>
        </div>
        <div class="offcanvas-body" part="body">
          <slot></slot>
        </div>
      </div>
      ${backdrop ? `<div part="backdrop" class="offcanvas-backdrop fade${shown ? " show" : ""}"${shown ? "" : " hidden"}></div>` : ""}
    `;
  }

  afterRender() {
    this.shadowRoot.querySelector(".btn-close").addEventListener("click", () => this.close());
    this.shadowRoot.querySelector(".offcanvas-backdrop")?.addEventListener("click", () => this.#onDismissRequest());
    if (this.#shown && !this.docked) {
      this.#addDocumentListeners();
    }
  }

  /** True while the panel is docked into the layout (responsive breakpoint reached). */
  get docked() {
    return this.hasAttribute("docked");
  }

  get shown() {
    return this.#shown;
  }

  open() {
    if (this.#shown || this.#transitioning || this.docked) {
      return;
    }
    const panel = this.shadowRoot?.querySelector('[part="panel"]');
    if (!panel) {
      this.#reflectOpen(true);
      return;
    }
    this.#shown = true;
    this.#transitioning = true;
    this.#reflectOpen(true);
    this.#syncTriggers();
    this.#previousFocus = document.activeElement;
    this.#lockBodyScroll();
    this.#addDocumentListeners();
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "true");
    const backdrop = this.shadowRoot.querySelector(".offcanvas-backdrop");
    if (backdrop) {
      backdrop.hidden = false;
      backdrop.offsetHeight; // force reflow so the fade transition runs
      backdrop.classList.add("show");
    }
    panel.classList.add("showing");
    afterTransition(panel, () => {
      panel.classList.remove("showing");
      panel.classList.add("show");
      this.#transitioning = false;
      panel.focus();
      this.dispatchEvent(new CustomEvent("ui-offcanvas:shown", { bubbles: true }));
    });
  }

  close() {
    if (!this.#shown || this.#transitioning) {
      return;
    }
    const panel = this.shadowRoot?.querySelector('[part="panel"]');
    this.#shown = false;
    this.#reflectOpen(false);
    this.#syncTriggers();
    this.#removeDocumentListeners();
    if (!panel) {
      this.#unlockBodyScroll();
      return;
    }
    this.#transitioning = true;
    const backdrop = this.shadowRoot.querySelector(".offcanvas-backdrop");
    backdrop?.classList.remove("show");
    panel.classList.add("hiding");
    afterTransition(panel, () => {
      panel.classList.remove("show", "hiding");
      panel.removeAttribute("role");
      panel.removeAttribute("aria-modal");
      if (backdrop) {
        backdrop.hidden = true;
      }
      this.#transitioning = false;
      this.#unlockBodyScroll();
      this.#previousFocus?.focus?.();
      this.#previousFocus = null;
      this.dispatchEvent(new CustomEvent("ui-offcanvas:hidden", { bubbles: true }));
    });
  }

  toggle() {
    if (this.#shown) {
      this.close();
    } else {
      this.open();
    }
  }

  #watchBreakpoint() {
    this.#media?.removeEventListener("change", this.#onMediaChange);
    const width = BREAKPOINTS[this.getAttribute("responsive")];
    this.#media = width ? window.matchMedia(`(min-width: ${width}px)`) : null;
    this.#media?.addEventListener("change", this.#onMediaChange);
    this.#applyDocked(Boolean(this.#media?.matches), false);
  }

  #onMediaChange = (event) => this.#applyDocked(event.matches, true);

  #applyDocked(docked, notify) {
    if (docked === this.docked) {
      return;
    }
    if (docked && this.#shown) {
      // Growing past the breakpoint while open: drop the overlay state at once.
      this.#shown = false;
      this.#transitioning = false;
      this.#reflectOpen(false);
      this.#removeDocumentListeners();
      this.#unlockBodyScroll();
    }
    this.toggleAttribute("docked", docked);
    this.#syncTriggers();
    this.requestRender();
    if (notify) {
      this.dispatchEvent(new CustomEvent("ui-offcanvas:dock", { bubbles: true, detail: { docked } }));
    }
  }

  #syncTriggers() {
    if (!this.id) {
      return;
    }
    for (const trigger of document.querySelectorAll(`[data-ui-offcanvas-toggle="${CSS.escape(this.id)}"]`)) {
      trigger.setAttribute("aria-controls", this.id);
      trigger.setAttribute("aria-expanded", String(this.#shown));
    }
  }

  #onDismissRequest() {
    if (this.getAttribute("backdrop") === "static") {
      return;
    }
    this.close();
  }

  #onDocumentKeydown = (event) => {
    if (event.key === "Escape") {
      this.#onDismissRequest();
    }
  };

  #addDocumentListeners() {
    document.addEventListener("keydown", this.#onDocumentKeydown);
  }

  #removeDocumentListeners() {
    document.removeEventListener("keydown", this.#onDocumentKeydown);
  }

  #reflectOpen(open) {
    this.#suppressOpenAttribute = true;
    this.toggleAttribute("open", open);
    this.#suppressOpenAttribute = false;
  }

  #lockBodyScroll() {
    if (this.hasAttribute("scroll") || this.#previousBodyOverflow !== null) {
      return;
    }
    this.#previousBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
  }

  #unlockBodyScroll() {
    if (this.#previousBodyOverflow === null) {
      return;
    }
    document.body.style.overflow = this.#previousBodyOverflow;
    this.#previousBodyOverflow = null;
  }
}

// One delegated listener for all triggers: data-ui-offcanvas-toggle="<id>".
document.addEventListener("click", (event) => {
  const trigger = event.target.closest?.("[data-ui-offcanvas-toggle]");
  const target = trigger && document.getElementById(trigger.dataset.uiOffcanvasToggle);
  if (target instanceof UiOffcanvas) {
    event.preventDefault();
    target.toggle();
  }
});

registerComponent("ui-offcanvas", UiOffcanvas);
