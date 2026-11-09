import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { afterTransition } from "../../../core/transitions.js";

const DIALOG_SIZES = new Set(["sm", "lg", "xl"]);
const FULLSCREEN_BREAKPOINTS = new Set(["sm", "md", "lg", "xl", "xxl"]);

/**
 * <ui-modal>.
 *
 * Attributes:
 * - open: visible state; reflected, can be set declaratively.
 * - heading: plain-text title (use the "heading" slot for rich content).
 * - size: "sm", "lg", or "xl".
 * - centered / scrollable: Bootstrap dialog modifiers.
 * - fullscreen: boolean, or a breakpoint ("md" → modal-fullscreen-md-down).
 * - static: backdrop click and Escape play the shake animation instead of
 *   closing.
 *
 * Slots: default (body), "heading", "footer". Slotted elements carrying
 * data-ui-modal-close close the modal on click.
 *
 * Triggers: any element with data-ui-modal-toggle="<id>" toggles the modal
 * with that id (aria-haspopup="dialog" and aria-controls are set on click).
 *
 * Methods / events:
 * - open(), close(), toggle()
 * - ui-modal:show (bubbles) when opening starts, before the transition —
 *   e.g. to load or reset the content.
 * - ui-modal:shown / ui-modal:hidden (bubble) after the transition ended.
 */
export class UiModal extends ShadowComponentElement {
  static stylesheet = new URL("./ui-modal.css", import.meta.url).href;
  static observedAttributes = [
    "open",
    "heading",
    "size",
    "centered",
    "scrollable",
    "fullscreen",
    "static",
  ];

  #shown = false;
  #transitioning = false;
  #suppressOpenAttribute = false;
  #previousFocus = null;
  #previousBodyStyle = null;

  constructor() {
    super();
    // Slotted footer buttons etc. close the modal via data-ui-modal-close.
    this.addEventListener("click", (event) => {
      if (event.target.closest?.("[data-ui-modal-close]")) {
        this.close();
      }
    });
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "open") {
      if (this.#suppressOpenAttribute) {
        return;
      }
      // Declarative open/close after the first render takes the animated
      // path; a plain re-render would skip transitions and side effects.
      if (this.hasRendered) {
        if (newValue !== null) {
          this.open();
        } else {
          this.close();
        }
        return;
      }
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  disconnectedCallback() {
    this.#removeDocumentListeners();
    if (this.#shown) {
      this.#unlockBodyScroll();
      this.#shown = false;
    }
  }

  render() {
    const open = this.hasAttribute("open");
    const heading = this.getAttribute("heading") || "";
    return `
      <div
        class="modal fade${open ? " show" : ""}"
        tabindex="-1"
        role="dialog"
        aria-modal="true"
        ${open ? 'style="display: block;"' : ""}
      >
        <div class="${escapeHtml(this.#dialogClasses())}">
          <div class="modal-content">
            <div class="modal-header" data-slot-wrapper="header" hidden>
              <h5 class="modal-title"><slot name="heading">${escapeHtml(heading)}</slot></h5>
              <button type="button" class="btn-close" aria-label="Close"></button>
            </div>
            <div class="modal-body">
              <slot></slot>
            </div>
            <div class="modal-footer" data-slot-wrapper="footer" hidden>
              <slot name="footer"></slot>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-backdrop fade${open ? " show" : ""}" style="display: ${open ? "block" : "none"};"></div>
    `;
  }

  afterRender() {
    const modal = this.shadowRoot.querySelector(".modal");
    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        this.#onDismissRequest();
      }
    });
    this.shadowRoot.querySelector(".btn-close").addEventListener("click", () => this.close());
    this.#syncSlotVisibility("heading", "header", () => Boolean(this.getAttribute("heading")));
    this.#syncSlotVisibility("footer", "footer", () => false);

    // Rendered directly into the open state (open attribute in markup or a
    // re-render while shown): make sure the side effects are active.
    if (this.hasAttribute("open") && !this.#shown) {
      this.#shown = true;
      this.#lockBodyScroll();
      this.#addDocumentListeners();
    }
  }

  get shown() {
    return this.#shown;
  }

  open() {
    if (this.#shown || this.#transitioning) {
      return;
    }
    const modal = this.shadowRoot?.querySelector(".modal");
    const backdrop = this.shadowRoot?.querySelector(".modal-backdrop");
    if (!modal) {
      this.#reflectOpen(true);
      return;
    }
    this.#shown = true;
    this.#transitioning = true;
    this.#reflectOpen(true);
    this.dispatchEvent(new CustomEvent("ui-modal:show", { bubbles: true }));
    this.#previousFocus = document.activeElement;
    this.#lockBodyScroll();
    this.#addDocumentListeners();
    backdrop.style.display = "block";
    modal.style.display = "block";
    modal.offsetHeight; // force reflow so the fade transition runs
    backdrop.classList.add("show");
    modal.classList.add("show");
    afterTransition(modal, () => {
      this.#transitioning = false;
      modal.focus();
      this.dispatchEvent(new CustomEvent("ui-modal:shown", { bubbles: true }));
    });
  }

  close() {
    if (!this.#shown || this.#transitioning) {
      return;
    }
    const modal = this.shadowRoot?.querySelector(".modal");
    const backdrop = this.shadowRoot?.querySelector(".modal-backdrop");
    this.#shown = false;
    this.#reflectOpen(false);
    this.#removeDocumentListeners();
    if (!modal) {
      this.#unlockBodyScroll();
      return;
    }
    this.#transitioning = true;
    modal.classList.remove("show");
    backdrop.classList.remove("show");
    afterTransition(modal, () => {
      modal.style.display = "none";
      backdrop.style.display = "none";
      this.#transitioning = false;
      this.#unlockBodyScroll();
      this.#previousFocus?.focus?.();
      this.#previousFocus = null;
      this.dispatchEvent(new CustomEvent("ui-modal:hidden", { bubbles: true }));
    });
  }

  toggle() {
    if (this.#shown) {
      this.close();
    } else {
      this.open();
    }
  }

  #dialogClasses() {
    const classes = ["modal-dialog"];
    const size = this.getAttribute("size");
    if (DIALOG_SIZES.has(size)) {
      classes.push(`modal-${size}`);
    }
    if (this.hasAttribute("centered")) {
      classes.push("modal-dialog-centered");
    }
    if (this.hasAttribute("scrollable")) {
      classes.push("modal-dialog-scrollable");
    }
    const fullscreen = this.getAttribute("fullscreen");
    if (fullscreen !== null) {
      classes.push(
        FULLSCREEN_BREAKPOINTS.has(fullscreen) ? `modal-fullscreen-${fullscreen}-down` : "modal-fullscreen",
      );
    }
    return classes.join(" ");
  }

  #syncSlotVisibility(slotName, wrapperName, hasFallbackContent) {
    const slot = this.shadowRoot.querySelector(`slot[name="${slotName}"]`);
    const wrapper = this.shadowRoot.querySelector(`[data-slot-wrapper="${wrapperName}"]`);
    const sync = () => {
      const hasContent = hasFallbackContent() || slot.assignedNodes().some((node) => (
        node.nodeType === Node.ELEMENT_NODE
        || (node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0)
      ));
      wrapper.hidden = !hasContent;
    };
    slot.addEventListener("slotchange", sync);
    sync();
  }

  #onDismissRequest() {
    if (this.hasAttribute("static")) {
      this.#playStaticAnimation();
      return;
    }
    this.close();
  }

  #playStaticAnimation() {
    const modal = this.shadowRoot?.querySelector(".modal");
    if (!modal || modal.classList.contains("modal-static")) {
      return;
    }
    modal.classList.add("modal-static");
    window.setTimeout(() => modal.classList.remove("modal-static"), 300);
  }

  #onDocumentKeydown = (event) => {
    if (event.key === "Escape") {
      this.#onDismissRequest();
    }
  };

  #onDocumentFocusIn = (event) => {
    // Light focus trap: pull focus back when it leaves the modal.
    if (this.#shown && !this.#transitioning && !event.composedPath().includes(this)) {
      this.shadowRoot?.querySelector(".modal")?.focus();
    }
  };

  #addDocumentListeners() {
    document.addEventListener("keydown", this.#onDocumentKeydown);
    document.addEventListener("focusin", this.#onDocumentFocusIn);
  }

  #removeDocumentListeners() {
    document.removeEventListener("keydown", this.#onDocumentKeydown);
    document.removeEventListener("focusin", this.#onDocumentFocusIn);
  }

  #reflectOpen(open) {
    this.#suppressOpenAttribute = true;
    this.toggleAttribute("open", open);
    this.#suppressOpenAttribute = false;
  }

  #lockBodyScroll() {
    const scrollbarWidth = Math.max(0, window.innerWidth - document.documentElement.clientWidth);
    this.#previousBodyStyle = {
      overflow: document.body.style.overflow,
      paddingRight: document.body.style.paddingRight,
    };
    document.body.style.overflow = "hidden";
    if (scrollbarWidth > 0) {
      const current = Number.parseFloat(getComputedStyle(document.body).paddingRight) || 0;
      document.body.style.paddingRight = `${current + scrollbarWidth}px`;
    }
  }

  #unlockBodyScroll() {
    if (!this.#previousBodyStyle) {
      return;
    }
    document.body.style.overflow = this.#previousBodyStyle.overflow;
    document.body.style.paddingRight = this.#previousBodyStyle.paddingRight;
    this.#previousBodyStyle = null;
  }
}

// One delegated listener for all triggers: data-ui-modal-toggle="<id>".
document.addEventListener("click", (event) => {
  const trigger = event.target.closest?.("[data-ui-modal-toggle]");
  const target = trigger && document.getElementById(trigger.dataset.uiModalToggle);
  if (target instanceof UiModal) {
    event.preventDefault();
    trigger.setAttribute("aria-haspopup", "dialog");
    trigger.setAttribute("aria-controls", target.id);
    target.toggle();
  }
});

registerComponent("ui-modal", UiModal);
