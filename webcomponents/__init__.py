"""webcomponents: web components grouped into modules and submodules.

The package directory is the distributable asset tree:

    core/        shared base classes (JS)
    vendor/      third-party libraries, shared by all modules
    modules/<module>/<submodule>/   one component each (JS, plain CSS, manifest)

Python adds a Flask blueprint that serves the tree, a snapshot export for projects without
Python (``python -m webcomponents.export``) and the server-side grid layout helpers.
"""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, send_from_directory

from .grid_layout import build_unit_areas, default_layout, normalize_layout

PACKAGE_ROOT = Path(__file__).resolve().parent

# Only browser assets are served; Python sources stay private.
SERVED_SUFFIXES = {".js", ".mjs", ".css", ".map", ".json", ".svg", ".png", ".jpg", ".gif", ".webp", ".woff", ".woff2"}


def create_blueprint(url_prefix: str = "/webcomponents", name: str = "webcomponents", versioned: bool = True) -> Blueprint:
    """Serve the asset tree (``url_for("webcomponents.static", filename="modules/bootstrap/bootstrap.js")``).

    versioned: url_for builds /webcomponents/v-<version>/…, cached for a year (delivery.version_static)."""
    blueprint = Blueprint(name, __name__, url_prefix=url_prefix)

    def serve(filename: str):
        if Path(filename).suffix.lower() not in SERVED_SUFFIXES:
            abort(404)
        return send_from_directory(PACKAGE_ROOT, filename)

    blueprint.add_url_rule("/<path:filename>", endpoint="static", view_func=serve)
    if versioned:
        from .delivery import version_static

        version_static(blueprint, "static", PACKAGE_ROOT, view_func=serve)
    return blueprint


__all__ = [
    "PACKAGE_ROOT",
    "build_unit_areas",
    "create_blueprint",
    "default_layout",
    "normalize_layout",
]
