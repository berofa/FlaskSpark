"""ui-badge (Bootstrap 6 badge)."""

from __future__ import annotations

from .common import THEMES, VARIANT_ATTRIBUTE, lines

# Label colours as GitLab offers them (and two extremes: black and a very light one).
GITLAB_COLORS = (
    ("#428fdc", "Doing"),
    ("#6699cc", "Review"),
    ("#dc143c", "High"),
    ("#6944d3", "Feature"),
    ("#009966", "Done"),
    ("#000000", "Blocked"),
    ("#ffecdb", "Backend"),
    ("#f9b71b", "Waiting"),
)

PAGE = {
    "title": "ui-badge",
    "summary": "Small components for indicating status and counts, or labelling items. Badges scale with the font "
    "size of their parent and come solid (default), subtle or outlined, in a theme colour or a free colour, and "
    "split into scope and value like GitLab's scoped labels.",
    "submodule": "ui-badge",
    "entry": "modules/bootstrap/ui-badge/ui-badge.js",
    "sections": [
        {
            "id": "examples",
            "title": "Examples",
            "intro": "<code>appearance</code>: <code>solid</code> (default), <code>subtle</code> or <code>outline</code>.",
            "html": lines(
                '<ui-badge variant="primary">New</ui-badge>',
                '<ui-badge variant="primary" appearance="subtle">New</ui-badge>',
                '<ui-badge variant="primary" appearance="outline">New</ui-badge>',
            ),
            "preview_class": "d-flex gap-2 align-items-center",
        },
        {
            "id": "headings",
            "title": "Headings",
            "intro": "Badges adapt to the font size of the parent element.",
            "html": lines(*(f"<h{level}>Example heading <ui-badge>New</ui-badge></h{level}>" for level in range(1, 7))),
        },
        {
            "id": "buttons",
            "title": "Buttons",
            "intro": "As a counter in a button. Make sure the context is clear to screen reader users (e.g. with a "
            "visually hidden text).",
            "html": '<ui-button variant="primary">\n  Notifications <ui-badge variant="danger">4</ui-badge>\n</ui-button>',
        },
        {
            "id": "positioned",
            "title": "Positioned",
            "intro": "Utilities on <code>&lt;ui-badge&gt;</code> position the element itself; "
            "<code>badge-class</code> adds classes to the badge inside (here a border in the background colour). "
            "Without a count, a plain <code>&lt;span&gt;</code> with utilities makes a generic indicator.",
            "html": lines(
                '<ui-button variant="primary" class="position-relative">',
                "  Inbox",
                '  <ui-badge variant="danger" pill badge-class="border border-bg" '
                'class="position-absolute top-0 start-100 translate-middle">',
                '    99+ <span class="visually-hidden">unread messages</span>',
                "  </ui-badge>",
                "</ui-button>",
                '<ui-button variant="primary" class="position-relative">',
                "  Profile",
                '  <span class="position-absolute top-0 start-100 translate-middle p-2 bg-danger border border-bg rounded-circle">',
                '    <span class="visually-hidden">New alerts</span>',
                "  </span>",
                "</ui-button>",
            ),
            "preview_class": "d-flex gap-5 pt-2",
        },
        {
            "id": "variants",
            "title": "Variants",
            "intro": "Every theme colour, in all three appearances. Don't rely on colour alone to convey meaning.",
            "html": lines(
                *(f'<ui-badge variant="{name}">{name.title()}</ui-badge>' for name in THEMES),
                *(f'<ui-badge variant="{name}" appearance="subtle">{name.title()}</ui-badge>' for name in THEMES),
                *(f'<ui-badge variant="{name}" appearance="outline">{name.title()}</ui-badge>' for name in THEMES),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "pill",
            "title": "Pill badges",
            "intro": "<code>pill</code> rounds the badge fully.",
            "html": lines(*(f'<ui-badge variant="{name}" pill>{name.title()}</ui-badge>' for name in THEMES)),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "color",
            "title": "Free colour",
            "intro": "<code>color</code> takes any CSS colour (e.g. a label's colour from GitLab) and wins over "
            "<code>variant</code>. Solid badges get white or dark text, whichever contrasts more (WCAG luminance, "
            "computed by the component). Subtle and outline badges write in the colour, darkened in light mode and "
            "lightened in dark mode as far as the page needs (very light or very dark colours stay readable).",
            "html": lines(
                *(f'<ui-badge color="{c}">{n}</ui-badge>' for c, n in GITLAB_COLORS),
                *(f'<ui-badge color="{c}" appearance="subtle">{n}</ui-badge>' for c, n in GITLAB_COLORS),
                *(f'<ui-badge color="{c}" appearance="outline">{n}</ui-badge>' for c, n in GITLAB_COLORS),
            ),
            "preview_class": "d-flex flex-wrap gap-2",
        },
        {
            "id": "scoped",
            "title": "Scoped (split)",
            "intro": "<code>scope</code> splits the badge like a scoped label in GitLab (<code>status::triage</code>): "
            "the scope on the left filled with the colour, the value (the content) on the right on the page's "
            "background, framed and written in the colour. Both halves are one badge: same height, one frame, "
            "radii only outside; <code>pill</code> works. Screen readers hear «Status: Triage» (a visually hidden "
            "colon). Without <code>color</code> the scope takes the <code>variant</code>'s theme colour, else a "
            "neutral one.",
            "html": lines(
                *(f'<ui-badge scope="{scope}" color="{c}">{n}</ui-badge>' for (c, n), scope in zip(
                    GITLAB_COLORS, ("Status", "Status", "Priority", "Type", "Workflow", "Status", "Team", "Status"))),
                '<ui-badge scope="Status" color="#428fdc" pill>Doing</ui-badge>',
                '<ui-badge scope="Release" variant="success">v1.4.0</ui-badge>',
                '<ui-badge scope="Release" variant="warning" pill>v1.5.0</ui-badge>',
                '<ui-badge scope="Area">Docs</ui-badge>',
            ),
            "preview_class": "d-flex flex-wrap gap-2 align-items-center",
        },
        {
            "id": "scoped-size",
            "title": "Scoped badges in text",
            "intro": "Like every badge it scales with its parent; a link (<code>href</code>) keeps the split.",
            "html": lines(
                '<h4>Issue #42 <ui-badge scope="Priority" color="#dc143c">High</ui-badge></h4>',
                '<p class="mb-0">Moved to <ui-badge scope="Status" color="#6699cc" href="#">Review</ui-badge> '
                'by Anna.</p>',
            ),
        },
        {
            "id": "links",
            "title": "Links",
            "intro": "With <code>href</code> the badge is a link.",
            "html": '<ui-badge variant="primary" href="#">Primary link</ui-badge>\n'
            '<ui-badge variant="secondary" appearance="subtle" href="#">Secondary link</ui-badge>',
            "preview_class": "d-flex gap-2",
        },
    ],
    "elements": [
        {
            "tag": "ui-badge",
            "attributes": [
                VARIANT_ATTRIBUTE,
                ("appearance", "string", "<code>solid</code> (default), <code>subtle</code> or <code>outline</code>."),
                ("pill", "boolean", "Fully rounded (<code>rounded-pill</code>)."),
                ("href", "url", "Renders the badge as a link (with <code>target</code>, <code>rel</code>)."),
                ("badge-class", "string", "Further Bootstrap classes for the badge inside (utilities); classes on "
                 "the element itself style the host."),
                ("color", "string", "A free CSS colour (hex, rgb(), oklch(), var(), …); wins over "
                 "<code>variant</code>. The text on the fill is white or dark by WCAG contrast; text and lines in "
                 "the colour are darkened (light mode) or lightened (dark mode) as far as needed."),
                ("scope", "string", "Splits the badge: the scope filled on the left, the content on the right on "
                 "the page's background, framed in the colour (like GitLab's scoped labels). "
                 "<code>appearance</code> does not apply."),
            ],
            "slots": [("(default)", "The content (with <code>scope</code>: the value). Without content the badge is "
                       "hidden.")],
            "parts": [
                ("badge", "The <code>.badge</code> element (span or link)."),
                ("scope", "With <code>scope</code>: the filled left half."),
                ("value", "With <code>scope</code>: the right half (the content)."),
            ],
        }
    ],
    "tokens": {"host": "ui-badge", "example_token": "--bs-badge-font-weight", "example_value": "400"},
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["badge"]
