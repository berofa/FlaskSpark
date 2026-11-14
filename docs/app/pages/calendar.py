"""ui-calendar (module "calendar": FullCalendar on Bootstrap 6 tokens)."""

from __future__ import annotations

from .common import lines

DEMO_SOURCE = lines(
    "const day = (offset, time = \"\") => {",
    "  const d = new Date();",
    "  d.setDate(d.getDate() + offset);",
    "  return d.toISOString().slice(0, 10) + (time ? `T${time}` : \"\");",
    "};",
    "const events = async () => [",
    '  { id: "1", title: "Team meeting", start: day(0, "10:00"), end: day(0, "11:00"), subtitle: "Room 2" },',
    '  { id: "2", title: "Holidays", start: day(3), end: day(8), allDay: true, color: "#49A33B" },',
    '  { id: "3", title: "Done task", start: day(-2), allDay: true, display: "list-item", muted: true },',
    '  { id: "4", title: "Review", start: day(1, "14:00"), end: day(1, "15:30"), color: "#7e57c2", subtitle: "Online" },',
    "];",
)

PAGE = {
    "title": "ui-calendar",
    "summary": "Calendar views month, week, day and agenda, built on FullCalendar (MIT, loaded on first use) and themed "
    "with Bootstrap 6's tokens, so it follows the page theme and colour mode.",
    "module": "calendar",
    "submodule": "ui-calendar",
    "entry": "modules/calendar/ui-calendar/ui-calendar.js",
    "scripts": ["modules/calendar/calendar.js"],
    "sections": [
        {
            "id": "example",
            "title": "Events from a source",
            "stacked": True,
            "intro": "The page hands the calendar an async <code>source</code>; it is called for every range shown. "
            "<code>muted</code> strikes an event through (e.g. a done task), <code>display: \"list-item\"</code> shows it "
            "as a dot.",
            "html": lines('<ui-calendar id="calendarDemo" view="month" locale="en" style="--ui-calendar-height: 36rem"></ui-calendar>'),
            "script": lines("const calendar = document.querySelector(\"#calendarDemo\");", DEMO_SOURCE, "calendar.source = events;",
                            'calendar.addEventListener("ui-calendar:event-click", (event) => console.log(event.detail));'),
        },
        {
            "id": "soft",
            "title": "Week, soft events, editing",
            "stacked": True,
            "intro": "<code>soft</code> tints events in their colour with time and subtitle below the title; "
            "<code>editable</code> lets them be moved and resized (<code>ui-calendar:event-change</code>), "
            "<code>selectable</code> selects free ranges (<code>ui-calendar:select</code>).",
            "html": lines('<ui-calendar id="calendarWeek" view="week" locale="en" soft editable selectable scroll-time="8"',
                          '  style="--ui-calendar-height: 32rem"></ui-calendar>'),
        },
        {
            "id": "locale",
            "title": "Locale and first day of the week",
            "stacked": True,
            "intro": "<code>locale</code> takes a full language tag (default: the page's <code>&lt;html lang&gt;</code>): "
            "its language gives the texts, the whole tag the date formats and the first day of the week. "
            "<code>en-CH</code> and <code>en-GB</code> show the day before the month and start on Monday, "
            "<code>en-US</code> (or plain <code>en</code>) on Sunday. <code>first-day</code> sets it explicitly "
            "(<code>0</code> Sunday … <code>6</code> Saturday, or a weekday name).",
            "html": lines(
                '<ui-calendar id="calendarLocale" view="week" locale="en-CH" style="--ui-calendar-height: 22rem"></ui-calendar>',
                '<div class="mt-3">',
                '  <ui-calendar id="calendarSunday" view="month" locale="en-GB" first-day="sunday"',
                '    style="--ui-calendar-height: 26rem"></ui-calendar>',
                "</div>",
            ),
        },
        {
            "id": "own-toolbar",
            "title": "Own toolbar",
            "intro": "<code>toolbar=\"none\"</code> hides the built-in toolbar; navigate with the methods and show "
            "<code>title</code> (also in <code>ui-calendar:range</code>).",
            "html": lines(
                '<div class="d-flex gap-2 align-items-center mb-2">',
                '  <ui-button size="sm" onclick="calendarBare.prev()">‹</ui-button>',
                '  <ui-button size="sm" onclick="calendarBare.today()">Today</ui-button>',
                '  <ui-button size="sm" onclick="calendarBare.next()">›</ui-button>',
                '  <strong id="calendarBareTitle" class="ms-2"></strong>',
                "</div>",
                '<ui-calendar id="calendarBare" view="agenda" agenda-days="14" toolbar="none" locale="en" style="--ui-calendar-height: 20rem"></ui-calendar>',
            ),
        },
    ],
    "tokens": {"host": "ui-calendar", "example_token": "--ui-calendar-event-bg", "example_value": "#7e57c2"},
    "elements": [
        {
            "tag": "ui-calendar",
            "attributes": [
                ("view", "string", "<code>month</code> (default), <code>week</code>, <code>day</code> or <code>agenda</code>; follows the user's switching."),
                ("date", "string", "ISO date shown (default today); follows the user's navigation."),
                ("agenda-days", "number", "Days the agenda covers (default 30)."),
                ("scroll-time", "number", "Hour week and day start scrolled to (default 7)."),
                ("locale", "string", "Language tag, e.g. <code>en-CH</code> (default: the nearest <code>lang</code>, i.e. the page's, else <code>en</code>). "
                 "Its language gives the texts (bundled <code>de</code> and <code>en</code>, others in English), the full tag the date formats and the first day of the week."),
                ("first-day", "string", "First day of the week: <code>0</code> (Sunday) … <code>6</code> (Saturday) or a weekday name (<code>monday</code>); "
                 "default from the locale (Monday for <code>de</code>, <code>de-CH</code>, <code>en-GB</code>, <code>en-CH</code>; Sunday for <code>en</code>, <code>en-US</code>)."),
                ("month-label, week-label, day-label, agenda-label, today-label", "string", "The toolbar's texts (default in the calendar's language); a page sets its translations, e.g. <code>month-label=\"{{ _('Month') }}\"</code>."),
                ("toolbar", "string", "<code>none</code> hides the built-in toolbar."),
                ("selectable", "boolean", "Free ranges can be selected (<code>ui-calendar:select</code>)."),
                ("editable", "boolean", "Events can be moved and resized (<code>ui-calendar:event-change</code>)."),
                ("full-day", "boolean", "Week and day show all 24 hours without scrolling."),
                ("soft", "boolean", "Tinted events with time and subtitle; past events faded."),
            ],
            "events": [
                ("ui-calendar:range", "<code>{view, start, end, title}</code>."),
                ("ui-calendar:event-click", "<code>{id, data, start, end, allDay}</code>."),
                ("ui-calendar:date-click", "<code>{date, allDay}</code>."),
                ("ui-calendar:select", "<code>{start, end, allDay}</code> (end exclusive)."),
                ("ui-calendar:event-change", "<code>{id, data, start, end, allDay, oldStart, oldEnd, oldAllDay, revert()}</code>."),
            ],
            "methods": [
                ("source", "Async <code>({start, end}) =&gt; [event, …]</code>; an event: <code>{id, title, start, end?, allDay?, color?, "
                 "textColor?, display?, muted?, subtitle?, editable?, resizable?, data?}</code>."),
                ("refetch() / today() / prev() / next() / gotoDate(date) / unselect()", "Navigation and selection."),
                ("title", "The shown range as text."),
                ("localeTag / locale / firstDay", "The full language tag, the language of the texts and the first day of the week in use."),
            ],
            "parts": [("calendar", "The element FullCalendar renders into.")],
        }
    ],
}

PAGE["page_script"] = lines(
    DEMO_SOURCE,
    'for (const id of ["calendarDemo", "calendarWeek", "calendarBare", "calendarLocale", "calendarSunday", "calendarCustom"]) document.getElementById(id).source = events;',
    'const bare = document.getElementById("calendarBare");',
    "window.calendarBare = bare;",
    'bare.addEventListener("ui-calendar:range", (event) => { document.getElementById("calendarBareTitle").textContent = event.detail.title; });',
)

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["calendar"]
