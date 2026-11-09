import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { collapseElement, expandElement } from "../../../core/collapse-transition.js";

/**
 * <ui-collapse>.
 *
 * Attributes:
 * - open: visible state; reflected, can be toggled declaratively.
 * - horizontal: animates width instead of height.
 *
 * Methods / events:
 * - show(), hide(), toggle()
 * - ui-collapse:shown / ui-collapse:hidden (bubble) after the transition.
 */
export class UiCollapse extends ShadowComponentElement {
  static stylesheet = new URL("./ui-collapse.css", import.meta.url).href;
  static observedAttributes = ["open", "horizontal"];

  #suppressOpenAttribute = false;
  #animating = false;

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "open") {
      if (this.#suppressOpenAttribute) {
        return;
      }
      // Declarative toggles after the first render take the animated path.
      if (this.hasRendered) {
        if (newValue !== null) {
          this.show();
        } else {
          this.hide();
        }
        return;
      }
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  get shown() {
    return this.hasAttribute("open");
  }

  render() {
    const open = this.hasAttribute("open");
    const horizontal = this.hasAttribute("horizontal");
    return `
      <div class="collapse${horizontal ? " collapse-horizontal" : ""}${open ? " show" : ""}">
        <slot></slot>
      </div>
    `;
  }

  show() {
    if (this.#animating || this.shown) {
      return;
    }
    const node = this.shadowRoot?.querySelector(".collapse, .collapsing");
    this.#reflectOpen(true);
    if (!node) {
      return;
    }
    this.#animating = true;
    expandElement(node, {
      dimension: this.hasAttribute("horizontal") ? "width" : "height",
      onComplete: () => {
        this.#animating = false;
        this.dispatchEvent(new CustomEvent("ui-collapse:shown", { bubbles: true }));
      },
    });
  }

  hide() {
    if (this.#animating || !this.shown) {
      return;
    }
    const node = this.shadowRoot?.querySelector(".collapse, .collapsing");
    this.#reflectOpen(false);
    if (!node) {
      return;
    }
    this.#animating = true;
    collapseElement(node, {
      dimension: this.hasAttribute("horizontal") ? "width" : "height",
      onComplete: () => {
        this.#animating = false;
        this.dispatchEvent(new CustomEvent("ui-collapse:hidden", { bubbles: true }));
      },
    });
  }

  toggle() {
    if (this.shown) {
      this.hide();
    } else {
      this.show();
    }
  }

  #reflectOpen(open) {
    this.#suppressOpenAttribute = true;
    this.toggleAttribute("open", open);
    this.#suppressOpenAttribute = false;
  }
}

registerComponent("ui-collapse", UiCollapse);
