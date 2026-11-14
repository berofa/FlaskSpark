"""ui-dropzone (file drop area; no Bootstrap counterpart)."""

from __future__ import annotations

from .common import THEMES, lines

PAGE = {
    "title": "ui-dropzone",
    "summary": "An area to drop files on, pick them with the file dialog or paste them. It hands the files over, or works "
    "as a form field with a file list. Built on Bootstrap's form field and tokens.",
    "submodule": "ui-dropzone",
    "entry": "modules/bootstrap/ui-dropzone/ui-dropzone.js",
    "sections": [
        {
            "id": "example",
            "title": "Hand-over",
            "intro": "Without <code>name</code> the dropzone only hands the files over (<code>ui-dropzone:files</code>); the "
            "page uploads them. Click, <kbd>Enter</kbd> / <kbd>Space</kbd>, drop or paste.",
            "html": lines('<ui-dropzone id="dzHandOver" multiple accept="image/*" hint="Images only"></ui-dropzone>',
                          '<p class="mt-2 mb-0 small" id="dzHandOverLog">No files yet.</p>'),
            "script": lines('document.querySelector("#dzHandOver").addEventListener("ui-dropzone:files", (event) => {',
                            "  upload(event.detail.files);",
                            "});"),
        },
        {
            "id": "form-field",
            "title": "Form field",
            "intro": "With <code>name</code> the chosen files are listed (remove buttons) and submitted with the form; "
            "<code>label</code>, <code>help</code> and <code>required</code> like the other fields.",
            "html": lines(
                '<form onsubmit="event.preventDefault(); this.querySelector(\'output\').value = new FormData(this).getAll(\'attachments\').map((f) => f.name).join(\', \') || \'–\'">',
                '  <ui-dropzone name="attachments" label="Attachments" help="PDF or images, at most 3 files of 5 MB." multiple',
                '    max-files="3" max-size="5MB" accept=".pdf,image/*" required></ui-dropzone>',
                '  <ui-button type="submit" variant="primary" class="mt-3">Submit</ui-button> <output class="ms-2"></output>',
                "</form>",
            ),
        },
        {
            "id": "limits",
            "title": "Limits and messages",
            "intro": "<code>accept</code>, <code>max-size</code> and <code>max-files</code> reject files "
            "(<code>ui-dropzone:reject</code> with the reasons) and show a message; <code>type-message</code>, "
            "<code>size-message</code> and <code>count-message</code> change it (<code>{name}</code>, "
            "<code>{size}</code>, <code>{max}</code>).",
            "html": lines('<ui-dropzone name="small" max-size="100KB" size-message="{name} is {size}; at most {max}, please."',
                          '  text="Files up to 100 KB"></ui-dropzone>'),
        },
        {
            "id": "variants",
            "title": "Theme and custom content",
            "intro": "<code>variant</code> colours the drag-over state; the default slot replaces icon and text, the "
            "<code>icon</code> slot only the icon. <code>disabled</code> turns it off.",
            "html": lines(
                '<div class="vstack gap-3">',
                '  <ui-dropzone variant="success"><strong>Drop the report here</strong></ui-dropzone>',
                '  <ui-dropzone disabled text="Uploads are closed"></ui-dropzone>',
                "</div>",
            ),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines(
                'const zone = document.querySelector("ui-dropzone[name]");',
                'zone.addEventListener("ui-dropzone:reject", (event) => console.log(event.detail.rejected));',
                'zone.addEventListener("ui-dropzone:change", (event) => console.log(event.detail.files));',
                "zone.open();      // the file dialog",
                "zone.add(files);  // like a drop",
                "zone.remove(0);",
                "zone.clear();",
            ),
        },
    ],
    "tokens": {"host": "ui-dropzone", "example_token": "--ui-dropzone-border-style", "example_value": "solid"},
    "elements": [
        {
            "tag": "ui-dropzone",
            "attributes": [
                ("accept", "string", "Like <code>&lt;input type=\"file\" accept&gt;</code>; drops are filtered too."),
                ("multiple", "boolean", "More than one file."),
                ("max-files / max-size", "string", "Limits (size: <code>500KB</code>, <code>10MB</code> or bytes)."),
                ("variant", "string", "Theme colour of the drag-over state: " + ", ".join(f"<code>{t}</code>" for t in THEMES) + "."),
                ("name", "string", "Form field: lists and submits the files."),
                ("required / disabled", "boolean", "Form states."),
                ("label / text / hint / help", "string", "Texts (text default: <code>Drop files here or click to choose</code>)."),
                ("error", "string", "A message shown as invalid."),
                ("type-message / size-message / count-message", "string", "Messages of rejected files."),
                ("remove-label", "string", "Name of the remove buttons (default <code>Remove</code>)."),
            ],
            "slots": [("(default)", "Replaces icon, text and hint."), ("icon", "Replaces the icon.")],
            "parts": [("field / label / help / feedback", "The form field."), ("zone / icon / text / hint", "The area."),
                      ("list / file / file-name / file-size / remove", "The file list.")],
            "events": [("ui-dropzone:files", "Accepted files: <code>detail.files</code>."),
                       ("ui-dropzone:reject", "<code>detail.rejected</code>: <code>[{file, reason}]</code> (type, size, count)."),
                       ("ui-dropzone:change / change", "Form field: the chosen files changed.")],
            "methods": [("open()", "The file dialog."), ("add(files)", "Like a drop."), ("remove(index) / clear()", "Form field."),
                        ("files", "The chosen files (read only).")],
        }
    ],
}

PAGE["page_script"] = lines(
    'document.querySelector("#dzHandOver").addEventListener("ui-dropzone:files", (event) => {',
    '  document.querySelector("#dzHandOverLog").textContent = "Handed over: " + event.detail.files.map((f) => f.name).join(", ");',
    "});",
)

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["dropzone"]
