import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";

export class UiCard extends ShadowComponentElement {
  static stylesheet = new URL("./ui-card.css", import.meta.url).href;
  static observedAttributes = [
    "variant",
    "bg",
    "text",
    "border",
    "shadow",
    "align",
    "body-padding",
  ];

  render() {
    const cardClasses = this.resolveCardClasses();
    const bodyClasses = this.resolveBodyClasses();

    return `
      <article class="${escapeHtml(cardClasses)}" data-part="card" part="card">
        <slot name="image-top"></slot>
        <div class="card-header" data-slot-wrapper="header" part="header" hidden>
          <slot name="header"></slot>
        </div>
        <div class="${escapeHtml(bodyClasses)}" part="body">
          <slot name="eyebrow"></slot>
          <slot name="title"></slot>
          <slot name="subtitle"></slot>
          <slot name="text"></slot>
          <slot name="link"></slot>
          <slot></slot>
        </div>
        <ul class="list-group list-group-flush" data-slot-wrapper="list" hidden>
          <slot name="list"></slot>
        </ul>
        <div class="card-footer" data-slot-wrapper="footer" part="footer" hidden>
          <slot name="footer"></slot>
        </div>
        <slot name="image-bottom"></slot>
        <div class="card-img-overlay d-grid gap-3" data-slot-wrapper="overlay" hidden>
          <slot name="overlay"></slot>
        </div>
      </article>
    `;
  }

  afterRender() {
    ["header", "list", "footer", "overlay"].forEach((slotName) => {
      const slot = this.shadowRoot.querySelector(`slot[name="${slotName}"]`);
      if (!slot) {
        return;
      }

      const sync = () => this.syncSlotVisibility(slotName, slot);
      slot.addEventListener("slotchange", sync);
      sync();
    });
  }

  syncSlotVisibility(slotName, slot) {
    const wrapper = this.shadowRoot.querySelector(`[data-slot-wrapper="${slotName}"]`);
    const hasContent = slot.assignedNodes().some((node) => {
      if (node.nodeType === Node.ELEMENT_NODE) {
        return true;
      }
      if (node.nodeType === Node.TEXT_NODE) {
        return node.textContent.trim().length > 0;
      }
      return false;
    });

    if (wrapper) {
      wrapper.hidden = !hasContent;
    }

    if (slotName === "overlay") {
      const card = this.shadowRoot.querySelector("[data-part='card']");
      card?.classList.toggle("ui-card--has-overlay", hasContent);
    }
  }

  resolveCardClasses() {
    const classes = ["card", "h-100"];
    const variant = this.getAttribute("variant");
    const bg = this.getAttribute("bg");
    const text = this.getAttribute("text");
    const border = this.getAttribute("border");
    const shadow = this.getAttribute("shadow");
    const align = this.getAttribute("align");

    if (variant) {
      classes.push(`text-bg-${variant}`);
    }
    if (bg) {
      classes.push(`bg-${bg}`);
    }
    if (text) {
      classes.push(`text-${text}`);
    }
    if (border) {
      classes.push(`border-${border}`);
    }
    if (align) {
      classes.push(`text-${align}`);
    }
    if (shadow === "sm") {
      classes.push("shadow-sm");
    } else if (shadow === "lg") {
      classes.push("shadow-lg");
    } else if (shadow === "none") {
      classes.push("shadow-none");
    } else if (shadow) {
      classes.push("shadow");
    }

    return classes.join(" ");
  }

  resolveBodyClasses() {
    const classes = ["card-body", "d-grid", "gap-3"];
    const bodyPadding = this.getAttribute("body-padding");

    if (bodyPadding) {
      classes.push(`p-${bodyPadding}`);
    }

    return classes.join(" ");
  }
}

registerComponent("ui-card", UiCard);
