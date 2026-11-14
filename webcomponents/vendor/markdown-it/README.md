# markdown-it (vendored)

- Version: 14.1.0 (npm `markdown-it`; the version markdown-it-py 4.x ports, so the browser renders like the server)
- Source: https://registry.npmjs.org/markdown-it/-/markdown-it-14.1.0.tgz, file `dist/markdown-it.min.js`, unchanged
  (SHA-256 `38c70a1e7ca91ab40e2d9e6e60129851a717ed1c7d4acbbdd41bf9503791cf68`)
- License: MIT (see `LICENSE`). The bundle contains markdown-it's dependencies entities (BSD-2-Clause), linkify-it,
  mdurl, punycode.js and uc.micro (MIT); their licences are in `LICENSES-bundled.txt`.
- The file is a UMD build: imported as an ES module it sets `globalThis.markdownit`.

Used by `ui-markdown` and `ui-markdown-editor` (module `bootstrap`, `ui-markdown/markdown.js`), loaded on first use.
