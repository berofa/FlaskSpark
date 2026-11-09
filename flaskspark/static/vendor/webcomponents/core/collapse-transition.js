import { afterTransition } from "./transitions.js";

/**
 * Bootstrap-style collapse expand/collapse (the .collapsing class dance),
 * shared by ui-collapse, ui-accordion, and ui-navbar.
 *
 * The node is expected to carry .collapse (plus .collapse-horizontal for
 * dimension "width"); the caller owns any surrounding state.
 */
export function expandElement(node, { dimension = "height", onComplete } = {}) {
  const scrollSize = dimension === "width" ? "scrollWidth" : "scrollHeight";
  node.classList.remove("collapse", "show");
  node.classList.add("collapsing");
  node.style[dimension] = "0";
  node.offsetHeight; // force reflow so the transition starts at 0
  node.style[dimension] = `${node[scrollSize]}px`;
  afterTransition(node, () => {
    node.classList.remove("collapsing");
    node.classList.add("collapse", "show");
    node.style[dimension] = "";
    onComplete?.();
  });
}

export function collapseElement(node, { dimension = "height", onComplete } = {}) {
  const scrollSize = dimension === "width" ? "scrollWidth" : "scrollHeight";
  node.style[dimension] = `${node[scrollSize]}px`;
  node.offsetHeight; // force reflow so the transition starts at full size
  node.classList.remove("collapse", "show");
  node.classList.add("collapsing");
  node.style[dimension] = "0";
  afterTransition(node, () => {
    node.classList.remove("collapsing");
    node.classList.add("collapse");
    node.style[dimension] = "";
    onComplete?.();
  });
}
