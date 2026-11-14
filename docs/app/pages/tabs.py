"""ui-tabs (Bootstrap 6 nav with the tab plugin)."""

from __future__ import annotations

from .common import lines


def tabs(attributes: str = "", panels: tuple[tuple[str, str], ...] = (("Home", "home"), ("Profile", "profile"), ("Contact", "contact")),
         extra: str = "") -> str:
    rows = [f"<ui-tabs{attributes}>"]
    for index, (heading, name) in enumerate(panels):
        disabled = " disabled" if name == "disabled" else ""
        rows.append(f'  <ui-tab-panel heading="{heading}" name="{name}"{disabled}>This is some placeholder content the '
                    f"<strong>{heading} tab’s</strong> associated content.</ui-tab-panel>")
    if extra:
        rows.append(extra)
    rows.append("</ui-tabs>")
    return lines(*rows)


WITH_DISABLED = (("Home", "home"), ("Profile", "profile"), ("Contact", "contact"), ("Disabled", "disabled"))

PAGE = {
    "title": "ui-tabs",
    "summary": "Tabbable panes: tabs, pills, underline or a list group, horizontal or vertical, in a card, with "
    "Bootstrap's fade, the WAI-ARIA keyboard pattern and remembered selection.",
    "submodule": "ui-tabs",
    "entry": "modules/bootstrap/ui-tabs/ui-tabs.js",
    "sections": [
        {
            "id": "tabs",
            "title": "Nav tabs",
            "intro": "One <code>&lt;ui-tab-panel heading&gt;</code> per tab. Arrow keys, Home and End switch tabs.",
            "html": tabs(panels=WITH_DISABLED),
        },
        {"id": "pills", "title": "Pills", "html": tabs(' variant="pills"', WITH_DISABLED)},
        {"id": "underline", "title": "Underline", "html": tabs(' variant="underline"')},
        {
            "id": "vertical",
            "title": "Vertical",
            "intro": "<code>vertical</code> puts the navigation in a column beside the panes.",
            "html": tabs(' variant="pills" vertical', (("Home", "home"), ("Profile", "profile"), ("Messages", "messages"), ("Settings", "settings"))),
        },
        {
            "id": "list-groups",
            "title": "List groups",
            "intro": "<code>variant=\"list\"</code>: a list group beside the panes.",
            "html": tabs(' variant="list"', (("Home", "home"), ("Profile", "profile"), ("Messages", "messages"), ("Settings", "settings"))),
        },
        {
            "id": "fill",
            "title": "Fill and justify",
            "html": lines(tabs(' variant="pills" fill'), tabs(' variant="pills" justified')),
            "preview_class": "d-grid gap-4",
        },
        {
            "id": "card",
            "title": "In a card, with actions",
            "intro": "<code>card</code> puts the tabs into a card header; the slot <code>actions</code> sits beside them.",
            "html": tabs(" card", extra='  <ui-button slot="actions" size="sm" appearance="outline" variant="secondary">Action</ui-button>'),
        },
        {
            "id": "instant",
            "title": "Without fade",
            "intro": "<code>instant</code> switches at once (<code>.tab-pane-instant</code>); the fade tokens tune it otherwise.",
            "html": tabs(" instant"),
        },
        {
            "id": "plain-markup",
            "title": "Plain markup",
            "intro": "Bootstrap's tab data API works on its own markup too: <code>data-bs-toggle=\"tab\"</code> "
            "(<code>pill</code>, <code>list</code>) with <code>data-bs-target</code> on a <code>.tab-pane</code>.",
            "html": lines(
                '<ul class="nav nav-tabs" role="tablist">',
                '  <li class="nav-item" role="presentation"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#plain-home" type="button" role="tab" aria-selected="true">Home</button></li>',
                '  <li class="nav-item" role="presentation"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#plain-profile" type="button" role="tab" aria-selected="false" tabindex="-1">Profile</button></li>',
                "</ul>",
                '<div class="tab-content pt-3">',
                '  <div class="tab-pane active show" id="plain-home" role="tabpanel">Home content.</div>',
                '  <div class="tab-pane" id="plain-profile" role="tabpanel">Profile content.</div>',
                "</div>",
            ),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines(
                'const tabs = document.querySelector("ui-tabs");',
                'tabs.addEventListener("ui-tabs:change", (event) => console.log(event.detail.name));',
                'tabs.show("profile");',
                "",
                "// plain markup: events on the toggles",
                'document.addEventListener("ui-tab:shown", (event) => console.log(event.target, event.detail.relatedTarget));',
            ),
        },
    ],
    "elements": [
        {
            "tag": "ui-tabs",
            "attributes": [
                ("variant", "string", "<code>tabs</code> (default), <code>pills</code>, <code>underline</code>, <code>list</code>."),
                ("vertical", "boolean", "Navigation in a column beside the panes."),
                ("fill / justified", "boolean", "<code>nav-fill</code> / <code>nav-justified</code>."),
                ("instant", "boolean", "No fade."),
                ("card", "boolean", "Tabs in a card header, panes in its body."),
                ("persist-key", "string", "Remembers the active tab in localStorage."),
                ("label", "string", "Accessible name of the tab list."),
            ],
            "slots": [("(panels)", "<code>&lt;ui-tab-panel&gt;</code> children."), ("actions", "Content beside the tabs.")],
            "parts": [("nav, tab, content, pane, actions", "Navigation, tabs, pane container, panes, actions."),
                      ("card, header, body", "With <code>card</code>.")],
            "events": [
                ("ui-tabs:show", "Before a switch; cancelable. <code>detail</code>: index, name, panel, previous."),
                ("ui-tabs:change / ui-tabs:shown", "After a switch, same detail."),
            ],
            "methods": [("show(indexOrName)", "Activates a tab."), ("panels / activeIndex", "Panels, index of the active one.")],
        },
        {
            "tag": "ui-tab-panel",
            "attributes": [
                ("heading", "string", "Label of its tab."),
                ("name", "string", "Stable id (persistence, events, <code>show()</code>)."),
                ("active / disabled", "boolean", "State."),
            ],
        },
    ],
    "tokens": {"host": "ui-tabs", "example_token": "--bs-nav-link-color", "example_value": "var(--bs-primary-fg)"},
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["tabs"]
