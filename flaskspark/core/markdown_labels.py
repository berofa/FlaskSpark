"""The texts of the Markdown editor (ui-markdown-editor) in the page's language, from the core's catalogue.

    <ui-markdown-editor name="text" labels='{{ markdown_editor_labels()|tojson }}'></ui-markdown-editor>

The keys and English texts are the editor's DEFAULT_LABELS (webcomponents/modules/bootstrap/ui-markdown-editor/
editor-commands.js; a test keeps them equal). The alert titles (alert-note …) also translate the titles of the Jinja
filter markdown (flaskspark.markdown.alert_titles).
"""

from __future__ import annotations

from flaskspark.core.module import N_

LABELS = {
    "toolbar": N_("Formatting"),
    "mode": N_("Editing mode"),
    "mode-text": N_("Text"),
    "mode-markdown": N_("Markdown"),
    "format": N_("Text style"),
    "paragraph": N_("Normal text"),
    "heading-1": N_("Heading 1"),
    "heading-2": N_("Heading 2"),
    "heading-3": N_("Heading 3"),
    "heading-4": N_("Heading 4"),
    "heading-5": N_("Heading 5"),
    "heading-6": N_("Heading 6"),
    "bold": N_("Bold (Ctrl+B)"),
    "italic": N_("Italic (Ctrl+I)"),
    "strike": N_("Strikethrough"),
    "quote": N_("Quote"),
    "code": N_("Code"),
    "link": N_("Link (Ctrl+K)"),
    "bullets": N_("Bulleted list"),
    "numbers": N_("Numbered list"),
    "tasks": N_("Task list"),
    "table": N_("Table"),
    "table-size": N_("{columns} × {rows}"),
    "attach": N_("Attach a file"),
    "more": N_("More"),
    "alert": N_("Alert"),
    "alert-note": N_("Note"),
    "alert-tip": N_("Tip"),
    "alert-important": N_("Important"),
    "alert-warning": N_("Warning"),
    "alert-caution": N_("Caution"),
    "code-block": N_("Code block"),
    "details": N_("Collapsible section"),
    "details-summary": N_("Details"),
    "rule": N_("Horizontal line"),
    "toc": N_("Table of contents"),
    "row-add": N_("Add a row"),
    "column-add": N_("Add a column"),
    "row-delete": N_("Delete the row"),
    "column-delete": N_("Delete the column"),
    "table-delete": N_("Delete the table"),
    "link-url": N_("Link address"),
    "link-text": N_("Text"),
    "language": N_("Language (e.g. python)"),
    "insert": N_("Insert"),
    "cancel": N_("Cancel"),
    "commands": N_("Commands"),
    "no-commands": N_("No matching command"),
    "uploading": N_("Uploading {name} …"),
    "upload-failed": N_("Upload failed: {name}"),
    "required": N_("Required"),
}


def markdown_editor_labels() -> dict[str, str]:
    """The editor's texts translated (English outside a request)."""
    try:
        from flask_babel import gettext

        return {key: gettext(text) for key, text in LABELS.items()}
    except Exception:  # no app or request context
        return dict(LABELS)


__all__ = ["LABELS", "markdown_editor_labels"]
