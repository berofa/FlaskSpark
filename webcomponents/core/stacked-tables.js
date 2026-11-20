/**
 * Stacked tables in the light DOM: a <table> with Bootstrap's .table-stacked (or a breakpoint variant such as
 * .sm:table-stacked) shows its rows as blocks on narrow containers, every cell with the label of its column. The
 * label comes from the cell's data-cell attribute; this fills it in from the column headers (first row of <thead>)
 * where it is missing, in <tbody> and <tfoot>, also for rows that are rendered again later (live data).
 *
 * - A header's label is its data-cell attribute, else its text. Empty headers (icon columns) give no label.
 * - Cells spanning several columns get no label (e.g. a row "nothing yet" over the whole width).
 * - <ui-table stacked> does the same in its shadow tree; this is for tables rendered straight into the page.
 *
 * installStackedTables(root = document) watches root (once); labelStackedCells(table) is the part without observer.
 */

const STACKED = /(^|\s)([a-z0-9]+:)?table-stacked(\s|$)/;

/** True for a table with .table-stacked or one of its breakpoint variants. */
export function isStackedTable(table) {
  return table?.tagName === "TABLE" && STACKED.test(table.getAttribute("class") || "");
}

/** The label of every column (by index, spans repeated), "" where a header has none. */
export function columnLabels(table) {
  const labels = [];
  for (const cell of table.tHead?.rows[0]?.cells || []) {
    const label = (cell.getAttribute("data-cell") ?? cell.textContent).replace(/\s+/g, " ").trim();
    for (let span = 0; span < (cell.colSpan || 1); span += 1) {
      labels.push(label);
    }
  }
  return labels;
}

/** Sets data-cell on the body and footer cells that have none (from the column headers). */
export function labelStackedCells(table) {
  const labels = columnLabels(table);
  if (!labels.some(Boolean)) {
    return;
  }
  const rows = [...table.tBodies].flatMap((body) => [...body.rows]).concat([...(table.tFoot?.rows || [])]);
  for (const row of rows) {
    let column = 0;
    for (const cell of row.cells) {
      const span = cell.colSpan || 1;
      if (span === 1 && labels[column] && !cell.hasAttribute("data-cell")) {
        cell.setAttribute("data-cell", labels[column]);
      }
      column += span;
    }
  }
}

function tablesIn(node) {
  if (node.nodeType !== 1) {
    return [];
  }
  const tables = node.tagName === "TABLE" ? [node] : [...node.querySelectorAll("table")];
  const around = node.closest("table");
  if (around && !tables.includes(around)) {
    tables.push(around);
  }
  return tables.filter(isStackedTable);
}

const installed = new WeakSet();

/** Labels the stacked tables under root now and whenever rows or tables are added. */
export function installStackedTables(root = document) {
  if (installed.has(root)) {
    return;
  }
  installed.add(root);
  const start = root.body || root;
  for (const table of tablesIn(start)) {
    labelStackedCells(table);
  }
  new MutationObserver((records) => {
    const tables = new Set();
    for (const record of records) {
      for (const node of record.addedNodes) {
        for (const table of tablesIn(node)) {
          tables.add(table);
        }
      }
      // A class added later (e.g. re-rendered table element kept, class changed).
      if (record.type === "attributes" && isStackedTable(record.target)) {
        tables.add(record.target);
      }
    }
    tables.forEach(labelStackedCells);
  }).observe(start, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
}
