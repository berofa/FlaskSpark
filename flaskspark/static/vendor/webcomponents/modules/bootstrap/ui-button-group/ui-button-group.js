import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";

/**
 * <ui-button-group>.
 *
 * Groups <ui-button> (and <ui-dropdown>) children with collapsed borders and radii like
 * Bootstrap's .btn-group. Border/radius corrections happen inside each
 * button's shadow tree, so the group mirrors its state onto the children
 * via the "grouped" attribute (horizontal|vertical), their place via
 * "group-first" / "group-last", and mirrors "size". A button may sit in a
 * <ui-tooltip> or <ui-popover> child (a hint per button) and still belongs
 * to the group.
 *
 * Attributes:
 * - vertical: stacks the buttons vertically.
 * - size: "sm" or "lg", mirrored onto every child ui-button.
 * - label: aria-label for the group.
 */
export class UiButtonGroup extends ShadowComponentElement {
  static stylesheet = new URL("./ui-button-group.css", import.meta.url).href;
  static observedAttributes = ["vertical", "size", "label"];

  #knownChildren = [];

  render() {
    const vertical = this.hasAttribute("vertical");
    const label = this.getAttribute("label") || "";
    return `
      <div class="${vertical ? "btn-group-vertical" : "btn-group"}" role="group"${label ? ` aria-label="${escapeHtml(label)}"` : ""}>
        <slot></slot>
      </div>
    `;
  }

  afterRender() {
    // Re-rendering recreates the slot, which fires slotchange again — only
    // re-sync when the child set actually changed, or this would loop.
    this.#knownChildren = this.getButtons();
    this.shadowRoot.querySelector("slot").addEventListener("slotchange", () => {
      if (this.#childrenChanged()) {
        this.#syncButtons();
      }
    });
    this.#syncButtons();
  }

  /** Grouped children: ui-button and ui-dropdown (a dropdown inside the group, like Bootstrap's nested .btn-group). */
  getButtons() {
    return Array.from(this.querySelectorAll(":scope > ui-button, :scope > ui-dropdown, "
      + ":scope > ui-tooltip > ui-button, :scope > ui-popover > ui-button"));
  }

  #childrenChanged() {
    const children = this.getButtons();
    const unchanged = children.length === this.#knownChildren.length
      && children.every((child, index) => child === this.#knownChildren[index]);
    if (unchanged) {
      return false;
    }
    this.#knownChildren = children;
    return true;
  }

  #syncButtons() {
    const orientation = this.hasAttribute("vertical") ? "vertical" : "horizontal";
    const size = this.getAttribute("size");
    const buttons = this.getButtons();
    buttons.forEach((button, index) => {
      button.setAttribute("grouped", orientation);
      button.toggleAttribute("group-first", index === 0);
      button.toggleAttribute("group-last", index === buttons.length - 1);
      if (size === "sm" || size === "lg") {
        button.setAttribute("size", size);
      }
    });
  }
}

registerComponent("ui-button-group", UiButtonGroup);
