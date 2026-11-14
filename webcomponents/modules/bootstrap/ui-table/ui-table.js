import { registerComponent } from "../../../core/registry.js";
import { HOST_TOKENS_CLASS } from "../../../core/shadow-sheet-transforms.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { BOOTSTRAP_SHADOW_STYLES, themeColor } from "../shadow-styles.js";

const ALIGN = new Set(["top", "middle", "bottom"]);
const BREAKPOINTS = new Set(["sm", "md", "lg", "xl", "2xl"]);

/**
 * <ui-table>: Bootstrap 6 .table for an author-provided light-DOM <table>.
 *
 * Table rows cannot be slotted into a shadow <table> (the HTML table model needs real parent / child
 * elements), so the component moves its <table> child into its shadow tree and styles it there. A newly
 * inserted <table> child replaces the current one. Script access goes through the `table` property.
 * The shadow tree has the whole Bootstrap CSS, so cell markup like text-end, table-active, table-group-divider,
 * theme-success on a row or align-middle keeps working; classes on the <table> are kept (caption-top, mb-0).
 *
 * Attributes:
 * - variant: theme colour of the whole table. size="sm": compact cells.
 * - striped, striped-columns, hover, bordered, borderless: Bootstrap's accents and borders.
 * - valign: top | middle | bottom (vertical alignment of the cells).
 * - card: rounded, bordered and clipped like a card (.table-card).
 * - responsive: horizontal scrolling (.table-responsive), or below a breakpoint: sm | md | lg | xl | 2xl.
 * - stacked: rows as blocks with label–value pairs (.table-stacked), or below a container width:
 *   sm | md | lg | xl | 2xl. Cells without data-cell get the label of their column header.
 * Icon column: class="table-icons" on a column header (or on single cells) makes a narrow, right-aligned column
 * for icon buttons that never wraps; the body and footer cells of that column get the class too.
 * Total row: class="table-total" on a <tr> (usually in <tfoot>): a stronger line above, bold.
 * Custom properties: --ui-table-head-color, --ui-table-head-font-weight (head cells),
 * --ui-table-last-row-border-width (bottom border of the last body row; 0 drops it).
 * Parts: wrapper, table.
 */
export class UiTable extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-table.css", import.meta.url).href];
  static observedAttributes = ["variant", "size", "striped", "striped-columns", "hover", "bordered", "borderless", "valign",
    "card", "responsive", "stacked"];

  #table = null;
  #authorClasses = "";
  #observer = null;
  #rows = null;

  connectedCallback() {
    this.#adopt();
    this.#observer ??= new MutationObserver(() => {
      if (this.#adopt()) {
        this.requestRender();
      }
    });
    this.#observer.observe(this, { childList: true });
    super.connectedCallback();
  }

  disconnectedCallback() {
    this.#observer?.disconnect();
    this.#rows?.disconnect();
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

  #breakpoint(name) {
    const value = this.getAttribute(name);
    return BREAKPOINTS.has(value) ? `${value}:` : "";
  }

  render() {
    const responsive = this.hasAttribute("responsive") || (this.hasAttribute("stacked") && this.#breakpoint("stacked"));
    const classes = [responsive ? `${this.#breakpoint("responsive")}table-responsive` : "", this.hasAttribute("card") ? "table-card" : "",
      "ui-table-wrapper"].filter(Boolean).join(" ");
    return `<div class="${classes}" part="wrapper" data-wrapper></div>`;
  }

  afterRender() {
    const table = this.#table;
    if (!table) {
      return;
    }
    const variant = themeColor(this.getAttribute("variant"));
    const align = this.getAttribute("valign");
    const classes = ["table", HOST_TOKENS_CLASS,
      variant ? `theme-${variant}` : "",
      this.getAttribute("size") === "sm" ? "table-sm" : "",
      this.hasAttribute("striped") ? "table-striped" : "",
      this.hasAttribute("striped-columns") ? "table-striped-columns" : "",
      this.hasAttribute("hover") ? "table-hover" : "",
      this.hasAttribute("bordered") ? "table-bordered" : "",
      this.hasAttribute("borderless") ? "table-borderless" : "",
      ALIGN.has(align) ? `align-${align}` : "",
      this.hasAttribute("stacked") ? `${this.#breakpoint("stacked")}table-stacked` : "",
      this.#authorClasses];
    table.className = classes.filter(Boolean).join(" ");
    table.setAttribute("part", "table");
    // render() replaced the shadow content; (re-)insert the table node itself, which keeps its listeners and form state.
    this.shadowRoot.querySelector("[data-wrapper]").append(table);
    this.#rows?.disconnect();
    this.#decorateCells();
    this.#rows = new MutationObserver(() => this.#decorateCells());
    this.#rows.observe(table, { childList: true, subtree: true });
  }

  /**
   * Fills in what the column headers say for the cells below them: the table-icons class of an icon column and,
   * for stacked rows, each cell's data-cell label where missing.
   */
  #decorateCells() {
    const stacked = this.hasAttribute("stacked");
    const headers = [];
    for (const cell of this.#table.tHead?.rows[0]?.cells || []) {
      const header = { label: cell.textContent.trim(), icons: cell.classList.contains("table-icons") };
      for (let span = 0; span < (cell.colSpan || 1); span += 1) {
        headers.push(header);
      }
    }
    const rows = [...this.#table.tBodies].flatMap((body) => [...body.rows]).concat([...(this.#table.tFoot?.rows || [])]);
    for (const row of rows) {
      let column = 0;
      for (const cell of row.cells) {
        const header = headers[column];
        if (header?.icons && (cell.colSpan || 1) === 1) {
          cell.classList.add("table-icons");
        }
        if (stacked && header?.label && !cell.hasAttribute("data-cell") && row.parentElement.tagName === "TBODY") {
          cell.setAttribute("data-cell", header.label);
        }
        column += cell.colSpan || 1;
      }
    }
  }
}

registerComponent("ui-table", UiTable);
