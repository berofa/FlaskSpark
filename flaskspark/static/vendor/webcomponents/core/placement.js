/**
 * Position a floating box (tooltip) next to an anchor rectangle.
 *
 * Pure function so it can be tested without a DOM. All values are viewport
 * pixels (getBoundingClientRect).
 *
 * @param {{left:number, top:number, width:number, height:number}} anchor
 * @param {{width:number, height:number}} box  size of the floating box
 * @param {{width:number, height:number}} viewport
 * @param {"top"|"bottom"|"left"|"right"} preferred
 * @param {{gap?:number, margin?:number}} [options]  gap between anchor and box, minimum distance to the viewport edge
 * @returns {{placement:string, left:number, top:number, arrow:number}}
 *   arrow: offset of the anchor centre along the box edge (left for top/bottom, top for left/right)
 */
export function computePlacement(anchor, box, viewport, preferred = "top", options = {}) {
  const gap = options.gap ?? 6;
  const margin = options.margin ?? 4;
  const opposite = { top: "bottom", bottom: "top", left: "right", right: "left" };
  const sides = Object.keys(opposite);
  const first = sides.includes(preferred) ? preferred : "top";
  const order = [first, opposite[first], ...sides.filter((side) => side !== first && side !== opposite[first])];

  const fits = {
    top: anchor.top - gap - box.height >= margin,
    bottom: anchor.top + anchor.height + gap + box.height <= viewport.height - margin,
    left: anchor.left - gap - box.width >= margin,
    right: anchor.left + anchor.width + gap + box.width <= viewport.width - margin,
  };
  const placement = order.find((side) => fits[side]) ?? first;

  const centerX = anchor.left + anchor.width / 2;
  const centerY = anchor.top + anchor.height / 2;
  const clamp = (value, size, limit) => Math.max(margin, Math.min(value, limit - size - margin));

  let left;
  let top;
  if (placement === "top" || placement === "bottom") {
    left = clamp(centerX - box.width / 2, box.width, viewport.width);
    top = placement === "top" ? anchor.top - gap - box.height : anchor.top + anchor.height + gap;
    return { placement, left, top, arrow: centerX - left };
  }
  top = clamp(centerY - box.height / 2, box.height, viewport.height);
  left = placement === "left" ? anchor.left - gap - box.width : anchor.left + anchor.width + gap;
  return { placement, left, top, arrow: centerY - top };
}
