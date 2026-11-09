import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";

export class UiGrid extends ShadowComponentElement {
  static stylesheet = new URL("./ui-grid.css", import.meta.url).href;
  static observedAttributes = [
    "columns",
    "columns-sm",
    "columns-md",
    "columns-lg",
    "columns-xl",
    "gap",
  ];

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue === newValue) {
      return;
    }
    // Attributes only map to CSS custom properties, so a full re-render is
    // unnecessary once the shadow DOM exists.
    if (this.hasRendered) {
      this.applyGridVariables();
      return;
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  render() {
    return `
      <div class="ui-grid">
        <slot></slot>
      </div>
    `;
  }

  afterRender() {
    this.applyGridVariables();
  }

  applyGridVariables() {
    const mappings = [
      ["columns", "--_grid-columns"],
      ["columns-sm", "--_grid-columns-sm"],
      ["columns-md", "--_grid-columns-md"],
      ["columns-lg", "--_grid-columns-lg"],
      ["columns-xl", "--_grid-columns-xl"],
      ["gap", "--_grid-gap"],
    ];

    mappings.forEach(([attributeName, cssName]) => {
      const value = this.getAttribute(attributeName);
      if (value) {
        this.style.setProperty(cssName, value);
      } else {
        this.style.removeProperty(cssName);
      }
    });
  }
}

registerComponent("ui-grid", UiGrid);
