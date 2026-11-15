/**
 * The page «Settings» (flaskspark/settings.html, admins):
 * - the tab of the address (/settings#access, /settings#<module>) opens directly, the address follows the tab;
 * - Access: every switch of the role x area matrix is saved at once (POST {role_id, area, allowed}); it switches back
 *   when that fails;
 * - Users: a user's role is saved at once when chosen (POST {user_id, role_id}; "": the sign-in's role again); the
 *   choice goes back when that fails;
 * - a module's tab: «Save» sends the fields that changed (POST {values}; an emptied field: the default again), a
 *   field's «Default» button resets that one at once. The answer's message as a notice (a warning when services must
 *   restart), then the page's content again from the server.
 * - Data: «Remove» (one item) or «Clean up all» opens a dialog that lists exactly what is deleted; confirmed, the items
 *   go to POST {items}; the answer's message names the backup, then the page's content again from the server.
 */
import { notice, request } from "flaskspark/ui.js";
import { preload, t } from "flaskspark/i18n.js";
import { refreshPage, validateForm } from "flaskspark/forms.js";
import { findInPath, hostOf, inTables } from "flaskspark/shadow-paths.js";

preload(["Nothing changed.", "Saved", "Removed"]);

const tabs = document.querySelector("ui-tabs[data-settings-tabs]");
const wanted = location.hash.slice(1) && tabs?.querySelector(`ui-tab-panel[name="${CSS.escape(location.hash.slice(1))}"]`);
if (wanted) customElements.whenDefined("ui-tabs").then(() => tabs.show?.(wanted.getAttribute("name")));
tabs?.addEventListener("ui-tabs:change", (event) => {
  if (event.detail.name) history.replaceState(null, "", `#${event.detail.name}`);
});

/** The value of a setting's field as the form shows it ("true"/"false" for a switch). */
function current(field) {
  return field.matches("ui-check") ? String(Boolean(field.checked)) : String(field.value ?? "");
}

/** The fields of a settings form that differ from what the page showed: {path: value}. */
function changedValues(form) {
  const values = {};
  for (const box of form.querySelectorAll("[data-setting]")) {
    const field = box.querySelector("[name]");
    if (!field) continue;
    const value = current(field);
    if (value !== box.dataset.initial) values[box.dataset.setting] = value;
  }
  return values;
}

async function saveSettings(form, values) {
  const data = await request(form.getAttribute("action"), "POST", { values });
  notice(data.message || t("Saved"), data.restart?.length ? "warning" : "success");
  await refreshPage();
}

/** The tables of the page: their controls live in the <ui-table>'s shadow tree (see shadow-paths.js). */
const tables = () => document.querySelectorAll("ui-table");

async function accessChanged(event) {
  const check = findInPath(event.composedPath(), "ui-check[data-role][data-area]");
  if (!check) return;
  const table = hostOf(check).closest("[data-access-url]");
  try {
    const data = await request(table.dataset.accessUrl, "POST", {
      role_id: Number(check.dataset.role),
      area: check.dataset.area,
      allowed: Boolean(check.checked),
    });
    notice(data.message || t("Saved"));
  } catch (error) {
    check.checked = !check.checked;
    notice(error.message, "danger");
  }
}

/** The role each user's select showed last (to go back to when saving fails). */
const shownRoles = new Map();

async function userRoleChanged(event) {
  const select = findInPath(event.composedPath(), "ui-select[data-user]");
  if (!select) return;
  const box = hostOf(select).closest("[data-users-url]");
  try {
    const data = await request(box.dataset.usersUrl, "POST", {
      user_id: Number(select.dataset.user),
      role_id: select.value ? Number(select.value) : null,
    });
    shownRoles.set(select, select.value);
    notice(data.message || t("Saved"));
  } catch (error) {
    select.value = shownRoles.get(select) ?? "";
    notice(error.message, "danger");
  }
}

// A change in a <ui-table> stays in its shadow tree: listened for on the tables once they are upgraded.
customElements.whenDefined("ui-table").then(() => {
  for (const box of tables()) {
    const table = box.table ?? box;
    table.addEventListener("change", accessChanged);
    table.addEventListener("change", userRoleChanged);
  }
  for (const select of inTables(tables(), "ui-select[data-user]")) shownRoles.set(select, select.value);
});

document.addEventListener("submit", async (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || !form.hasAttribute("data-settings-form")) return;
  event.preventDefault();
  if (!validateForm(form)) return;
  const values = changedValues(form);
  if (!Object.keys(values).length) {
    notice(t("Nothing changed."), "info");
    return;
  }
  try {
    await saveSettings(form, values);
  } catch (error) {
    notice(error.message, "danger");
  }
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest?.("[data-reset]");
  const form = button?.closest("form[data-settings-form]");
  if (!form) return;
  event.preventDefault();
  try {
    await saveSettings(form, { [button.dataset.reset]: null });
  } catch (error) {
    notice(error.message, "danger");
  }
});

/** The items chosen for the clean-up (ids) while the dialog is open. */
let cleaning = [];

function leftoverRows(ids) {
  const rows = inTables(tables(), "tr[data-leftover]");
  return ids === "all" ? rows : rows.filter((row) => ids.includes(row.dataset.leftover));
}

function confirmCleanup(ids) {
  const dialog = document.querySelector("ui-dialog[data-leftovers-dialog]");
  const list = dialog?.querySelector("[data-leftovers-list]");
  if (!dialog || !list) return;
  const rows = leftoverRows(ids);
  cleaning = ids === "all" ? ["all"] : rows.map((row) => row.dataset.leftover);
  list.replaceChildren(...rows.map((row) => {
    const item = document.createElement("li");
    const title = document.createElement("strong");
    title.textContent = row.dataset.title;
    const what = document.createElement("ul");
    let deletes = [];
    try {
      deletes = JSON.parse(row.dataset.deletes || "[]");
    } catch {
      deletes = [];
    }
    what.replaceChildren(...deletes.map((text) => {
      const line = document.createElement("li");
      line.textContent = text;
      return line;
    }));
    item.append(title, what);
    return item;
  }));
  dialog.querySelector("[data-leftovers-notice]")?.replaceChildren();
  dialog.show();
}

document.addEventListener("click", async (event) => {
  const one = findInPath(event.composedPath(), "[data-clean]");
  const all = findInPath(event.composedPath(), "[data-clean-all]");
  if (one || all) {
    event.preventDefault();
    confirmCleanup(all ? "all" : [one.dataset.clean]);
    return;
  }
  const confirm = event.target.closest?.("[data-leftovers-confirm]");
  if (!confirm || !cleaning.length) return;
  event.preventDefault();
  const dialog = confirm.closest("ui-dialog");
  const box = dialog.querySelector("[data-leftovers-notice]");
  const url = confirm.closest("[data-leftovers-url]").dataset.leftoversUrl;
  confirm.setAttribute("disabled", "");
  try {
    const data = await request(url, "POST", { items: cleaning });
    cleaning = [];
    await dialog.hide();
    notice(data.message || t("Removed"), "info");  // stays longer: it names the backup
    await refreshPage();
  } catch (error) {
    notice(error.message, "danger", box);
  } finally {
    confirm.removeAttribute("disabled");
  }
});
