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
