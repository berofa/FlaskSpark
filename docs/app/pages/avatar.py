"""ui-avatar and ui-avatar-stack (Bootstrap 6 avatar, new in v6)."""

from __future__ import annotations

from urllib.parse import quote

from .common import THEMES, VARIANT_ATTRIBUTE, lines


def face(letter: str, colour: str) -> str:
    """A data URL of a coloured square with a letter (stands in for a photo)."""
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' fill='{colour}'/>"
           f"<circle cx='32' cy='25' r='12' fill='white' opacity='.85'/><rect x='12' y='42' width='40' height='26' rx='13' fill='white' opacity='.85'/></svg>")
    return "data:image/svg+xml," + quote(svg)


FACES = [face(*pair) for pair in (("A", "#6f42c1"), ("B", "#0d6efd"), ("C", "#198754"), ("D", "#fd7e14"), ("E", "#d63384"))]
SIZES = ["xs", "sm", "", "lg", "xl"]


def avatar(index: int = 0, extra: str = "") -> str:
    return f'<ui-avatar src="{FACES[index % len(FACES)]}" alt="User {index + 1}"{extra}></ui-avatar>'


PAGE = {
    "title": "ui-avatar",
    "summary": "Users or entities as an image or initials, with a status indicator, in sizes, and as overlapping stacks — "
    "new in Bootstrap 6.",
    "submodule": "ui-avatar",
    "entry": "modules/bootstrap/ui-avatar/ui-avatar.js",
    "sections": [
        {"id": "image", "title": "Image", "intro": "<code>src</code> and <code>alt</code>.", "html": lines(avatar(0))},
        {
            "id": "initials",
            "title": "Initials",
            "intro": "Text content as initials; <code>variant</code> colours them, <code>subtle</code> uses the light theme colour.",
            "html": lines("<ui-avatar>AB</ui-avatar>", *[f'<ui-avatar variant="{t}">{t[:2].upper()}</ui-avatar>' for t in THEMES],
                          "<br class=\"mb-2\">", *[f'<ui-avatar variant="{t}" subtle>{t[:2].upper()}</ui-avatar>' for t in THEMES]),
        },
        {
            "id": "sizes",
            "title": "Sizes",
            "intro": "<code>size</code> <code>xs</code>, <code>sm</code>, <code>lg</code>, <code>xl</code>, or "
            "<code>--bs-avatar-size</code> for any size.",
            "html": lines(*[avatar(i, f' size="{s}"' if s else "") for i, s in enumerate(SIZES)],
                          avatar(1, ' style="--bs-avatar-size: 6rem"')),
        },
        {
            "id": "status",
            "title": "Status indicator",
            "intro": "<code>status</code> <code>online</code> (green circle), <code>offline</code> (grey square), <code>busy</code> "
            "(red square), <code>away</code> (yellow circle); it is announced by its name (<code>status-label</code>). It scales "
            "with the size.",
            "html": lines(*[avatar(i, f' status="{s}"') for i, s in enumerate(("online", "offline", "busy", "away"))],
                          *[avatar(i, f' status="online" size="{s}"' if s else ' status="online"') for i, s in enumerate(SIZES)]),
        },
        {
            "id": "stack",
            "title": "Avatar stack",
            "intro": "<code>&lt;ui-avatar-stack&gt;</code> overlaps its avatars, the first on top; hover lifts one. <code>size</code> "
            "on the stack sizes every avatar; an initials avatar shows a count.",
            "html": lines(
                '<div class="vstack align-items-start gap-3">',
                *["  <ui-avatar-stack" + (f' size="{s}"' if s else "") + ">" + "".join(avatar(i) for i in range(4)) + "</ui-avatar-stack>" for s in ("sm", "", "xl")],
                '  <ui-avatar-stack size="lg">' + "".join(avatar(i) for i in range(3)) + '<ui-avatar variant="secondary">+5</ui-avatar></ui-avatar-stack>',
                "</div>",
            ),
        },
    ],
    "tokens": {"host": "ui-avatar", "example_token": "--bs-avatar-border-radius", "example_value": "var(--bs-radius-5)"},
    "elements": [
        {
            "tag": "ui-avatar",
            "attributes": [("src / alt", "string", "Image."), VARIANT_ATTRIBUTE, ("subtle", "boolean", "Light theme colour."),
                           ("size", "string", "<code>xs</code>, <code>sm</code>, <code>lg</code>, <code>xl</code>."),
                           ("status / status-label", "string", "<code>online</code>, <code>offline</code>, <code>busy</code>, <code>away</code>; its spoken name.")],
            "slots": [("(default)", "Initials (without <code>src</code>).")],
            "parts": [("avatar", "The avatar."), ("img", "The image."), ("status", "The status dot.")],
        },
        {
            "tag": "ui-avatar-stack",
            "attributes": [("size", "string", "Size of every avatar without its own.")],
            "slots": [("(default)", "<code>&lt;ui-avatar&gt;</code> children.")],
            "parts": [("stack", "The stack.")],
        },
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = {**CUSTOM["avatar"], "html": lines(f'<ui-avatar class="square-avatar" src="{FACES[2]}" alt="Square" status="online"></ui-avatar>',
                                                  '<ui-avatar class="square-avatar" variant="accent">SQ</ui-avatar>')}
