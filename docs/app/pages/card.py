"""ui-card and ui-card-group (Bootstrap 6 card)."""

from __future__ import annotations

from .common import THEMES, VARIANT_ATTRIBUTE, lines, placeholder

TEXT = "Some quick example text to build on the card title and make up the bulk of the card’s content."
LONG = ("This is a wider card with supporting text below as a natural lead-in to additional content. This content "
        "is a little bit longer.")
LIST = lines(
    '  <ui-list-group flush slot="list">',
    "    <ui-list-group-item>An item</ui-list-group-item>",
    "    <ui-list-group-item>A second item</ui-list-group-item>",
    "    <ui-list-group-item>A third item</ui-list-group-item>",
    "  </ui-list-group>",
)


def card(*content: str, attributes: str = "") -> str:
    return lines(f"<ui-card{attributes}>", *content, "</ui-card>")


def grid_cards(columns: str, cards: int = 4, extra: str = "", text: str = LONG) -> str:
    return lines(
        f'<div class="row {columns} g-4">',
        *(lines(
            '  <div class="col">',
            f'    <ui-card class="h-100"{extra}>',
            "      " + placeholder("Image cap", 140, "image-top"),
            '      <h4 class="card-title">Card title</h4>',
            f'      <p class="card-text">{text}</p>',
            "    </ui-card>",
            "  </div>",
        ) for _ in range(cards)),
        "</div>",
    )


PAGE = {
    "title": "ui-card",
    "summary": "A flexible content container: header, body and footer, image caps and overlays, horizontal cards, "
    "list groups, theme colours, subtle and translucent cards, and card groups.",
    "submodule": "ui-card",
    "entry": "modules/bootstrap/ui-card/ui-card.js",
    "sections": [
        {
            "id": "example",
            "title": "Example",
            "intro": "Each part is a slot and only rendered with content, so the dividers between the parts are "
            "Bootstrap's own. The default slot is the card body.",
            "html": card(
                "  " + placeholder("Image cap", 180, "image-top"),
                '  <h4 class="card-title">Card title</h4>',
                f'  <p class="card-text">{TEXT}</p>',
                '  <ui-button variant="primary" href="#">Go somewhere</ui-button>',
                attributes=' style="width: 18rem;"',
            ),
        },
        {
            "id": "body",
            "title": "Body",
            "intro": "The body is a column with a gap between its children.",
            "html": card("  This is some text within a card body."),
        },
        {
            "id": "titles",
            "title": "Titles, text, and links",
            "intro": "Bootstrap's <code>.card-title</code>, <code>.card-subtitle</code> (closer to the title) and "
            "<code>.card-text</code> classes work on the content.",
            "html": card(
                '  <h4 class="card-title">Card title</h4>',
                '  <h6 class="card-subtitle fg-3">Card subtitle</h6>',
                f'  <p class="card-text">{TEXT}</p>',
                '  <div class="d-flex gap-3"><a href="#">Card link</a> '
                '<a href="#">Another link</a></div>',
                attributes=' style="width: 18rem;"',
            ),
        },
        {
            "id": "images",
            "title": "Images",
            "intro": "<code>image-top</code> and <code>image-bottom</code> are image caps.",
            "html": card(
                "  " + placeholder("Image cap", 180, "image-top"),
                f'  <p class="card-text">{TEXT}</p>',
                attributes=' style="width: 18rem;"',
            ),
        },
        {
            "id": "list-groups",
            "title": "List groups",
            "intro": "A <code>&lt;ui-list-group flush&gt;</code> in the slot <code>list</code>, alone or with header "
            "and footer.",
            "html": lines(
                card(LIST, attributes=' style="width: 18rem;"'),
                card('  <span slot="header">Featured</span>', LIST, attributes=' style="width: 18rem;"'),
                card(LIST, '  <span slot="footer">Card footer</span>', attributes=' style="width: 18rem;"'),
            ),
            "preview_class": "d-flex flex-wrap gap-3 align-items-start",
        },
        {
            "id": "kitchen-sink",
            "title": "Kitchen sink",
            "html": card(
                "  " + placeholder("Image cap", 180, "image-top"),
                '  <h4 class="card-title">Card title</h4>',
                f'  <p class="card-text">{TEXT}</p>',
                LIST,
                '  <div slot="footer" class="d-flex gap-3"><a href="#">Card link</a> '
                '<a href="#">Another link</a></div>',
                attributes=' style="width: 18rem;"',
            ),
        },
        {
            "id": "header-footer",
            "title": "Header and footer",
            "intro": "Slots <code>header</code> and <code>footer</code>; a heading works as header, too. "
            "<code>align</code> centres or right-aligns the whole card.",
            "html": lines(
                card(
                    '  <span slot="header">Featured</span>',
                    '  <h4 class="card-title">Special title treatment</h4>',
                    '  <p class="card-text">With supporting text below as a natural lead-in to additional content.</p>',
                    '  <ui-button variant="primary" href="#">Go somewhere</ui-button>',
                ),
                card(
                    '  <h5 slot="header">Featured</h5>',
                    '  <h4 class="card-title">Special title treatment</h4>',
                    '  <p class="card-text">With supporting text below as a natural lead-in to additional content.</p>',
                ),
                card(
                    '  <span slot="header">Quote</span>',
                    "  <figure>",
                    '    <blockquote class="blockquote"><p>A well-known quote, contained in a blockquote element.</p></blockquote>',
                    '    <figcaption class="blockquote-footer">Someone famous in <cite title="Source Title">Source Title</cite></figcaption>',
                    "  </figure>",
                ),
                card(
                    '  <span slot="header">Featured</span>',
                    '  <h4 class="card-title">Special title treatment</h4>',
                    '  <p class="card-text">With supporting text below as a natural lead-in to additional content.</p>',
                    '  <ui-button variant="primary" href="#" class="mx-auto">Go somewhere</ui-button>',
                    '  <span slot="footer" class="fg-2">2 days ago</span>',
                    attributes=' align="center"',
                ),
            ),
            "preview_class": "d-grid gap-3",
        },
        {
            "id": "heading",
            "title": "Heading row with icon and actions",
            "intro": "<code>heading</code> writes the title into the header; <code>icon</code> puts an icon in front of it, "
            "by name from the page's icon sprite (<code>&lt;meta name=\"ui-icon-sprite\" content=\"…/bootstrap-icons.svg\"&gt;</code> "
            "or <code>setIconSprite(url)</code>), or any markup in the slot <code>icon</code>. The slot <code>actions</code> "
            "sits at the end of the row. The icon's colour is <code>--ui-card-icon-color</code>.",
            "html": card(
                '  <svg slot="icon" viewBox="0 0 16 16" width="1em" height="1em" fill="currentColor" aria-hidden="true">'
                '<path d="M0 0h1v15h15v1H0zm10 3.5a.5.5 0 0 1 .5-.5h4a.5.5 0 0 1 .5.5v4a.5.5 0 0 1-1 0V4.9l-3.613 4.417a.5.5 0 0 1-.74.037'
                'L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61L13.445 4H10.5a.5.5 0 0 1-.5-.5"/></svg>',
                '  <ui-button slot="actions" size="sm" variant="secondary" outline>Export</ui-button>',
                '  <p class="card-text">Revenue of the last 30 days.</p>',
                attributes=' heading="Revenue"',
            ),
        },
        {
            "id": "collapsible",
            "title": "Collapsible",
            "intro": "<code>collapsible</code> makes the header a button that folds the card away (a chevron at the end); "
            "<code>collapsed</code> starts folded. Each toggle fires <code>ui-card:toggle</code> with "
            "<code>{collapsed}</code>; <code>card.toggle()</code> does it by script.",
            "html": lines(
                card('  <p class="card-text">Details that are not always needed.</p>', attributes=' heading="Details" collapsible collapsed'),
                card('  <p class="card-text">Open at the start.</p>', attributes=' heading="Open" collapsible class="mt-3"'),
            ),
        },
        {
            "id": "width", "stacked": True,
            "title": "Width",
            "intro": "Cards fill their container; size them with the grid, width utilities or your own CSS.",
            "html": lines(
                '<div class="row">',
                '  <div class="sm:col-6 mb-3 sm:mb-0">',
                card('    <h4 class="card-title">Special title treatment</h4>',
                     '    <p class="card-text">With supporting text below as a natural lead-in to additional content.</p>'),
                "  </div>",
                '  <div class="sm:col-6">',
                card('    <h4 class="card-title">Special title treatment</h4>',
                     '    <p class="card-text">With supporting text below as a natural lead-in to additional content.</p>'),
                "  </div>",
                "</div>",
                card('  <h4 class="card-title">Card title</h4>', '  <p class="card-text">A card with w-75.</p>',
                     attributes=' class="w-75 mt-3"'),
                card('  <h4 class="card-title">Card title</h4>', '  <p class="card-text">A card with w-50.</p>',
                     attributes=' class="w-50 mt-3"'),
            ),
        },
        {
            "id": "navigation",
            "title": "Navigation",
            "intro": "Bootstrap's nav tabs or pills in the header (<code>.card-header-tabs</code>).",
            "html": card(
                '  <ul slot="header" class="nav nav-tabs card-header-tabs">',
                '    <li class="nav-item"><a class="nav-link active" aria-current="true" href="#">Active</a></li>',
                '    <li class="nav-item"><a class="nav-link" href="#">Link</a></li>',
                '    <li class="nav-item"><a class="nav-link disabled" aria-disabled="true">Disabled</a></li>',
                "  </ul>",
                '  <h4 class="card-title">Special title treatment</h4>',
                '  <p class="card-text">With supporting text below as a natural lead-in to additional content.</p>',
                '  <ui-button variant="primary" href="#" class="mx-auto">Go somewhere</ui-button>',
                attributes=' align="center"',
            ),
        },
        {
            "id": "image-caps",
            "title": "Image caps",
            "html": lines(
                card(
                    "  " + placeholder("Image cap", 180, "image-top"),
                    '  <h4 class="card-title">Card title</h4>',
                    f'  <p class="card-text">{LONG}</p>',
                    '  <p class="card-text"><small class="fg-2">Last updated 3 mins ago</small></p>',
                    attributes=' class="mb-3"',
                ),
                card(
                    '  <h4 class="card-title">Card title</h4>',
                    f'  <p class="card-text">{LONG}</p>',
                    '  <p class="card-text"><small class="fg-2">Last updated 3 mins ago</small></p>',
                    "  " + placeholder("Image cap", 180, "image-bottom"),
                ),
            ),
        },
        {
            "id": "image-overlays",
            "title": "Image overlays",
            "intro": "An image in the slot <code>image</code> as the background, the text in <code>overlay</code>. "
            "Content larger than the image overflows it.",
            "html": card(
                "  " + placeholder("Card image", 270, "image"),
                '  <div slot="overlay">',
                '    <h4 class="card-title">Card title</h4>',
                f'    <p class="card-text">{LONG}</p>',
                '    <p class="card-text"><small>Last updated 3 mins ago</small></p>',
                "  </div>",
                attributes=' variant="inverse"',
            ),
        },
        {
            "id": "card-row",
            "title": "Card row",
            "intro": "<code>row</code> makes a horizontal card; images go into <code>image-start</code> or "
            "<code>image-end</code>.",
            "html": lines(
                card(
                    "  " + placeholder("Image", 250, "image-start"),
                    '  <h4 class="card-title">Card title</h4>',
                    f'  <p class="card-text">{LONG}</p>',
                    '  <p class="card-text"><small class="fg-2">Last updated 3 mins ago</small></p>',
                    attributes=' row style="max-width: 540px;"',
                ),
                card(
                    '  <h4 class="card-title">Card title</h4>',
                    f'  <p class="card-text">{LONG}</p>',
                    '  <p class="card-text"><small class="fg-2">Last updated 3 mins ago</small></p>',
                    "  " + placeholder("Image", 250, "image-end"),
                    attributes=' row style="max-width: 540px;" class="mt-3"',
                ),
            ),
        },
        {
            "id": "theme-variants", "stacked": True,
            "title": "Theme variants",
            "intro": "<code>variant</code> colours border, header and footer.",
            "html": lines(*(card(f'  <span slot="header">{name.title()}</span>', '  <h4 class="card-title">Card title</h4>',
                                 '  <p class="card-text">Card text…</p>', attributes=f' variant="{name}"') for name in THEMES)),
            "preview_class": "docs-card-grid",
        },
        {
            "id": "subtle", "stacked": True,
            "title": "Subtle theme variants",
            "intro": "<code>subtle</code> uses the theme's subtle background and border colours instead.",
            "html": lines(*(card(f'  <span slot="header">{name.title()}</span>', '  <h4 class="card-title">Card title</h4>',
                                 '  <p class="card-text">Card text…</p>', attributes=f' variant="{name}" subtle')
                            for name in THEMES)),
            "preview_class": "docs-card-grid",
        },
        {
            "id": "translucent",
            "title": "Translucent cards",
            "intro": "<code>translucent</code> blurs and saturates what lies behind the card.",
            "html": lines(
                card('  <h4 class="card-title">Translucent card</h4>',
                     '  <p class="card-text">This card has a translucent background with a backdrop blur effect.</p>',
                     '  <ui-button variant="primary" href="#">Go somewhere</ui-button>',
                     attributes=' translucent style="width: 18rem;"'),
                card('  <span slot="header">Featured</span>', '  <h4 class="card-title">Card with header</h4>',
                     '  <p class="card-text">Headers and footers are also made translucent to maintain a consistent look.</p>',
                     '  <span slot="footer" class="fg-2">2 days ago</span>',
                     attributes=' translucent style="width: 18rem;"'),
            ),
            "preview_class": "d-flex flex-wrap gap-3 p-4 docs-translucent-backdrop",
        },
        {
            "id": "card-groups", "stacked": True,
            "title": "Card groups",
            "intro": "<code>&lt;ui-card-group&gt;</code> attaches the cards with equal width and height once the group "
            "is at least 576px wide (a container query); narrower, they stack.",
            "html": lines(
                "<ui-card-group>",
                *(lines(
                    "  <ui-card>",
                    "    " + placeholder("Image cap", 140, "image-top"),
                    '    <h4 class="card-title">Card title</h4>',
                    f'    <p class="card-text">{text}</p>',
                    '    <small slot="footer" class="fg-2">Last updated 3 mins ago</small>',
                    "  </ui-card>",
                ) for text in (LONG, "This card has supporting text below as a natural lead-in to additional content.",
                               LONG + " This card has even longer content than the first to show that equal height action.")),
                "</ui-card-group>",
            ),
        },
        {
            "id": "grid-cards", "stacked": True,
            "title": "Grid cards",
            "intro": "The grid's <code>row-cols-*</code> classes control the cards per row; <code>h-100</code> on the "
            "cards gives equal heights.",
            "html": lines(grid_cards("row-cols-1 md:row-cols-2"), grid_cards("row-cols-1 md:row-cols-3", 3)),
            "preview_class": "d-grid gap-4",
        },
    ],
    "elements": [
        {
            "tag": "ui-card",
            "attributes": [
                VARIANT_ATTRIBUTE,
                ("subtle", "boolean", "Subtle theme backgrounds and borders (<code>.card-subtle</code>)."),
                ("translucent", "boolean", "Blurred translucent background (<code>.card-translucent</code>)."),
                ("row", "boolean", "Horizontal card (<code>.card-row</code>)."),
                ("align", "string", "<code>start</code>, <code>center</code> or <code>end</code>."),
                ("shadow", "string", "Box shadow: empty for the default, or <code>xs</code>, <code>sm</code>, "
                 "<code>lg</code>, <code>xl</code>, <code>none</code>."),
                ("card-class", "string", "Further Bootstrap classes for the card."),
                ("body-class", "string", "Further Bootstrap classes for the body (e.g. <code>flex-row gap-4</code>)."),
                ("heading", "string", "A title in the header; the header becomes a row (icon, heading, actions)."),
                ("icon", "string", "An icon in front of the heading, by name from the page's icon sprite."),
                ("collapsible / collapsed", "boolean", "The header folds the card away / the card is folded."),
                ("toggle-label", "string", "Accessible name of the toggle without a heading (default <code>Toggle</code>)."),
            ],
            "events": [("ui-card:toggle", "Folded or unfolded; detail <code>{collapsed}</code>.")],
            "methods": [("toggle(force)", "Folds or unfolds the card (<code>true</code>: fold, <code>false</code>: unfold).")],
            "slots": [
                ("(default)", "The card body. Bootstrap 5 slots <code>eyebrow</code>, <code>title</code>, "
                 "<code>subtitle</code>, <code>text</code>, <code>link</code> also go into the body, in this order."),
                ("header / footer", "Header and footer (<code>.card-header</code>, <code>.card-footer</code>); with "
                 "<code>heading</code> the slot <code>header</code> follows the heading."),
                ("icon / actions", "The heading row's icon (any markup) and its end (buttons, a badge)."),
                ("image-top / image-bottom", "Image caps."),
                ("image-start / image-end", "Images of a <code>row</code> card."),
                ("image / overlay", "Background image and the content over it."),
                ("list", "A <code>&lt;ui-list-group flush&gt;</code>."),
            ],
            "parts": [
                ("card", "The <code>.card</code> element."),
                ("header, body, footer, list", "The rendered parts."),
                ("title, icon, heading, actions, toggle, chevron", "The heading row (toggle and chevron: collapsible)."),
                ("image-top, image-bottom, image-start, image-end, image, overlay", "The image wrappers and overlay."),
            ],
        },
        {
            "tag": "ui-card-group",
            "slots": [("(default)", "<code>&lt;ui-card&gt;</code> elements.")],
            "parts": [("group", "The flex container.")],
        },
    ],
    "tokens": {"host": "ui-card", "example_token": "--bs-card-border-radius", "example_value": "var(--bs-radius-3)"},
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["card"]
