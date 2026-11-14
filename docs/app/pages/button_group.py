"""ui-button-group (Bootstrap 6 button group)."""

from __future__ import annotations

from .common import lines


def group(buttons: list[str], attributes: str = ' label="Basic example"') -> str:
    return lines(f"<ui-button-group{attributes}>", *(f"  {button}" for button in buttons), "</ui-button-group>")


def buttons(variant: str, labels: tuple[str, ...] = ("Left", "Middle", "Right"), extra: str = "") -> list[str]:
    return [f'<ui-button variant="{variant}"{extra}>{label}</ui-button>' for label in labels]


def toggles(kind: str, name: str = "") -> list[str]:
    named = f' name="{name}"' if name else ""
    return [f'<ui-check type="{kind}"{named} button="outline" variant="primary"{" checked" if kind == "radio" and n == 1 else ""}>'
            f'{"Check" if kind == "checkbox" else "Radio"} {n}</ui-check>' for n in (1, 2, 3)]


PAGE = {
    "title": "ui-button-group",
    "summary": "A series of buttons on a single line or stacked in a column: dividers, theme and style variants, "
    "toggle buttons, toolbars, sizes and nesting.",
    "submodule": "ui-button-group",
    "entry": "modules/bootstrap/ui-button-group/ui-button-group.js",
    "sections": [
        {
            "id": "examples",
            "title": "Examples",
            "intro": "Give the group a <code>label</code> (it has <code>role=\"group\"</code>), so assistive technology "
            "announces the buttons as a group.",
            "html": group(buttons("primary")),
        },
        {
            "id": "links",
            "title": "With links",
            "intro": "Link buttons group the same way, as an alternative to a nav.",
            "html": group([
                '<ui-button variant="primary" href="#" active current="page">Active link</ui-button>',
                '<ui-button variant="primary" href="#">Link</ui-button>',
                '<ui-button variant="primary" href="#">Link</ui-button>',
            ], ' label="Links"'),
        },
        {
            "id": "dividers",
            "title": "Dividers",
            "intro": "<code>divider</code> draws a line between the buttons, best with solid buttons of one colour; "
            "also in vertical groups.",
            "html": lines(
                group(['<ui-button variant="primary">Left</ui-button>', '<ui-button variant="primary" active>Active</ui-button>',
                       '<ui-button variant="primary">Right</ui-button>'], ' divider label="Divided"'),
                group(buttons("secondary", ("Left", "Right")), ' divider label="Divided"'),
                group(['<ui-button variant="primary">Left</ui-button>', '<ui-button variant="primary" active>Active</ui-button>',
                       '<ui-button variant="primary">Right</ui-button>'], ' divider vertical label="Divided vertical"'),
                group(buttons("secondary", ("Left", "Right")), ' divider vertical label="Divided vertical"'),
            ),
            "preview_class": "d-flex flex-wrap align-items-start gap-2",
        },
        {
            "id": "theme-variants",
            "title": "Theme variants",
            "intro": "Any theme colour, also mixed within a group.",
            "html": lines(
                group(buttons("accent"), ' label="Accent theme example"'),
                group(['<ui-button variant="danger">Left</ui-button>', '<ui-button variant="warning">Middle</ui-button>',
                       '<ui-button variant="success">Right</ui-button>'], ' label="Mixed styles example"'),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "style-variants",
            "title": "Style variants",
            "intro": "Every button appearance works; dividers or the buttons' own borders separate them.",
            "html": lines(
                group(buttons("primary"), ' divider label="Solid example"'),
                group(buttons("primary", extra=' appearance="outline"'), ' label="Outlined example"'),
                group(buttons("primary", extra=' appearance="subtle"'), ' divider label="Subtle example"'),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "toggle-buttons",
            "title": "Toggle buttons",
            "intro": "Checkboxes and radios as buttons (<code>&lt;ui-check button&gt;</code>): any or all checkboxes, "
            "one radio at a time.",
            "html": lines(
                group(toggles("checkbox"), ' label="Basic checkbox toggle button group"'),
                group(toggles("radio", "btnradio"), ' label="Basic radio toggle button group"'),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "toolbar",
            "title": "Button toolbar",
            "intro": "Combine groups into a toolbar with Bootstrap's <code>.btn-toolbar</code>; input groups fit in, too.",
            "html": lines(
                '<div class="btn-toolbar" role="toolbar" aria-label="Toolbar with button groups">',
                group(buttons("primary", ("1", "2", "3", "4")), ' label="First group"'),
                group(buttons("secondary", ("5", "6", "7")), ' label="Second group"'),
                group(buttons("info", ("8",)), ' label="Third group"'),
                "</div>",
                '<div class="btn-toolbar justify-content-between mt-3" role="toolbar" aria-label="Toolbar with an input group">',
                group(buttons("secondary", ("1", "2", "3", "4"), ' appearance="outline"'), ' label="First group"'),
                '  <ui-input prefix="@" placeholder="Input group example" aria-label="Input group example"></ui-input>',
                "</div>",
            ),
        },
        {
            "id": "sizing",
            "title": "Sizing",
            "intro": "<code>size</code> on the group sizes every button (<code>lg</code>, <code>sm</code>, <code>xs</code>).",
            "html": lines(
                group(buttons("secondary", extra=' appearance="outline"'), ' size="lg" label="Large button group"'),
                group(buttons("secondary", extra=' appearance="outline"'), ' label="Default button group"'),
                group(buttons("secondary", extra=' appearance="outline"'), ' size="sm" label="Small button group"'),
                group(buttons("secondary", extra=' appearance="outline"'), ' size="xs" label="Extra small button group"'),
            ),
            "preview_class": "d-flex flex-column align-items-start gap-2",
        },
        {
            "id": "nesting",
            "title": "Nesting",
            "intro": "A group inside a group, e.g. for a menu next to buttons; its outer corners follow its place.",
            "html": group([
                '<ui-button variant="primary">1</ui-button>',
                '<ui-button variant="primary">2</ui-button>',
                '<ui-button-group label="Nested">',
                '    <ui-button variant="primary">3</ui-button>',
                '    <ui-button variant="primary">4</ui-button>',
                "  </ui-button-group>",
            ], ' label="Button group with nested group"'),
        },
        {
            "id": "vertical",
            "title": "Vertical variation",
            "intro": "<code>vertical</code> stacks the buttons.",
            "html": lines(
                group(['<ui-button variant="primary">Button</ui-button>'] * 6, ' vertical label="Vertical button group"'),
                group(toggles("radio", "vbtn-radio"), ' vertical label="Vertical radio toggle button group"'),
            ),
            "preview_class": "d-flex align-items-start gap-3",
        },
    ],
    "elements": [
        {
            "tag": "ui-button-group",
            "attributes": [
                ("vertical", "boolean", "Stacks the buttons (<code>.btn-group-vertical</code>)."),
                ("divider", "boolean", "A line between the buttons (<code>.btn-group-divider</code>)."),
                ("size", "string", "<code>xs</code>, <code>sm</code> or <code>lg</code> for every button."),
                ("label", "string", "Accessible name of the group."),
                ("role", "string", "<code>group</code> (default) or <code>toolbar</code>."),
            ],
            "slots": [("(default)", "<code>&lt;ui-button&gt;</code>, <code>&lt;ui-check button&gt;</code>, nested "
                       "<code>&lt;ui-button-group&gt;</code>, also inside a <code>&lt;ui-tooltip&gt;</code>.")],
            "parts": [("group", "The <code>.btn-group</code> element.")],
        }
    ],
    "notes": [
        "The members are separate shadow trees, so the group tells each one its place (attributes "
        "<code>grouped</code>, <code>group-first</code>, <code>group-last</code>, <code>group-divider</code>); the "
        "members style their corners, borders and divider from that.",
        "The button group has no CSS variables of its own; style the buttons with theirs (see <code>ui-button</code>).",
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["button_group"]
