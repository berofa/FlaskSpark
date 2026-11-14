"""ui-pagination (Bootstrap 6 pagination)."""

from __future__ import annotations

from .common import THEMES, VARIANT_ATTRIBUTE, lines

PAGE = {
    "title": "ui-pagination",
    "summary": "Page links for a series of pages: the current one active, previous / next, gaps when there are many pages.",
    "submodule": "ui-pagination",
    "entry": "modules/bootstrap/ui-pagination/ui-pagination.js",
    "sections": [
        {
            "id": "overview",
            "title": "Overview",
            "intro": "<code>total</code> pages, <code>current</code> one. With <code>href</code> (a pattern with <code>{page}</code>) the "
            "entries are links; without it buttons, and <code>ui-pagination:change</code> tells the page.",
            "html": lines('<ui-pagination total="3" current="2" label="Page navigation example"></ui-pagination>',
                          '<ui-pagination total="3" current="1" href="?page={page}" label="With links" class="mt-3"></ui-pagination>'),
        },
        {
            "id": "icons",
            "title": "Working with icons",
            "intro": "<code>arrows=\"icons\"</code> shows « and » (named by <code>prev-label</code> / <code>next-label</code>); "
            "<code>arrows=\"none\"</code> drops them.",
            "html": lines('<ui-pagination total="3" current="1" arrows="icons"></ui-pagination>', '<ui-pagination total="3" current="3" arrows="none" class="mt-3"></ui-pagination>'),
        },
        {
            "id": "many",
            "title": "Many pages",
            "intro": "More pages than <code>max</code> entries (7) are shortened with gaps around the current page. Click through:",
            "html": lines('<ui-pagination total="20" current="10"></ui-pagination>', '<ui-pagination total="50" current="1" max="9" class="mt-3"></ui-pagination>'),
        },
        {
            "id": "disabled",
            "title": "Active and disabled",
            "intro": "The current page is <code>.active</code> with <code>aria-current=\"page\"</code>; previous on the first and next on "
            "the last page are disabled.",
            "html": lines('<ui-pagination total="5" current="1"></ui-pagination>'),
        },
        {
            "id": "variants",
            "title": "Variants",
            "intro": "<code>variant</code> themes the component, hover, focus and the active page.",
            "html": lines('<div class="vstack gap-2">', *[f'  <ui-pagination total="3" current="2" variant="{t}"></ui-pagination>' for t in THEMES[:5]], "</div>"),
        },
        {
            "id": "sizing",
            "title": "Sizing",
            "html": lines('<ui-pagination total="3" current="1" size="lg" arrows="none"></ui-pagination>',
                          '<ui-pagination total="3" current="1" arrows="none" class="mt-2"></ui-pagination>',
                          '<ui-pagination total="3" current="1" size="sm" arrows="none" class="mt-2"></ui-pagination>'),
        },
        {
            "id": "alignment",
            "title": "Alignment",
            "html": lines('<ui-pagination total="3" current="1" align="center"></ui-pagination>',
                          '<ui-pagination total="3" current="1" align="end" class="mt-2"></ui-pagination>'),
        },
        {
            "id": "plain-markup",
            "title": "Plain markup",
            "intro": "Bootstrap's own <code>.pagination</code> markup is styled by the page CSS.",
            "html": lines('<nav aria-label="Plain"><ul class="pagination">', '  <li class="page-item disabled"><span class="page-link">Previous</span></li>',
                          '  <li class="page-item active"><a class="page-link" href="#" aria-current="page">1</a></li>',
                          '  <li class="page-item"><a class="page-link" href="#">2</a></li>', '  <li class="page-item"><a class="page-link" href="#">Next</a></li>',
                          "</ul></nav>"),
        },
        {
            "id": "javascript",
            "title": "JavaScript",
            "script": lines('const pagination = document.querySelector("ui-pagination");',
                            'pagination.addEventListener("ui-pagination:change", (event) => load(event.detail.page)); // preventDefault() keeps the page',
                            "pagination.current = 4;"),
        },
    ],
    "tokens": {"host": "ui-pagination", "example_token": "--bs-pagination-border-radius", "example_value": "var(--bs-radius-pill)"},
    "elements": [
        {
            "tag": "ui-pagination",
            "attributes": [
                ("total / current", "number", "Number of pages and the current one (1)."),
                ("max", "number", "Entries for the page numbers including gaps (7, at least 5)."),
                ("href", "string", "Link pattern with <code>{page}</code>; without it buttons."),
                ("size", "string", "<code>sm</code> or <code>lg</code>."), VARIANT_ATTRIBUTE,
                ("align", "string", "<code>start</code>, <code>center</code>, <code>end</code>."),
                ("arrows", "string", "<code>icons</code> (« ») or <code>none</code>."),
                ("prev-label / next-label / label", "string", "Texts (Previous, Next, Pagination)."),
            ],
            "parts": [("nav", "The nav."), ("list", "The list."), ("item", "An entry."), ("link", "A link or button.")],
            "events": [("ui-pagination:change", "<code>detail.page</code>; cancelable.")],
            "methods": [("current", "Get / set the current page.")],
        }
    ],
}

from .custom import CUSTOM  # noqa: E402

PAGE["custom"] = CUSTOM["pagination"]
