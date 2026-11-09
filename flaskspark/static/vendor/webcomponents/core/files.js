/**
 * File helpers without DOM (testable in Node).
 */

/** Does `file` ({name, type}) match an accept list ("image/*,.pdf,application/zip"; empty: everything)? */
export function acceptsFile(accept, file) {
  const rules = String(accept || "").split(",").map((r) => r.trim().toLowerCase()).filter(Boolean);
  if (!rules.length) return true;
  const name = String(file.name || "").toLowerCase();
  const type = String(file.type || "").toLowerCase();
  return rules.some((rule) => {
    if (rule.startsWith(".")) return name.endsWith(rule);
    if (rule.endsWith("/*")) return type.startsWith(rule.slice(0, -1));
    return type === rule;
  });
}

const UNITS = { b: 1, kb: 1024, mb: 1024 ** 2, gb: 1024 ** 3 };

/** Bytes of a size like "500", "200KB", "10 MB", "1.5gb"; null for empty or unreadable values. */
export function parseSize(value) {
  const match = String(value ?? "").trim().toLowerCase().match(/^(\d+(?:\.\d+)?)\s*(b|kb|mb|gb)?$/);
  return match ? Math.round(Number(match[1]) * UNITS[match[2] || "b"]) : null;
}

/** A readable size: "512 B", "1.5 KB", "12 MB". */
export function formatSize(bytes) {
  const units = ["B", "KB", "MB", "GB"];
  let size = Number(bytes) || 0;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  const digits = unit === 0 || size >= 10 ? 0 : 1;
  return `${size.toFixed(digits).replace(/\.0$/, "")} ${units[unit]}`;
}

/**
 * Splits picked files into accepted and rejected ones ({file, reason}: "type", "size", "count").
 * Options: accept, maxSize (bytes), maxFiles (in total, with `existing` already chosen), multiple.
 */
export function selectFiles(files, { accept = "", maxSize = null, maxFiles = null, multiple = false, existing = 0 } = {}) {
  const accepted = [];
  const rejected = [];
  const limit = multiple ? (maxFiles ?? Number.POSITIVE_INFINITY) - existing : 1;
  for (const file of files) {
    if (!acceptsFile(accept, file)) {
      rejected.push({ file, reason: "type" });
    } else if (maxSize !== null && file.size > maxSize) {
      rejected.push({ file, reason: "size" });
    } else if (accepted.length >= limit) {
      rejected.push({ file, reason: "count" });
    } else {
      accepted.push(file);
    }
  }
  return { accepted, rejected };
}
