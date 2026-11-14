"""The overview page: what the components are, what they bring, what the page provides, how to style them."""

from __future__ import annotations

from .common import lines


def table(head: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    """A small Bootstrap table for the prose sections (cells are HTML)."""
    head_html = "".join(f'<th scope="col">{cell}</th>' for cell in head)
    rows_html = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return (f'<div class="table-responsive mt-3"><table class="table align-top docs-token-table"><thead><tr>{head_html}</tr></thead>'
            f"<tbody>{rows_html}</tbody></table></div>")


PAGE = {
    "title": "webcomponents",
    "summary": "Bootstrap 6 as custom elements: every component renders Bootstrap's own markup in a shadow tree and brings its "
    "CSS and behaviour along, so a page only writes <ui-button variant=\"primary\">. Styled through CSS variables.",
    "css": lines(
        ".brand-theme {",
        "  --bs-primary-bg: #6f42c1;",
        "  --bs-primary-bg-subtle: #efe7fa;",
        "  --bs-primary-fg: #59359a;",
        "  --bs-primary-border: #c9b3ec;",
        "}",
        ".rounded-buttons {",
        "  --bs-btn-border-radius: var(--bs-radius-pill);",
        "}",
        ".lifted::part(button) {",
        "  box-shadow: 0 .5rem 1rem rgb(0 0 0 / .15);",
        "  transform: translateY(-1px);",
        "}",
    ),
    "sections": [
        {
            "id": "quick-start",
            "title": "Quick start",
            "intro": "Load Bootstrap 6's CSS on the page (the design tokens and Bootstrap for your own markup) and the "
            "module script; then use the elements. With FlaskSpark, <code>VENDOR_INCLUDE_WEBCOMPONENTS = True</code> does both "
            "in <code>layouts/framework.html</code>.",
            "script": lines(
                '<link rel="stylesheet" href="/webcomponents/vendor/bootstrap6/css/bootstrap.min.css">',
                '<script type="module" src="/webcomponents/modules/bootstrap/bootstrap.js"></script>',
                "",
                '<ui-button variant="primary">Save</ui-button>',
                '<ui-alert variant="success" dismissible><p>Saved.</p></ui-alert>',
            ),
            "script_language": "HTML",
        },
        {
            "id": "shadow-dom",
            "title": "How a component is built",
            "intro": "An element like <code>&lt;ui-button&gt;</code> is the <strong>host</strong> in your page (light DOM). It "
            "renders Bootstrap's markup — <code>&lt;button class=\"btn-solid theme-primary\"&gt;</code> — into its own "
            "<strong>shadow root</strong>. Your content (the label, a card's body, an alert's text) stays in your page and is "
            "shown through a <code>&lt;slot&gt;</code> inside. The shadow root is encapsulated: page CSS does not reach the "
            "markup inside, and the component's CSS does not leak out." + table(
                ("Part", "Lives in", "Styled by"),
                [
                    ("<code>&lt;ui-button&gt;</code> (host)", "your page", "your CSS (box, margins, display) and the component's <code>:host</code> rules"),
                    ("<code>&lt;button class=\"btn …\"&gt;</code>", "the shadow root", "Bootstrap's CSS inside the shadow root, CSS variables, <code>::part()</code>"),
                    ("your content (slotted)", "your page", "your CSS and Bootstrap's classes of the page (utilities, typography)"),
                ],
            ),
            "html": lines('<ui-button variant="primary">I am slotted text in a shadow-DOM button</ui-button>'),
        },
        {
            "id": "included",
            "title": "What a component brings along",
            "intro": "Nothing to include per component: loading the module (or one component's script) brings everything it "
            "needs. Each stylesheet is fetched once and shared by all shadow roots (constructable stylesheets)." + table(
                ("Included automatically", "What it is"),
                [
                    ("Bootstrap 6 CSS", "The whole <code>bootstrap.min.css</code> in every shadow root, as one shared sheet: Bootstrap's "
                     "classes, utilities and states work inside. Prepared once: its <code>:root</code> token blocks are removed (the "
                     "tokens come from the page) and each component's token defaults are moved to its host."),
                    ("<code>:host</code> baseline", "<code>core/ui-shadow-base.css</code>: <code>display</code>, <code>box-sizing</code>, "
                     "<code>[hidden]</code>, text colour."),
                    ("Component CSS", "<code>ui-x.css</code> next to the script: only what Bootstrap's CSS cannot do inside a shadow tree."),
                    ("Document CSS", "A few components style their slotted content (which lives in your page) with a small sheet added to "
                     "the document once, in <code>@layer components</code> so your CSS wins: alert, card, carousel, list group, menu, "
                     "richtext, plain dialogs."),
                    ("Behaviour", "Bootstrap's JavaScript, rewritten per element: toggles, focus handling, keyboard, events "
                     "(<code>ui-x:show</code> …), form association (inputs, selects, checks, chips, dropzone submit with the form). "
                     "The data API (<code>data-bs-toggle</code>, <code>data-bs-target</code>) also drives Bootstrap's own markup."),
                ],
            ),
        },
        {
            "id": "page",
            "title": "What the page provides",
            "intro": "The components read Bootstrap's design tokens (<code>--bs-primary-bg</code>, <code>--bs-spacer</code>, fonts, "
            "radii …) from the page; CSS variables are inherited into shadow trees." + table(
                ("You provide", "Why"),
                [
                    ("Bootstrap 6 CSS on the page (or at least <code>modules/bootstrap/ui-tokens.css</code>)",
                     "The tokens, colour modes and fonts. The full CSS is needed for anything in light DOM: your slotted content's "
                     "classes, Bootstrap markup without an element (nav, navbar, plain <code>.collapse</code>, <code>.carousel</code>), "
                     "and <code>ui-menu</code>, which keeps Bootstrap's <code>.menu</code> in your page."),
                    ("<code>data-bs-theme</code>", "Colour mode: <code>light</code> / <code>dark</code> on <code>&lt;html&gt;</code> or "
                     "any element (the switcher in this page's header does that, see <code>theme.js</code>)."),
                    ("Page layout", "Grid, spacing between elements, the page's own typography — as with plain Bootstrap."),
                    ("Labels in your language", "Built-in texts are English; every one has a <code>*-label</code> attribute."),
                    ("<code>data-bs-validate</code> on forms", "Client-side validation feedback of the form fields, like Bootstrap 6 "
                     "(<code>=\"valid\"</code> also for valid fields); without it the browser's own messages apply."),
                ],
            ),
        },
        {
            "id": "styling",
            "title": "Styling: page tokens",
            "intro": "From global to local, five ways. <strong>1. Page tokens</strong> theme everything below them: set Bootstrap's "
            "tokens on <code>:root</code> for the whole page, or on any wrapper for a part of it. Here the primary colour of one box.",
            "html": lines(
                '<div class="brand-theme d-flex flex-wrap gap-2 align-items-center">',
                '  <ui-button variant="primary">Button</ui-button>',
                '  <ui-button variant="primary" appearance="outline">Outline</ui-button>',
                '  <ui-badge variant="primary">Badge</ui-badge>',
                '  <ui-check checked label="Check"></ui-check>',
                "</div>",
            ),
            "script": lines(".brand-theme {", "  --bs-primary-bg: #6f42c1;", "  --bs-primary-bg-subtle: #efe7fa;",
                            "  --bs-primary-fg: #59359a;", "  --bs-primary-border: #c9b3ec;", "}"),
            "script_language": "CSS",
        },
        {
            "id": "styling-attributes",
            "title": "Styling: attributes",
            "intro": "<strong>2. Attributes</strong> are Bootstrap's modifier classes: <code>variant</code> (theme colour), "
            "<code>size</code>, <code>appearance</code>, <code>flush</code>, <code>pill</code> … — listed under Reference on "
            "every page. A <code>class</code> on the element styles only the host box; for Bootstrap classes on the inner "
            "element some components have <code>button-class</code>, <code>badge-class</code>, <code>card-class</code>.",
            "html": lines('<ui-button variant="success" size="sm">Small success</ui-button>',
                          '<ui-button variant="danger" appearance="subtle">Subtle danger</ui-button>',
                          '<ui-button button-class="w-100" variant="primary" class="d-block mt-2">Inner class w-100</ui-button>'),
        },
        {
            "id": "styling-tokens",
            "title": "Styling: component tokens",
            "intro": "<strong>3. Component tokens</strong> (<code>--bs-btn-*</code>, <code>--bs-card-*</code>, own "
            "<code>--ui-gallery-*</code> …) change one kind of component; each page lists them under <em>CSS variables</em> "
            "with a <em>Customizing</em> demo. Set them <strong>on the element itself</strong> (or a selector matching it, like "
            "<code>.toolbar ui-button</code>): a component sets its own defaults on its host, so a value on a wrapper "
            "<code>div</code> does not reach it — unlike page tokens.",
            "html": lines('<ui-button class="rounded-buttons" variant="primary">Pill via token</ui-button>',
                          '<div class="rounded-buttons d-inline-block"><ui-button variant="secondary">Wrapper: no effect</ui-button></div>'),
            "script": lines(".rounded-buttons {", "  --bs-btn-border-radius: var(--bs-radius-pill);", "}"),
            "script_language": "CSS",
        },
        {
            "id": "styling-parts",
            "title": "Styling: parts",
            "intro": "<strong>4. <code>::part()</code></strong> reaches the inner elements a component exposes (listed under "
            "<em>CSS parts</em>), for properties without a token. Selectors like <code>ui-button .btn</code> do not work: "
            "the shadow root is closed to page selectors.",
            "html": lines('<ui-button class="lifted" variant="primary">Lifted with ::part(button)</ui-button>'),
            "script": lines(".lifted::part(button) {", "  box-shadow: 0 .5rem 1rem rgb(0 0 0 / .15);", "  transform: translateY(-1px);", "}"),
            "script_language": "CSS",
        },
        {
            "id": "styling-content",
            "title": "Styling: your content",
            "intro": "<strong>5. Slotted content</strong> is yours: it stays in the page, so your CSS and Bootstrap's classes "
            "(loaded on the page) style it as usual. <strong>Colour modes</strong> work the same way: "
            "<code>data-bs-theme=\"dark\"</code> on any element switches the tokens below it.",
            "html": lines(
                '<div data-bs-theme="dark" class="p-3 rounded-5 bg-body">',
                '  <ui-card style="max-width: 20rem">',
                '    <h5 class="card-title fg-success">Utilities in a card</h5>',
                '    <p class="card-text fst-italic mb-2">This text is light DOM: page classes style it.</p>',
                '    <ui-button variant="primary" size="sm">Dark mode button</ui-button>',
                "  </ui-card>",
                "</div>",
            ),
        },
        {
            "id": "light-dom",
            "title": "Light DOM and plain Bootstrap",
            "intro": "Not everything needs a shadow root. <code>ui-menu</code> keeps Bootstrap's <code>.menu</code> in your page "
            "(menus must be styled where they appear), nav and navbar are plain Bootstrap markup with docs pages but no element, "
            "and the data API also drives plain markup: <code>.collapse</code>, <code>&lt;dialog class=\"dialog|drawer\"&gt;</code>, "
            "<code>.carousel</code>, <code>.chip-input[data-bs-chips]</code>, <code>data-bs-toggle=\"tooltip|popover\"</code>. "
            "Their tokens are set on Bootstrap's element, like in Bootstrap.",
        },
        {
            "id": "loading",
            "title": "Loading and versions",
            "intro": "Load the module entry (<code>modules/bootstrap/bootstrap.js</code>, all components) or single components "
            "(<code>modules/bootstrap/ui-button/ui-button.js</code>). The Flask blueprint serves versioned URLs; without Python, "
            "<code>python -m webcomponents.export</code> writes the plain files (FlaskSpark ships such a snapshot). The calendar is "
            "its own module (<code>modules/calendar/calendar.js</code>, FullCalendar loaded on first use).",
        },
    ],
}
