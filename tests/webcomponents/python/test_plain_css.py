"""No preprocessor: the library and the docs app are plain CSS, built without libsass."""
from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCS_CSS = ROOT / "docs" / "app" / "static" / "styles" / "app.min.css"

# Builds the docs app (docs/run.py builds its asset bundles on start) with libsass made unimportable.
BUILD_WITHOUT_SASS = """
import runpy, sys
sys.modules["sass"] = None
app = runpy.run_path("docs/run.py", run_name="docs_app")["app"]
print(app.config["ASSETS_SCSS_ENTRY"], app.config["ASSETS_SCSS_FILTERS"])
"""


def test_no_scss_sources_left():
    sources = sorted(
        str(path.relative_to(ROOT))
        for folder in ("webcomponents", "docs")
        for pattern in ("*.scss", "*.sass")
        for path in (ROOT / folder).rglob(pattern)
    )
    assert sources == []


def test_package_ships_no_scss_and_develops_without_libsass():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_data = pyproject["tool"]["setuptools"]["package-data"]["webcomponents"]
    assert [pattern for pattern in package_data if "scss" in pattern] == []
    dev = pyproject["project"]["optional-dependencies"]["dev"]
    assert [requirement for requirement in dev if "libsass" in requirement] == []


def test_docs_app_builds_its_css_without_libsass():
    DOCS_CSS.unlink(missing_ok=True)
    result = subprocess.run(
        [sys.executable, "-c", BUILD_WITHOUT_SASS],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.split() == ["css/app.css", "rcssmin"]
    css = DOCS_CSS.read_text(encoding="utf-8")
    assert ".docs-layout" in css and ".docs-resizable" in css
    assert "/*" not in css  # minified: comments are gone
