/**
 * The JSON API of the attachments (flaskspark.core.attachments, /api/attachments): list, upload with progress,
 * change, order and delete the files of an item (owner type + id).
 *
 *   import * as attachments from "flaskspark/attachments.js";
 *   const { attachments: files, ready, max_size } = await attachments.list("note", 7);
 *   const { promise, abort } = attachments.upload("note", 7, file, (loaded, total) => {});
 */
import { request } from "flaskspark/ui.js";
import { t } from "flaskspark/i18n.js";

const base = (ownerType, ownerId) => `/api/attachments/${encodeURIComponent(ownerType)}/${Number(ownerId)}`;

/** {attachments, ready, max_size} of an item. */
export function list(ownerType, ownerId) {
  return request(base(ownerType, ownerId));
}

/**
 * Upload `file` as the raw request body (the server writes it to the storage while it arrives).
 * onProgress(loaded, total); resolves {attachment, message}, rejects with an Error carrying the server's message.
 * Returns {promise, abort}.
 */
export function upload(ownerType, ownerId, file, onProgress = () => {}) {
  const xhr = new XMLHttpRequest();
  const promise = new Promise((resolve, reject) => {
    xhr.open("POST", base(ownerType, ownerId));
    xhr.setRequestHeader("Accept", "application/json");
    xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
    xhr.setRequestHeader("X-File-Name", encodeURIComponent(file.name));
    xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
    xhr.upload.addEventListener("progress", (e) => onProgress(e.loaded, e.lengthComputable ? e.total : file.size));
    xhr.addEventListener("load", () => {
      let data = {};
      try {
        data = JSON.parse(xhr.responseText || "{}");
      } catch { /* not JSON (e.g. a proxy's error page) */ }
      if (xhr.status === 401) location.reload();
      if (xhr.status >= 200 && xhr.status < 300) resolve(data);
      else reject(new Error(data.error || (xhr.status === 413 ? t("The file is too large.") : t("Upload failed ({status}).", { status: xhr.status }))));
    });
    xhr.addEventListener("error", () => reject(new Error(t("Connection lost."))));
    xhr.addEventListener("abort", () => reject(new Error(t("Cancelled."))));
    xhr.send(file);
  });
  return { promise, abort: () => xhr.abort() };
}

export function update(id, changes) {
  return request(`/api/attachments/${Number(id)}`, "POST", { action: "update", ...changes });
}

export function remove(id) {
  return request(`/api/attachments/${Number(id)}`, "POST", { action: "delete" });
}

export function reorder(ownerType, ownerId, ids) {
  return request(`${base(ownerType, ownerId)}/order`, "POST", { ids });
}

/** 1536000 -> "1.5 MB" (in the page's language). */
export function fileSize(bytes) {
  if (bytes == null) return "–";
  const units = ["B", "kB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1000 && unit < units.length - 1) {
    value /= 1000;
    unit += 1;
  }
  return `${value.toLocaleString(document.documentElement.lang || undefined, { maximumFractionDigits: unit ? 1 : 0 })} ${units[unit]}`;
}
