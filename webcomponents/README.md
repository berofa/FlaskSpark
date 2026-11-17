# webcomponents

Web components with **shadow roots**, grouped into **modules** and
**submodules**, styled via CSS variables, built on Bootstrap 6. The package is
part of FlaskSpark and is installed with it (`pip install FlaskSpark`). Usable
from Python (FlaskSpark serves it as a blueprint, see
[Using them in a FlaskSpark app](#using-them-in-a-flaskspark-app)) and without
Python (snapshot export of the plain JS/CSS files, e.g. for a TYPO3 site
package, see [Export without Python](#export-without-python)).

- Package / asset tree: this directory (`webcomponents/` in the FlaskSpark repository)
- Docs app: [`docs/app`](../docs/app) — FlaskSpark app with examples and usage
  of every component; serves as the living reference.

Documentation conventions: **this README holds the technical documentation**
(architecture, build, tests, conventions); **the docs app under `docs/`
holds the examples** and shows how each component is used.

## Structure

```
webcomponents/                 Python package = distributable asset tree
  __init__.py                  create_blueprint(), grid layout helpers
  export.py                    snapshot export (python -m webcomponents.export)
  grid_layout.py               server-side grid layout normalization
  tokens.py                    documented CSS variables of a component; ui-tokens.css generator
  core/                        shared by all modules
    shadow-component-element.js   base class (render scheduling, style loading)
    light-component-element.js    base class for light-DOM components
    light-feed-element.js         light-DOM component bound to a feed (renderData)
    feeds.js                      findFeed(), readEmbeddedJson()
    shared-shadow-styles.js       stylesheet cache (shadow roots and document)
    escape.js                     escapeHtml — required for all interpolated values
    registry.js                   customElements registration helper
    form-control-element.js       base class for form-associated controls
    placement.js                  computePlacement (floating boxes, pure)
    morph.js                      morph(target, html): only what changed instead of innerHTML (live updates without flicker)
    validation.js                 validationMessage(): the German messages of invalid fields (stricter email)
    transitions.js, collapse-transition.js
    triggers.js, tip.js, sanitize.js, slotted-items.js, files.js
    ui-shadow-base.css            :host baseline of every shadow root (plain CSS, part of BOOTSTRAP_SHADOW_STYLES)
  vendor/                      third-party libraries, one copy for all modules
    bootstrap6/                Bootstrap 6.0.0-alpha.1 (precompiled CSS + JS bundle)
    fullcalendar/              FullCalendar (module calendar)
    vanilla-calendar-pro/      Vanilla Calendar Pro 3.4.0 (ui-datepicker, loaded on first use)
    markdown-it/               markdown-it 14.1.0 (ui-markdown, ui-markdown-editor, loaded on first use)
  modules/
    bootstrap/                 module: Bootstrap components
      module.json              manifest (entry, module files, vendor libraries)
      bootstrap.js             module entry: imports every submodule, theme switcher
      theme.js                 data-bs-theme switcher
      shadow-styles.js         the shared Bootstrap sheet of every shadow root, token hoisting
      ui-tokens.css            Bootstrap 6 tokens for pages without Bootstrap (generated)
      ui-tooltip/              submodule: one component
        submodule.json         manifest (elements, entry, runtime files, tokens, requires)
        ui-tooltip.js          component; registers its own elements
        ui-tooltip.css         component styles (plain CSS)
      ui-accordion/ ui-alert/ … (one folder per component)
    calendar/                  module: ui-calendar (FullCalendar)
```

Rules:

- **Vendor is global.** Libraries live once under `vendor/`; a module names the
  ones it needs in `module.json` (`"vendor": ["bootstrap"]`). The export copies
  them along.
- **A submodule brings everything it needs**: its JS, compiled CSS and manifest.
  Shared code comes from `core/`; a dependency on another submodule is declared
  in `submodule.json` (`"requires": ["ui-grid"]`).
- **Element prefix**: `ui-*`. The library holds UI components only; non-visual
  helpers (data feeds, live channels) belong to the app.

## Using the components

Everything of a module:

```html
<script type="module" src="/webcomponents/modules/bootstrap/bootstrap.js"></script>
```

Single submodules only (each registers its own elements):

```html
<script type="module" src="/webcomponents/modules/bootstrap/ui-tooltip/ui-tooltip.js"></script>
```

Each component loads its stylesheet from next to its own script
(`new URL("./ui-x.css", import.meta.url)`), so no base path configuration is
needed — the files only have to keep their relative layout.

Host pages provide the Bootstrap tokens: either they load full Bootstrap, or
they include `modules/bootstrap/ui-tokens.css` (generated from the vendored
Bootstrap 6 CSS: `python -m webcomponents.tokens > webcomponents/modules/bootstrap/ui-tokens.css`;
a test keeps it in sync). Bootstrap's `:root` /
`[data-bs-theme]` variable blocks are **not** part of the component
stylesheets — those selectors never match inside a shadow tree. Dark mode:
`data-bs-theme="dark"` on `<html>` (see `theme.js`); the custom properties
inherit through the shadow boundary.

## Shadow DOM or light DOM

- **Shadow DOM** (`ShadowComponentElement`) for self-contained building blocks
  like the Bootstrap module: styles are encapsulated, hosts theme them via
  `::part()` and CSS variables.
- **Light DOM** (`LightComponentElement`, `LightFeedElement`) for components
  that compose other components, typically app-specific cards: a page's
  `::part()` rules do not reach into a nested shadow tree, so a card that
  renders `ui-table` inside its own shadow root could not be themed by the
  page anymore. Their stylesheet is adopted into the document once.

## Data feeds

Components can take their data from a feed of the app: an element with
`subscribe(callback)` that returns the unsubscribe function, referenced by id
(`feed="…"`), so ten components on a page still make one request. The feeds
themselves (JSON with polling, live channels, …) are not part of this library;
it provides the consumer side: `LightFeedElement` (core; implements
`renderData(data)`) and `findFeed()` (resolves the element once it is defined).

```html
<my-json-feed id="stats" src="/stats"></my-json-feed>   <!-- the app's feed -->
<my-stat-card feed="stats"></my-stat-card>   <!-- extends LightFeedElement, implements renderData(data) -->
```

## Writing components

- Extend `ShadowComponentElement` or `LightComponentElement` (`core/`); declare
  `static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-x.css", import.meta.url).href]` and
  `static observedAttributes`. Rendering is scheduled automatically
  (attribute changes coalesce into one mount per microtask).
- Every dynamic value interpolated into a `render()` template string **must**
  go through `escapeHtml()`.
- One folder per component under its module, with `submodule.json`; the
  component file ends with its `registerComponent(...)` calls. Add the import
  to the module entry (`bootstrap.js`).
- Plain CSS: one `ui-<name>.css` next to the script (no SCSS in the library).
  Components without a Bootstrap counterpart declare their own `--ui-<name>-*`
  tokens on `:host` and list them in `submodule.json` (`"file"` source); the
  docs app shows them.
- Add an example page for the component to the docs app (`docs/`).
- Expose CSS parts (`part="…"`) on the elements host pages need to theme.
  Bootstrap declares many `--bs-*` variables on the component class itself
  (e.g. `.btn`, `.tooltip`), so host overrides must target the part.
- Display-only pages (an info screen: `<html data-screen>`, which sets the
  inherited `--ui-screen: on`): a component's own controls must not show.
  `core/ui-shadow-base.css` hides `.btn-close`, `.chip-dismiss`,
  `.ui-card-chevron`, `.ui-card-actions` and anything marked
  `data-screen-hide` (a style query on `--ui-screen`, `:host-context()` as the
  fallback); a new component with controls of another kind marks them
  `data-screen-hide`. `UiContextMenu.open()` refuses there (`displayOnly()`),
  and `theme.js` keeps a mode the page fixes (`<html data-theme-fixed>`).

### Bootstrap module notes

- Validation follows Bootstrap 6: client-side feedback (is-invalid / is-valid and the messages) only inside an
  element with `data-bs-validate` (usually the form; `="valid"` also marks valid fields), after a field was left
  or a submit was tried (like `:user-invalid`). Without it the browser's own messages apply. A server message
  (`error`) and `validate()` always show (`core/validation.js`: `validationMode`, `onSubmitAttempt`).
- `ui-check`, `ui-input`, `ui-textarea` and `ui-select` are form-associated
  (`ElementInternals`): they submit under their `name`, follow form reset and
  disabled fieldsets and take part in constraint validation. `change` is
  re-dispatched on the host because the native event stops at the shadow
  boundary.
- `ui-input clearable`: an × inside the field at the right while it has a value
  (Firefox has none for type="search"; the browser's own is hidden), Escape
  does the same; both fire input and change as typing would.
- `ui-toast` / `ui-toast-container`: Bootstrap toasts, fixed at a corner so a
  message never moves the page; `showToast(message, {variant, delay})` creates
  the container on first use. A variant takes the alerts' subtle colours; the
  delay pauses while hovered or focused.
- `ui-richtext` (formatted text, value = HTML, also form-associated) keeps its
  editable area in the light DOM (a `[contenteditable]` child in the slot): the
  browsers' editing commands and the selection don't work reliably inside a
  shadow tree (Firefox). Its toolbar is in the shadow tree; pasted HTML is
  reduced to structure and simple markup (`cleanHtml`). A host app still
  sanitises the HTML on the server before it uses it.
- `ui-markdown-editor` (value = Markdown, form-associated) has two modes: «Text» edits the rendered text (a
  light-DOM `[contenteditable]` like `ui-richtext`, typography `ui-markdown/markdown-body.css` adopted into the page)
  and «Markdown» the source in a monospace `<textarea>` in its shadow tree. Every edit converts back with
  `toMarkdown()`; an unchanged text keeps its Markdown as written. Task lists are `<ul data-task>` with
  `<li data-checked>` while editing, relative URLs are shown with `base-url` and kept in `data-md-src`/`data-md-href`.
  The «/» and «+» menus list `BUILTIN_COMMANDS` plus the page's (`UiMarkdownEditor.addCommand()`) and the editor's
  own (`editor.addCommand()`); texts in `labels` (keys `DEFAULT_LABELS`, `editor-commands.js`). No Mermaid or PlantUML.
- `ui-markdown/markdown.js` is the browser's half of `flaskspark.markdown`: `render()` (markdown-it with the same
  core rules for task lists, alerts, heading ids and the table of contents), `sanitize()` (the same allowlist as the
  server's nh3 call; parses with `DOMParser`, without a DOM with a small tree builder) and `toMarkdown()`. The cases in
  `tests/webcomponents/fixtures/markdown_cases.json` run in node and in pytest, and pytest compares both outputs.
  `ui-markdown` shows Markdown (or HTML rendered elsewhere, sanitised again) in its shadow tree.
- Bootstrap selects some images per colour mode via `[data-bs-theme]`, which
  never matches inside a shadow tree. `ui-check` draws the switch knob as a
  gradient with `light-dark()`, `ui-select` draws its caret as an inline SVG in
  `currentColor`.
- `ui-table` moves the author's `<table>` child into its shadow tree (rows
  cannot be slotted). The shared Bootstrap sheet keeps cell classes working;
  page-level classes do not apply inside. Use `valign`, not `align` (browsers
  map the legacy attribute to text-align). `class="table-icons"` on a column
  header makes an icon column for buttons (narrow, right-aligned, no wrapping;
  not Bootstrap, the component copies the class to the cells of the column).
  `class="table-total"` on a row (usually in `<tfoot>`) makes a total row
  (bold, a stronger line above).
- `ui-card heading="…"` turns the header into a row: an icon (`icon` by name,
  or the slot `icon`), the heading, the slot `header`, and the slot `actions`
  at the end; `collapsible` (+ `collapsed`) folds the card from its header
  (`ui-card:toggle`). Icons by name come from the page's icon sprite
  (`core/icons.js`: `<meta name="ui-icon-sprite" content="…/bootstrap-icons.svg">`
  or `setIconSprite(url)`; inline SVG with `<use>`, so they work in shadow
  trees, where an icon font's classes do not reach).
- `ui-kpi` and `ui-kpi-group` (not Bootstrap): key figures as tiles (label,
  value, a line below, trend arrow, `size` sm/lg), in a responsive grid.
- `ui-chip` is Bootstrap 6's `.chip` (static by default; `toggle` makes it a
  form-associated toggle); `ui-chip-input` is Bootstrap's chip input.
- `ui-dropzone`, `ui-gallery`, `ui-grid`, `ui-grid-editor`, `ui-richtext` and
  `ui-calendar` are not Bootstrap components: built from Bootstrap 6's tokens,
  form field and buttons, themed with their own `--ui-<name>-*` tokens.
  `ui-dropzone` hands files over or is a form field (`name`); `ui-gallery`'s
  `editable` and `sortable` only fire events, saving is the host's job.
- `ui-tooltip` uses a `popover="manual"` bubble in the top layer (not clipped
  by cards); without Popover API support it falls back to `position: fixed`.
- `ui-popover` works the same way with a title and a rich body (`heading` /
  `content` slots): hover and focus open it, a click pins it open
  (`trigger="click"`: click only).

## Bootstrap 6

Bootstrap 6 (`vendor/bootstrap6`, 6.0.0-alpha.1) is used as the precompiled
`dist` CSS (no Sass sources). Every component is migrated and has plain CSS only. A
component with a Bootstrap counterpart implements **every feature of
Bootstrap's documentation** (variants, sizes, states, behaviour, events) and
documents its CSS variables.

- **Shared Bootstrap copy.** A component adopts `BOOTSTRAP_SHADOW_STYLES`
  (`modules/bootstrap/shadow-styles.js`) before its own sheet:
  `static stylesheets = [...BOOTSTRAP_SHADOW_STYLES, new URL("./ui-x.css", import.meta.url).href]`.
  That is the full Bootstrap CSS as **one** sheet shared by all shadow roots,
  prepared once (`prepareBootstrapSheet`), plus the `:host` baseline
  (`core/ui-shadow-base.css`). Bootstrap's markup and classes work inside the
  shadow tree as documented.
- **Page tokens inherit.** Bootstrap 6 declares its tokens for `:root, :host`.
  These blocks are removed from the shared copy (`stripRootTokenRules` in
  `core/shadow-sheet-transforms.js`), otherwise every component would reset the
  tokens the page sets. The page provides them by loading Bootstrap 6 itself.
- **Component tokens are themeable on the element.** Bootstrap declares
  component tokens on the class (`.badge { --bs-badge-padding-x: … }`), where a
  page rule for `ui-badge` could never win. `hoistComponentTokens` adds
  `:host(ui-badge) { <defaults> }` and, right after the base rule,
  `:where(.ui-host-tokens):is(.badge) { <token>: inherit }`; the component puts
  `HOST_TOKENS_CLASS` on its own inner element. So `ui-badge { --bs-badge-…: … }`
  works, modifiers (`.badge-outline`, `.btn-sm`) still win as in Bootstrap, and
  the same class inside other components (a `.btn-close` in an alert) keeps
  Bootstrap's defaults. New components add their base rule to `TOKEN_HOISTS`.
- **Slotted content.** Bootstrap styles direct children (`.alert > p`,
  `.card-body > *`). A shadow tree cannot (`::slotted()` loses against page
  rules), so such rules go into `ui-x.document.css` (`static documentStylesheet`),
  adopted into the page once, inside `@layer components` so they rank like
  Bootstrap's own (above reboot, below utilities).
- **Items rendered by the container.** Sibling rules
  (`.list-group-item + .list-group-item`, `.breadcrumb-divider`) need all items
  in one tree: `ui-list-group` and `ui-breadcrumb` render one wrapper per item and
  slot the item element into it (`core/slotted-items.js`); `ui-card` renders only
  the parts that have content. Re-rendering uses `morph()`, so focus and state stay.
- **CSS variables documentation.** `submodule.json` names the rules that declare
  a component's tokens and describes each token (`"tokens"`); defaults are read
  from the vendored CSS (`webcomponents/tokens.py`), the docs app shows the table.
  `tests/webcomponents/python/test_tokens.py` fails on undescribed tokens and on token sources
  that are not hoisted.
- **Browser tests.** `docs/app/templates/tests/components.html` checks the
  components in a real browser (tokens, behaviour, events);
  `tests/webcomponents/python/test_browser.py` starts the docs app and runs it in headless
  Chromium (skipped without Chromium).
- **Dark mode** needs no work inside components: Bootstrap 6 colours with
  `light-dark()`, and `color-scheme` (set by `data-bs-theme`) inherits into
  shadow trees.
- **Renamed tokens and classes** (selection): `--bs-body-color` → `--bs-fg-body`,
  `--bs-body-bg` → `--bs-bg-body`, `--bs-secondary-color` → `--bs-fg-3`,
  `--bs-tertiary-bg` → `--bs-bg-2`, `--bs-primary-text-emphasis` →
  `--bs-primary-fg-emphasis`. Variants are `.theme-*` classes (`.theme-danger`
  instead of `.alert-danger`), buttons `.btn-solid`/`-outline`/`-subtle`/`-text`;
  `display-*`/`lead` are gone (`text-4xl`, `text-lg`); breakpoints `lg` 1024px,
  `xl` 1280px, `2xl` instead of `xxl`; responsive classes are `md:…` and
  partly container queries.
- **Components:** `ui-accordion` (native `<details>`), `ui-alert`, `ui-badge` (also in a free `color` with contrast text computed by WCAG luminance, and split with `scope` like GitLab's scoped labels: parts `scope` and `value`), `ui-breadcrumb`, `ui-button`, `ui-carousel` (scroll snap, plus the data API for plain `.carousel` markup), `ui-chip` and `ui-chip-input` (new, with the `data-bs-chips` data API), `ui-table`, `ui-gallery` (+ declarative `ui-gallery-item`; own `--ui-gallery-*` tokens, documented from the component CSS), `ui-dropzone` (hand-over or form field with file list and limits), `ui-grid` (v6 breakpoints, container queries), `ui-grid-editor`, `ui-richtext` (form field, pressed tools, label attributes), `ui-markdown-editor` and `ui-markdown` (Markdown, markdown-it), `ui-range` (new in v6), the toggler data API (`toggler.js`, new in v6), password strength (`ui-input strength`, `strength.js`, new in v6), `ui-otp` (new in v6), `ui-datepicker` (new in v6, Vanilla Calendar Pro), `ui-combobox` (new in v6), nav overflow (`nav-overflow.js`, data API, new in v6), scrollspy (`scrollspy.js`, data API), `ui-avatar` (+ `ui-avatar-stack`, new in v6), `ui-pagination`, `ui-placeholder`, `ui-progress`, `ui-kpi` (+ `ui-kpi-group`, key figures as tiles, own `--ui-kpi-*` tokens), `ui-spinner`, `ui-stepper` (new in v6),
  `ui-button-group`, `ui-card` (+ `ui-card-group`), `ui-check`,
  `ui-close-button` (new), `ui-collapse`, `ui-dialog`, `ui-drawer`,
  `ui-input`, `ui-list-group`, `ui-menu`, `ui-popover`, `ui-select`,
  `ui-tabs`, `ui-textarea`, `ui-toast`, `ui-tooltip`. Navbar and nav are
  Bootstrap's own markup (docs pages), without an element of their own.
- **Renamed like Bootstrap 6:** `ui-modal` → `ui-dialog`, `ui-offcanvas` →
  `ui-drawer`, `ui-dropdown` → `ui-menu`, `ui-navbar` → navbar markup (the old elements are gone; host apps
  switch when they take this version). Triggers use Bootstrap's data API:
  `data-bs-toggle="dialog|drawer|menu"`, `data-bs-target`, `data-bs-dismiss`
  (`core/triggers.js`).
- **Dialog and drawer** run on the native `<dialog>` in the shadow tree
  (top layer, backdrop, focus trap); `ui-drawer` extends `ui-dialog`. The data
  API also opens Bootstrap's plain `<dialog class="dialog|drawer">` markup
  (`ui-dialog/plain-dialog.js`), e.g. the drawer of a navbar, where Bootstrap's
  `.md:navbar-expand [class*=drawer]` rules need the drawer in the light DOM.
- **Data API on plain markup** (like Bootstrap's JavaScript): collapse, tab
  (`tab`, `pill`, `list`), menu, dialog, drawer, tooltip and popover toggles
  work on Bootstrap's own markup too.
- **Tooltip and popover** share `core/tip.js` (top layer, responsive
  placement, triggers, delay, offset, sanitized HTML via `core/sanitize.js`);
  the box lives in the component's shadow root, or in the page for plain markup.
- **Menu in the light DOM.** `ui-menu` wraps Bootstrap's own menu markup and
  adds the behaviour (top layer via `popover`, placement with
  `core/placement.js` `placeAligned`, auto close, keyboard, submenus): nested
  submenus are grandchildren of the host and cannot be slotted, and every
  class of Bootstrap's menu docs works unchanged. Plain markup with
  `data-bs-toggle="menu"` works without the wrapper.
- **Grouped members.** Members of a `ui-button-group` (and buttons in an input
  group's prefix/suffix) are separate shadow trees; the container sets
  `grouped`, `group-first`, `group-last`, `group-divider` on them and
  `modules/bootstrap/grouped.css` mirrors Bootstrap's `.btn-group` rules.

## Build

No preprocessor: the library and the docs app are **plain CSS**, nothing has to
be compiled (a test keeps it that way). What SCSS used to do, native CSS does:

- **Variables** → custom properties (`--bs-*`, `--ui-<name>-*`), themeable from
  the page through the shadow boundary.
- **Mixins / shared partials** → shared stylesheets adopted into every shadow
  root (`BOOTSTRAP_SHADOW_STYLES`: Bootstrap's CSS, `core/ui-shadow-base.css`,
  `grouped.css`, `form-field.css`).
- **Colour functions** → `color-mix()`, `light-dark()` and `oklch()` (as in
  Bootstrap 6's tokens); **nesting**, if needed → native CSS nesting.
- The docs app's page styles (`docs/app/static/css/app.css`) go through
  FlaskSpark's asset bundle with `rcssmin` only (`ASSETS_CSS_FILTERS` in
  `docs/app/__init__.py`).

## Python

`webcomponents` exposes:

- `create_blueprint(url_prefix="/webcomponents")` — serves the asset tree
  (JS, CSS, JSON, images, fonts; no Python or SCSS sources), e.g.
  `url_for("webcomponents.static", filename="modules/bootstrap/bootstrap.js")`.
  Versioned by default: `url_for` builds `/webcomponents/v-<version>/…`, cached
  for a year (`immutable`); relative imports keep the version, and the version
  follows the files (an edit gives new URLs without a restart).
- `delivery.version_static(app, "static", app.static_folder)` — the same for the
  host's own static files.
- `delivery.install_preload(app, {"/static/": app.static_folder, "/webcomponents/": PACKAGE_ROOT})`
  — every HTML answer gets `<link rel="modulepreload">` for all modules its
  module scripts import (also through the import map) and `<link rel="preload"
  as="fetch">` for the components' stylesheets: one round trip instead of one per
  import level. Install it after Flask-Compress.
- Several directories under one URL prefix (e.g. FlaskSpark module packages, `FlaskSpark.static_dirs`): pass a
  list in lookup order, `version_static(app, "static", dirs)` and `install_preload(app, {"/static/": dirs, …})`.
- `normalize_layout`, `default_layout`, `build_unit_areas` — server-side grid
  layout normalization. Keep semantics in sync with
  `modules/bootstrap/ui-grid/grid-layout.js`.

## Using them in a FlaskSpark app

The package comes with FlaskSpark; there is nothing else to install. Switch the
components on in the app's configuration:

```dotenv
VENDOR_INCLUDE_WEBCOMPONENTS=true
```

FlaskSpark then

- registers the blueprint (`/webcomponents/…`, versioned URLs cached for a year),
- loads the Bootstrap 6 CSS for the page (block `flaskspark_vendor_styles`) and
  the `bootstrap` module (block `flaskspark_vendor_scripts`) in
  `layouts/framework.html`,
- gives templates `vendor_include_webcomponents` and
  `webcomponents_url(filename)`, e.g.
  `{{ webcomponents_url('modules/calendar/calendar.js') }}`.

Apps must **not** register the blueprint themselves any more,
and they must not keep a copy of the package (the former snapshot under
`flaskspark/static/vendor/webcomponents` is gone). Modular apps built on
`flaskspark.core` have the option on by default and import the components as
`webcomponents/…` through the page's import map.

For an editable checkout of FlaskSpark, changes to the components are live in
every app after a restart (assets immediately).

## Export without Python

Projects without Python (e.g. a TYPO3 site package or a static site) take a
snapshot of the runtime files. Any environment with FlaskSpark installed can
make it (`pip install FlaskSpark`, a virtual environment is enough):

```sh
python -m webcomponents.export TARGET_DIR                        # all modules
python -m webcomponents.export TARGET_DIR bootstrap              # one module
python -m webcomponents.export TARGET_DIR bootstrap/ui-tooltip   # single submodules (+ their requires)
python -m webcomponents.export TARGET_DIR bootstrap --no-vendor  # without vendor libraries
```

- `TARGET_DIR`: the directory to write into (created if missing; existing files
  are overwritten, files that are no longer exported stay — empty it first for
  a clean snapshot).
- Selection (any number, default: all modules): `<module>` exports the module
  completely, `<module>/<submodule>` single components; the submodules they
  name in `"requires"` come along.
- `--no-vendor`: leave out the vendor libraries the modules name in
  `module.json` (e.g. when the project brings Bootstrap 6 itself).

`core/` (JS and CSS) is always exported. The target keeps the package layout
(`core/`, `modules/…`, `vendor/…`), so relative imports and stylesheet URLs
keep working. `webcomponents.json` in the target records the version, the
exported modules with their submodules and the vendor libraries; the command
prints the same summary. The module entry (`bootstrap.js`) is only exported
with the complete module; with single submodules, load each one's script.

In the project, serve the target directory under any path and load the module
(and the page tokens, see [Using the components](#using-the-components)):

```html
<link rel="stylesheet" href="/assets/webcomponents/vendor/bootstrap6/css/bootstrap.min.css">
<script type="module" src="/assets/webcomponents/modules/bootstrap/bootstrap.js"></script>
```

Take a new snapshot after every FlaskSpark update.

## Tests

The grid layout logic exists twice by design — server-side
(`webcomponents/grid_layout.py`) and client-side
(`webcomponents/modules/bootstrap/ui-grid/grid-layout.js`). Both test suites
assert against the **same fixture file** (`tests/webcomponents/fixtures/grid_layout_cases.json`),
so a behavior change in one implementation fails the other suite until both
are updated:

From the FlaskSpark checkout:

```sh
.venv/bin/python -m pytest tests/webcomponents/python   # Python suite
node --test tests/webcomponents/js/                     # JS suite (Node ≥ 20; also: npm test)
```

Keep the tests current: when the layout semantics change intentionally,
adjust both implementations, regenerate the fixtures with
`python scripts/generate_grid_layout_fixtures.py` (the Python implementation
is the reference), review the fixture diff, and make sure both suites pass.
New pure logic (Python or JS) gets tests under `tests/webcomponents/` in the same pattern.

## Run the docs app

The docs app lives in `docs/` of the FlaskSpark repository. From the checkout:

```sh
uv venv .venv
uv pip install -e ".[dev]"
cp docs/.env.example docs/.env  # optional, defaults work
.venv/bin/python docs/run.py
```
