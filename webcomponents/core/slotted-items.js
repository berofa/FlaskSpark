/**
 * Items of a container component rendered inside the container's own shadow tree.
 *
 * Bootstrap styles many components by their relation to siblings
 * (`.list-group-item + .list-group-item`, `:first-child`, `.card > …`). Those
 * selectors only work when all items sit in one tree, so the container renders
 * one wrapper per item (e.g. `<li class="list-group-item">`) and slots the
 * item element into it: each item gets its own slot name.
 */

/** The child elements of `host` matching `selector`, each assigned to the slot `<prefix>-<index>`. */
export function assignItemSlots(host, selector, prefix) {
  const items = [...host.children].filter((child) => child.matches(selector));
  items.forEach((item, index) => {
    const name = `${prefix}-${index}`;
    if (item.slot !== name) {
      item.slot = name;
    }
  });
  return items;
}

/**
 * Calls `callback` when children are added or removed, or when one of the
 * `attributes` changes on a child (not deeper: item content is slotted and
 * needs no new render). Returns the function that stops observing.
 */
export function observeItems(host, attributes, callback) {
  const observer = new MutationObserver((records) => {
    const relevant = records.some((record) => (record.type === "childList"
      ? record.target === host
      : record.target.parentElement === host));
    if (relevant) {
      callback();
    }
  });
  observer.observe(host, { childList: true, subtree: true, attributes: true, attributeFilter: attributes });
  return () => observer.disconnect();
}
