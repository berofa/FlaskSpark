# Third-Party Notices

This project includes third-party software components.

## Bootstrap 6

- Component: Bootstrap 6.0.0-alpha.1 (precompiled CSS and JS bundle, `VENDOR_INCLUDE_WEBCOMPONENTS`)
- Upstream: https://github.com/twbs/bootstrap
- License: MIT License
- License text: `webcomponents/vendor/bootstrap6/LICENSE`

Distributed unchanged under `webcomponents/vendor/bootstrap6/`, as part of the
web components snapshot.

## Vanilla Calendar Pro

- Component: Vanilla Calendar Pro 3.4.0 (date picker of `ui-datepicker`)
- Upstream: https://github.com/uvarov-frontend/vanilla-calendar-pro
- License: MIT License
- License text: `webcomponents/vendor/vanilla-calendar-pro/LICENSE`

Distributed under `webcomponents/vendor/vanilla-calendar-pro/`, as part of the
web components snapshot.

## FullCalendar

- Component: FullCalendar 7.1.3 (Vanilla JS, `ui-calendar`)
- Upstream: https://github.com/fullcalendar/fullcalendar
- License: MIT License
- License text: `webcomponents/vendor/fullcalendar/LICENSE.md`

Distributed unchanged under `webcomponents/vendor/fullcalendar/`.

## Bootstrap Icons

- Component: Bootstrap Icons 1.13.1 (icon font and SVG sprite of `flaskspark.core`'s layout)
- Upstream: https://github.com/twbs/icons
- License: MIT License
- License text: `flaskspark/core/web/static/flaskspark/vendor/bootstrap-icons/LICENSE`

Distributed unchanged under `flaskspark/core/web/static/flaskspark/vendor/bootstrap-icons/`.

## markdown-it

- Component: markdown-it 14.1.0 (`dist/markdown-it.min.js`, Markdown in the browser: `ui-markdown`,
  `ui-markdown-editor`), with its bundled dependencies entities (BSD-2-Clause), linkify-it, mdurl, punycode.js and
  uc.micro (MIT)
- Upstream: https://github.com/markdown-it/markdown-it
- License: MIT License
- License text: `webcomponents/vendor/markdown-it/LICENSE`; the bundled libraries' licences:
  `webcomponents/vendor/markdown-it/LICENSES-bundled.txt`

Distributed unchanged under `webcomponents/vendor/markdown-it/` (origin and checksum in its `README.md`).

## Python dependencies for Markdown

`flaskspark.markdown` uses, as installed dependencies (not distributed with FlaskSpark): markdown-it-py with
linkify-it-py (MIT, https://github.com/executablebooks/markdown-it-py, https://github.com/tsutsu3/linkify-it-py) and
nh3 (MIT, https://github.com/messense/nh3; it builds on ammonia, MIT/Apache-2.0).

## Web components

The web components (`webcomponents/`) are part of FlaskSpark and under its licence; the third-party libraries they use
are listed above.

---

This file should be updated whenever new third-party components are added,
removed, or upgraded.
