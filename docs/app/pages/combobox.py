"""ui-combobox (Bootstrap 6 combobox, new in v6)."""

from __future__ import annotations

from .common import lines

COUNTRIES = [("us", "United States"), ("uk", "United Kingdom"), ("ch", "Switzerland"), ("de", "Germany"), ("fr", "France"),
             ("jp", "Japan"), ("br", "Brazil"), ("ca", "Canada")]
GLOBE = ('<svg class="menu-item-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" '
         'aria-hidden="true"><path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8m7.5-6.92A7 7 0 0 0 1.08 7.5h2.95c.06-1.47.3-2.86.7-4.07A7 7 0 0 1 7.5 1.08'
         'M8.5 1.08V7.5h2.95A12 12 0 0 0 8.5 1.08M1.08 8.5a7 7 0 0 0 6.42 6.42V8.5zm7.42 6.42A7 7 0 0 0 14.92 8.5H8.5z"/></svg>')


def options(items, indent: str = "  ", selected: str = "") -> list[str]:
    return [f'{indent}<ui-option value="{value}"{" selected" if value == selected else ""}>{label}</ui-option>' for value, label in items]


PAGE = {
    "title": "ui-combobox",
    "summary": "A select-like field whose options are your own markup — icons, descriptions, badges — with search, check "
    "marks and multiple selection. New in Bootstrap 6, on the menu plugin.",
    "submodule": "ui-combobox",
    "entry": "modules/bootstrap/ui-combobox/ui-combobox.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "One <code>&lt;ui-option value&gt;</code> per option; keyboard: <kbd>↓</kbd> / <kbd>↑</kbd>, <kbd>Home</kbd> / "
            "<kbd>End</kbd>, <kbd>Enter</kbd>, <kbd>Escape</kbd>.",
            "html": lines('<ui-combobox label="Combobox" placeholder="Select an item…" name="option">',
                          *options([("1", "Option one"), ("2", "Option two"), ("3", "Option three")]), "</ui-combobox>"),
        },
        {
            "id": "preselected",
            "title": "Pre-selected value",
            "intro": "<code>selected</code> on an option, or <code>value</code> on the combobox.",
            "html": lines('<ui-combobox label="Role" value="editor">', *options([("admin", "Administrator"), ("editor", "Editor"), ("viewer", "Viewer")]),
                          "</ui-combobox>"),
        },
        {
            "id": "custom-content",
            "title": "Icons, descriptions and check marks",
            "intro": "The option's content is yours (here an icon with <code>.menu-item-icon</code>); <code>description</code> adds "
            "a second line, <code>check</code> a check mark on the selected option, <code>label</code> the text shown in the field.",
            "html": lines(
                '<ui-combobox label="Priority" placeholder="Set priority…" check>',
                '  <ui-option value="low" description="No rush">Low</ui-option>',
                '  <ui-option value="medium" description="Normal priority" selected>Medium</ui-option>',
                '  <ui-option value="high" description="Needs attention">High</ui-option>',
                "</ui-combobox>",
                '<ui-combobox label="Language" placeholder="Choose a language…" class="mt-3">',
                f'  <ui-option value="en" label="English">{GLOBE} English</ui-option>',
                f'  <ui-option value="de" label="Deutsch">{GLOBE} Deutsch <ui-badge variant="success" class="ms-auto">Beta</ui-badge></ui-option>',
                "</ui-combobox>",
            ),
        },
        {
            "id": "search",
            "title": "Search",
            "intro": "<code>search</code> adds a field that filters the options by their text (<code>normalize</code> ignores "
            "accents: «zurich» finds «Zürich»).",
            "html": lines('<ui-combobox label="Country" placeholder="Select a country…" search normalize no-results-label="No country found">',
                          *options(COUNTRIES + [("zh", "Zürich (canton)")]), "</ui-combobox>"),
        },
        {
            "id": "groups",
            "title": "Groups",
            "intro": "<code>&lt;ui-option header&gt;</code> labels a group, <code>&lt;ui-option divider&gt;</code> draws a line.",
            "html": lines('<ui-combobox label="Language" placeholder="Select a language…">', "  <ui-option header>Frontend</ui-option>",
                          *options([("js", "JavaScript"), ("ts", "TypeScript")]), "  <ui-option divider></ui-option>",
                          "  <ui-option header>Backend</ui-option>", *options([("py", "Python"), ("go", "Go")]), "</ui-combobox>"),
        },
        {
            "id": "multiple",
            "title": "Multiple select",
            "intro": "<code>multiple</code>: options toggle and the menu stays open; the field shows the count "
            "(<code>count-label</code>); the form gets every value.",
            "html": lines(
                '<form onchange="this.querySelector(\'output\').value = new FormData(this).getAll(\'skills\').join(\', \')">',
                '  <ui-combobox name="skills" label="Skills" placeholder="Select skills…" multiple check value="css,js">',
                *options([("html", "HTML"), ("css", "CSS"), ("js", "JavaScript"), ("py", "Python")], "    "),
                "  </ui-combobox>",
                '  <p class="small mt-2 mb-0">Form values: <output>css, js</output></p>',
                "</form>",
            ),
        },
        {
            "id": "sizes",
            "title": "Sizes and disabled",
            "intro": "<code>size</code> <code>sm</code> or <code>lg</code>; <code>disabled</code> on the field or an option.",
            "html": lines('<ui-combobox size="sm" placeholder="Small select…" aria-label="Small">', *options([("a", "A")], "  "), "</ui-combobox>",
                          '<ui-combobox size="lg" placeholder="Large select…" aria-label="Large" class="mt-2">', *options([("a", "A")], "  "), "</ui-combobox>",
                          '<ui-combobox placeholder="Cannot interact…" disabled aria-label="Disabled" class="mt-2"></ui-combobox>',
                          '<ui-combobox placeholder="One option disabled" aria-label="Partly disabled" class="mt-2">',
                          '  <ui-option value="a">Available</ui-option>', '  <ui-option value="b" disabled>Unavailable</ui-option>', "</ui-combobox>"),
        },
        {
            "id": "plain-markup",
            "title": "Plain markup",
            "intro": "Bootstrap's own markup: a <code>[data-bs-toggle=\"combobox\"]</code> toggle and its <code>.menu</code>; "
            "<code>data-bs-name</code> creates a hidden input for the form.",
            "html": lines(
                '<button class="form-control combobox-toggle" type="button" data-bs-toggle="combobox" data-bs-name="plain" data-bs-placeholder="Plain markup…">',
                '  <span class="combobox-value">Plain markup…</span>',
                "</button>",
                '<div class="menu">',
                '  <button class="menu-item" type="button" data-bs-value="a">Alpha</button>',
                '  <button class="menu-item" type="button" data-bs-value="b">Beta</button>',
                "</div>",
            ),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines('const combobox = document.querySelector("ui-combobox");',
                            'combobox.addEventListener("ui-combobox:change", (event) => console.log(event.detail.value));',
                            'combobox.value = "2";', "combobox.show();"),
        },
    ],
    "tokens": {"host": "ui-combobox", "example_token": "--bs-menu-item-active-bg", "example_value": "var(--bs-success-bg)"},
    "elements": [
        {
            "tag": "ui-combobox",
            "attributes": [
                ("value", "string", "Initial value (several comma-separated)."),
                ("multiple", "boolean", "Several options; the form gets each value."),
                ("placeholder", "string", "Text while nothing is selected."),
                ("search / search-placeholder / no-results-label / normalize", "", "Search field, its texts, accent-insensitive."),
                ("check", "boolean", "Check marks on selected options."),
                ("placement", "string", "Menu placement (<code>bottom-start</code>)."),
                ("count-label", "string", "Field text for several (<code>{n} selected</code>)."),
                ("name / label / help / size / required / disabled / error", "", "Like the other form fields."),
            ],
            "slots": [("(options)", "<code>&lt;ui-option&gt;</code> children.")],
            "parts": [("field / label / help / feedback", "The form field."), ("control / value / caret", "The toggle."),
                      ("menu / item / check / search / no-results", "The menu.")],
            "events": [("ui-combobox:show / ui-combobox:hide", "Before; cancelable."), ("ui-combobox:shown / ui-combobox:hidden", "After."),
                       ("ui-combobox:change", "<code>detail.value</code>, <code>detail.item</code>."), ("input / change", "As usual.")],
            "methods": [("value / values", "Get / set (values: array)."), ("show() / hide() / toggle()", "The menu.")],
        },
        {
            "tag": "ui-option",
            "attributes": [("value", "string", "The value."), ("selected / disabled", "boolean", "States."),
                           ("description", "string", "Second line."), ("label", "string", "Text in the field (default: the content)."),
                           ("header / divider", "boolean", "A group heading / a line instead of an option.")],
            "slots": [("(default)", "The option's content.")],
        },
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["combobox"]
