/**
 * The parts of ui-markdown-editor without a DOM (testable with node): its texts, the commands of the «/» and «+»
 * menus (built in and added by apps), and the edits of the Markdown source.
 */

/** The texts of the editor (English); a page passes its own as JSON in `labels` or the property labels. */
export const DEFAULT_LABELS = Object.freeze({
  "toolbar": "Formatting",
  "mode": "Editing mode",
  "mode-text": "Text",
  "mode-markdown": "Markdown",
  "format": "Text style",
  "paragraph": "Normal text",
  "heading-1": "Heading 1",
  "heading-2": "Heading 2",
  "heading-3": "Heading 3",
  "heading-4": "Heading 4",
  "heading-5": "Heading 5",
  "heading-6": "Heading 6",
  "bold": "Bold (Ctrl+B)",
  "italic": "Italic (Ctrl+I)",
  "strike": "Strikethrough",
  "quote": "Quote",
  "code": "Code",
  "link": "Link (Ctrl+K)",
  "bullets": "Bulleted list",
  "numbers": "Numbered list",
  "tasks": "Task list",
  "table": "Table",
  "table-size": "{columns} × {rows}",
  "attach": "Attach a file",
  "more": "More",
  "alert": "Alert",
  "alert-note": "Note",
  "alert-tip": "Tip",
  "alert-important": "Important",
  "alert-warning": "Warning",
  "alert-caution": "Caution",
  "code-block": "Code block",
  "details": "Collapsible section",
  "details-summary": "Details",
  "rule": "Horizontal line",
  "toc": "Table of contents",
  "row-add": "Add a row",
  "column-add": "Add a column",
  "row-delete": "Delete the row",
  "column-delete": "Delete the column",
  "table-delete": "Delete the table",
  "link-url": "Link address",
  "link-text": "Text",
  "language": "Language (e.g. python)",
  "insert": "Insert",
  "cancel": "Cancel",
  "commands": "Commands",
  "no-commands": "No matching command",
  "uploading": "Uploading {name} …",
  "upload-failed": "Upload failed: {name}",
  "required": "Required",
});

/** labels with {placeholders} filled in. */
export function format(text, params = {}) {
  return Object.entries(params).reduce((out, [k, v]) => out.replaceAll(`{${k}}`, String(v)), String(text));
}

const ALERTS = ["note", "tip", "important", "warning", "caution"];
const ALERT_ICONS = { note: "info-circle", tip: "lightbulb", important: "exclamation-circle",
  warning: "exclamation-triangle", caution: "exclamation-octagon" };

/**
 * The built-in commands of the menus: id, label (a key of the labels), icon (editor-icons.js), menus ("slash",
 * "plus") and keywords for the «/» search. The editor runs them by id.
 */
export const BUILTIN_COMMANDS = Object.freeze([
  { id: "heading-1", label: "heading-1", icon: "type-h1", menus: ["slash"], keywords: ["h1", "title"] },
  { id: "heading-2", label: "heading-2", icon: "type-h2", menus: ["slash"], keywords: ["h2"] },
  { id: "heading-3", label: "heading-3", icon: "type-h3", menus: ["slash"], keywords: ["h3"] },
  { id: "bullets", label: "bullets", icon: "list-ul", menus: ["slash"], keywords: ["ul", "list"] },
  { id: "numbers", label: "numbers", icon: "list-ol", menus: ["slash"], keywords: ["ol", "list"] },
  { id: "tasks", label: "tasks", icon: "list-check", menus: ["slash"], keywords: ["todo", "checkbox", "list"] },
  { id: "quote", label: "quote", icon: "quote", menus: ["slash"], keywords: ["blockquote"] },
  { id: "table", label: "table", icon: "table", menus: ["slash"], keywords: [] },
  ...ALERTS.map((kind) => ({ id: `alert-${kind}`, label: `alert-${kind}`, icon: ALERT_ICONS[kind],
    menus: ["slash", "plus"], keywords: ["alert", kind], group: "alert" })),
  { id: "code-block", label: "code-block", icon: "code-square", menus: ["slash", "plus"], keywords: ["pre", "fence"] },
  { id: "details", label: "details", icon: "chevron-bar-expand", menus: ["slash", "plus"],
    keywords: ["collapse", "summary", "expand"] },
  { id: "rule", label: "rule", icon: "hr", menus: ["slash", "plus"], keywords: ["hr", "divider", "line"] },
  { id: "toc", label: "toc", icon: "list-nested", menus: ["slash", "plus"], keywords: ["contents", "toc"] },
  { id: "attach", label: "attach", icon: "paperclip", menus: ["slash"], keywords: ["file", "upload", "image"] },
]);

const registry = [];

/**
 * A command for every editor on the page (e.g. an app's «Embedded view»):
 *   { id, label, icon?, menus?: ["slash", "plus"], keywords?, markdown?: string | (editor) => string,
 *     run?: (editor) => void }
 * markdown is inserted at the cursor (rendered in the text mode); run does anything else. icon: a name of
 * editor-icons.js or SVG markup. A command with the same id replaces the former one.
 */
export function addCommand(command) {
  const cmd = normalizeCommand(command);
  const i = registry.findIndex((c) => c.id === cmd.id);
  if (i >= 0) registry.splice(i, 1, cmd);
  else registry.push(cmd);
  return cmd;
}

/** Removes a command added with addCommand(). */
export function removeCommand(id) {
  const i = registry.findIndex((c) => c.id === id);
  if (i >= 0) registry.splice(i, 1);
}

/** The commands added for every editor. */
export function registeredCommands() {
  return [...registry];
}

export function normalizeCommand(command) {
  if (!command || typeof command !== "object" || !command.id || !command.label) {
    throw new TypeError("A command needs an id and a label");
  }
  if (!command.markdown && typeof command.run !== "function") {
    throw new TypeError(`Command ${command.id}: markdown or run() is needed`);
  }
  return { menus: ["slash", "plus"], keywords: [], icon: "", ...command, custom: true };
}

/** The commands of a menu ("slash" or "plus"): built-in, then the page's, then the editor's own. */
export function menuCommands(menu, own = [], builtin = BUILTIN_COMMANDS) {
  const all = new Map();
  for (const cmd of [...builtin, ...registry, ...own]) all.set(cmd.id, cmd);
  return [...all.values()].filter((cmd) => (cmd.menus || []).includes(menu));
}

/** The commands matching what was typed after «/» (label, id or a keyword starts with it or contains it). */
export function filterCommands(commands, query, labels = DEFAULT_LABELS) {
  const q = String(query || "").trim().toLowerCase();
  if (!q) return commands;
  const text = (cmd) => [labels[cmd.label] || cmd.label, cmd.id, ...(cmd.keywords || [])].map((s) => String(s).toLowerCase());
  const starts = commands.filter((cmd) => text(cmd).some((s) => s.startsWith(q) || s.split(/\s+/).some((w) => w.startsWith(q))));
  const contains = commands.filter((cmd) => !starts.includes(cmd) && text(cmd).some((s) => s.includes(q)));
  return [...starts, ...contains];
}

// --- Markdown source ---------------------------------------------------------------------------------------------

/**
 * Text wrapped in a mark (** for bold, * for italic, ~~ for strikethrough, ` for code) or unwrapped when it is
 * wrapped already. Returns the new value and selection.
 */
export function toggleWrap(value, start, end, mark) {
  const before = value.slice(0, start);
  const selected = value.slice(start, end);
  const after = value.slice(end);
  const n = mark.length;
  if (before.endsWith(mark) && after.startsWith(mark)) {
    return { value: before.slice(0, -n) + selected + after.slice(n), start: start - n, end: end - n };
  }
  if (selected.length >= 2 * n && selected.startsWith(mark) && selected.endsWith(mark)) {
    const inner = selected.slice(n, -n);
    return { value: before + inner + after, start, end: start + inner.length };
  }
  return { value: before + mark + selected + mark + after, start: start + n, end: end + n };
}

/** A link around the selection ([text](url)); without a selection the text given or the address. */
export function insertLink(value, start, end, url, text = "") {
  const label = value.slice(start, end) || text || url;
  const link = `[${label}](${url})`;
  const out = value.slice(0, start) + link + value.slice(end);
  return { value: out, start: start + link.length, end: start + link.length };
}

/** A text inserted at the cursor (replacing the selection). */
export function insertText(value, start, end, text) {
  return { value: value.slice(0, start) + text + value.slice(end), start: start + text.length, end: start + text.length };
}

/** A block (table, alert, …) on lines of its own, a blank line before and after. */
export function insertBlock(value, start, end, block) {
  const before = value.slice(0, start);
  const after = value.slice(end);
  const lead = !before ? "" : before.endsWith("\n\n") ? "" : before.endsWith("\n") ? "\n" : "\n\n";
  const body = block.replace(/\n+$/, "");
  const trail = !after ? "\n" : after.startsWith("\n\n") ? "" : after.startsWith("\n") ? "\n" : "\n\n";
  const out = before + lead + body + trail + after;
  const caret = (before + lead + body).length;
  return { value: out, start: caret, end: caret };
}

/** An empty table in Markdown (a header row and `rows` rows). */
export function tableMarkdown(columns = 3, rows = 2) {
  const cols = Math.max(1, columns);
  const row = `|${"   |".repeat(cols)}`;
  return [row, `|${" --- |".repeat(cols)}`, ...Array.from({ length: Math.max(1, rows) }, () => row)].join("\n");
}

/** An empty table for the text mode: a header row and `rows` rows, every cell editable. */
export function tableHtml(columns = 3, rows = 2) {
  const cols = Math.max(1, columns);
  const cells = (tag) => `<tr>${`<${tag}><br></${tag}>`.repeat(cols)}</tr>`;
  return `<table><thead>${cells("th")}</thead><tbody>${cells("td").repeat(Math.max(1, rows))}</tbody></table>`;
}

/** The Markdown of a built-in insert command (used in the Markdown mode). */
export function builtinMarkdown(id, labels = DEFAULT_LABELS, selected = "") {
  if (id.startsWith("alert-")) return `> [!${id.slice(6).toUpperCase()}]\n> ${selected}`;
  if (id.startsWith("heading-")) return `${"#".repeat(Number(id.slice(8)))} ${selected}`;
  switch (id) {
    case "code-block": return `\`\`\`\n${selected}\n\`\`\``;
    case "details": return `<details>\n<summary>${labels["details-summary"]}</summary>\n\n${selected}\n\n</details>`;
    case "rule": return "---";
    case "toc": return "[[_TOC_]]";
    case "table": return tableMarkdown();
    case "bullets": return `- ${selected}`;
    case "numbers": return `1. ${selected}`;
    case "tasks": return `- [ ] ${selected}`;
    case "quote": return `> ${selected}`;
    default: return null;
  }
}

/** The Markdown of an attachment: an image for image files, a link otherwise. */
export function attachmentMarkdown({ url, name }, type = "") {
  const label = String(name || url).replace(/[[\]\\]/g, (c) => `\\${c}`);
  const target = /[\s()<>]/.test(url) ? `<${String(url).replace(/[<>]/g, encodeURIComponent)}>` : url;
  const image = String(type).startsWith("image/") || (!type && /\.(png|jpe?g|gif|webp|avif|svg)(\?|#|$)/i.test(url));
  return `${image ? "!" : ""}[${label}](${target})`;
}
