"""ui-markdown and ui-markdown-editor (Markdown shown and edited; no Bootstrap counterpart)."""

from __future__ import annotations

from .common import lines

SAMPLE = "\n".join([
    "[[_TOC_]]",
    "",
    "## Release notes",
    "",
    "Some **bold**, *italic*, ~~struck~~ text, `inline code` and a link to https://example.com.",
    "",
    "- [x] Planned",
    "- [ ] Released",
    "",
    "> [!note]",
    "> Alerts like on GitHub and GitLab.",
    "",
    "> [!warning] Mind the gap",
    "> With a title of its own.",
    "",
    "| Version | Date |",
    "| :--- | ---: |",
    "| 1.0 | 2026-11-14 |",
    "",
    "```mermaid",
    "graph TD; A-->B",
    "```",
    "",
    "<details>",
    "<summary>More</summary>",
    "",
    "Hidden until opened.",
    "",
    "</details>",
])


def _attr(text: str) -> str:
    return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "&#10;")


PAGE = {
    "title": "ui-markdown-editor / ui-markdown",
    "summary": "Markdown edited as formatted text or as source, and Markdown shown, both with the rules of the server's "
    "flaskspark.markdown (tables, task lists, alerts, collapsible sections, table of contents; sanitised). "
    "The value is always Markdown. Mermaid and PlantUML stay code blocks.",
    "submodule": "ui-markdown-editor",
    "entry": "modules/bootstrap/ui-markdown-editor/ui-markdown-editor.js",
    "sections": [
        {
            "id": "editor",
            "title": "Editor",
            "intro": "«Text» edits the formatted text, «Markdown» the source (monospace). Type <kbd>/</kbd> at the "
            "start of a line for the commands, <kbd>+</kbd> in the toolbar for alerts, code block, collapsible section, "
            "line and table of contents. <kbd>Ctrl+B</kbd> / <kbd>I</kbd> / <kbd>K</kbd> in both modes.",
            "html": lines(f'<ui-markdown-editor id="mdEditor" label="Description" rows="10" value="{_attr(SAMPLE)}"></ui-markdown-editor>',
                          '<pre class="small mt-3" id="mdValue"></pre>'),
        },
        {
            "id": "form",
            "title": "Form field",
            "intro": "<code>name</code> submits the Markdown; <code>help</code>, <code>placeholder</code>, "
            "<code>required</code>, <code>error</code>, <code>readonly</code> and <code>disabled</code> like the other "
            "fields; <code>mode=\"markdown\"</code> starts in the source.",
            "html": lines(
                '<form onsubmit="event.preventDefault(); this.querySelector(\'output\').value = new FormData(this).get(\'note\')">',
                '  <ui-markdown-editor name="note" label="Note" placeholder="Write something, / for commands" required rows="4"></ui-markdown-editor>',
                '  <ui-button type="submit" variant="primary" class="mt-3">Submit</ui-button> <output class="ms-2 small"></output>',
                "</form>",
                '<ui-markdown-editor class="mt-3" label="Source first" mode="markdown" rows="3" value="**Hello**"></ui-markdown-editor>',
                '<ui-markdown-editor class="mt-3" label="Read only" readonly rows="2" value="Not *editable*."></ui-markdown-editor>',
            ),
        },
        {
            "id": "upload",
            "title": "Attachments",
            "intro": "The paperclip, «/» → attachment, dropping or pasting files: the editor fires "
            "<code>ui-markdown-editor:attach</code> (cancelable) and otherwise calls <code>uploadHandler(file)</code>, "
            "which returns <code>{url, name}</code>; images are inserted as images, other files as links. The docs "
            "app stores nothing: its handler only answers with a made-up address.",
            "html": '<ui-markdown-editor id="mdUpload" label="With uploads" rows="4"></ui-markdown-editor>',
            "script": lines(
                'const editor = document.querySelector("#mdUpload");',
                "editor.uploadHandler = async (file) => {",
                "  const body = new FormData();",
                '  body.append("file", file);',
                '  const response = await fetch("/api/uploads", { method: "POST", body });',
                "  if (!response.ok) throw new Error(response.statusText);",
                "  const { url } = await response.json();",
                "  return { url, name: file.name };",
                "};",
                "// or take over: preventDefault() and insert later",
                'editor.addEventListener("ui-markdown-editor:attach", (e) => {',
                "  e.preventDefault();",
                "  upload(e.detail.file).then((url) => e.detail.insert({ url, name: e.detail.file.name }));",
                "});",
            ),
        },
        {
            "id": "commands",
            "title": "Own commands",
            "intro": "Apps add entries to the «/» and «+» menus: for every editor of the page with "
            "<code>UiMarkdownEditor.addCommand()</code>, for one editor with <code>editor.addCommand()</code>. "
            "<code>markdown</code> is inserted at the cursor (text or function), <code>run(editor)</code> does anything "
            "else. Here: «Embedded view» and «Signature».",
            "html": '<ui-markdown-editor id="mdCommands" label="With own commands" rows="4"></ui-markdown-editor>',
            "script": lines(
                'import { UiMarkdownEditor } from "/webcomponents/modules/bootstrap/ui-markdown-editor/ui-markdown-editor.js";',
                "",
                "UiMarkdownEditor.addCommand({",
                '  id: "embedded-view", label: "Embedded view", icon: "table", menus: ["slash", "plus"],',
                '  keywords: ["query", "view"],',
                '  markdown: "```view\\nlabel = \\"bug\\"\\n```",',
                "});",
                'document.querySelector("#mdCommands").addCommand({',
                '  id: "signature", label: "Signature", menus: ["slash"],',
                '  markdown: () => `— ${new Date().toLocaleDateString()}`,',
                "});",
            ),
        },
        {
            "id": "texts",
            "title": "Texts",
            "intro": "All texts are in <code>labels</code> (JSON attribute or property; keys: <code>DEFAULT_LABELS</code> in "
            "<code>editor-commands.js</code>). Apps on <code>flaskspark.core</code> get them translated: "
            "<code>labels='{{ markdown_editor_labels()|tojson }}'</code>. The alert titles (<code>alert-note</code> …) "
            "are used for the Markdown too.",
            "html": lines(
                '<ui-markdown-editor rows="3" labels=\'{"mode-text": "Text", "mode-markdown": "Markdown", '
                '"paragraph": "Normaler Text", "bold": "Fett (Ctrl+B)", "italic": "Kursiv (Ctrl+I)", '
                '"alert-note": "Hinweis", "more": "Mehr"}\' value="> [!note]&#10;> Ein Hinweis."></ui-markdown-editor>',
            ),
        },
        {
            "id": "display",
            "title": "Showing Markdown",
            "intro": "<code>&lt;ui-markdown&gt;</code> renders Markdown in the browser (sanitised, same typography as the "
            "editor): from <code>value</code>, a <code>&lt;script type=\"text/markdown\"&gt;</code> child or its text. "
            "HTML rendered on the server (<code>{{ text|markdown }}</code>) goes in as children; it is sanitised again (the "
            "children are in the page until the component takes them, so they must be safe already: the filter's output is). "
            "<code>base-url</code> puts a prefix in front of relative links and images (e.g. a GitLab project's uploads).",
            "html": lines(
                f'<ui-markdown value="{_attr(SAMPLE)}"></ui-markdown>',
                '<ui-markdown class="mt-3"><p>Rendered on the <strong>server</strong> (e.g. <code>{{ text|markdown }}</code>).</p></ui-markdown>',
            ),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines(
                'import { loadMarkdown, render, toMarkdown } from "/webcomponents/modules/bootstrap/ui-markdown/markdown.js";',
                "",
                "await loadMarkdown(); // markdown-it, loaded on first use",
                'const html = render("**hi**", { baseUrl: "https://git.example.com/group/project" });',
                "const text = toMarkdown(html); // \"**hi**\\n\"",
                "",
                'const editor = document.querySelector("ui-markdown-editor");',
                'editor.addEventListener("change", () => save(editor.value)); // Markdown',
                'editor.value = "# New content";',
                'editor.mode = "markdown";',
            ),
        },
    ],
    "tokens": {"host": "ui-markdown-editor", "example_token": "--ui-markdown-editor-toolbar-bg",
               "example_value": "transparent"},
    "elements": [
        {
            "tag": "ui-markdown-editor",
            "attributes": [
                ("name / value", "string", "Form name and initial Markdown."),
                ("label / help / placeholder", "string", "Texts."),
                ("rows", "number", "Minimum height in lines (default 8)."),
                ("required / disabled / readonly", "boolean", "Form states (required: not empty)."),
                ("error", "string", "A message shown as invalid."),
                ("mode", "text | markdown", "The mode (default text)."),
                ("base-url", "string", "Prefix of relative links and images while showing them (the Markdown keeps them)."),
                ("breaks", "boolean", "A line break is a <code>&lt;br&gt;</code>."),
                ("labels", "JSON", "The texts by key (English defaults)."),
            ],
            "slots": [("(default)", "The editable text (created; a light-DOM child).")],
            "parts": [("field / label / help / feedback", "The form field."),
                      ("frame / toolbar / group / tool / modes / mode", "The editor."),
                      ("source", "The Markdown textarea."), ("menu", "Menus, table picker, dialog."),
                      ("status", "Upload messages.")],
            "events": [("input / change", "While typing / on leaving after a change."),
                       ("ui-markdown-editor:mode", "The mode changed (<code>detail.mode</code>)."),
                       ("ui-markdown-editor:attach", "A file to attach (<code>detail.file</code>, <code>detail.insert({url, name})</code>; cancelable)."),
                       ("ui-markdown-editor:upload-error", "<code>uploadHandler</code> failed (<code>detail.file</code>, <code>detail.error</code>).")],
            "methods": [("value", "Get / set the Markdown."), ("mode", "text or markdown."), ("labels", "Get / set the texts."),
                        ("uploadHandler", "(file) → Promise&lt;{url, name}&gt;."),
                        ("rewriteUrl", "(url, kind) → url or null, e.g. an image proxy."),
                        ("addCommand(cmd) / removeCommand(id)", "Commands of this editor; static on the class for all."),
                        ("insertMarkdown(text)", "Inserts Markdown at the cursor."),
                        ("focus() / checkValidity() / reportValidity()", "As usual.")],
        },
        {
            "tag": "ui-markdown",
            "attributes": [
                ("value", "string", "The Markdown (or a <code>script type=\"text/markdown\"</code> child, or the text)."),
                ("base-url", "string", "Prefix of relative links and images."),
                ("breaks", "boolean", "A line break is a <code>&lt;br&gt;</code>."),
                ("note-label … caution-label", "string", "Titles of the alerts."),
            ],
            "parts": [("body", "The rendered content (<code>.markdown-body</code>).")],
            "events": [("ui-markdown:render", "After rendering.")],
            "methods": [("value / html", "Markdown, or HTML rendered elsewhere (sanitised)."),
                        ("rewriteUrl", "(url, kind) → url or null.")],
        },
    ],
    "notes": [
        "Typography tokens of both: <code>--ui-markdown-*</code> (gap, quote, code, tables, alert colours; "
        "<code>ui-markdown/markdown-body.css</code>).",
        "The conversion (<code>ui-markdown/markdown.js</code>) and the Python module <code>flaskspark.markdown</code> "
        "share their rules and test cases, so the browser and the server render the same HTML and write the same Markdown.",
    ],
    "page_script": lines(
        'import { UiMarkdownEditor } from "/webcomponents/modules/bootstrap/ui-markdown-editor/ui-markdown-editor.js";',
        'const main = document.querySelector("#mdEditor");',
        'const out = document.querySelector("#mdValue");',
        "const show = () => { out.textContent = main.value; };",
        'main?.addEventListener("input", show);',
        'main?.addEventListener("ui-markdown-editor:mode", show);',
        "customElements.whenDefined(\"ui-markdown-editor\").then(() => setTimeout(show, 300));",
        'const upload = document.querySelector("#mdUpload");',
        "if (upload) upload.uploadHandler = async (file) => ({ url: `/uploads/${encodeURIComponent(file.name)}`, name: file.name });",
        "UiMarkdownEditor.addCommand({",
        '  id: "embedded-view", label: "Embedded view", icon: "table", menus: ["slash", "plus"], keywords: ["query", "view"],',
        '  markdown: "```view\\nlabel = \\"bug\\"\\n```",',
        "});",
        'document.querySelector("#mdCommands")?.addCommand({',
        '  id: "signature", label: "Signature", menus: ["slash"], markdown: () => `— ${new Date().toLocaleDateString()}`,',
        "});",
    ),
}
