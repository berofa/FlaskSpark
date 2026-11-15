/**
 * Which item of a <ui-list-group> a click chose. The items are rendered in the list's shadow tree around slots, so a
 * click on an item's content (its text, an icon: light DOM, slotted) has a target outside the shadow tree: the item's
 * wrapper is found in the click's composed path, not with closest().
 *
 * @param {EventTarget[]} path event.composedPath() of the click
 * @param {ShadowRoot} root the list's shadow root: the path is searched up to it only
 * @returns {number} the index of the action item (data-index of its wrapper), -1 for none
 */
export function clickedIndex(path, root) {
  for (const node of path) {
    if (node === root) break;
    if (node?.dataset?.index !== undefined && node.classList?.contains("list-group-item-action")) {
      return Number(node.dataset.index);
    }
  }
  return -1;
}
