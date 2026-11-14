/**
 * Client-side grid layout normalization.
 *
 * Mirrors ui_components/grid_layout.py — keep both in sync when the layout
 * semantics change.
 */

export function coercePositiveInt(value, fallback = 1) {
  const numeric = Number.parseInt(value, 10);
  return Number.isFinite(numeric) && numeric > 0 ? numeric : fallback;
}

export function normalizeItemId(value) {
  if (value === null || value === undefined) {
    return null;
  }
  const text = String(value).trim();
  return text || null;
}

export function buildUnitAreas(rowsCount, columnsCount) {
  const areas = [];
  for (let rowIndex = 1; rowIndex <= rowsCount; rowIndex += 1) {
    for (let columnIndex = 1; columnIndex <= columnsCount; columnIndex += 1) {
      areas.push({
        row: rowIndex,
        column: columnIndex,
        row_span: 1,
        column_span: 1,
        item_ids: [],
        cell_items: {},
      });
    }
  }
  return areas;
}

export function defaultLayout() {
  return {
    rows_count: 1,
    columns_count: 1,
    areas: buildUnitAreas(1, 1),
  };
}

function assignUnplacedItemsToAreas(areas, itemIds) {
  if (!Array.isArray(areas) || !areas.length || !Array.isArray(itemIds) || !itemIds.length) {
    return;
  }

  const byFillOrder = (left, right) => {
    const leftCount = Array.isArray(left.item_ids) ? left.item_ids.length : 0;
    const rightCount = Array.isArray(right.item_ids) ? right.item_ids.length : 0;
    if (leftCount !== rightCount) {
      return leftCount - rightCount;
    }
    if (left.row !== right.row) {
      return left.row - right.row;
    }
    return left.column - right.column;
  };

  const sortedAreas = [...areas].sort(byFillOrder);

  itemIds.forEach((itemId) => {
    const targetArea = sortedAreas[0];
    if (!targetArea) {
      return;
    }

    const anchorKey = `${targetArea.row}:${targetArea.column}`;
    targetArea.item_ids.push(itemId);
    if (!targetArea.cell_items[anchorKey]) {
      targetArea.cell_items[anchorKey] = [];
    }
    targetArea.cell_items[anchorKey].push(itemId);
    sortedAreas.sort(byFillOrder);
  });
}

export function normalizeGridLayout(payload, activeItemIds) {
  const activeIds = activeItemIds.map((value) => normalizeItemId(value)).filter(Boolean);
  const activeSet = new Set(activeIds);
  const source = payload && typeof payload === "object" ? payload : {};
  const rowsCount = coercePositiveInt(source.rows_count ?? source.rows ?? 1, 1);
  const columnsCount = coercePositiveInt(source.columns_count ?? source.columns ?? 1, 1);
  const rawAreas = Array.isArray(source.areas) ? source.areas : buildUnitAreas(rowsCount, columnsCount);
  const occupancy = Array.from({ length: rowsCount }, () => Array(columnsCount).fill(null));
  const normalizedAreas = [];
  const usedItems = new Set();

  function markArea(area) {
    const row = coercePositiveInt(area.row, 1);
    const column = coercePositiveInt(area.column, 1);
    const rowSpan = coercePositiveInt(area.row_span, 1);
    const columnSpan = coercePositiveInt(area.column_span, 1);

    if (row + rowSpan - 1 > rowsCount || column + columnSpan - 1 > columnsCount) {
      return false;
    }

    for (let rowIndex = row - 1; rowIndex < row - 1 + rowSpan; rowIndex += 1) {
      for (let columnIndex = column - 1; columnIndex < column - 1 + columnSpan; columnIndex += 1) {
        if (occupancy[rowIndex][columnIndex] !== null) {
          return false;
        }
      }
    }

    const rawItemIds = Array.isArray(area.item_ids) ? area.item_ids : [];
    const rawCellItems = area.cell_items && typeof area.cell_items === "object" && !Array.isArray(area.cell_items)
      ? area.cell_items
      : {};
    const itemIds = [];
    const cellItems = {};
    const localUsed = new Set();

    Object.keys(rawCellItems).sort().forEach((cellKey) => {
      if (!String(cellKey).includes(":")) {
        return;
      }
      const [rowPart, columnPart] = String(cellKey).split(":", 2);
      const cellRow = coercePositiveInt(rowPart, 0);
      const cellColumn = coercePositiveInt(columnPart, 0);
      if (!(row <= cellRow && cellRow < row + rowSpan && column <= cellColumn && cellColumn < column + columnSpan)) {
        return;
      }

      const rawCellItemIds = Array.isArray(rawCellItems[cellKey]) ? rawCellItems[cellKey] : [];
      const normalizedCellItemIds = [];

      rawCellItemIds.forEach((rawItemId) => {
        const itemId = normalizeItemId(rawItemId);
        if (!itemId || !activeSet.has(itemId) || usedItems.has(itemId) || localUsed.has(itemId)) {
          return;
        }
        localUsed.add(itemId);
        normalizedCellItemIds.push(itemId);
        itemIds.push(itemId);
      });

      if (normalizedCellItemIds.length) {
        cellItems[`${cellRow}:${cellColumn}`] = normalizedCellItemIds;
      }
    });

    const anchorKey = `${row}:${column}`;
    rawItemIds.forEach((rawItemId) => {
      const itemId = normalizeItemId(rawItemId);
      if (!itemId || !activeSet.has(itemId) || usedItems.has(itemId) || localUsed.has(itemId)) {
        return;
      }
      localUsed.add(itemId);
      itemIds.push(itemId);
      if (!cellItems[anchorKey]) {
        cellItems[anchorKey] = [];
      }
      cellItems[anchorKey].push(itemId);
    });

    itemIds.forEach((itemId) => usedItems.add(itemId));

    normalizedAreas.push({
      row,
      column,
      row_span: rowSpan,
      column_span: columnSpan,
      item_ids: itemIds,
      cell_items: cellItems,
    });

    const areaIndex = normalizedAreas.length - 1;
    for (let rowIndex = row - 1; rowIndex < row - 1 + rowSpan; rowIndex += 1) {
      for (let columnIndex = column - 1; columnIndex < column - 1 + columnSpan; columnIndex += 1) {
        occupancy[rowIndex][columnIndex] = areaIndex;
      }
    }
    return true;
  }

  rawAreas
    .filter((area) => area && typeof area === "object")
    .sort((left, right) => {
      if (coercePositiveInt(left.row, 1) !== coercePositiveInt(right.row, 1)) {
        return coercePositiveInt(left.row, 1) - coercePositiveInt(right.row, 1);
      }
      return coercePositiveInt(left.column, 1) - coercePositiveInt(right.column, 1);
    })
    .forEach((area) => {
      markArea(area);
    });

  for (let rowIndex = 0; rowIndex < rowsCount; rowIndex += 1) {
    for (let columnIndex = 0; columnIndex < columnsCount; columnIndex += 1) {
      if (occupancy[rowIndex][columnIndex] === null) {
        markArea({
          row: rowIndex + 1,
          column: columnIndex + 1,
          row_span: 1,
          column_span: 1,
          item_ids: [],
          cell_items: {},
        });
      }
    }
  }

  const unplacedItemIds = [];
  const rawUnusedIds = Array.isArray(source.unused_item_ids) ? source.unused_item_ids : [];
  rawUnusedIds.forEach((rawItemId) => {
    const itemId = normalizeItemId(rawItemId);
    if (!itemId || !activeSet.has(itemId) || usedItems.has(itemId)) {
      return;
    }
    usedItems.add(itemId);
    unplacedItemIds.push(itemId);
  });

  activeIds.forEach((itemId) => {
    if (!usedItems.has(itemId)) {
      usedItems.add(itemId);
      unplacedItemIds.push(itemId);
    }
  });

  assignUnplacedItemsToAreas(normalizedAreas, unplacedItemIds);

  normalizedAreas.sort((left, right) => {
    if (left.row !== right.row) {
      return left.row - right.row;
    }
    return left.column - right.column;
  });

  return {
    rows_count: rowsCount,
    columns_count: columnsCount,
    areas: normalizedAreas,
  };
}
