/*
 * flaskspark.core: the script of every page.
 * - Colour mode: webcomponents' theme.js keeps data-bs-theme (stored in localStorage "ui-theme", the
 *   [data-theme-value] buttons); the layout and the themes key on html.theme-dark / html.theme-light.
 * - Background requests that come back with 401 (a sign-in that expired, once SSO comes) reload the page, which then
 *   goes to the sign-in.
 * - Emoticons typed into any text field become emoji (webcomponents/core/emoticons.js; [data-emoticons="off"] keeps
 *   them as typed).
 * - Stacked tables (.table-stacked, .sm:table-stacked …) get the labels of their cells from the column headers
 *   (webcomponents/core/stacked-tables.js), also for rows rendered later.
 */
import { installEmoticons } from "webcomponents/core/emoticons.js";
import { installStackedTables } from "webcomponents/core/stacked-tables.js";

installEmoticons();
installStackedTables();

const root = document.documentElement;

function syncModeClasses() {
  const dark = root.getAttribute("data-bs-theme") === "dark";
  root.classList.toggle("theme-dark", dark);
  root.classList.toggle("theme-light", !dark);
}

new MutationObserver(syncModeClasses).observe(root, { attributes: true, attributeFilter: ["data-bs-theme"] });
syncModeClasses();

const nativeFetch = window.fetch.bind(window);
window.fetch = async (...args) => {
  const response = await nativeFetch(...args);
  if (response.status === 401 && new URL(response.url, location.href).origin === location.origin) {
    location.reload();
  }
  return response;
};
