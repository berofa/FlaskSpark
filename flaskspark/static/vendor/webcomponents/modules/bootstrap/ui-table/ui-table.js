import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";

const ALIGN = new Set(["top", "middle", "bottom"]);

/**
 * <ui-table>: Bootstrap .table for an author-provided light-DOM <table>.
 *
 * Table rows cannot be slotted into a shadow <table> (the HTML table model
 * needs real parent/child elements), so the component moves the <table>
 * child into its shadow tree and styles it there. A newly inserted <table>
 * child replaces the current one. Script access goes through the `table`
 * property (document.querySelector does not reach into the shadow tree).
 *
 * The stylesheet also contains Bootstrap's reboot and utility classes, so
 * cell markup like text-end, text-success, fw-semibold, small or
 * font-monospace keeps working. Page-level classes do not apply inside.
 *
 * Attributes:
 * - size: "sm" for .table-sm.
 * - striped, hover, bordered, borderless: Bootstrap table modifiers.
 * - valign: "top" | "middle" | "bottom" (vertical cell alignment). Not "align":
 *   browsers map that legacy attribute to text-align on any element.
 * - responsive: horizontal scrolling wrapper (.table-responsive).
 *
 * Classes on the <table> itself are kept (e.g. "mb-0", "caption-top").
 *
 * CSS parts: wrapper, table.
 * Custom properties: --ui-table-head-color, --ui-table-head-font-weight
 * (th cells), plus Bootstrap's --bs-table-* via ::part(table).
 */
export class UiTable extends ShadowComponentElement {
  static stylesheet = new URL("./ui-table.css", import.meta.url).href;
  static observedAttributes = ["size", "striped", "hover", "bordered", "borderless", "valign", "responsive"];

  #table = null;
  #authorClasses = "";
  #observer = null;

  connectedCallback() {
    this.#adopt();
    if (!this.#observer) {
      this.#observer = new MutationObserver(() => {
        if (this.#adopt()) {
          this.requestRender();
        }
      });
    }
    this.#observer.observe(this, { childList: true });
    super.connectedCallback();
  }

  disconnectedCallback() {
    this.#observer?.disconnect();
  }

  /** The managed <table> element (lives in the shadow tree once rendered). */
  get table() {
    return this.#table;
  }

  #adopt() {
    const table = this.querySelector(":scope > table");
    if (!table || table === this.#table) {
      return false;
    }
    this.#table?.remove();
    this.#table = table;
    this.#authorClasses = table.getAttribute("class") || "";
    return true;
  }

  render() {
    return `<div class="${this.hasAttribute("responsive") ? "table-responsive" : "ui-table"}" part="wrapper" data-wrapper></div>`;
  }

  afterRender() {
    const table = this.#table;
    if (!table) {
      return;
    }
    const classes = ["table"];
    if (this.getAttribute("size") === "sm") classes.push("table-sm");
    if (this.hasAttribute("striped")) classes.push("table-striped");
    if (this.hasAttribute("hover")) classes.push("table-hover");
    if (this.hasAttribute("bordered")) classes.push("table-bordered");
    if (this.hasAttribute("borderless")) classes.push("table-borderless");
    const align = this.getAttribute("valign");
    if (ALIGN.has(align)) classes.push(`align-${align}`);
    table.className = [...classes, this.#authorClasses].join(" ").trim();
    table.setAttribute("part", "table");
    // render() replaced the shadow content; (re-)insert the table node itself,
    // which keeps its listeners and form state.
    this.shadowRoot.querySelector("[data-wrapper]").append(table);
  }
}

registerComponent("ui-table", UiTable);
