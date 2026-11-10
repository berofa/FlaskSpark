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

const SIDES = ["top", "bottom", "left", "right"];
const OPPOSITE = { top: "bottom", bottom: "top", left: "right", right: "left" };

/**
 * Bootstrap's menu placements: "<side>[-<align>]" with side top, bottom, left, right, start or end (logical:
 * start = left in LTR) and align start or end (without one: centred).
 * Responsive: "bottom-start md:bottom-end lg:end-start" — the last breakpoint at or below the viewport width wins.
 *
 * @param {string} value  the placement attribute
 * @param {number} width  viewport width in px
 * @param {Record<string, number>} breakpoints  e.g. { sm: 576, md: 768, … }
 * @returns {string} the placement for this width, e.g. "bottom-end"
 */
export function resolvePlacement(value, width, breakpoints) {
  let result = "bottom-start";
  let best = -1;
  for (const token of String(value || "").trim().split(/\s+/).filter(Boolean)) {
    const [prefix, placement] = token.includes(":") ? token.split(":") : ["", token];
    const min = prefix ? breakpoints[prefix] : 0;
    if (min !== undefined && width >= min && min >= best) {
      best = min;
      result = placement;
    }
  }
  return result;
}

/**
 * Position a menu at an anchor: side and alignment like Floating UI's placements, flipped to the other side
 * when it does not fit, shifted to stay inside the viewport.
 *
 * @param {{left:number, top:number, width:number, height:number}} anchor
 * @param {{width:number, height:number}} box
 * @param {{width:number, height:number}} viewport
 * @param {string} placement  "bottom-start", "end", "top-end", "left", … (logical start/end follow `rtl`)
 * @param {{offset?:[number, number], margin?:number, rtl?:boolean}} [options]
 *   offset: [along the side, away from the anchor] like Bootstrap's data-bs-offset
 * @returns {{placement:string, left:number, top:number}} placement: the physical side and alignment used
 */
export function placeAligned(anchor, box, viewport, placement = "bottom-start", options = {}) {
  const [skid, distance] = options.offset ?? [0, 2];
  const margin = options.margin ?? 4;
  const rtl = Boolean(options.rtl);
  let [side, align = ""] = String(placement).split("-");
  if (side === "start") side = rtl ? "right" : "left";
  if (side === "end") side = rtl ? "left" : "right";
  if (!SIDES.includes(side)) side = "bottom";
  const vertical = side === "top" || side === "bottom";
  const fits = {
    top: anchor.top - distance - box.height >= margin,
    bottom: anchor.top + anchor.height + distance + box.height <= viewport.height - margin,
    left: anchor.left - distance - box.width >= margin,
    right: anchor.left + anchor.width + distance + box.width <= viewport.width - margin,
  };
  if (!fits[side] && fits[OPPOSITE[side]]) {
    side = OPPOSITE[side];
  }
  let left;
  let top;
  if (vertical) {
    top = side === "bottom" ? anchor.top + anchor.height + distance : anchor.top - distance - box.height;
    // start/end along the inline axis: start = the anchor's left edge in LTR, right edge in RTL.
    const atStart = rtl ? anchor.left + anchor.width - box.width : anchor.left;
    const atEnd = rtl ? anchor.left : anchor.left + anchor.width - box.width;
    left = (align === "start" ? atStart : align === "end" ? atEnd : anchor.left + (anchor.width - box.width) / 2) + skid;
    left = Math.max(margin, Math.min(left, viewport.width - box.width - margin));
  } else {
    left = side === "right" ? anchor.left + anchor.width + distance : anchor.left - distance - box.width;
    top = (align === "start" ? anchor.top : align === "end" ? anchor.top + anchor.height - box.height
      : anchor.top + (anchor.height - box.height) / 2) + skid;
    top = Math.max(margin, Math.min(top, viewport.height - box.height - margin));
  }
  return { placement: align ? `${side}-${align}` : side, left, top };
}
