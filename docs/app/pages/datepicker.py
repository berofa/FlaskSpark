"""ui-datepicker (Bootstrap 6 datepicker, new in v6)."""

from __future__ import annotations

from .common import lines

CALENDAR_ICON = ('<svg slot="start" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" '
                 'aria-hidden="true"><path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 '
                 '2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5M1 4v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4z"/></svg>')

PAGE = {
    "title": "ui-datepicker",
    "summary": "A date field with a calendar popup, or an inline calendar — new in Bootstrap 6, built on Vanilla Calendar "
    "Pro (MIT, loaded on first use) and styled by Bootstrap. The form gets ISO dates.",
    "submodule": "ui-datepicker",
    "entry": "modules/bootstrap/ui-datepicker/ui-datepicker.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "The calendar opens when the field gets the focus; a click on a date takes it and closes it, as do "
            "<kbd>Escape</kbd>, a click outside or moving the focus away. The field shows the date in the browser's format, "
            "the form submits <code>YYYY-MM-DD</code>.",
            "html": lines('<ui-datepicker label="Datepicker" placeholder="Choose date…" help="The form gets 2026-06-10."></ui-datepicker>'),
        },
        {
            "id": "icon",
            "title": "With icon",
            "intro": "An icon in the <code>start</code> (or <code>end</code>) slot; the calendar is placed below the whole field.",
            "html": lines('<ui-datepicker label="Select date" placeholder="Choose date…">', f"  {CALENDAR_ICON}", "</ui-datepicker>"),
        },
        {
            "id": "min-max",
            "title": "Min and max dates",
            "html": lines('<ui-datepicker label="Event date (2026 only)" min="2026-01-01" max="2026-12-31" placeholder="Select a date in 2026"></ui-datepicker>'),
        },
        {
            "id": "modes",
            "title": "Multiple dates and ranges",
            "intro": "<code>mode=\"multiple\"</code> picks several dates, <code>mode=\"range\"</code> a start and an end (the "
            "popup closes after both); <code>months</code> shows months side by side; <code>value</code> preselects.",
            "html": lines(
                '<ui-datepicker label="Several dates" mode="multiple" placeholder="Select dates…"></ui-datepicker>',
                '<ui-datepicker label="Date range, two months" mode="range" months="2" value="2026-06-25,2026-07-08" class="mt-3"></ui-datepicker>',
            ),
        },
        {
            "id": "options",
            "title": "Locale, format, first weekday and placement",
            "intro": "<code>locale</code> (e.g. <code>de-CH</code>), <code>date-format</code> (Intl options as JSON or the "
            "<code>dateFormat</code> property), <code>first-weekday</code> (0 Sunday) and <code>placement</code> "
            "(<code>left</code>, <code>center</code>, <code>right</code>, <code>auto</code>).",
            "html": lines(
                '<ui-datepicker label="Swiss German, long format" locale="de-CH" value="2026-11-09"',
                '  date-format=\'{"weekday":"long","day":"numeric","month":"long","year":"numeric"}\'></ui-datepicker>',
                '<ui-datepicker label="Week starts on Sunday, right aligned" first-weekday="0" placement="right" class="mt-3"></ui-datepicker>',
            ),
        },
        {
            "id": "inline",
            "title": "Inline",
            "intro": "<code>inline</code> shows the calendar in the page; it is still a form field.",
            "html": lines(
                '<form onchange="this.querySelector(\'output\').value = new FormData(this).get(\'when\')">',
                '  <ui-datepicker inline name="when" mode="range" label="Travel dates"></ui-datepicker>',
                '  <p class="small mb-0">Form value: <output>–</output></p>',
                "</form>",
            ),
        },
        {
            "id": "dark",
            "title": "Dark mode",
            "intro": "The popup follows the colour mode around the element; <code>datepicker-theme</code> forces one for the popup only.",
            "html": lines(
                '<div data-bs-theme="dark" class="p-3 bg-body fg-body rounded-5">',
                '  <ui-datepicker label="Dark mode datepicker" placeholder="Select a date"></ui-datepicker>',
                "</div>",
                '<ui-datepicker label="Light field, dark calendar" datepicker-theme="dark" class="mt-3"></ui-datepicker>',
            ),
        },
        {
            "id": "plain-markup",
            "title": "Plain markup and button trigger",
            "intro": "Bootstrap's own markup: <code>data-bs-toggle=\"datepicker\"</code> on an input (opens on focus) or a "
            "button (shows the date in <code>[data-bs-datepicker-display]</code>), options as <code>data-bs-*</code>.",
            "html": lines(
                '<input type="text" class="form-control" data-bs-toggle="datepicker" autocomplete="off" placeholder="Plain input" aria-label="Date">',
                '<button type="button" class="btn-outline theme-secondary mt-3" data-bs-toggle="datepicker" data-bs-selection-mode="multiple-ranged">',
                '  <span data-bs-datepicker-display>Choose a range</span>',
                "</button>",
            ),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines(
                'const picker = document.querySelector("ui-datepicker");',
                'picker.addEventListener("ui-datepicker:change", (event) => console.log(event.detail.dates));',
                'picker.selectedDates = ["2026-12-24"];',
                "picker.dateFormat = (date, locale) => date.toLocaleDateString(locale, { month: \"short\", day: \"numeric\" });",
                "picker.vcpOptions = { disableWeekdays: [0, 6] }; // any Vanilla Calendar Pro option, before it renders",
                "picker.show();",
            ),
        },
    ],
    "tokens": {"host": "ui-datepicker", "example_token": "--bs-datepicker-day-selected-bg", "example_value": "var(--bs-success-bg)"},
    "elements": [
        {
            "tag": "ui-datepicker",
            "attributes": [
                ("value", "string", "ISO date(s), comma-separated."),
                ("mode", "string", "<code>single</code> (default), <code>multiple</code>, <code>range</code>."),
                ("months", "number", "Months side by side (1)."),
                ("min / max", "string", "ISO dates."),
                ("first-weekday", "number", "0 Sunday … 6 (default 1, Monday)."),
                ("locale", "string", "Language of the calendar and the dates (default: the browser's)."),
                ("placement", "string", "<code>left</code>, <code>center</code>, <code>right</code>, <code>auto</code>."),
                ("inline", "boolean", "Always visible, no field."),
                ("date-format", "string", "Intl.DateTimeFormat options as JSON."),
                ("datepicker-theme", "string", "<code>light</code>, <code>dark</code>, <code>auto</code> for the popup."),
                ("name / label / help / placeholder / required / disabled / error", "string", "Like the other form fields."),
            ],
            "slots": [("start / end", "Icons inside the field.")],
            "parts": [("field / label / help / feedback", "The form field."), ("control", "The text field."), ("calendar", "The calendar.")],
            "events": [("ui-datepicker:show / ui-datepicker:hide", "Before; cancelable."), ("ui-datepicker:shown / ui-datepicker:hidden", "After."),
                       ("ui-datepicker:change", "A date was picked: <code>detail.dates</code> (ISO)."), ("input / change", "As usual.")],
            "methods": [("selectedDates / value", "Get / set the ISO dates."), ("dateFormat / vcpOptions", "Formatting and library options."),
                        ("show() / hide() / toggle()", "The popup.")],
        }
    ],
    "notes": ["Vanilla Calendar Pro 3.4.0 (MIT) lives in <code>vendor/vanilla-calendar-pro</code> and is imported the first time a "
              "datepicker appears."],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["datepicker"]
