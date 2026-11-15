/**
 * Events and elements across shadow trees, for page scripts with controls in a <ui-table>.
 *
 * <ui-table> moves its <table> into its shadow tree: a click inside reaches the page retargeted to the <ui-table>
 * (event.target is the table, not the button), a change of a control stays in the shadow tree (not composed), and
 * document.querySelectorAll() no longer finds the rows. So: listen for "change" on the tables themselves
 * (inTables / the `table` property), find the control on the event's composed path (findInPath) and go on in the page
 * from its host (hostOf).
 */

/** The first element on `path` (event.composedPath()) that matches `selector`, else undefined. */
export function findInPath(path, selector) {
  return path.find((node) => typeof node?.matches === "function" && node.matches(selector));
}

/** The shadow host of an element in a shadow tree (e.g. its <ui-table>), else the element itself. */
export function hostOf(element) {
  return element.getRootNode?.()?.host ?? element;
}

/** The elements matching `selector` in the given <ui-table>s (their moved <table>) or plain tables. */
export function inTables(tables, selector) {
  return [...tables].flatMap((box) => [...(box.table ?? box).querySelectorAll(selector)]);
}
