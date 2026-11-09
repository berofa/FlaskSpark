/**
 * Helpers for the consumers of a data feed. A feed is any element of the app (not part of this library) with
 * subscribe(callback) -> unsubscribe, e.g. an app's <hidden-json-feed>.
 *
 * Consumers reference a feed by id (e.g. <ui-x feed="prices">). The feed may
 * be defined after the consumer, so findFeed() waits for the element's
 * definition before returning it.
 */

/** Resolve a feed element by id once it is defined; null (with a warning) if missing. */
export async function findFeed(id) {
  if (!id) {
    return null;
  }
  if (document.readyState === "loading") {
    await new Promise((resolve) => document.addEventListener("DOMContentLoaded", resolve, { once: true }));
  }
  const element = document.getElementById(id);
  if (!element) {
    console.warn(`Feed #${id} not found`);
    return null;
  }
  await customElements.whenDefined(element.localName);
  return element;
}

/** Initial data embedded as <script type="application/json"> child, or undefined. */
export function readEmbeddedJson(host) {
  const script = host.querySelector(':scope > script[type="application/json"]');
  if (!script) {
    return undefined;
  }
  try {
    return JSON.parse(script.textContent);
  } catch (error) {
    console.warn("Invalid embedded JSON", error);
    return undefined;
  }
}
