/**
 * The page numbers a pagination shows (DOM-free): all pages when they fit into `max` entries, else the first and
 * last page, a window around the current one and "…" gaps; always exactly `max` entries (each gap counts as one).
 * Returns numbers and the string "gap".
 */
export function pageWindow(current, total, max = 7) {
  const pages = Math.max(1, Math.floor(total));
  const page = Math.min(Math.max(1, Math.floor(current)), pages);
  const slots = Math.max(5, Math.floor(max));
  const range = (from, to) => Array.from({ length: to - from + 1 }, (_, index) => from + index);
  if (pages <= slots) {
    return range(1, pages);
  }
  if (page <= slots - 3) {
    return [...range(1, slots - 2), "gap", pages];
  }
  if (page >= pages - (slots - 4)) {
    return [1, "gap", ...range(pages - (slots - 3), pages)];
  }
  const middle = slots - 4;
  const start = page - Math.floor((middle - 1) / 2);
  return [1, "gap", ...range(start, start + middle - 1), "gap", pages];
}
