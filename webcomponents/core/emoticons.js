/**
 * Emoticons typed into a field become emoji (":-)" → 🙂), in every text field of the page: <input> (text, search),
 * <textarea> and contenteditable areas (ui-markdown-editor, ui-richtext), also inside shadow trees.
 *
 * - An emoticon counts only at the start of the text or after a space (no "http://" or "Punkt 8)").
 * - Those that end in a bracket, "*" or "|" turn at once; those that could go on as a word, a path or a number
 *   (":D", ":P", ":/", "^^", "<3", …) turn when a space, line break or punctuation follows.
 * - Replaced through the browser's editing (insertText): Ctrl+Z / Cmd+Z brings the emoticon back.
 * - Not in password, e-mail, URL, phone and number fields, not in code (<code>, <pre>) of an editable area, not
 *   while an input method composes, and not in anything inside [data-emoticons="off"].
 *
 * installEmoticons(root = document) listens on root (once); replacement(before) is the pure part.
 */

/** [emoticon, emoji, at once]: at once false: only when a space or punctuation follows. */
export const EMOTICONS = [
  [">:-(", "😠", true], [">:(", "😠", true],
  [":'-(", "😢", true], [":'(", "😢", true], [":'-)", "🥲", true], [":')", "🥲", true],
  [":-)", "🙂", true], [":)", "🙂", true], ["=)", "🙂", true],
  [";-)", "😉", true], [";)", "😉", true],
  [":-(", "🙁", true], [":(", "🙁", true], ["=(", "🙁", true],
  [":-*", "😘", true], [":*", "😘", true],
  [":-|", "😐", true], [":|", "😐", true],
  ["B-)", "😎", true], ["8-)", "😎", true],
  ["(y)", "👍", true], ["(Y)", "👍", true],
  [":-D", "😃", false], [":D", "😃", false], ["xD", "😆", false], ["XD", "😆", false],
  [";-P", "😜", false], [";P", "😜", false], [";-p", "😜", false], [";p", "😜", false],
  [":-P", "😛", false], [":P", "😛", false], [":-p", "😛", false], [":p", "😛", false],
  [":-O", "😮", false], [":O", "😮", false], [":-o", "😮", false], [":o", "😮", false],
  [":-/", "😕", false], [":/", "😕", false], [":-S", "😖", false],
  ["</3", "💔", false], ["<3", "❤️", false],
  ["^_^", "😊", false], ["^^", "😊", false], ["o_O", "😳", false], ["O_o", "😳", false],
].sort((a, b) => b[0].length - a[0].length); // the longest first (">:(" before ":(")

const AFTER = /[\s.,!?;:]/u; // what lets an emoticon that could go on turn
const SPACE = /\s/u;
const SKIPPED_TYPES = new Set(["password", "email", "url", "tel", "number"]);

/**
 * The emoticon that ends the text before the caret: {start, end, emoji} (positions in `before`), or null.
 * `before` is the text up to the caret, the character just typed last.
 */
export function replacement(before) {
  if (!before) return null;
  const last = before.at(-1);
  const trailing = AFTER.test(last) ? 1 : 0;
  for (const [emoticon, emoji, atOnce] of EMOTICONS) {
    // at once: the emoticon right before the caret; else only with a space or punctuation after it
    for (const shift of atOnce ? [0] : trailing ? [1] : []) {
      const end = before.length - shift;
      const start = end - emoticon.length;
      if (start < 0 || before.slice(start, end) !== emoticon) continue;
      if (start > 0 && !SPACE.test(before[start - 1])) continue;
      return { start, end, emoji };
    }
  }
  return null;
}

function textField(el) {
  if (el instanceof HTMLTextAreaElement) return true;
  return el instanceof HTMLInputElement && !SKIPPED_TYPES.has(el.type) && ["text", "search", ""].includes(el.type);
}

/** Inside [data-emoticons="off"], also across shadow boundaries. */
function switchedOff(el) {
  for (let node = el; node; node = node.parentNode || node.host) {
    if (node.nodeType === 1 && node.getAttribute("data-emoticons") === "off") return true;
  }
  return false;
}

function inField(el) {
  const caret = el.selectionStart;
  if (caret == null || caret !== el.selectionEnd) return;
  const found = replacement(el.value.slice(0, caret));
  if (!found) return;
  const value = el.value;
  el.setSelectionRange(found.start, found.end);
  // the browser's editing keeps undo; where it doesn't take (an older browser), the text is set directly
  if (!document.execCommand?.("insertText", false, found.emoji) || el.value === value) {
    el.setRangeText(found.emoji, found.start, found.end, "end");
    el.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
  }
  const at = found.start + found.emoji.length + (caret - found.end);
  el.setSelectionRange(at, at);
}

function inEditable(root) {
  const selection = (root.getSelection ? root : document).getSelection?.();
  if (!selection || !selection.isCollapsed || !selection.rangeCount) return;
  const range = selection.getRangeAt(0);
  const node = range.startContainer;
  if (node.nodeType !== 3) return;
  if (node.parentElement?.closest("code, pre")) return;
  const found = replacement(node.data.slice(0, range.startOffset));
  if (!found) return;
  const target = document.createRange();
  target.setStart(node, found.start);
  target.setEnd(node, found.end);
  selection.removeAllRanges();
  selection.addRange(target);
  if (!document.execCommand?.("insertText", false, found.emoji)) {
    target.deleteContents();
    target.insertNode(document.createTextNode(found.emoji));
    selection.collapse(target.endContainer, target.endOffset);
  }
  if (found.end < range.startOffset) { // the space after it stays after the caret: move past it
    selection.modify?.("move", "forward", "character");
  }
}

const installed = new WeakSet();

/** Emoticons become emoji in every text field below root (the page by default); installing twice does nothing. */
export function installEmoticons(root = document) {
  if (installed.has(root)) return;
  installed.add(root);
  root.addEventListener("input", (event) => {
    if (event.isComposing || !["insertText", "insertLineBreak", "insertParagraph"].includes(event.inputType)) return;
    if (event.inputType === "insertText" && !event.data) return;
    const el = event.composedPath?.()[0] || event.target;
    if (!(el instanceof Element) || switchedOff(el)) return;
    if (textField(el)) {
      if (!el.readOnly && !el.disabled) inField(el);
    } else if (el.isContentEditable && event.inputType === "insertText") {
      inEditable(el.getRootNode());
    }
  }, true);
}
