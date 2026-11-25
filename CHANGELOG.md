# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

## [1.2.0] - 2026-11-25

### Added
- Navigation entries without a group: `NavItem("", …)` stands without a heading right below «Home», before every
  group.

## [1.1.0] - 2026-11-22

### Added
- Stacked tables in the light DOM: a `<table>` with `.table-stacked` or a breakpoint variant (`.sm:table-stacked` …)
  gets the labels of its cells from the column headers (`webcomponents/core/stacked-tables.js`, installed by the
  core's `app.js`), also for rows rendered later (live data).
- `LightComponentElement`: `static morph = true` patches the children with `morph()` from the second render on
  instead of replacing them, so a component re-rendered on every live update keeps its elements and the page does not
  jump (iOS Safari has no scroll anchoring). Listeners belong on the component then (delegated), not on its children.

### Changed
- Stacked tables (light DOM and `<ui-table stacked>`): one line per cell, the label at the start and the value at the
  end, in the page font also in monospace cells; the footer (totals) stacks like the body; the table is as wide as
  its container, never wider. `<ui-table>` labels footer cells too, cells spanning several columns no longer.

### Fixed
- `<ui-tabs>`: the actions beside the tabs are never wider than the header and wrap inside (they stuck out of the card
  on phones and widened the page).
- Layout: the page no longer scrolls sideways on iOS Safari when something sticks out (`overflow-x: clip` on the root
  too; the body alone was ignored there).
- Stacked tables: cells patched by `morph()` lose their labels no longer (they are set again before the next paint).

## [1.0.0] - 2026-11-17

### Highlights
- `flaskspark.core`: a framework for modular apps on Flask: modules with a manifest, services over NATS, live data in
  the browser, access by role and area, settings, accounts, sharing, attachments, migrations per module and backups.
- The `ui-*` web components with Bootstrap 6 are part of FlaskSpark.
- Bootstrap 5 and SCSS are gone: FlaskSpark's assets are plain, modern CSS. Apps on 0.x see README «Upgrading from
  0.x»; a retired setting stops the start and names its replacement.
- Python 3.11 or newer.

### Added
- Access: pages of an area (`Area(..., parent="<area>")`), each with its own right, listed indented right below their
  area on «Settings › Access»; a new one starts with the rights its area has then. The area's switch switches all its
  pages and shows whether all (on), some (half) or none are allowed.
- Layout: `.app-third` on children of `.app-stack` puts them three in a row (two where narrower), e.g. cards of
  several modules on the start page.
- Info screens: two or three sections with `.app-screen-aside` share the column on the right one below the other,
  each an equal share of its height.
- Pages of sections (`PAGE_SECTIONS`): `Section(template, position)` places a section of a module elsewhere than at its
  module's `POSITION` (`flaskspark.core.module.page_sections()`, used by the start page, the profile and the info
  screens), e.g. between two sections of another module.
- Layout: `.app-area` on a child of `.app-stack` begins a group of sections with its own title (more room above);
  `.app-grid-3` has three columns from a container width of 1100px (was 1300px).
- Start page: `config.yaml` `app.home_title: false` leaves out its title.
- OAuth sign-in: the username's claim is configurable (`OAUTH_USERNAME_CLAIM`, default `username`), a username needs
  no dot any more, the names come from `given_name`/`family_name` or `name` first, and the groups from the userinfo
  endpoint when the ID token has none. So GitLab works as the identity provider.
- Navigation: `Module.nav_disabled()` names menu entries (of any module) that can't be used right now, asked for every
  page; the layout greys them out and makes them not clickable (`aria-disabled="true"`, `tabindex="-1"`, token
  `--app-nav-disabled-opacity`). Groups and entries carry `data-nav-group` for the modules' navigation scripts.
- Status tiles: `StatusTile.HREF` links a tile (and its dot) in `<ui-service-status>` to a page (`href` in the JSON).
- Info screens: pages for a display on the wall nobody operates. A module declares them in its manifest
  (`Module.SCREENS`, `Screen(key, title, area, description, icon, mode, reload_at, position)`), any module fills them
  with `PAGE_SECTIONS["screen:<key>"]`; `/screen/<key>` (and the list `/screen`) renders them with the new layout
  `layouts/screen.html`: no navigation or page chrome, a head row with logo, title, live state and clock, sizes in
  proportion to the viewport (designed for 1920 × 1080, token `--app-screen-scale`, `?scale=`), the app's colour mode
  unless `Screen.mode` or `?mode=` fixes one. `<html data-screen>` makes the page display-only: `frame.css` hides
  buttons, toolbars, dialogs; the web components hide their own controls (`--ui-screen: on`); `flaskspark/screen.js`
  swallows right clicks, clicks and activating keys (`[data-screen-keep]` opts out, `[data-screen-hide]` hides
  anything), reloads the page when the push channel stayed down for long (once the server answers) and daily at
  `Screen.reload_at`, and offers `onNewDay(callback)`. Tokens `--app-screen-scale`, `--app-screen-padding`,
  `--app-screen-gap`, `--app-screen-logo-height`.
- Info screens: a section with `.app-screen-aside` is a column on the right over the whole height (token
  `--app-screen-aside-width`, default 28%), the other sections stay one below the other on the left.
- «Settings › Screens» (admins): every info screen of the loaded modules with title, description, module, area, colour
  mode, daily reload and a link opening it in a new tab (`/settings#screens`).
- `layouts/framework.html`: block `html_attrs` (attributes of `<html>`).
- A page may fix its colour mode: `<html data-theme-fixed="light|dark|system">` (the layout's early script and
  webcomponents' `theme.js` neither read nor store the visitor's choice then).
- `contextMenu()` attaches nothing and `UiContextMenu.open()` refuses on a display-only page (`<html data-screen>`).
- Command line: the app's command (`flaskspark`, or its alias) runs the modules' `Module.CLI` commands too
  (`myapp <command> …`, in the web app's context like `flask --app flaskspark.core.web.app:create_app <command>`);
  `--help` lists them.
- Accounts: `accounts.for_module(name).create_app_account(type, name, *, secret, username, settings, test, **fields)`
  creates an account of the application from code (an import, a command) with the form's checks, the vetoes and the
  «connected» change, instead of `accounts.store.create`.
- `flaskspark.core.i18n`: `tr(text, /, **params)`, `ntr(singular, plural, n, /, **params)`, `N_`,
  `current_language()` and `using(locale)`: the visitor's language in a request, the application's elsewhere, for
  code that runs in both (texts positional-only, so a placeholder may be called `text`). Also `app_language()`,
  `locales()`, `best_match()`, `catalogue(directory, locale)`.
- Translations over NATS: `events.request()` sends the current language as the header `Accept-Language` (new
  argument `headers=`); `i18n.with_request_language` (decorator for message handlers), `i18n.language_of(msg)` and
  `i18n.request_headers()` let a service answer in the requester's language.
- The language in the profile: a signed-in user's choice is kept as the personal setting `core.language`
  (`core_user_settings`) and wins over the cookie and the browser on every device; the profile shows «Language», the
  sidebar's buttons change the same choice. Without sign-in nothing changes. `FlaskSpark.locale_preferences`
  (callables asked before the cookie) for FlaskSpark apps in general.
- `flaskspark/i18n.js`: `nt(singular, plural, n, params)` with the language's plural rule (parsed, no eval),
  `preloadCatalog(...parts)` (every text of a module, "core" or "app"), `preload()` also takes `[singular, plural]`.
  The layout puts the catalogue of the page's module into the page (`<script id="flaskspark-i18n">`; more with
  `{% set i18n_modules = [...] %}`), so `t()` needs no request. `GET`/`POST /api/i18n/catalog`.
- `flaskspark.core.i18n_extract:extract_js` (entry point `flaskspark_js`): a Babel extractor for scripts that finds
  `t()`, `nt()`, `N_()` … inside template literals (also in `${…}` within attribute quotes, nested), each string of
  `t(a ? "x" : "y")` and `t(a || "x")`, and plurals (`-k nt:1,2`).
- `flaskspark.markdown`: `render()` (GitHub/GitLab flavoured: tables, strikethrough, autolinks, task lists, alerts
  `> [!note]` … with optional title, `<details>`, table of contents `[[_TOC_]]`/`[TOC]` with heading ids, code blocks
  with their language; Mermaid/PlantUML stay code blocks), sanitised with an allowlist (nh3), `base_url` and
  `rewrite_url(url, kind)` for relative and proxied URLs; `to_markdown()` back from HTML; `sanitize()`. Jinja filter
  `markdown` in every FlaskSpark app. New dependencies: markdown-it-py (with linkify) and nh3.
- `ui-markdown-editor` (form field, value Markdown): modes «Text» (formatted) and «Markdown» (monospace source),
  toolbar like GitLab's editor (text style, bold, italic, strikethrough, quote, code, link dialog, lists, task list,
  table picker and table tools, attachment, «+» menu), «/» commands, both extensible (`UiMarkdownEditor.addCommand()`,
  `editor.addCommand()`), attachments by event `ui-markdown-editor:attach` or `uploadHandler(file)`, drop and paste of
  files, texts in `labels`. `ui-markdown` shows Markdown sanitised in the browser. `ui-markdown/markdown.js`: the
  browser's render/sanitize/toMarkdown with the server's rules (shared test cases); markdown-it 14.1.0 vendored
  (`webcomponents/vendor/markdown-it`, loaded on first use).
- `flaskspark.core`: Jinja global `markdown_editor_labels()` (the editor's texts in the page's language; German in the
  core's catalogue).
- Accounts: the built-in type `gitlab` (address of the instance, an access token kept encrypted as the account's
  password, `verify_tls`; the test asks `GET /api/v4/user` and answers «Connected as <name>»). Offered only when a
  loaded module names it. Account types may sign in with a secret alone: `AccountType.USERNAME = False` and
  `SECRET_LABEL` (the form then asks e.g. for an «Access token» and no user name).
- Accounts of the application: `Module.APP_ACCOUNT_TYPES` names types a module reads as accounts that belong to no
  person (owner `accounts.APP`, user id 0). Admins keep them in «Settings» → «Accounts» (`/api/settings/accounts`,
  the same API and `<ui-user-accounts>` as the profile, without sharing; also without sign-in). A module reads them
  with `accounts.for_module(NAME).app(type)` and `.app_account(type, name=None)`; `AccountAccess.is_app`.
- `flaskspark.core.gitlab`: a small client for GitLab's REST API (`GitLab(url, token)`, `GitLab.from_account()`,
  `get`/`post`/`put`/`delete`, `pages()` with `X-Next-Page` or `Link`, timeouts, `GitLabError` with `status` and
  `timeout`; the token goes only to the instance's own host, redirects elsewhere are followed without it).
- `ui-badge`: `color` (a free CSS colour, text white or dark by WCAG contrast, text and lines darkened/lightened as
  far as the page needs in light and dark mode) and `scope` (a split badge like GitLab's scoped labels: the scope
  filled, the value framed on the page's background; parts `scope` and `value`; read as «Scope: value»).
- `flaskspark.core` layout: the docked sidebar floats (inset from the window's edges, rounded, with a shadow and a
  milky, blurred background): tokens `--app-sidebar-inset` (`1rem`; `0` attaches it as a column with a line at its
  end, no corners and no shadow), `--app-sidebar-radius`, `--app-sidebar-shadow` (light and dark), `--app-sidebar-bg`
  (now a milky surface). The panel is the wrapper `.app-sidebar-wrap` (Bootstrap resets the docked drawer's
  background and border inside its shadow tree).
- Tokens so themes need no layout rules: `--app-nav-group-color` (titles of the navigation's groups),
  `--app-field-bg` (fields), `--app-tooltip-max-width` and `--app-tooltip-text-align`, `--app-table-cell-padding-y`
  (`.app-table`), `--app-table-last-row-border-width` (`.app-table` and `ui-table`, default `0`),
  `--app-card-icon-color` (the icon of a card's heading).
- Layout classes: `.app-total-row` (a total row of `.app-table`), `ui-accordion.app-card-accordion` (items like
  cards), `.app-fold-toggle` with `.app-fold-chevron` (a toggle that folds something away), `.app-section`,
  `.app-section-head`, `.app-section-title`, `.app-section-foot` and `.app-sections` (sections inside a card).
- Input groups: `ui-textarea` and `ui-richtext` get the styled prefix too; the corners on the attached side of
  prefix, suffix and field are square.
- A spinner in a count of the navigation (`ui-spinner` in `.app-nav-badge`) is as small as the digits.
- `config.yaml` `app.home_entry`: `false` hides «Home» in the navigation, `true` shows it; unset it shows only while
  «/» is the core's own start page (not when a module or the app answers «/» or `app.start` leads elsewhere).
- Import map prefix `app/` for the app's own JS (the app package's `static/app/`).
- `theme.yaml`: `apple_touch_icon` (inside `images/`) and `manifest` (a file inside `images/`, or the manifest's fields,
  served as `/theme/manifest.webmanifest` with the theme's name and colours as defaults; `true`: the defaults alone);
  the layout links both.
- Web components: `ui-kpi` and `ui-kpi-group` (key figures as tiles: label, value, a line below, trend arrow, theme
  colour, sizes, a responsive grid; `--ui-kpi-*` tokens). `ui-card` attributes `heading`, `icon`, `collapsible`,
  `collapsed`, `toggle-label`, slots `icon` and `actions`, event `ui-card:toggle`, method `toggle()`, token
  `--ui-card-icon-color`. `ui-table`: a total row (`class="table-total"`). `webcomponents/core/icons.js`: icons by name
  from the page's sprite (`<meta name="ui-icon-sprite">`, `setIconSprite()`); the core's layout names Bootstrap
  Icons' sprite.
- Layout tokens so a theme stays token-only (`frame.css`, README «Themes»): `--app-sidebar-bg`, `--app-chrome-blur`,
  `--app-card-radius`, `--app-card-shadow`, `--app-card-border`, `--app-nav-radius`, `--app-nav-font-weight`,
  `--app-nav-hover-bg`, `--app-nav-active-bg`, `--app-nav-active-fg`, `--app-nav-active-border`,
  `--app-nav-active-border-width`, `--app-btn-radius`, `--app-btn-font-weight`, `--app-glow-opacity`,
  `--app-glow-blur`, `--app-brand-max-height`, `--app-brand-compact-height` (defaults: the values so far).
- Start page: a view of a module or the app on `/` replaces the core's (`HomeView` is a fallback); `config.yaml`
  `app.start` (a path or an endpoint) sends `/` there. The access treats what `/` is and what `app.start` names as
  the start page (`flaskspark.core.web.start_endpoints()`, `start_url()`).
- FlaskSpark views: `fallback = True` registers a view only when no other view claims its URL.
- `config.yaml` `flask:`: Flask's and FlaskSpark's settings (e.g. `PERMANENT_SESSION_LIFETIME`, `ROLE_DEFAULTS`),
  applied by `flaskspark.core.web.app.create()` (`flask_settings(cfg)`).
- `flaskspark.core.config.load_env()`: the env files into the environment without the configuration.
- `flaskspark.core.db.USER` and `db.ROLES`: FlaskSpark's users and roles as targets of foreign keys
  (`ForeignKey(db.USER.c.id)`), in a `MetaData` of their own (`flaskspark.core.db.signin`).
- Migrations: the history `signin` has a second revision `29f594d439bf` that adds the columns older `user` and
  `roles` tables lack (`role_id`, `first_name`, `last_name`, `admin`; `is_admin`, `rank`), so `db adopt` takes over
  such tables; on tables the first revision created it does nothing.
- Backups: `backup.include` and `Module.backup_paths(cfg)` add directories outside the state directory to the state
  archive (below `extra/<absolute path>`); `backup.included(cfg)`.
- Profile: the modules' sections `PAGE_SECTIONS["profile"]` (of the modules the visitor may use).
- Accounts: a change of an account's shares is an `AccountChange("shared")` (told after the commit, also to the users
  of the roles); `Module.account_change_veto(change)` and `accounts.add_veto(callback)` refuse a change with a reason
  (`connected`, `changed`, `removed`, `activated`, `deactivated`, `shared`); `store.update()`/`store.delete()` take
  `check=False` to undo a failed test without asking. `Shareable.check_change()` and `Shareable.shares_changed()`.
- `flaskspark.core.i18n`: translations outside a request in the application's language (`gettext`, `language`,
  `translations`; `config.yaml` `notifications.language`, else the first of `app.locales`).
- Notifications: `Notifier.send(..., params=)` translates source texts; an opt-in history
  (`notifications.history: true`: `STATE_DIR/notifications/history.jsonl`, `notify.history()`).
- Attachments: `update()`, `delete()` and `delete_for()` take `cfg=` (the files are removed from that storage).
- `flaskspark.core.accounts`: accounts of the users in the core. A user connects one login at a provider once and
  switches on what it offers; account types (`AccountType`: fields with kinds and defaults, connection test,
  description) `imap`, `smtp`, `caldav` and `carddav` ship with the core, modules register more. A module names the
  types it uses in the new manifest field `ACCOUNT_TYPES` and reads them with `accounts.for_module(<name>)`
  (`for_user`, `all`, `get`, `test`, `record_test`; only its declared types, the password decrypted on access).
  New page «Profile» (`/profile`, with sign-in only) with `<ui-user-accounts>`: connect, edit, test, switch off,
  share and remove accounts; presets from `config.yaml` `accounts.providers`. Passwords encrypted with
  `flaskspark.core.secrets` (name `accounts`). Tables `core_accounts` and `core_account_types`.
- `flaskspark.core.shares`: sharing of any module's items with roles, read or write, with joining and leaving and
  notices when a share ends; `Shareable` named in the new manifest field `SHAREABLES`; `access`, `can_read`,
  `can_write`, `shared_with`, `grant`, `revoke`, `set_targets`, `forget`, …; the web component `<ui-share-dialog>`
  (`flaskspark/ui-share-dialog.js`) and the API `/api/shares/<type>/<id>`. Tables `core_shares`,
  `core_share_members`, `core_share_notices`.
- `flaskspark.core.attachments`: files attached to any module's items; `AttachmentOwner` named in the new manifest
  field `ATTACHMENT_OWNERS` (rights of its own or from a share type), storage below `STATE_DIR/attachments/<store>`
  (part of the backups), streamed uploads with a size limit (`attachments.max_size_mb`), thumbnails of images, PDFs
  and videos, `delete_for()` after the commit, the web component `<ui-attachments>` (drop zone, gallery with a
  lightbox) and the API `/api/attachments/…`. Table `core_attachments`. New extra `files` (Pillow, pillow-heif,
  pypdfium2) for the thumbnails; without it there are none.
- `flaskspark.core.db`: `after_commit(session, callback)` and `after_rollback(session, callback)`.
- The core's migration `7d3f9a2c1e64` (history `core`) creates the tables of accounts, shares and attachments.
- `flaskspark.core`: the router is a service of the core like web and push
  (`ServiceInfo("router")`, unit `flaskspark-router.service`, `flaskspark service router`, also `flaskspark router`;
  module `flaskspark.core.services.router`, `ROUTER_HOST`/`ROUTER_PORT`). It proxies with or without
  NATS; with NATS (user `router`, permissions `ms.router.>` and the bucket `services`) it sends heartbeats with its
  routes, open connections and WebSockets, requests and upstream failures per minute. New status tile «Router»; the
  guardian's `ServicesCheck` watches it; systemd `READY`/`WATCHDOG`. The supervisor still starts it last.
- `flaskspark.core`: a module the application no longer delivers (removed or renamed in a new version) no longer stops
  the start. Its revision in `alembic_version` is left alone (Alembic only sees the revisions it knows), the start
  warns, the status tile «Modules» shows «no longer delivered: … — its tables are kept», and the delivered modules are
  migrated as usual; its tables and data stay, and when it comes back its history goes on. A revision of no module
  ever recorded is treated the same way, with a warning of its own. The core's new table `core_module_chains` records
  every delivered module (revision, tables, label, version, last seen) at every start. `db adopt` keeps the revisions
  of such modules.
- «Settings › Data» (admins) and `flaskspark data` / `data clean <id…|all> [--yes]`: what is left over (tables, revisions
  and record of modules no longer delivered, tables no model describes, unknown revisions, stored settings, access
  cells and personal settings of what is gone, state directories) and its clean-up, after a backup; JSON API
  `GET`/`POST /api/settings/data`. The database API has `table_names()`, `row_count()` and `drop_tables()`
  (abstract `Database`, SQLite implementation). «Settings» is always in the sidebar for admins.
- `flaskspark` console script (the command line of apps on `flaskspark.core`) with `db upgrade|current|check|adopt`
  and `db revision -m … --module <name>` (autogenerated against that module's tables only); `db adopt` takes over a
  database of an earlier single history.
- The built-in web app `flaskspark.core.web.wsgi:app`: an application needs no `web/` of its own.
- `Module.OPTIONAL_DEPENDS` and `flaskspark.core.modules.is_enabled(cfg, name)`; `modules.skipped(cfg)`; `flaskspark
  modules` lists the modules that are not loaded and why.
- Translations per module (`<package>/locales`), loaded automatically: the core's, the modules', then the app's.
- Status tile «Modules»: the loaded modules, those not loaded, and the state of the migrations.
- `FlaskSpark(app_dir=...)`: the directory of an installed application package.
- `flaskspark.core.web.app:create_app`: the built-in web app for the `flask` command line (the modules' `CLI`).
- The web components are part of FlaskSpark (package `webcomponents`, with their docs app in `docs/` and their tests).
  Projects without Python take a snapshot with `python -m webcomponents.export`.
- `flaskspark.core` (extra `FlaskSpark[core]`): the core of modular apps — modules switched on in `config.yaml`, themes,
  a database API with rights per module, services over NATS (push to the browser, router, supervisor for a single
  container), a layout with navigation from the modules' manifests, access prepared for sign-in, sessions on the server.
- `VENDOR_INCLUDE_WEBCOMPONENTS` config (opt-in, default off): FlaskSpark registers the web components' blueprint and
  `layouts/framework.html` loads the Bootstrap 6 page CSS and the `bootstrap` module (new blocks
  `flaskspark_vendor_styles` and `flaskspark_vendor_scripts`). Templates get `webcomponents_url(filename)`.
- Module packages: `FlaskSpark(modules=[...])` registers the views and models of further packages and serves their
  templates and static files after the app's (`FlaskSpark.static_dirs`).
- `STRICT_IMPORTS` config: a view or model module that fails to import stops the start (default: skipped with a
  warning, as before).
- `flaskspark.core` brings its own catalogue (`flaskspark/core/locales`, English and German, `scripts/core-i18n`):
  apps no longer need the core's texts in their catalogue; an app's own translation still wins.
- `ROLE_DEFAULTS` config: apps choose the default roles that `Role.ensure_defaults()` creates (default unchanged:
  Administrators, Editors, Users, Guests).
- `flaskspark.core` manifests: `EXPOSURE` (`INTERNAL`/`PUBLIC`, checked; `modules.internal()`), `NAV_BADGES`
  (`NavBadge`: a module's counts on menu entries of other modules, per area), `SETTINGS` (a module's own sections on
  «Settings»), `push_sources(nc)` (topics the push service serves on demand through a module's `TopicSource`, with
  linger and `max_age`) and `ServiceInfo.unit` (its systemd unit).
- `flaskspark.core.service.LoopService` (a synchronous loop with heartbeats and systemd notifications),
  `flaskspark.core.task.Task` (a run once) and `service.write_heartbeat()`.
- `flaskspark.core.secrets`: per-module secrets encrypted with a key from the environment (`APP_SECRET_KEY`, its name
  configurable with `APP_SECRET_KEY_ENV`, a module's own `APP_SECRET_KEY_<MODULE>`).
- The guardian watches the service directory and the NATS servers between its runs (`StatusWatch`): the status tiles
  reload at once on a change. Without a readable directory the status tiles fall back to systemd on the host for
  services with a unit. Helpers for modules' tiles: `StatusContext.ask()`, `failing()`, `read_json()`, `thousands()`,
  `next_run()`, `health.request()`.
- `RoleAccess`: an admin sets a user's role by hand on «Settings › Users» (table `core_user_role`, API
  `/api/settings/users`); it is applied again after every sign-in.
- CLI commands `units` and `guard-check`; `Config.enabled(section)`.
- Settings of the kinds `text`, `time`, `ints`, `texts` and `json`.
- Backups: `backup.mirror_dir` copies the backup folder to a second folder; the backup tile shows the mirror.
- `Area.position`: the order of the areas across the modules.

### Changed
- «Settings › Access»: the roles are the columns, the areas (and their pages) the rows, so many areas fit.
- Sidebar: the signed-in user is a button to the profile above the colour mode (the separate profile button is gone);
  `config.yaml` `app.sign_out: false` leaves «Sign out» out, `status.everyone: true` shows the services' status to
  everyone (and opens `/api/status/services` to them).
- The profile has no language of its own any more (the sidebar's buttons keep a signed-in user's language on every
  device); the sidebar's «Browser default» comes first, before the languages.
- `flaskspark.core.i18n.gettext()`/`translations()`: the catalogues are cached per process and language and loaded
  again when a `.mo` file changes (mtime), instead of looking up the configuration and the modules on every call
  (in the demo app 6–8 ms per call before, about 0.002–0.015 ms now).
- `accounts.for_module(...).all(type)` returns the users' accounts only, never the application's;
  `for_user(0, …)` returns nothing.
- The core's `ui-chip` rule respects a chip's own `--ui-chip-active-bg` and `--ui-chip-active-border-color`.
- `--app-chrome-blur` is `18px` (with a little saturation) for the sidebar and the top bar; `.app-card-head` and the
  section titles colour their icon with `--app-card-icon-color`.
- `ui-table` and `.app-table` drop the line under the last row by default (`--app-table-last-row-border-width`).
- The core's CSS (`frame.css`, `ui-service-status.css`, the components' stylesheets) is plain modern CSS: native
  nesting, custom properties, `color-mix()`, `light-dark()`, logical properties; the rendering stays the same.
- Assets of FlaskSpark apps are plain CSS (no preprocessor): the bundle `css` (was `scss`) builds `ASSETS_CSS_ENTRY`
  (default `css/app.css`, was `scss/app.scss`) into `styles/app.min.css`, minified with `rcssmin` in production
  (`ASSETS_CSS_FILTERS`, `ASSETS_CSS_OUTPUT`); `ASSETS_BUNDLES` take the types `css` and `js`. Without a stylesheet of
  its own an app gets FlaskSpark's default `css/app.css`: a small base in modern CSS (cascade layer `flaskspark`,
  `:where()`, tokens `--fs-*` with `light-dark()`/`color-mix()`, nesting, a modular type scale with `pow()`, logical
  properties, styled flash messages) that follows Bootstrap 6's colour mode and yields to Bootstrap 6 and the app.
  A setting of the former pipeline (`ASSETS_SCSS_*`, `LIBSASS_INCLUDES`, `VENDOR_INCLUDE_BOOTSTRAP`) or a bundle of
  type `scss` stops the start with the replacement named (README «Upgrading from 0.x»).
- The logo in the docked sidebar takes the column's width (up to `--app-brand-max-height`, default `8rem`, aligned
  to the start); the top bar and the drawer's heading keep the small logo (`--app-brand-compact-height`). Themes no
  longer set the logo's height.
- `flaskspark.core.accounts.types()` is now `account_types()`: the function hid the submodule
  `flaskspark.core.accounts.types`. Calling `accounts.types()` still works (the submodule is callable) but warns
  (`DeprecationWarning`).
- FlaskSpark reads its settings from the environment when `FlaskSpark(...)` is created, not at the import of
  `flaskspark.config` (`flaskspark.config.from_environment()`; `Config` stays as the import's snapshot): values from
  `.env` or `CONFIG_DIR/app.env` loaded after the import (e.g. `ROLE_DEFAULTS`) count.
- `flaskspark.core.bus.ENV_FILE` is `None` by default; `bus.env_file()` reads `NATS_ENV_FILE` when NATS is first
  needed, after the env files (it may be set in `CONFIG_DIR/app.env`). Setting `ENV_FILE` still overrides it.
- `flaskspark.core.secrets`: the env files are loaded before the key's variable is named, so `APP_SECRET_KEY_ENV` may
  be set in `CONFIG_DIR/app.env`.
- The guardian's `Finding` has `params`; the core's checks give English source texts with `%(name)s` (no longer
  composed texts) and the guardian sends them in the application's language. A module's composed texts are sent as
  they are. `Finding.render(locale=None, cfg=None)` gives (title, message); the heartbeat's findings carry their
  `source` for the status tile (the visitor's language).
- The profile (`/profile`) exists with sign-in when a module adds a section (`PAGE_SECTIONS["profile"]`) or uses
  accounts; `/api/accounts` still only when a type is offered.
- `flaskspark.core`: outside the code every service is named `flaskspark-<service>` (e.g. `flaskspark-push`,
  `flaskspark-releases`), not after the application: the supervisor's children and log lines, the NATS connection
  names, gunicorn's process name, the status tiles (`process`), the guardian's findings and the command line
  (`services` with process name and unit, `status`, `service flaskspark-<name>`). `ServiceInfo.unit` defaults to
  `flaskspark-<name>.service`; a unit systemd does not know leaves a tile «unknown». Helpers
  `flaskspark.core.service.process_name()` / `unit_name()`. NATS subjects (`ms.<service>.heartbeat`), the service
  directory's keys, the NATS users and permissions and the guardian's finding keys keep the short name.
- `flaskspark.core`: an application is an installed package that delivers modules, and FlaskSpark is the runtime.
  Every installed module (entry point group `flaskspark.modules`) is loaded automatically, ordered by the manifest's
  new `POSITION`; `config.yaml` `modules:` / `APP_MODULES` are optional and restrict and order them. A module whose
  `DEPENDS` is not loaded is no longer a start failure: it is left out and logged. The app's package (entry point
  `flaskspark.apps`) brings `config.yaml`; themes come from the entry point group `flaskspark.themes`. The classic
  layout (`config.yaml`, `themes/`, `web/` in the project, modules as `modules.<name>`) keeps working.
- `flaskspark.core` migrations: one Alembic history per module (`<package>/migrations/versions`, its own branch), the
  core's own history `core` (and `signin` with sign-in); the web service and the supervisor upgrade at their start,
  with a backup first. No Flask-Migrate for them (the classic layout's `web/migrations` stays with Flask-Migrate).
- Python 3.11 or newer.
- The snapshot of the web components under `static/vendor/webcomponents` is gone (they are part of FlaskSpark);
  apps no longer register the `webcomponents` blueprint themselves.

### Removed
- The login provider `Default` (a stub that could not even be instantiated): `login_provider="Default"` stops the start
  and names `OAuth` and a provider of the app (`<app_module>/helpers/login_provider_default.py`) instead.
- Bootstrap 5 (`flaskspark/static/vendor/bootstrap`, `VENDOR_INCLUDE_BOOTSTRAP`): Bootstrap 6 comes with the web
  components (`VENDOR_INCLUDE_WEBCOMPONENTS`).
- SCSS: FlaskSpark's `scss/app.scss` (Bootstrap 5), the SCSS settings and include paths, the dependency `libsass`
  and the transitional build `python -m webcomponents.build`.
- The unused Bootstrap 5/webpack scripts `flaskspark/static/scripts/app.js` and `webpack.js`.

### Fixed
- «Settings»: the switches of «Access» and the role selects of «Users» saved nothing, and «Remove» on «Data» did
  nothing: `<ui-table>` moves its table into its shadow tree, where a control's change stays and a click reaches the
  page retargeted. `settings.js` listens on the tables and finds the controls on the composed path (new
  `flaskspark/shadow-paths.js`: `findInPath`, `hostOf`, `inTables`).
- OAuth sign-in: the very first user becomes an administrator again (the users were counted after the new one was
  added, so it got the role Guests).
- `<ui-list-group>`: a click on an action item's content (its text, an icon) chose nothing, only a click on its padding
  did (`ui-list-group:action`); the item is now found in the click's composed path (`list-group-click.js`).
- `ui-calendar`: dates are formatted with the full language tag (`locale` or `<html lang>`, e.g. `en-CH` or
  `en-GB`: day before month, not the US order) and the week starts on the locale's first day (Monday for `de`,
  `de-CH`, `en-GB`, `en-CH`); the new attribute `first-day` (`0`–`6` or a weekday name) sets it explicitly.
- `guard-check`: the findings are printed with their values in the application's language (`Finding.render()`),
  no longer as raw source texts with `%(name)s`.
- `ui-calendar`: the language follows the page (`locale`, else the nearest `lang`, i.e. `<html lang>`, else English;
  `de-CH` → `de`) instead of a fixed German; the toolbar's texts per language and translatable with `month-label`,
  `week-label`, `day-label`, `agenda-label`, `today-label`. They are now set through FullCalendar 7's `buttons`
  option (the former `buttonText` was ignored by FullCalendar 7). An unloadable FullCalendar is reported in English.
- `flaskspark.core.shares.dialog()` returns the kind's `LABEL` (an `N_()` text) translated into the current language
  (`i18n.tr`), also when a module calls it itself; the share API no longer translates it a second time.
- The core's catalogue: `"{pct} % of {size}"` was taken for a Python format too and failed `pybabel compile`'s check
  (`scripts/core-i18n`); now `"{percent} of {size}"` (the attachments' upload progress).
- `db revision` on a database that is not at the heads says «run `<app> db upgrade` first» instead of Alembic's
  traceback.
- Migrations: a revision with `depends_on` to another history no longer leaves that history «pending» or «without a
  revision» (Alembic keeps only the dependent revision in `alembic_version`; `migrations.positions()` derives where
  every history stands from the rows and what they depend on), so neither the start nor `db upgrade` demand
  `db adopt`.
- `attachments.attachment_of(session=)` (and so `update()`/`delete()` with a session) uses that session; it opened a
  session of its own and did not see the module's uncommitted work.
- The push session's topics come once each (two modules with the same `PUSH_TOPICS` pattern).
- The OAuth login provider loads the user with `db.session.get()` (no `LegacyAPIWarning`).
- View discovery registers only the view classes defined in a module: the imported `FlaskSparkMethodView` no longer
  gets a stray route `/<module_name>` in every view module.
- Production no longer overrides `ASSETS_CACHE`: apps can disable the webassets filter cache.

## [0.1.2] - 2026-02-22

### Highlights
- Major README overhaul with clearer, step-by-step documentation.
- Template/layout documentation consolidated and improved.
- Expanded class-based view documentation with practical HTML + API examples.
- Expanded OAuth/OIDC and custom login provider documentation.
- Expanded database/migration documentation with full workflows.
- i18n documentation now includes full Babel workflow (`extract`, `init`, `update`, `compile`).
- Custom login providers can now be resolved from the app first, with FlaskSpark fallback.

### Changed
- Login provider loading now checks modules in this order:
  1. `<app_module>.helpers.login_provider_<name>`
  2. `flaskspark.helpers.login_provider_<name>`
- Project version bumped to `0.1.2` in `pyproject.toml`.

### Documentation
- Added/updated guidance for:
  - quick start and configuration precedence
  - templates and framework hook blocks
  - assets and bundle behavior
  - class-based views and API method patterns
  - OAuth/OIDC setup and login-provider behavior
  - database migrations and model lifecycle
  - i18n setup and compile process
- Clarified current provider status:
  - `OAuth` is implemented
  - `Default` is currently a stub (not fully implemented yet)

### Notes
- No breaking API changes intended in this release.
- Existing apps should continue to work; custom login provider setups can now live in the app package directly.
