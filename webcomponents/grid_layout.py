"""Generic helpers for component grid layouts."""

from __future__ import annotations

from typing import Iterable


def _coerce_positive_int(value, fallback: int = 1) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(1, numeric)


def _normalize_item_id(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_unit_areas(rows_count: int, columns_count: int) -> list[dict]:
    return [
        {
            "row": row_index,
            "column": column_index,
            "row_span": 1,
            "column_span": 1,
            "item_ids": [],
            "cell_items": {},
        }
        for row_index in range(1, rows_count + 1)
        for column_index in range(1, columns_count + 1)
    ]


def default_layout() -> dict:
    return {
        "rows_count": 1,
        "columns_count": 1,
        "areas": build_unit_areas(1, 1),
    }


def _assign_unplaced_items_to_areas(areas: list[dict], item_ids: list[str]) -> None:
    if not areas or not item_ids:
        return

    def _sort_key(area: dict) -> tuple[int, int, int]:
        return (len(area["item_ids"]), area["row"], area["column"])

    sorted_areas = sorted(areas, key=_sort_key)

    for item_id in item_ids:
        target_area = sorted_areas[0]
        anchor_key = f'{target_area["row"]}:{target_area["column"]}'
        target_area["item_ids"].append(item_id)
        target_area.setdefault("cell_items", {}).setdefault(anchor_key, []).append(item_id)
        sorted_areas.sort(key=_sort_key)


def normalize_layout(payload: dict | None, active_item_ids: Iterable[str]) -> dict:
    active_ids = [item_id for item_id in (_normalize_item_id(value) for value in active_item_ids) if item_id]
    active_set = set(active_ids)
    source = payload if isinstance(payload, dict) else {}
    rows_count = _coerce_positive_int(source.get("rows_count") or source.get("rows") or 1, 1)
    columns_count = _coerce_positive_int(source.get("columns_count") or source.get("columns") or 1, 1)
    raw_areas = source.get("areas")
    if not isinstance(raw_areas, list):
        raw_areas = build_unit_areas(rows_count, columns_count)

    occupancy: list[list[int | None]] = [
        [None for _ in range(columns_count)] for _ in range(rows_count)
    ]
    normalized_areas: list[dict] = []
    used_items: set[str] = set()

    def _mark_area(area: dict) -> bool:
        row = _coerce_positive_int(area.get("row"), 1)
        column = _coerce_positive_int(area.get("column"), 1)
        row_span = _coerce_positive_int(area.get("row_span"), 1)
        column_span = _coerce_positive_int(area.get("column_span"), 1)
        if row + row_span - 1 > rows_count or column + column_span - 1 > columns_count:
            return False
        for row_index in range(row - 1, row - 1 + row_span):
            for column_index in range(column - 1, column - 1 + column_span):
                if occupancy[row_index][column_index] is not None:
                    return False

        raw_item_ids = area.get("item_ids")
        if not isinstance(raw_item_ids, list):
            raw_item_ids = []
        raw_cell_items = area.get("cell_items")
        if not isinstance(raw_cell_items, dict):
            raw_cell_items = {}

        item_ids: list[str] = []
        cell_items: dict[str, list[str]] = {}
        local_used: set[str] = set()

        for cell_key in sorted(raw_cell_items.keys()):
            if ":" not in str(cell_key):
                continue
            row_part, column_part = str(cell_key).split(":", 1)
            cell_row = _coerce_positive_int(row_part, 0)
            cell_column = _coerce_positive_int(column_part, 0)
            if not (row <= cell_row < row + row_span and column <= cell_column < column + column_span):
                continue
            raw_cell_item_ids = raw_cell_items.get(cell_key)
            if not isinstance(raw_cell_item_ids, list):
                continue
            normalized_cell_item_ids = []
            for raw_item_id in raw_cell_item_ids:
                item_id = _normalize_item_id(raw_item_id)
                if not item_id or item_id not in active_set or item_id in used_items or item_id in local_used:
                    continue
                local_used.add(item_id)
                normalized_cell_item_ids.append(item_id)
                item_ids.append(item_id)
            if normalized_cell_item_ids:
                cell_items[f"{cell_row}:{cell_column}"] = normalized_cell_item_ids

        anchor_key = f"{row}:{column}"
        for raw_item_id in raw_item_ids:
            item_id = _normalize_item_id(raw_item_id)
            if not item_id or item_id not in active_set or item_id in used_items or item_id in local_used:
                continue
            local_used.add(item_id)
            item_ids.append(item_id)
            cell_items.setdefault(anchor_key, []).append(item_id)

        used_items.update(item_ids)
        normalized_areas.append(
            {
                "row": row,
                "column": column,
                "row_span": row_span,
                "column_span": column_span,
                "item_ids": item_ids,
                "cell_items": cell_items,
            }
        )
        area_index = len(normalized_areas) - 1
        for row_index in range(row - 1, row - 1 + row_span):
            for column_index in range(column - 1, column - 1 + column_span):
                occupancy[row_index][column_index] = area_index
        return True

    for raw_area in sorted(
        [area for area in raw_areas if isinstance(area, dict)],
        key=lambda item: (
            _coerce_positive_int(item.get("row"), 1),
            _coerce_positive_int(item.get("column"), 1),
        ),
    ):
        _mark_area(raw_area)

    for row_index in range(rows_count):
        for column_index in range(columns_count):
            if occupancy[row_index][column_index] is None:
                _mark_area(
                    {
                        "row": row_index + 1,
                        "column": column_index + 1,
                        "row_span": 1,
                        "column_span": 1,
                        "item_ids": [],
                        "cell_items": {},
                    }
                )

    unplaced_item_ids: list[str] = []
    raw_unused_ids = source.get("unused_item_ids")
    if not isinstance(raw_unused_ids, list):
        raw_unused_ids = []

    for raw_item_id in raw_unused_ids:
        item_id = _normalize_item_id(raw_item_id)
        if not item_id or item_id not in active_set or item_id in used_items:
            continue
        used_items.add(item_id)
        unplaced_item_ids.append(item_id)

    for item_id in active_ids:
        if item_id in used_items:
            continue
        used_items.add(item_id)
        unplaced_item_ids.append(item_id)

    _assign_unplaced_items_to_areas(normalized_areas, unplaced_item_ids)

    normalized_areas.sort(key=lambda area: (area["row"], area["column"]))
    return {
        "rows_count": rows_count,
        "columns_count": columns_count,
        "areas": normalized_areas,
    }
