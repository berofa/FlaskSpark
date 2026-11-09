import { registerComponent } from "../../../core/registry.js";
import { ShadowComponentElement } from "../../../core/shadow-component-element.js";
import { escapeHtml } from "../../../core/escape.js";
import { defaultLayout, normalizeGridLayout, normalizeItemId } from "../ui-grid/grid-layout.js";
import { BOOTSTRAP_SHADOW_STYLES } from "../shadow-styles.js";

/** Texts of the editor; each can be replaced with an attribute "<key>-label" (e.g. merge-left-label). */
const LABELS = {
  "empty": "Empty cell",
  "merge-left": "Merge left",
  "merge-up": "Merge up",
  "merge-right": "Merge right",
  "merge-down": "Merge down",
  "unmerge": "Unmerge cell",
  "add-row": "Add row",
  "remove-row": "Remove row",
  "add-column": "Add column",
  "remove-column": "Remove column",
  "row-actions": "Row actions",
  "column-actions": "Column actions",
  "cell-actions": "Cell actions",
};

/**
 * <ui-grid-editor>: edits a ui-grid layout: items (cards) are dragged between cells, cells are merged and
 * split, rows and columns added and removed. Not a Bootstrap component: built from Bootstrap 6 cards, badges,
 * buttons and tokens, themed with its own --ui-grid-editor-* tokens.
 *
 * Data: a <script type="application/json"> child or the property `data` = {items: [{id, eyebrow, title,
 * description, meta, badge}], layout} (layout normalized like grid_layout.py).
 * Attributes: save-url (POSTs {layout} as JSON after every change), <key>-label for every text (see LABELS).
 * Events (bubble): ui-grid-editor:change {layout} after every change, ui-grid-editor:error {error, layout}
 * when saving failed.
 */
export class UiGridEditor extends ShadowComponentElement {
  static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-grid-editor.css", import.meta.url).href];
  static observedAttributes = ["save-url", ...Object.keys(LABELS).map((key) => `${key}-label`)];

  constructor() {
    super();
    this.state = defaultLayout();
    this.items = [];
    this.itemsById = new Map();
    this.dragItemId = null;
    this.dragNode = null;
    this.dragImageNode = null;
    this.dragPreviewNode = null;
    this.dragPreviewMountNode = null;
    this.dragPreviewIndex = null;
    this.dragTargetAreaNode = null;
    this.initialized = false;
    this._data = null;
  }

  set data(value) {
    this._data = value;
    this.initialized = false;
    this.requestRender();
  }

  get data() {
    return this._data;
  }

  render() {
    return `
      <div class="ui-grid-editor" data-part="editor">
        <div class="ui-grid-editor__stage">
          <div class="ui-grid-editor__surface" data-grid-surface></div>
        </div>
      </div>
    `;
  }

  afterRender() {
    this.surface = this.shadowRoot.querySelector("[data-grid-surface]");
    this.labels = this.readLabels();

    if (!this.initialized) {
      this.initialize();
    }

    this.renderEditor();
  }

  readLabels() {
    return Object.fromEntries(Object.entries(LABELS).map(([key, text]) => [key, this.getAttribute(`${key}-label`) || text]));
  }

  initialize() {
    const config = this.readConfig();
    const items = Array.isArray(config.items) ? config.items : [];
    this.items = items
      .map((item, index) => this.normalizeItem(item, index))
      .filter(Boolean);
    this.itemsById = new Map(this.items.map((item) => [item.id, item]));
    this.state = normalizeGridLayout(config.layout, this.items.map((item) => item.id));
    this.ensureFullGrid();
    this.initialized = true;
  }

  readConfig() {
    if (this._data) {
      return this._data;
    }

    const scriptNode = Array.from(this.children).find((node) => (
      node.tagName === "SCRIPT" && node.type === "application/json"
    ));

    if (!scriptNode) {
      return { items: [], layout: defaultLayout() };
    }

    try {
      return JSON.parse(scriptNode.textContent || "{}");
    } catch (error) {
      return { items: [], layout: defaultLayout() };
    }
  }

  normalizeItem(item, index) {
    if (!item || typeof item !== "object") {
      return null;
    }

    const id = normalizeItemId(item.id ?? `item-${index + 1}`);
    if (!id) {
      return null;
    }

    return {
      id,
      eyebrow: item.eyebrow || "",
      title: item.title || id,
      description: item.description || "",
      meta: item.meta || "",
      badge: item.badge || "",
    };
  }

  getSortedAreas() {
    return [...this.state.areas].sort((left, right) => {
      if (left.row !== right.row) {
        return left.row - right.row;
      }
      return left.column - right.column;
    });
  }

  getAreaAnchorKey(area) {
    return `${area.row}:${area.column}`;
  }

  getAreaCellKeys(area) {
    const keys = [];
    for (let rowIndex = area.row; rowIndex < area.row + area.row_span; rowIndex += 1) {
      for (let columnIndex = area.column; columnIndex < area.column + area.column_span; columnIndex += 1) {
        keys.push(`${rowIndex}:${columnIndex}`);
      }
    }
    return keys;
  }

  sortCellKeys(cellKeys) {
    return [...cellKeys].sort((left, right) => {
      const [leftRow, leftColumn] = left.split(":").map((value) => Number.parseInt(value, 10));
      const [rightRow, rightColumn] = right.split(":").map((value) => Number.parseInt(value, 10));
      if (leftRow !== rightRow) {
        return leftRow - rightRow;
      }
      return leftColumn - rightColumn;
    });
  }

  cloneCellItems(cellItems = {}) {
    const cloned = {};
    Object.entries(cellItems).forEach(([cellKey, itemIds]) => {
      if (Array.isArray(itemIds) && itemIds.length) {
        cloned[String(cellKey)] = [...itemIds];
      }
    });
    return cloned;
  }

  ensureAreaCellItems(area) {
    if (!area) {
      return {};
    }

    const current = this.cloneCellItems(area.cell_items);
    const allowedKeys = new Set(this.getAreaCellKeys(area));
    const normalized = {};
    const assigned = new Set();

    this.sortCellKeys(Object.keys(current)).forEach((cellKey) => {
      if (!allowedKeys.has(cellKey)) {
        return;
      }
      const validIds = current[cellKey].filter((itemId) => area.item_ids.includes(itemId) && !assigned.has(itemId));
      if (!validIds.length) {
        return;
      }
      normalized[cellKey] = validIds;
      validIds.forEach((itemId) => assigned.add(itemId));
    });

    const remainingIds = area.item_ids.filter((itemId) => !assigned.has(itemId));
    if (remainingIds.length) {
      const anchorKey = this.getAreaAnchorKey(area);
      normalized[anchorKey] = [...(normalized[anchorKey] || []), ...remainingIds];
    }

    area.cell_items = normalized;
    return normalized;
  }

  removeItemFromAreaCellItems(area, itemId) {
    if (!area) {
      return;
    }
    const normalized = this.ensureAreaCellItems(area);
    Object.entries(normalized).forEach(([cellKey, itemIds]) => {
      const filteredIds = itemIds.filter((entry) => entry !== itemId);
      if (filteredIds.length) {
        normalized[cellKey] = filteredIds;
      } else {
        delete normalized[cellKey];
      }
    });
    area.cell_items = normalized;
  }

  addItemToAreaCellItems(area, itemId, cellKey = null) {
    if (!area) {
      return;
    }
    const normalized = this.ensureAreaCellItems(area);
    const targetKey = cellKey && this.getAreaCellKeys(area).includes(cellKey)
      ? cellKey
      : this.getAreaAnchorKey(area);
    normalized[targetKey] = [...(normalized[targetKey] || []), itemId];
    area.cell_items = normalized;
  }

  shiftCellItemsRows(startRow, delta) {
    this.state.areas.forEach((area) => {
      const shifted = {};
      Object.entries(this.ensureAreaCellItems(area)).forEach(([cellKey, itemIds]) => {
        const [row, column] = cellKey.split(":").map((value) => Number.parseInt(value, 10));
        const nextRow = row >= startRow ? row + delta : row;
        shifted[`${nextRow}:${column}`] = [...itemIds];
      });
      area.cell_items = shifted;
    });
  }

  shiftCellItemsColumns(startColumn, delta) {
    this.state.areas.forEach((area) => {
      const shifted = {};
      Object.entries(this.ensureAreaCellItems(area)).forEach(([cellKey, itemIds]) => {
        const [row, column] = cellKey.split(":").map((value) => Number.parseInt(value, 10));
        const nextColumn = column >= startColumn ? column + delta : column;
        shifted[`${row}:${nextColumn}`] = [...itemIds];
      });
      area.cell_items = shifted;
    });
  }

  getContainerByItemId(itemId) {
    return this.state.areas.find((area) => area.item_ids.includes(itemId)) || null;
  }

  createItemNode(itemId) {
    const item = this.itemsById.get(itemId);
    if (!item) {
      return null;
    }

    const itemNode = document.createElement("div");
    itemNode.className = "ui-grid-editor-item";
    itemNode.dataset.gridItem = "";
    itemNode.dataset.itemId = item.id;
    itemNode.draggable = true;
    itemNode.innerHTML = `
      <article class="card h-100">
        <div class="card-body">
          <div class="ui-grid-editor-item__header">
            <div class="ui-grid-editor-item__eyebrow">${escapeHtml(item.eyebrow)}</div>
            ${item.badge ? `<span class="badge theme-primary">${escapeHtml(item.badge)}</span>` : ""}
          </div>
          <h4 class="ui-grid-editor-item__title">${escapeHtml(item.title)}</h4>
          ${item.description ? `<p class="ui-grid-editor-item__description">${escapeHtml(item.description)}</p>` : ""}
          ${item.meta ? `<div class="ui-grid-editor-item__meta">${escapeHtml(item.meta)}</div>` : ""}
        </div>
      </article>
    `;

    itemNode.addEventListener("dragstart", (event) => {
      this.beginDrag(item.id, itemNode);
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", item.id);
      if (this.dragImageNode) {
        event.dataTransfer.setDragImage(this.dragImageNode, 16, 16);
      }
    });

    itemNode.addEventListener("dragend", () => {
      this.endDrag();
    });

    return itemNode;
  }

  beginDrag(itemId, itemNode) {
    this.dragItemId = itemId;
    this.dragNode = itemNode;
    this.createDragImage(itemNode);
    this.shadowRoot.querySelector("[data-part='editor']")?.classList.add("is-dragging");
    window.requestAnimationFrame(() => {
      if (this.dragNode === itemNode) {
        itemNode.classList.add("is-drag-origin");
      }
    });
  }

  endDrag() {
    this.dragItemId = null;
    this.shadowRoot.querySelector("[data-part='editor']")?.classList.remove("is-dragging");
    this.dragNode?.classList.remove("is-drag-origin");
    this.dragNode = null;
    this.clearDropPreview();
    this.clearDragImage();
  }

  createDragImage(itemNode) {
    this.clearDragImage();
    if (!itemNode) {
      return;
    }
    const rect = itemNode.getBoundingClientRect();
    const dragImage = itemNode.cloneNode(true);
    dragImage.classList.add("ui-grid-editor-drag-image");
    dragImage.style.width = `${rect.width}px`;
    document.body.appendChild(dragImage);
    this.dragImageNode = dragImage;
  }

  clearDragImage() {
    this.dragImageNode?.remove();
    this.dragImageNode = null;
  }

  buildDropPreview() {
    if (!this.dragNode) {
      return null;
    }
    const preview = this.dragNode.cloneNode(true);
    preview.classList.add("ui-grid-editor-drop-preview");
    preview.classList.remove("is-drag-origin");
    preview.removeAttribute("draggable");
    preview.dataset.gridPreview = "";
    return preview;
  }

  clearDropPreview() {
    this.dragPreviewNode?.remove();
    this.dragPreviewMountNode?.classList.remove("has-preview");
    this.dragTargetAreaNode?.classList.remove("is-drop-target");
    this.dragPreviewNode = null;
    this.dragPreviewMountNode = null;
    this.dragPreviewIndex = null;
    this.dragTargetAreaNode = null;
  }

  getRenderableStackItems(stack) {
    return Array.from(stack.querySelectorAll("[data-grid-item]")).filter((node) => (
      !node.dataset.gridPreview && node.dataset.itemId !== this.dragItemId
    ));
  }

  getPreviewIndexForStack(stack, clientY) {
    const itemNodes = this.getRenderableStackItems(stack);
    if (!itemNodes.length) {
      return 0;
    }

    for (let index = 0; index < itemNodes.length; index += 1) {
      const rect = itemNodes[index].getBoundingClientRect();
      if (clientY < rect.top + (rect.height / 2)) {
        return index;
      }
    }

    return itemNodes.length;
  }

  setDropPreview(areaNode, stack, index) {
    if (this.dragPreviewMountNode === stack && this.dragPreviewIndex === index) {
      return;
    }
    this.clearDropPreview();
    areaNode?.classList.add("is-drop-target");
    stack.classList.add("has-preview");
    const preview = this.buildDropPreview();
    if (!preview) {
      return;
    }
    const itemNodes = this.getRenderableStackItems(stack);
    const beforeNode = itemNodes[index] || null;
    if (beforeNode) {
      stack.insertBefore(preview, beforeNode);
    } else {
      stack.appendChild(preview);
    }
    this.dragTargetAreaNode = areaNode;
    this.dragPreviewMountNode = stack;
    this.dragPreviewNode = preview;
    this.dragPreviewIndex = index;
  }

  bindVirtualDropTarget(area, areaNode, stack) {
    const activate = (event) => {
      if (!this.dragItemId) {
        return;
      }
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      const index = this.getPreviewIndexForStack(stack, event.clientY);
      this.setDropPreview(areaNode, stack, index);
    };

    ["dragenter", "dragover"].forEach((eventName) => {
      stack.addEventListener(eventName, activate);
    });

    stack.addEventListener("dragleave", (event) => {
      if (this.dragPreviewMountNode !== stack) {
        return;
      }
      const rect = stack.getBoundingClientRect();
      if (
        event.clientX >= rect.left
        && event.clientX <= rect.right
        && event.clientY >= rect.top
        && event.clientY <= rect.bottom
      ) {
        return;
      }
      this.clearDropPreview();
    });

    stack.addEventListener("drop", (event) => {
      if (!this.dragItemId) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const index = this.getPreviewIndexForStack(stack, event.clientY);
      this.clearDropPreview();
      this.moveItem(this.dragItemId, area, index);
      this.endDrag();
    });
  }

  buildActionGroup(labelText, actions) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-grid-editor-action-group";
    wrapper.setAttribute("role", "group");
    wrapper.setAttribute("aria-label", labelText);

    actions.forEach((action) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn-subtle btn-sm theme-secondary ui-grid-editor-control";
      button.textContent = action.icon;
      button.title = action.title;
      button.setAttribute("aria-label", action.title);
      button.addEventListener("click", action.onClick);
      wrapper.appendChild(button);
    });

    return wrapper;
  }

  buildControls(area) {
    const actions = [
      ["left", "←", this.labels["merge-left"], this.canMerge(area, "left"), () => this.merge(area, "left")],
      ["up", "↑", this.labels["merge-up"], this.canMerge(area, "up"), () => this.merge(area, "up")],
      ["right", "→", this.labels["merge-right"], this.canMerge(area, "right"), () => this.merge(area, "right")],
      ["down", "↓", this.labels["merge-down"], this.canMerge(area, "down"), () => this.merge(area, "down")],
      ["split", "⤢", "Unmerge cell", area.row_span > 1 || area.column_span > 1, () => this.split(area)],
    ]
      .filter(([, , , enabled]) => enabled)
      .map(([, icon, title, , onClick]) => ({ icon, title, onClick }));

    if (!actions.length) {
      return null;
    }

    const controls = document.createElement("div");
    controls.className = "ui-grid-editor-controls";
    controls.appendChild(this.buildActionGroup(this.labels["cell-actions"], actions));
    return controls;
  }

  getEditorGridRowStart(area) {
    return area.row * 2;
  }

  getEditorGridRowSpan(area) {
    return Math.max(1, (area.row_span * 2) - 1);
  }

  getEditorGridColumnStart(area) {
    return area.column * 2;
  }

  getEditorGridColumnSpan(area) {
    return Math.max(1, (area.column_span * 2) - 1);
  }

  getEditorGridColumnTrackCount() {
    return (this.state.columns_count * 2) + 1;
  }

  getEditorGridRowTrackCount() {
    return (this.state.rows_count * 2) + 1;
  }

  getEditorBoundaryTrackSize() {
    return "3.5rem";
  }

  buildEditorGridTemplateColumns() {
    const boundaryTrackSize = this.getEditorBoundaryTrackSize();
    const tracks = [boundaryTrackSize];
    for (let columnIndex = 1; columnIndex <= this.state.columns_count; columnIndex += 1) {
      tracks.push("minmax(0, 1fr)");
      tracks.push(boundaryTrackSize);
    }
    return tracks.join(" ");
  }

  buildEditorGridTemplateRows() {
    const boundaryTrackSize = this.getEditorBoundaryTrackSize();
    const tracks = [];
    for (let rowIndex = 0; rowIndex <= this.state.rows_count; rowIndex += 1) {
      tracks.push(boundaryTrackSize);
      if (rowIndex < this.state.rows_count) {
        tracks.push("auto");
      }
    }
    return tracks.join(" ");
  }

  getContentColumnStartLine(columnIndex) {
    return columnIndex * 2;
  }

  getContentColumnEndLine(columnIndex) {
    return (columnIndex * 2) + 1;
  }

  getContentRowStartLine(rowIndex) {
    return rowIndex * 2;
  }

  getContentRowEndLine(rowIndex) {
    return (rowIndex * 2) + 1;
  }

  getBoundaryTrackLine(boundaryIndex) {
    return (boundaryIndex * 2) + 1;
  }

  getBlockedColumnsForRowBoundary(boundaryIndex) {
    if (boundaryIndex <= 0 || boundaryIndex >= this.state.rows_count) {
      return new Set();
    }
    const boundaryRow = boundaryIndex + 1;
    const blocked = new Set();
    this.state.areas.forEach((area) => {
      if (area.row < boundaryRow && (area.row + area.row_span) > boundaryRow) {
        for (let columnIndex = area.column; columnIndex < area.column + area.column_span; columnIndex += 1) {
          blocked.add(columnIndex);
        }
      }
    });
    return blocked;
  }

  getBlockedRowsForColumnBoundary(boundaryIndex) {
    if (boundaryIndex <= 0 || boundaryIndex >= this.state.columns_count) {
      return new Set();
    }
    const boundaryColumn = boundaryIndex + 1;
    const blocked = new Set();
    this.state.areas.forEach((area) => {
      if (area.column < boundaryColumn && (area.column + area.column_span) > boundaryColumn) {
        for (let rowIndex = area.row; rowIndex < area.row + area.row_span; rowIndex += 1) {
          blocked.add(rowIndex);
        }
      }
    });
    return blocked;
  }

  getUnblockedRanges(count, blockedSet) {
    const ranges = [];
    let rangeStart = null;
    for (let index = 1; index <= count; index += 1) {
      if (!blockedSet.has(index)) {
        if (rangeStart === null) {
          rangeStart = index;
        }
        continue;
      }
      if (rangeStart !== null) {
        ranges.push([rangeStart, index - 1]);
        rangeStart = null;
      }
    }
    if (rangeStart !== null) {
      ranges.push([rangeStart, count]);
    }
    return ranges;
  }

  shouldRenderRowToolbar(boundaryIndex) {
    return this.getBlockedColumnsForRowBoundary(boundaryIndex).size === 0;
  }

  buildRowToolbar(boundaryIndex) {
    const removeTargetRow = Math.min(boundaryIndex + 1, this.state.rows_count);
    const actions = [
      {
        icon: "+",
        title: this.labels["add-row"],
        onClick: () => this.addRowAt(boundaryIndex + 1),
      },
    ];

    if (this.canRemoveRow(removeTargetRow) && this.state.rows_count > 1) {
      actions.push({
        icon: "−",
        title: this.labels["remove-row"],
        onClick: () => this.removeRowAt(removeTargetRow),
      });
    }

    const toolbar = document.createElement("div");
    toolbar.className = "ui-grid-editor-row-toolbar";
    toolbar.style.gridColumn = `1 / span ${this.getEditorGridColumnTrackCount()}`;
    toolbar.style.gridRow = String((boundaryIndex * 2) + 1);
    toolbar.appendChild(this.buildActionGroup(this.labels["row-actions"], actions));
    return toolbar;
  }

  buildRowLineSegments(boundaryIndex) {
    const blockedColumns = this.getBlockedColumnsForRowBoundary(boundaryIndex);
    return this.getUnblockedRanges(this.state.columns_count, blockedColumns).map(([startColumn, endColumn]) => {
      const segment = document.createElement("div");
      segment.className = "ui-grid-editor-row-toolbar-segment";
      segment.style.gridRow = String((boundaryIndex * 2) + 1);
      segment.style.gridColumn = `${this.getContentColumnStartLine(startColumn)} / ${this.getContentColumnEndLine(endColumn)}`;
      return segment;
    });
  }

  shouldRenderColumnToolbar(boundaryIndex) {
    return this.getBlockedRowsForColumnBoundary(boundaryIndex).size === 0;
  }

  buildColumnToolbar(boundaryIndex) {
    const removeTargetColumn = Math.min(Math.max(boundaryIndex, 1), this.state.columns_count);
    const actions = [
      {
        icon: "+",
        title: this.labels["add-column"],
        onClick: () => this.addColumnAt(boundaryIndex + 1),
      },
    ];

    if (this.canRemoveColumn(removeTargetColumn) && this.state.columns_count > 1) {
      actions.push({
        icon: "−",
        title: this.labels["remove-column"],
        onClick: () => this.removeColumnAt(removeTargetColumn),
      });
    }

    const toolbar = document.createElement("div");
    toolbar.className = "ui-grid-editor-column-toolbar";
    toolbar.style.gridColumn = String((boundaryIndex * 2) + 1);
    toolbar.style.gridRow = `1 / span ${this.getEditorGridRowTrackCount()}`;
    toolbar.appendChild(this.buildActionGroup(this.labels["column-actions"], actions));
    return toolbar;
  }

  buildColumnLineSegments(boundaryIndex) {
    const blockedRows = this.getBlockedRowsForColumnBoundary(boundaryIndex);
    return this.getUnblockedRanges(this.state.rows_count, blockedRows).map(([startRow, endRow]) => {
      const segment = document.createElement("div");
      segment.className = "ui-grid-editor-column-toolbar-segment";
      segment.style.gridColumn = String(this.getBoundaryTrackLine(boundaryIndex));
      segment.style.gridRow = `${this.getContentRowStartLine(startRow)} / ${this.getContentRowEndLine(endRow)}`;
      return segment;
    });
  }

  createEmptyState(labelText) {
    const node = document.createElement("div");
    node.className = "ui-grid-editor-empty";
    node.textContent = labelText;
    return node;
  }

  getAreaElement(area) {
    const node = document.createElement("div");
    node.className = `ui-grid-editor-area${area.item_ids.length ? "" : " is-empty"}`;
    node.dataset.gridArea = "";
    node.dataset.row = String(area.row);
    node.dataset.column = String(area.column);
    node.dataset.rowSpan = String(area.row_span);
    node.dataset.columnSpan = String(area.column_span);
    node.style.gridRow = `${this.getEditorGridRowStart(area)} / span ${this.getEditorGridRowSpan(area)}`;
    node.style.gridColumn = `${this.getEditorGridColumnStart(area)} / span ${this.getEditorGridColumnSpan(area)}`;

    const controls = this.buildControls(area);
    const stack = document.createElement("div");
    stack.className = `ui-grid-editor-stack${area.item_ids.length === 1 ? " ui-grid-editor-stack--single" : ""}`;

    if (!area.item_ids.length) {
      stack.appendChild(this.createEmptyState(this.labels.empty));
    } else {
      area.item_ids.forEach((itemId) => {
        const itemNode = this.createItemNode(itemId);
        if (itemNode) {
          stack.appendChild(itemNode);
        }
      });
    }

    this.bindVirtualDropTarget(area, node, stack);
    node.appendChild(stack);
    if (controls) {
      node.appendChild(controls);
    }
    return node;
  }

  getAdjacentAreas(area, direction) {
    const areaRowStart = area.row;
    const areaRowEnd = area.row + area.row_span;
    const areaColumnStart = area.column;
    const areaColumnEnd = area.column + area.column_span;
    let candidates = [];

    if (direction === "left") {
      const boundaryColumn = area.column;
      candidates = this.state.areas
        .filter((candidate) => (
          candidate !== area
          && candidate.column + candidate.column_span === boundaryColumn
          && candidate.row >= areaRowStart
          && candidate.row + candidate.row_span <= areaRowEnd
        ))
        .sort((left, right) => left.row - right.row || left.column - right.column);

      let cursor = areaRowStart;
      const matches = [];
      for (const candidate of candidates) {
        if (candidate.row !== cursor) {
          return [];
        }
        matches.push(candidate);
        cursor += candidate.row_span;
      }
      if (cursor !== areaRowEnd) {
        return [];
      }
      const referenceColumn = matches[0]?.column;
      const referenceSpan = matches[0]?.column_span;
      return matches.every((candidate) => candidate.column === referenceColumn && candidate.column_span === referenceSpan)
        ? matches
        : [];
    }

    if (direction === "right") {
      const boundaryColumn = area.column + area.column_span;
      candidates = this.state.areas
        .filter((candidate) => (
          candidate !== area
          && candidate.column === boundaryColumn
          && candidate.row >= areaRowStart
          && candidate.row + candidate.row_span <= areaRowEnd
        ))
        .sort((left, right) => left.row - right.row || left.column - right.column);

      let cursor = areaRowStart;
      const matches = [];
      for (const candidate of candidates) {
        if (candidate.row !== cursor) {
          return [];
        }
        matches.push(candidate);
        cursor += candidate.row_span;
      }
      if (cursor !== areaRowEnd) {
        return [];
      }
      const referenceSpan = matches[0]?.column_span;
      return matches.every((candidate) => candidate.column_span === referenceSpan) ? matches : [];
    }

    if (direction === "up") {
      const boundaryRow = area.row;
      candidates = this.state.areas
        .filter((candidate) => (
          candidate !== area
          && candidate.row + candidate.row_span === boundaryRow
          && candidate.column >= areaColumnStart
          && candidate.column + candidate.column_span <= areaColumnEnd
        ))
        .sort((left, right) => left.column - right.column || left.row - right.row);

      let cursor = areaColumnStart;
      const matches = [];
      for (const candidate of candidates) {
        if (candidate.column !== cursor) {
          return [];
        }
        matches.push(candidate);
        cursor += candidate.column_span;
      }
      if (cursor !== areaColumnEnd) {
        return [];
      }
      const referenceRow = matches[0]?.row;
      const referenceSpan = matches[0]?.row_span;
      return matches.every((candidate) => candidate.row === referenceRow && candidate.row_span === referenceSpan)
        ? matches
        : [];
    }

    const boundaryRow = area.row + area.row_span;
    candidates = this.state.areas
      .filter((candidate) => (
        candidate !== area
        && candidate.row === boundaryRow
        && candidate.column >= areaColumnStart
        && candidate.column + candidate.column_span <= areaColumnEnd
      ))
      .sort((left, right) => left.column - right.column || left.row - right.row);

    let cursor = areaColumnStart;
    const matches = [];
    for (const candidate of candidates) {
      if (candidate.column !== cursor) {
        return [];
      }
      matches.push(candidate);
      cursor += candidate.column_span;
    }
    if (cursor !== areaColumnEnd) {
      return [];
    }
    const referenceSpan = matches[0]?.row_span;
    return matches.every((candidate) => candidate.row_span === referenceSpan) ? matches : [];
  }

  canMerge(area, direction) {
    return this.getAdjacentAreas(area, direction).length > 0;
  }

  merge(area, direction) {
    const adjacentAreas = this.getAdjacentAreas(area, direction);
    if (!adjacentAreas.length) {
      return;
    }
    const mergedAreas = [area, ...adjacentAreas];
    const mergedRowStart = Math.min(...mergedAreas.map((entry) => entry.row));
    const mergedRowEnd = Math.max(...mergedAreas.map((entry) => entry.row + entry.row_span));
    const mergedColumnStart = Math.min(...mergedAreas.map((entry) => entry.column));
    const mergedColumnEnd = Math.max(...mergedAreas.map((entry) => entry.column + entry.column_span));
    const merged = {
      row: mergedRowStart,
      column: mergedColumnStart,
      row_span: mergedRowEnd - mergedRowStart,
      column_span: mergedColumnEnd - mergedColumnStart,
      item_ids: mergedAreas.flatMap((entry) => entry.item_ids),
      cell_items: mergedAreas.reduce((accumulator, entry) => ({
        ...accumulator,
        ...this.cloneCellItems(this.ensureAreaCellItems(entry)),
      }), {}),
    };
    this.state.areas = this.state.areas.filter((entry) => entry !== area && !adjacentAreas.includes(entry));
    this.state.areas.push(merged);
    this.ensureFullGrid();
    this.renderEditor();
    this.save();
  }

  split(area) {
    this.state.areas = this.state.areas.filter((entry) => entry !== area);
    const cellItems = this.ensureAreaCellItems(area);
    for (let rowIndex = area.row; rowIndex < area.row + area.row_span; rowIndex += 1) {
      for (let columnIndex = area.column; columnIndex < area.column + area.column_span; columnIndex += 1) {
        const cellKey = `${rowIndex}:${columnIndex}`;
        const cellItemIds = [...(cellItems[cellKey] || [])];
        this.state.areas.push({
          row: rowIndex,
          column: columnIndex,
          row_span: 1,
          column_span: 1,
          item_ids: cellItemIds,
          cell_items: cellItemIds.length ? { [cellKey]: cellItemIds } : {},
        });
      }
    }
    this.ensureFullGrid();
    this.renderEditor();
    this.save();
  }

  ensureFullGrid() {
    const occupancy = new Set();
    this.state.areas.forEach((area) => {
      for (let rowIndex = area.row; rowIndex < area.row + area.row_span; rowIndex += 1) {
        for (let columnIndex = area.column; columnIndex < area.column + area.column_span; columnIndex += 1) {
          occupancy.add(`${rowIndex}:${columnIndex}`);
        }
      }
    });

    for (let rowIndex = 1; rowIndex <= this.state.rows_count; rowIndex += 1) {
      for (let columnIndex = 1; columnIndex <= this.state.columns_count; columnIndex += 1) {
        if (!occupancy.has(`${rowIndex}:${columnIndex}`)) {
          this.state.areas.push({
            row: rowIndex,
            column: columnIndex,
            row_span: 1,
            column_span: 1,
            item_ids: [],
            cell_items: {},
          });
        }
      }
    }

    this.state.areas = this.getSortedAreas();
  }

  addRowAt(rowIndex) {
    const targetRow = Math.max(1, Math.min(Number.parseInt(rowIndex, 10) || 1, this.state.rows_count + 1));
    this.shiftCellItemsRows(targetRow, 1);
    this.state.areas.forEach((area) => {
      const areaEnd = area.row + area.row_span - 1;
      if (area.row >= targetRow) {
        area.row += 1;
      } else if (area.row < targetRow && areaEnd >= targetRow) {
        area.row_span += 1;
      }
    });
    this.state.rows_count += 1;
    this.ensureFullGrid();
    this.renderEditor();
    this.save();
  }

  addColumnAt(columnIndex) {
    const targetColumn = Math.max(1, Math.min(Number.parseInt(columnIndex, 10) || 1, this.state.columns_count + 1));
    this.shiftCellItemsColumns(targetColumn, 1);
    this.state.areas.forEach((area) => {
      const areaEnd = area.column + area.column_span - 1;
      if (area.column >= targetColumn) {
        area.column += 1;
      } else if (area.column < targetColumn && areaEnd >= targetColumn) {
        area.column_span += 1;
      }
    });
    this.state.columns_count += 1;
    this.ensureFullGrid();
    this.renderEditor();
    this.save();
  }

  canRemoveRow(rowIndex) {
    return this.state.areas.every((area) => {
      const touches = rowIndex >= area.row && rowIndex < area.row + area.row_span;
      if (!touches) {
        return true;
      }
      return area.row_span === 1 && !area.item_ids.length;
    });
  }

  canRemoveColumn(columnIndex) {
    return this.state.areas.every((area) => {
      const touches = columnIndex >= area.column && columnIndex < area.column + area.column_span;
      if (!touches) {
        return true;
      }
      return area.column_span === 1 && !area.item_ids.length;
    });
  }

  removeRowAt(rowIndex) {
    const numericRow = Number.parseInt(rowIndex, 10);
    if (this.state.rows_count <= 1 || !this.canRemoveRow(numericRow)) {
      return;
    }
    this.shiftCellItemsRows(numericRow + 1, -1);
    this.state.areas = this.state.areas
      .filter((area) => area.row !== numericRow)
      .map((area) => (area.row > numericRow ? { ...area, row: area.row - 1 } : { ...area }));
    this.state.rows_count -= 1;
    this.ensureFullGrid();
    this.renderEditor();
    this.save();
  }

  removeColumnAt(columnIndex) {
    const numericColumn = Number.parseInt(columnIndex, 10);
    if (this.state.columns_count <= 1 || !this.canRemoveColumn(numericColumn)) {
      return;
    }
    this.shiftCellItemsColumns(numericColumn + 1, -1);
    this.state.areas = this.state.areas
      .filter((area) => area.column !== numericColumn)
      .map((area) => (area.column > numericColumn ? { ...area, column: area.column - 1 } : { ...area }));
    this.state.columns_count -= 1;
    this.ensureFullGrid();
    this.renderEditor();
    this.save();
  }

  moveItem(itemId, targetArea, targetIndex = null) {
    const sourceArea = this.getContainerByItemId(itemId);
    if (!sourceArea || !targetArea) {
      return;
    }

    const sourceIndex = sourceArea.item_ids.indexOf(itemId);
    if (sourceIndex === -1) {
      return;
    }

    sourceArea.item_ids.splice(sourceIndex, 1);
    if (sourceArea !== targetArea) {
      this.removeItemFromAreaCellItems(sourceArea, itemId);
    }

    let insertIndex = Number.isFinite(targetIndex) ? targetIndex : targetArea.item_ids.length;
    if (sourceArea === targetArea && sourceIndex < insertIndex) {
      insertIndex -= 1;
    }
    insertIndex = Math.max(0, Math.min(insertIndex, targetArea.item_ids.length));
    targetArea.item_ids.splice(insertIndex, 0, itemId);

    if (sourceArea !== targetArea) {
      this.addItemToAreaCellItems(targetArea, itemId);
    } else {
      this.ensureAreaCellItems(targetArea);
    }

    this.renderEditor();
    this.save();
  }

  serializeLayout() {
    return {
      rows_count: this.state.rows_count,
      columns_count: this.state.columns_count,
      areas: this.getSortedAreas().map((area) => ({
        row: area.row,
        column: area.column,
        row_span: area.row_span,
        column_span: area.column_span,
        item_ids: [...area.item_ids],
        cell_items: this.cloneCellItems(this.ensureAreaCellItems(area)),
      })),
    };
  }

  dispatchChange(payload) {
    this.dispatchEvent(new CustomEvent("ui-grid-editor:change", {
      bubbles: true,
      detail: {
        layout: payload,
      },
    }));
  }

  async save() {
    const payload = this.serializeLayout();
    this.dispatchChange(payload);

    const saveUrl = this.getAttribute("save-url");
    if (!saveUrl) {
      return;
    }

    try {
      const response = await fetch(saveUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ layout: payload }),
      });
      if (!response.ok) {
        throw new Error(`Unexpected status ${response.status}`);
      }
    } catch (error) {
      this.dispatchEvent(new CustomEvent("ui-grid-editor:error", {
        bubbles: true,
        detail: {
          error,
          layout: payload,
        },
      }));
    }
  }

  renderEditor() {
    this.surface.innerHTML = "";
    this.surface.style.setProperty("--ui-grid-editor-columns", String(this.getEditorGridColumnTrackCount()));
    this.surface.style.setProperty("--ui-grid-editor-rows", String(this.getEditorGridRowTrackCount()));
    this.surface.style.setProperty("--ui-grid-editor-boundary-size", this.getEditorBoundaryTrackSize());
    this.surface.style.gridTemplateColumns = this.buildEditorGridTemplateColumns();
    this.surface.style.gridTemplateRows = this.buildEditorGridTemplateRows();

    for (let boundaryIndex = 0; boundaryIndex <= this.state.columns_count; boundaryIndex += 1) {
      this.buildColumnLineSegments(boundaryIndex).forEach((segment) => this.surface.appendChild(segment));
      if (this.shouldRenderColumnToolbar(boundaryIndex)) {
        this.surface.appendChild(this.buildColumnToolbar(boundaryIndex));
      }
    }

    for (let boundaryIndex = 0; boundaryIndex <= this.state.rows_count; boundaryIndex += 1) {
      this.buildRowLineSegments(boundaryIndex).forEach((segment) => this.surface.appendChild(segment));
      if (this.shouldRenderRowToolbar(boundaryIndex)) {
        this.surface.appendChild(this.buildRowToolbar(boundaryIndex));
      }
    }

    this.getSortedAreas().forEach((area) => {
      this.surface.appendChild(this.getAreaElement(area));
    });
  }
}

registerComponent("ui-grid-editor", UiGridEditor);
