"""ui-carousel (Bootstrap 6 carousel)."""

from __future__ import annotations

from .common import lines

GREYS = ["#777", "#666", "#555", "#4c4c4c", "#444", "#3c3c3c", "#333"]


def slide(text: str, background: str, height: int = 300, width: str = "100%", extra: str = "") -> str:
    """A placeholder slide like the ones in Bootstrap's docs."""
    return (f'<svg class="d-block w-100 rounded-5" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="{text}"{extra}><rect width="100%" height="100%" fill="{background}"/>'
            f'<text x="50%" y="50%" fill="#eee" dy=".3em" text-anchor="middle">{text}</text></svg>')


def items(texts: list[str], height: int = 300, indent: str = "  ", attributes: list[str] | None = None) -> list[str]:
    result = []
    for index, text in enumerate(texts):
        extra = (attributes or [""] * len(texts))[index]
        result.append(f"{indent}<ui-carousel-item{extra}>{slide(text, GREYS[index % len(GREYS)], height)}</ui-carousel-item>")
    return result


THREE = ["First slide", "Second slide", "Third slide"]

PAGE = {
    "title": "ui-carousel",
    "summary": "A slideshow on CSS scroll snap: sliding, swiping and momentum come from the browser; controls, "
    "indicators, autoplay and the ends from the component. Several slides at once, peek and variable widths are CSS.",
    "submodule": "ui-carousel",
    "entry": "modules/bootstrap/ui-carousel/ui-carousel.js",
    "sections": [
        {
            "id": "top-controls",
            "title": "Top controls",
            "intro": "<code>placement=\"top\"</code> puts the controls above the slides, next to the <code>heading</code> "
            "slot. <code>controls</code> renders previous / next buttons.",
            "html": lines('<ui-carousel controls placement="top">', '  <h5 slot="heading" class="mb-0">Top controls</h5>',
                          *items(THREE), "</ui-carousel>"),
        },
        {
            "id": "bottom-controls",
            "title": "Bottom controls and indicators",
            "intro": "The default placement is below the slides; <code>indicators</code> adds one button per slide.",
            "html": lines("<ui-carousel controls indicators>", *items(THREE), "</ui-carousel>"),
        },
        {
            "id": "custom-content",
            "title": "Custom content",
            "intro": "A slide holds any markup; size and style it with utilities or CSS.",
            "html": lines(
                '<ui-carousel controls style="--bs-carousel-control-icon-width: 1rem;">',
                '  <ui-carousel-item><div class="d-flex flex-column justify-content-center bg-subtle-primary p-5 rounded-5" style="min-height: 240px;">',
                '    <h3>Build anything</h3><p class="mb-3">Compose slides from your own markup.</p>',
                '    <div><a class="btn-solid theme-primary" href="#">Get started</a></div></div></ui-carousel-item>',
                '  <ui-carousel-item><div class="d-flex flex-column justify-content-center text-center bg-subtle-success p-5 rounded-5" style="min-height: 240px;">',
                '    <h3>Style it your way</h3><p class="mb-3">Utilities or custom CSS size each slide.</p>',
                '    <div><a class="btn-solid theme-success" href="#">Learn more</a></div></div></ui-carousel-item>',
                "</ui-carousel>",
            ),
        },
        {
            "id": "overlay",
            "title": "Overlay controls",
            "intro": "<code>placement=\"overlay\"</code> lays the controls and indicators over the bottom of the slides "
            "(<code>.carousel-overlay</code>).",
            "html": lines("<ui-carousel controls indicators placement=\"overlay\">", *items(THREE), "</ui-carousel>"),
        },
        {
            "id": "fade",
            "title": "Crossfade",
            "intro": "<code>fade</code> crossfades instead of sliding.",
            "html": lines("<ui-carousel controls fade>", *items(THREE), "</ui-carousel>"),
        },
        {
            "id": "multiple",
            "title": "Multiple items",
            "intro": "<code>--bs-carousel-items</code> sets the whole slides per view, <code>--bs-carousel-items-gap</code> "
            "the space between them. Seamless looping needs one slide per view; here the ends stop.",
            "html": lines('<ui-carousel controls ends="stop" style="--bs-carousel-items: 3; --bs-carousel-items-gap: 1rem;">',
                          *items([str(n) for n in range(1, 8)], 160), "</ui-carousel>"),
        },
        {
            "id": "peek",
            "title": "Peeking",
            "intro": "<code>--bs-carousel-items-peek</code> reveals a sliver of the neighbouring slides.",
            "html": lines('<ui-carousel controls ends="stop" style="--bs-carousel-items-peek: 3rem; --bs-carousel-items-gap: 1rem;">',
                          *items(["First slide", "Second slide", "Third slide", "Fourth slide", "Fifth slide"], 240), "</ui-carousel>"),
        },
        {
            "id": "variable-width",
            "title": "Variable width and centre",
            "intro": "<code>auto</code> lets each item keep its own width; <code>center</code> snaps the active slide to the "
            "centre instead of the start.",
            "html": lines(
                '<ui-carousel controls auto center ends="stop" style="--bs-carousel-items-gap: 1rem;">',
                *[f'  <ui-carousel-item style="width: {w}px;">{slide(t, GREYS[i], 160)}</ui-carousel-item>'
                  for i, (t, w) in enumerate(zip("ABCDEF", [160, 320, 220, 380, 200, 300]))],
                "</ui-carousel>",
            ),
        },
        {
            "id": "autoplay",
            "title": "Autoplay",
            "intro": "<code>autoplay</code> cycles on load (every <code>interval</code> ms, default 5000) and pauses on "
            "hover (<code>pause=\"false\"</code> keeps it going). Any interaction stops it for good. Avoid autoplay for "
            "accessibility, or offer <code>play-pause</code>; the active indicator fills over the interval.",
            "html": lines("<ui-carousel autoplay controls indicators play-pause>", *items(THREE), "</ui-carousel>"),
        },
        {
            "id": "intervals",
            "title": "Individual intervals",
            "intro": "<code>interval</code> on an item overrides the carousel's.",
            "html": lines("<ui-carousel autoplay indicators play-pause>",
                          *items(["First: 2 seconds", "Second: 4 seconds", "Third: 6 seconds"], 300, "  ",
                                 [' interval="2000"', ' interval="4000"', ' interval="6000"']),
                          "</ui-carousel>"),
        },
        {
            "id": "ends",
            "title": "End behaviour",
            "intro": "<code>ends</code>: <code>loop</code> (default) scrolls on seamlessly past the ends, <code>wrap</code> "
            "jumps back, <code>stop</code> stops and disables the end controls.",
            "html": lines(
                '<ui-carousel controls placement="top" ends="wrap"><h5 slot="heading" class="mb-0">Wrap</h5>',
                *items(THREE, 160), "</ui-carousel>",
                '<ui-carousel controls placement="top" ends="stop" class="mt-4"><h5 slot="heading" class="mb-0">Stop</h5>',
                *items(THREE, 160), "</ui-carousel>",
            ),
        },
        {
            "id": "dark",
            "title": "Dark carousel",
            "intro": "<code>data-bs-theme=\"dark\"</code> darkens the controls and indicators, useful for overlays on light slides.",
            "html": lines(
                '<ui-carousel controls indicators placement="overlay" data-bs-theme="dark">',
                *[f'  <ui-carousel-item>{slide(t, c, 300).replace("#eee", "#999")}</ui-carousel-item>'
                  for t, c in zip(THREE, ["#f5f5f5", "#eee", "#e5e5e5"])],
                "</ui-carousel>",
            ),
        },
        {
            "id": "plain-markup",
            "title": "Plain markup",
            "intro": "The data API also drives Bootstrap's own <code>.carousel</code> markup: <code>data-bs-slide</code>, "
            "<code>data-bs-slide-to</code>, <code>.carousel-control-play-pause</code>, <code>data-bs-autoplay</code>, "
            "<code>data-bs-ends</code>, <code>data-bs-interval</code>. External triggers may also target a "
            "<code>&lt;ui-carousel&gt;</code>.",
            "html": lines(
                '<div id="plainCarousel" class="carousel slide">',
                '  <div class="carousel-inner">',
                *[f'    <div class="carousel-item{" active" if i == 0 else ""}">{slide(t, GREYS[i], 200)}</div>' for i, t in enumerate(THREE)],
                "  </div>",
                '  <div class="d-flex justify-content-between align-items-center">',
                "    <div>",
                '      <button class="btn-icon btn-sm" type="button" data-bs-target="#plainCarousel" data-bs-slide="prev"><span class="carousel-icon-prev" aria-hidden="true"></span><span class="visually-hidden">Previous</span></button>',
                '      <button class="btn-icon btn-sm" type="button" data-bs-target="#plainCarousel" data-bs-slide="next"><span class="carousel-icon-next" aria-hidden="true"></span><span class="visually-hidden">Next</span></button>',
                "    </div>",
                '    <div class="carousel-indicators">',
                *[f'      <button type="button" data-bs-target="#plainCarousel" data-bs-slide-to="{i}"' + (' class="active" aria-current="true"' if i == 0 else "") + f' aria-label="Slide {i + 1}"></button>' for i in range(3)],
                "    </div>",
                "  </div>",
                "</div>",
            ),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines(
                'const carousel = document.querySelector("ui-carousel");',
                'carousel.addEventListener("ui-carousel:slide", (event) => {',
                "  if (event.detail.to === 2) event.preventDefault(); // cancelable",
                "});",
                'carousel.addEventListener("ui-carousel:slid", (event) => console.log(event.detail.from, "→", event.detail.to));',
                "carousel.next();",
                "carousel.to(0);",
                "carousel.cycle(); // autoplay now; pause() stops it",
            ),
        },
    ],
    "tokens": {"host": "ui-carousel", "example_token": "--bs-carousel-items-gap", "example_value": "1rem"},
    "elements": [
        {
            "tag": "ui-carousel",
            "attributes": [
                ("controls", "boolean", "Previous / next buttons."),
                ("indicators", "boolean", "One indicator button per slide."),
                ("play-pause", "boolean", "Play / pause button for the autoplay."),
                ("placement", "string", "<code>bottom</code> (default), <code>top</code> (with the heading slot) or <code>overlay</code>."),
                ("fade", "boolean", "Crossfade instead of sliding."),
                ("center", "boolean", "Snap the active slide to the centre."),
                ("auto", "boolean", "Variable width: items keep their own width."),
                ("autoplay", "boolean", "Cycle on load."),
                ("interval", "number", "Autoplay interval in ms (default 5000)."),
                ("ends", "string", "<code>loop</code> (default), <code>wrap</code> or <code>stop</code>."),
                ("keyboard", "string", "<code>false</code>: no arrow keys."),
                ("pause", "string", "<code>false</code>: no pause on hover."),
                ("prev-label / next-label / play-label / pause-label", "string", "Accessible names (default Previous, Next, Play, Pause)."),
                ("indicator-label", "string", "Accessible name of the indicators, <code>{n}</code> is the number (default <code>Slide {n}</code>)."),
            ],
            "slots": [("(items)", "<code>&lt;ui-carousel-item&gt;</code> children."), ("heading", "Heading of the top controls row.")],
            "parts": [("carousel", "The <code>.carousel</code>."), ("inner", "The scroll container."), ("item", "Each slide."),
                      ("controls", "The group of buttons."), ("control / prev / next / play-pause", "The buttons."),
                      ("indicators / indicator", "The indicators."), ("heading", "The heading box (top placement).")],
            "events": [("ui-carousel:slide", "Before a slide; cancelable. <code>detail</code>: from, to, direction, relatedTarget."),
                       ("ui-carousel:slid", "After the new slide settled (same detail).")],
            "methods": [("next() / prev() / to(index)", "Navigate (respecting <code>ends</code>)."),
                        ("cycle() / pause()", "Start or stop the autoplay timer."),
                        ("togglePlayPause()", "Like the play / pause button."),
                        ("nextWhenVisible()", "Next, only when the page and the carousel are visible."),
                        ("activeIndex / items", "Read only.")],
        },
        {
            "tag": "ui-carousel-item",
            "attributes": [("active", "boolean", "Start slide."), ("interval", "number", "Own autoplay interval in ms.")],
            "slots": [("(default)", "The slide content.")],
        },
    ],
    "notes": ["Nested carousels are not supported (like in Bootstrap). Under <code>prefers-reduced-motion</code> the "
              "slides jump and the loop falls back to wrap."],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["carousel"]
