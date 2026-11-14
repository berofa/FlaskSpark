"""Fast delivery of the asset trees: versioned URLs with long caching, and module preloading.

Web components are ES modules that import each other; without help the browser asks for every file on every
page (no-cache) and discovers the imports one level after the other, a round trip per level. Two remedies:

- version_static(scope, endpoint, directory): url_for(endpoint, filename=…) builds /…/v-<version>/<filename>;
  those answers are cached for a year (immutable). Relative imports inside a module keep the version segment,
  so a whole module tree is cached. The version follows the files (newest mtime, count, sizes; looked at again
  every VERSION_TTL seconds): an edited file gives new URLs at once, also without a restart. The plain URLs keep
  working (no-cache), e.g. for links from outside.
- install_preload(app, trees): every HTML answer gets <link rel="modulepreload"> for all modules its module
  scripts import (directly or not, also through the page's import map) and <link rel="preload" as="fetch"> for
  the stylesheets the modules load with new URL("./x.css", import.meta.url): the browser loads them in parallel
  instead of level by level. trees maps URL prefixes to directories ({"/static/": app.static_folder, …}).

A URL prefix may be served from several directories (e.g. FlaskSpark's module packages, FlaskSpark.static_dirs):
pass a list, in lookup order, to version_static and as a value in trees; the first directory with the file wins.

create_blueprint() versions the webcomponents tree by default.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import threading
import time
import zlib
from pathlib import Path

from flask import Flask, g, request

VERSION_TTL = 3.0
YEAR = 365 * 24 * 3600
_SEGMENT = re.compile(r"/v-[0-9a-f]{8}/")
_IMPORT = re.compile(r"""(?:^|[;\s}])(?:import|export)\s*(?:[^'"`;]*?\sfrom\s*)?["']([^"']+)["']""", re.M)
_ASSET = re.compile(r"""new\s+URL\(\s*["']([^"']+\.css)["']\s*,\s*import\.meta\.url\s*\)""")
_SCRIPT = re.compile(r"""<script\b[^>]*\btype=["']module["'][^>]*\bsrc=["']([^"']+)["']""", re.I)
_SCRIPT2 = re.compile(r"""<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*\btype=["']module["']""", re.I)
_COMMENTS = re.compile(r"/\*.*?\*/|^\s*//[^\n]*", re.S | re.M)  # block comments, whole-line // comments
_IMPORTMAP = re.compile(r"""<script\b[^>]*type=["']importmap["'][^>]*>(.*?)</script>""", re.I | re.S)


def _dirs(directory) -> list[Path]:
    return [Path(d) for d in directory] if isinstance(directory, (list, tuple)) else [Path(directory)]


class _Version:
    """Short hash of the files of one or several directory trees, looked at again after VERSION_TTL seconds."""

    def __init__(self, directory):
        self.directories = _dirs(directory)
        self.value = ""
        self.checked = 0.0
        self.lock = threading.Lock()

    def get(self) -> str:
        now = time.monotonic()
        if now - self.checked < VERSION_TTL and self.value:
            return self.value
        with self.lock:
            if now - self.checked >= VERSION_TTL or not self.value:
                newest, count, size = 0, 0, 0
                for directory in self.directories:
                    for root, dirs, files in os.walk(directory):
                        dirs[:] = [d for d in dirs if not d.startswith((".", "__")) and d != "@eaDir"]
                        for name in files:
                            try:
                                st = os.stat(os.path.join(root, name))
                            except OSError:
                                continue
                            newest, count, size = max(newest, st.st_mtime_ns), count + 1, size + st.st_size
                self.value = f"{zlib.crc32(f'{newest}:{count}:{size}'.encode()):08x}"
                self.checked = now
        return self.value


def version_static(scope, endpoint: str, directory: str | Path | list, view_func=None,
                   rule: str = "/v-<v>/<path:filename>") -> _Version:
    """Version the static files of `endpoint` (an app's "static" or a blueprint's): see the module doc. scope is
    the Flask app or the blueprint that owns the endpoint (a blueprint passes its view_func); rule is relative to
    it (for the app: below its static_url_path); directory may be a list (several trees under one endpoint). Returns
    the version (version.get())."""
    version = _Version(directory)
    is_app = isinstance(scope, Flask)
    full = endpoint if is_app else f"{scope.name}.{endpoint}"
    if is_app:
        scope.add_url_rule(f"{scope.static_url_path}{rule}", endpoint=endpoint, view_func=scope.view_functions[endpoint])
    else:
        scope.add_url_rule(rule, endpoint=endpoint, view_func=view_func)

    def defaults(ep, values):
        if ep == full and "v" not in values:
            values["v"] = version.get()

    def strip(ep, values):
        if ep == full and values and "v" in values:
            values.pop("v")
            g.webcomponents_versioned = True

    def cache(response):
        if getattr(g, "webcomponents_versioned", False) and request.endpoint == full and response.status_code in (200, 304):
            response.cache_control.no_cache = None
            response.cache_control.public = True
            response.cache_control.max_age = YEAR
            response.cache_control.immutable = True
        return response

    if is_app:
        scope.url_defaults(defaults)
        scope.url_value_preprocessor(strip)
        scope.after_request(cache)
    else:
        scope.app_url_defaults(defaults)
        scope.url_value_preprocessor(strip)
        scope.after_request(cache)
    return version


class _Graph:
    """Modules and stylesheets reachable from a page's module scripts (URL paths, as the browser asks for them)."""

    def __init__(self, trees: dict):
        self.trees = sorted(((p if p.endswith("/") else p + "/", _dirs(d)) for p, d in trees.items()), key=lambda t: -len(t[0]))
        self.cache: dict[tuple, tuple[list[str], list[str]]] = {}
        self.lock = threading.Lock()

    def _file(self, url: str) -> Path | None:
        for prefix, directories in self.trees:
            if url.startswith(prefix):
                rest = _SEGMENT.sub("/", "/" + url[len(prefix):], count=1).lstrip("/")
                for directory in directories:
                    path = (directory / rest).resolve()
                    if path.is_file() and directory.resolve() in path.parents:
                        return path
                return None
        return None

    @staticmethod
    def _resolve(spec: str, base: str, imports: dict[str, str]) -> str | None:
        if spec.startswith(("./", "../", "/")):
            return posixpath.normpath(posixpath.join(posixpath.dirname(base), spec)) if not spec.startswith("/") else spec
        for key in sorted(imports, key=len, reverse=True):
            if key.endswith("/") and spec.startswith(key):
                return imports[key] + spec[len(key):]
            if spec == key:
                return imports[key]
        return None  # a package without a mapping, a full URL: not ours

    def walk(self, entries: tuple[str, ...], imports: dict[str, str]) -> tuple[list[str], list[str]]:
        key = (entries, tuple(sorted(imports.items())))
        with self.lock:
            if key in self.cache:
                return self.cache[key]
        modules: list[str] = []
        styles: list[str] = []
        seen = set(entries)
        todo = list(entries)
        while todo:
            url = todo.pop(0)
            path = self._file(url)
            if path is None:
                continue
            try:
                text = _COMMENTS.sub("", path.read_text(encoding="utf-8", errors="replace"))  # examples in docs aren't imports
            except OSError:
                continue
            for spec in _IMPORT.findall(text):
                dep = self._resolve(spec, url, imports)
                if dep and dep.endswith(".js") and dep not in seen:
                    seen.add(dep)
                    modules.append(dep)
                    todo.append(dep)
            for spec in _ASSET.findall(text):
                css = self._resolve(spec, url, imports)
                if css and css not in seen:
                    seen.add(css)
                    styles.append(css)
        with self.lock:
            if len(self.cache) > 200:
                self.cache.clear()
            self.cache[key] = (modules, styles)
        return modules, styles


def install_preload(app, trees: dict) -> None:
    """Add preload links for the module graph to every HTML answer (see the module doc)."""
    graph = _Graph(trees)

    @app.after_request
    def preload(response):
        if (response.status_code != 200 or response.direct_passthrough or response.is_streamed
                or response.mimetype != "text/html"):
            return response
        html = response.get_data(as_text=True)
        head = html.find("</head>")
        if head < 0:
            return response
        entries = tuple(dict.fromkeys(m.split("?")[0] for m in _SCRIPT.findall(html) + _SCRIPT2.findall(html)))
        if not entries:
            return response
        imports: dict[str, str] = {}
        for raw in _IMPORTMAP.findall(html):
            try:
                imports.update(json.loads(raw).get("imports") or {})
            except ValueError:
                pass
        try:
            modules, styles = graph.walk(entries, imports)
        except Exception:  # noqa: BLE001 - the page works without preloading
            return response
        links = "".join(f'<link rel="modulepreload" href="{u}">' for u in [*entries, *modules])
        links += "".join(f'<link rel="preload" as="fetch" crossorigin href="{u}">' for u in styles)
        response.set_data(html[:head] + links + html[head:])
        return response
