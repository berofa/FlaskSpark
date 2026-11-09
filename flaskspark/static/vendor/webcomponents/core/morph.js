/**
 * morph(target, html): give `target` the children described by `html`, changing only what differs, instead of
 * `target.innerHTML = html`. For parts of a page that are rendered again on every live update: unchanged nodes stay
 * (no flicker, images are not loaded again, focus and scroll positions stay), changed text and attributes are set,
 * missing nodes inserted, superfluous ones removed.
 *
 * - Compared with the DOM as it is (also after changes made directly), not with the html given last time.
 * - Elements match by position and tag; with an `id` or `data-key` attribute by that key (a list whose items move).
 * - Custom elements (a "-" in the tag) render their own children: their attributes are synced (their
 *   attributeChangedCallback does the rest); only when their markup inside changes is the element replaced.
 * - Checkboxes and radios show `checked` as the html says, other fields its `value` (not while focused).
 * - Event listeners on the target or above stay (delegation); listeners bound to replaced elements go with them.
 */

const SOURCE = Symbol("morph source"); // a custom element's markup inside as it was given (before it rendered)

export function morph(target, html) {
  const template = target.ownerDocument.createElement("template");
  template.innerHTML = html;
  morphChildren(target, template.content);
}

/** The children of `target` like those of `source` (a node whose children may be moved into target). */
export function morphChildren(target, source) {
  const wanted = [...source.childNodes];
  wanted.forEach((next, i) => {
    const current = target.childNodes[i];
    if (current && same(current, next)) {
      patch(current, next);
      return;
    }
    const k = key(next);
    const keyed = k && [...target.childNodes].slice(i + 1).find((n) => key(n) === k && same(n, next));
    if (keyed) {
      target.insertBefore(keyed, current || null);
      patch(keyed, next);
      return;
    }
    mark(next);
    target.insertBefore(next, current || null);
  });
  while (target.childNodes.length > wanted.length) target.removeChild(target.lastChild);
}

function key(node) {
  return node.nodeType === 1 ? node.getAttribute("data-key") || node.getAttribute("id") || null : null;
}

function same(a, b) {
  if (a.nodeType !== b.nodeType) return false;
  if (a.nodeType !== 1) return true;
  return a.tagName === b.tagName && key(a) === key(b);
}

function custom(node) {
  return node.nodeType === 1 && node.tagName.includes("-");
}

/** Remember the markup inside every custom element of a subtree before it is inserted (and renders). */
function mark(node) {
  if (node.nodeType !== 1) return;
  if (custom(node)) node[SOURCE] = node.innerHTML;
  for (const child of node.childNodes) mark(child);
}

function patch(current, next) {
  if (current.nodeType !== 1) {
    if (current.nodeValue !== next.nodeValue) current.nodeValue = next.nodeValue;
    return;
  }
  if (custom(current)) {
    const known = current[SOURCE] ?? current.innerHTML;
    if (known !== next.innerHTML) {
      mark(next);
      current.replaceWith(next);
      return;
    }
    current[SOURCE] = known;
    attributes(current, next);
    return;
  }
  attributes(current, next);
  morphChildren(current, next);
}

function attributes(current, next) {
  for (const { name } of [...current.attributes]) {
    if (!next.hasAttribute(name)) current.removeAttribute(name);
  }
  for (const { name, value } of [...next.attributes]) {
    if (current.getAttribute(name) !== value) current.setAttribute(name, value);
  }
  if (current.tagName === "INPUT") {
    // once clicked or typed in, a field no longer follows its attributes: its state as the html says
    if (current.type === "checkbox" || current.type === "radio") current.checked = next.hasAttribute("checked");
    else if (next.hasAttribute("value") && current.ownerDocument?.activeElement !== current) current.value = next.getAttribute("value");
  }
}
