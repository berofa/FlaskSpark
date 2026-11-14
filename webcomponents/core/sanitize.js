/**
 * HTML for tooltips and popovers with html enabled: only Bootstrap's default allow list of tags and attributes
 * survives (like Bootstrap's sanitizer). Everything else — scripts, event handlers, javascript: URLs — is dropped.
 */

const ARIA = /^aria-[\w-]*$/i;
const GLOBAL = ["class", "dir", "id", "lang", "role"];

export const DEFAULT_ALLOW_LIST = {
  "*": GLOBAL,
  a: ["target", "href", "title", "rel"],
  area: [],
  b: [],
  br: [],
  code: [],
  col: [],
  div: [],
  em: [],
  hr: [],
  h1: [], h2: [], h3: [], h4: [], h5: [], h6: [],
  i: [],
  img: ["src", "srcset", "alt", "title", "width", "height"],
  li: [],
  ol: [],
  p: [],
  pre: [],
  s: [],
  small: [],
  span: [],
  sub: [],
  sup: [],
  strong: [],
  u: [],
  ul: [],
};

const SAFE_URL = /^(?!javascript:)(?:[a-z0-9+.-]+:|[^&:/?#]*(?:[/?#]|$))/i;

/** The sanitized HTML of `html` (a string), as a string. */
export function sanitizeHtml(html, allowList = DEFAULT_ALLOW_LIST) {
  const doc = new DOMParser().parseFromString(String(html ?? ""), "text/html");
  const walk = (parent) => {
    for (const node of [...parent.childNodes]) {
      if (node.nodeType === Node.COMMENT_NODE) {
        node.remove();
        continue;
      }
      if (node.nodeType !== Node.ELEMENT_NODE) {
        continue;
      }
      const tag = node.localName;
      if (!Object.hasOwn(allowList, tag)) {
        node.remove();
        continue;
      }
      const allowed = [...(allowList["*"] || []), ...allowList[tag]];
      for (const attribute of [...node.attributes]) {
        const name = attribute.name.toLowerCase();
        const keep = (allowed.includes(name) || ARIA.test(name))
          && (!["href", "src"].includes(name) || SAFE_URL.test(attribute.value.trim()));
        if (!keep) {
          node.removeAttribute(attribute.name);
        }
      }
      walk(node);
    }
  };
  walk(doc.body);
  return doc.body.innerHTML;
}
