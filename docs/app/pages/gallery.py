"""ui-gallery (thumbnail tiles with a lightbox; no Bootstrap counterpart)."""

from __future__ import annotations

from urllib.parse import quote

from .common import lines

COLOURS = ["#0d6efd", "#6f42c1", "#d63384", "#fd7e14", "#198754", "#20c997"]


def picture(text: str, colour: str, width: int = 800, height: int = 600) -> str:
    """A data URL of a coloured SVG picture (stands in for a photo)."""
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
           f"<rect width='100%' height='100%' fill='{colour}'/><text x='50%' y='50%' fill='white' font-family='sans-serif' "
           f"font-size='{height // 8}' text-anchor='middle' dominant-baseline='middle'>{text}</text></svg>")
    return "data:image/svg+xml," + quote(svg)


def items(count: int = 6, indent: str = "  ") -> list[str]:
    return [f'{indent}<ui-gallery-item src="{picture(f"Photo {n + 1}", COLOURS[n % len(COLOURS)])}" title="Photo {n + 1}" '
            f'description="Description of photo {n + 1}"></ui-gallery-item>' for n in range(count)]


PAGE = {
    "title": "ui-gallery",
    "summary": "Images and videos as thumbnail tiles; a click opens a lightbox with previous / next, keyboard and swipe. "
    "Not a Bootstrap component: built from Bootstrap's tokens and buttons, themed with its own variables.",
    "submodule": "ui-gallery",
    "entry": "modules/bootstrap/ui-gallery/ui-gallery.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "One <code>&lt;ui-gallery-item&gt;</code> per picture: <code>src</code> is what the lightbox shows, "
            "<code>thumb</code> the tile (default: <code>src</code>). In the lightbox: <kbd>←</kbd> / <kbd>→</kbd>, "
            "<kbd>Home</kbd> / <kbd>End</kbd>, swipe, <kbd>Escape</kbd>.",
            "html": lines("<ui-gallery>", *items(), "</ui-gallery>"),
        },
        {
            "id": "captions",
            "title": "Captions and tile size",
            "intro": "<code>captions</code> shows the titles; <code>--ui-gallery-tile-size</code>, "
            "<code>--ui-gallery-tile-aspect</code> and <code>--ui-gallery-gap</code> set the grid.",
            "html": lines('<ui-gallery captions style="--ui-gallery-tile-size: 10rem; --ui-gallery-tile-aspect: 4 / 3; --ui-gallery-gap: 1rem;">',
                          *items(4), "</ui-gallery>"),
        },
        {
            "id": "videos",
            "title": "Videos and missing thumbnails",
            "intro": "<code>kind=\"video\"</code> plays <code>src</code> in the lightbox and marks the tile; without a "
            "thumbnail the tile names the kind.",
            "html": lines(
                "<ui-gallery captions>",
                f'  <ui-gallery-item kind="video" src="clip.mp4" thumb="{picture("", "#212529")}" title="A video"></ui-gallery-item>',
                '  <ui-gallery-item kind="video" src="clip.mp4" title="Video without thumbnail"></ui-gallery-item>',
                f'  <ui-gallery-item src="{picture("Photo", "#198754")}" thumb="" title="Image without thumbnail"></ui-gallery-item>',
                "</ui-gallery>",
            ),
        },
        {
            "id": "editable",
            "title": "Editable and sortable",
            "intro": "<code>editable</code> adds an edit button (<code>ui-gallery:edit</code>); <code>sortable</code> lets "
            "tiles be dragged to another place (<code>ui-gallery:reorder</code>; the items are reordered).",
            "html": lines('<ui-gallery editable sortable captions>', *items(4), "</ui-gallery>"),
        },
        {
            "id": "data",
            "title": "Items from data",
            "intro": "The <code>items</code> property takes the items as objects (it wins over children once set); "
            "<code>empty</code> is shown without items.",
            "html": lines('<ui-gallery id="galleryData" empty="No pictures yet." captions></ui-gallery>',
                          '<ui-button size="sm" class="mt-2" onclick="loadGallery()">Load</ui-button>'),
            "script": lines(
                "function loadGallery() {",
                '  document.querySelector("#galleryData").items = [',
                f'    {{ id: 1, kind: "image", src: "{picture("A", "#0d6efd")[:40]}…", title: "A" }},',
                "    // …",
                "  ];",
                "}",
            ),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines(
                'const gallery = document.querySelector("ui-gallery");',
                'gallery.addEventListener("ui-gallery:open", (event) => console.log(event.detail.index));',
                'gallery.addEventListener("ui-gallery:reorder", (event) => save(event.detail.ids));',
                "gallery.show(0);",
                "gallery.next();",
                "gallery.close();",
            ),
        },
    ],
    "tokens": {"host": "ui-gallery", "example_token": "--ui-gallery-tile-size", "example_value": "12rem"},
    "elements": [
        {
            "tag": "ui-gallery",
            "attributes": [
                ("captions", "boolean", "Title under every tile."),
                ("editable", "boolean", "Edit buttons (tiles and lightbox)."),
                ("sortable", "boolean", "Drag tiles to reorder."),
                ("empty", "string", "Text without items."),
                ("open-label / edit-label / prev-label / next-label / close-label", "string",
                 "Texts (defaults English; <code>{title}</code> in open-label is the item's title)."),
                ("image-label / video-label / lightbox-label", "string", "Kind names and the lightbox's name."),
            ],
            "slots": [("(items)", "<code>&lt;ui-gallery-item&gt;</code> children (not rendered themselves).")],
            "parts": [("grid / item / tile / thumb / play / edit / caption / empty", "The tiles."),
                      ("lightbox / stage / media / bar / title / description / count / control", "The lightbox.")],
            "events": [("ui-gallery:open", "<code>detail.item</code>, <code>detail.index</code>."), ("ui-gallery:close", "Lightbox closed."),
                       ("ui-gallery:edit", "<code>detail.item</code>."), ("ui-gallery:reorder", "<code>detail.ids</code>, <code>detail.items</code>.")],
            "methods": [("show(index) / close() / next() / prev()", "The lightbox."), ("move(from, to)", "Reorder like dragging."),
                        ("items", "Get / set the items."), ("index", "Open item or -1.")],
        },
        {
            "tag": "ui-gallery-item",
            "attributes": [("src", "string", "Image or video URL."), ("thumb", "string", "Tile image (default: src; empty: none)."),
                           ("kind", "string", "<code>image</code> (default) or <code>video</code>."),
                           ("title / description", "string", "Texts."), ("item-id", "string", "Id in the events (default: id).")],
        },
    ],
}

PAGE["page_script"] = lines(
    "window.loadGallery = () => {",
    '  document.querySelector("#galleryData").items = ' + "[" + ", ".join(
        f'{{ id: {n}, kind: "image", src: "{picture(t, c)}", title: "{t}" }}'
        for n, (t, c) in enumerate([("A", "#0d6efd"), ("B", "#d63384"), ("C", "#198754")], 1)) + "];",
    "};",
)

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = {**CUSTOM["gallery"], "html": lines('<ui-gallery class="contact-sheet">', *items(8), "</ui-gallery>")}
