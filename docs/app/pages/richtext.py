"""ui-richtext (formatted text field; no Bootstrap counterpart)."""

from __future__ import annotations

from .common import lines

PAGE = {
    "title": "ui-richtext",
    "summary": "A form field for formatted text: bold, italic, underline, strikethrough, lists, quote and links. The value is "
    "HTML; pasted HTML is reduced to structure and simple markup.",
    "submodule": "ui-richtext",
    "entry": "modules/bootstrap/ui-richtext/ui-richtext.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "<kbd>Ctrl+B</kbd> / <kbd>I</kbd> / <kbd>U</kbd> as usual, <kbd>Ctrl+K</kbd> for a link. The tools of the "
            "formatting at the cursor look pressed.",
            "html": lines('<ui-richtext label="Message" placeholder="Write something…" rows="5"',
                          '  value="<p>Some <b>bold</b> and <i>italic</i> text.</p><ul><li>a list</li></ul><blockquote>A quote</blockquote>"></ui-richtext>'),
        },
        {
            "id": "form",
            "title": "Form field",
            "intro": "<code>name</code> submits the HTML; <code>help</code>, <code>required</code>, <code>error</code> and "
            "<code>disabled</code> like the other fields.",
            "html": lines(
                '<form onsubmit="event.preventDefault(); this.querySelector(\'output\').value = new FormData(this).get(\'body\')">',
                '  <ui-richtext name="body" label="Description" help="Paste from Word or a web page: only the structure stays." required rows="3"></ui-richtext>',
                '  <ui-button type="submit" variant="primary" class="mt-3">Submit</ui-button> <output class="ms-2 small"></output>',
                "</form>",
                '<ui-richtext class="mt-3" label="Read only" disabled rows="2" value="<p>Not editable.</p>"></ui-richtext>',
            ),
        },
        {
            "id": "texts",
            "title": "Texts",
            "intro": "The tools' names have attributes: <code>bold-label</code>, <code>italic-label</code>, "
            "<code>underline-label</code>, <code>strikethrough-label</code>, <code>bullets-label</code>, "
            "<code>numbers-label</code>, <code>quote-label</code>, <code>link-label</code>, <code>unlink-label</code>, "
            "<code>clear-label</code>, <code>toolbar-label</code> and <code>link-prompt</code>.",
            "html": lines('<ui-richtext rows="2" bold-label="Fett (Ctrl+B)" italic-label="Kursiv (Ctrl+I)" toolbar-label="Formatierung"',
                          '  link-prompt="Adresse des Links:"></ui-richtext>'),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines(
                'const editor = document.querySelector("ui-richtext");',
                'editor.addEventListener("change", () => save(editor.value));',
                'editor.value = "<p>New content</p>"; // taken as it is (the attribute and pastes are cleaned)',
                "console.log(editor.text); // plain text",
                "editor.focus();",
            ),
        },
    ],
    "tokens": {"host": "ui-richtext", "example_token": "--ui-richtext-toolbar-bg", "example_value": "transparent"},
    "elements": [
        {
            "tag": "ui-richtext",
            "attributes": [
                ("name / value", "string", "Form name and initial HTML (cleaned)."),
                ("label / help / placeholder", "string", "Texts."),
                ("rows", "number", "Height in lines (default 8)."),
                ("disabled / required", "boolean", "Form states (required: not empty)."),
                ("error", "string", "A message shown as invalid."),
                ("&lt;tool&gt;-label / toolbar-label / link-prompt", "string", "The texts (English defaults)."),
            ],
            "slots": [("(default)", "The editable area (created when missing; a <code>[contenteditable]</code> child is used).")],
            "parts": [("field / label / help / feedback", "The form field."), ("frame / toolbar / group / tool", "The editor.")],
            "events": [("input", "While typing (from the editable area)."), ("change", "On leaving it after a change.")],
            "methods": [("value", "Get / set the HTML."), ("text", "The plain text."), ("editor", "The editable element."),
                        ("focus() / checkValidity() / reportValidity()", "As usual.")],
        }
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["richtext"]
