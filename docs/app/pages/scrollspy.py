"""Scrollspy (Bootstrap 6 data API): the link of the section being read is active."""

from __future__ import annotations

from .common import lines

TEXT = ("This is some placeholder content for the scrollspy page. Note that as you scroll down the page, the appropriate "
        "navigation link is highlighted. It's repeated throughout the component example. We keep adding some more example "
        "copy here to emphasize the scrolling and highlighting.")


def sections(prefix: str, names: list[str], indent: str = "    ") -> list[str]:
    return [line for i, name in enumerate(names) for line in (f'{indent}<h4 id="{prefix}-{i + 1}">{name}</h4>', f"{indent}<p>{TEXT}</p>")]


ITEMS = ["First heading", "Second heading", "Third heading", "Fourth heading", "Fifth heading"]

PAGE = {
    "title": "Scrollspy (data API)",
    "summary": "Marks the link of the section being read as active while the page or a box scrolls — in a nav, list group, "
    "menu or any links. No element of its own.",
    "entry": "modules/bootstrap/scrollspy.js",
    "sections": [
        {
            "id": "nav",
            "title": "Nav",
            "stacked": True,
            "intro": "<code>data-bs-spy=\"scroll\"</code> and <code>data-bs-target</code> on the scrolling element (here a box with "
            "a height and <code>overflow-y: auto</code>; often <code>&lt;body&gt;</code>), <code>tabindex=\"0\"</code> for keyboard "
            "scrolling. A section is active once its top passed the activation line (<code>data-bs-top-margin</code>, default 12%); "
            "at the bottom the last one.",
            "html": lines(
                '<nav id="spyNav" class="nav nav-pills mb-3">',
                *[f'  <a class="nav-link" href="#spy-{i + 1}">{n.split()[0]}</a>' for i, n in enumerate(ITEMS)],
                "</nav>",
                '<div data-bs-spy="scroll" data-bs-target="#spyNav" data-bs-smooth-scroll="true" tabindex="0" class="p-3 rounded-5 bg-1" style="height: 220px; overflow-y: auto; position: relative">',
                *sections("spy", ITEMS),
                "</div>",
            ),
        },
        {
            "id": "nested",
            "title": "Nested nav and list group",
            "stacked": True,
            "intro": "Links in a nested nav activate their parents. A <code>&lt;ui-list-group&gt;</code> with <code>href</code> items "
            "works as well: they get <code>active</code>.",
            "html": lines(
                '<div class="d-flex gap-4">',
                '  <ui-list-group id="spyList" style="width: 12rem">',
                *[f'    <ui-list-group-item href="#spyl-{i + 1}">Item {i + 1}</ui-list-group-item>' for i in range(4)],
                "  </ui-list-group>",
                '  <div data-bs-spy="scroll" data-bs-target="#spyList" tabindex="0" class="flex-fill" style="height: 220px; overflow-y: auto; position: relative">',
                *sections("spyl", [f"Item {i + 1}" for i in range(4)], "    "),
                "  </div>",
                "</div>",
            ),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines(
                'import { ScrollSpyController, plainScrollSpy } from "…/modules/bootstrap/bootstrap.js";',
                'const spy = new ScrollSpyController(document.body, { target: "#toc", topMargin: "96px", smoothScroll: true });',
                'document.body.addEventListener("ui-scrollspy:activate", (event) => console.log(event.detail.relatedTarget));',
                "spy.refresh(); // after sections were added or shown",
            ),
        },
    ],
    "elements": [
        {
            "tag": "[data-bs-spy=\"scroll\"]",
            "attributes": [
                ("data-bs-target", "string", "The links' container (nav, list group, menu, any element)."),
                ("data-bs-top-margin", "string", "Activation line from the top: <code>12%</code> (default) or pixels (<code>96px</code>)."),
                ("data-bs-root-margin", "string", "IntersectionObserver rootMargin; wins over top-margin."),
                ("data-bs-threshold", "string", "IntersectionObserver thresholds (<code>0</code>)."),
                ("data-bs-smooth-scroll", "boolean", "A click on a link scrolls smoothly, then sets the hash and focus."),
            ],
            "events": [("ui-scrollspy:activate", "On the spied element: <code>detail.relatedTarget</code> is the link.")],
            "methods": [("ScrollSpyController / plainScrollSpy(element)", "Exported by the module: refresh(), dispose().")],
        }
    ],
}
