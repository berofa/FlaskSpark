import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";

const BREAKPOINTS = ["sm", "md", "lg", "xl", "2xl"];
const GAPS = ["gap", "gap-x", "gap-y"];

/**
 * <ui-grid>: its children in an equal-column CSS grid, with a column count per Bootstrap 6 breakpoint.
 * Not a Bootstrap component (Bootstrap's .row/.col are markup); themed with --ui-grid-* tokens.
 *
 * Attributes:
 * - columns (default 1), columns-sm, columns-md, columns-lg, columns-xl, columns-2xl: columns from that
 *   breakpoint up (576, 768, 1024, 1280, 1536px), each falling back to the next smaller one.
 * - container: the breakpoints apply to the grid's own width (container queries) instead of the viewport.
 * - gap, gap-x, gap-y: spacing (any CSS length, or a Bootstrap spacer 0–12 like "3").
 * - align: start | center | end | stretch (vertical alignment of the children).
 * A child spans columns or rows with the style grid-column: span 2 (or --ui-grid-span: 2).
 * Parts: grid.
 */
export class UiGrid extends ShadowComponentElement {
  #own = new Set(); // properties this element set (a page's own inline values stay)

  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-grid.css", import.meta.url).href];
  static observedAttributes = ["columns", ...BREAKPOINTS.map((name) => `columns-${name}`), ...GAPS, "container", "align"];

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue === newValue) {
      return;
    }
    if (this.hasRendered && name !== "container") {
      this.#apply(); // attributes only map to custom properties
      return;
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  render() {
    return `<div class="ui-grid${this.hasAttribute("container") ? " ui-grid-container" : ""}" part="grid"><slot></slot></div>`;
  }

  afterRender() {
    this.#apply();
  }

  #apply() {
    const set = (property, value) => {
      if (value) {
        this.style.setProperty(property, value);
        this.#own.add(property);
      } else if (this.#own.delete(property)) {
        this.style.removeProperty(property);
      }
    };
    set("--ui-grid-columns", this.getAttribute("columns"));
    BREAKPOINTS.forEach((name) => set(`--_columns-${name}`, this.getAttribute(`columns-${name}`)));
    GAPS.forEach((name) => {
      const value = this.getAttribute(name);
      const length = value && /^\d+$/.test(value.trim()) ? `var(--bs-spacer-${value.trim()})` : value;
      set(`--ui-grid-${name}`, length);
    });
    set("--ui-grid-align", this.getAttribute("align"));
  }
}

registerComponent("ui-grid", UiGrid);
