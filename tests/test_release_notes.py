"""scripts/release_notes.py: the release notes of a version are its section of CHANGELOG.md."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release_notes.py"

CHANGELOG = """# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added
- Something new.

## [1.2.0] - 2026-12-01

### Added
- A feature.

### Fixed
- A bug.

## [1.1.0] - 2026-11-20

### Changed
- Older.
"""


def _module():
    spec = importlib.util.spec_from_file_location("release_notes", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_section_of_a_version_without_its_heading():
    notes = _module().section(CHANGELOG, "1.2.0")

    assert notes == "### Added\n- A feature.\n\n### Fixed\n- A bug."


def test_the_last_section_ends_with_the_file():
    assert _module().section(CHANGELOG, "1.1.0") == "### Changed\n- Older."


def test_a_leading_v_is_ignored():
    assert _module().section(CHANGELOG, "v1.1.0") == "### Changed\n- Older."


def test_a_version_without_a_section_is_an_error():
    with pytest.raises(LookupError):
        _module().section(CHANGELOG, "1.0.0")


def test_a_version_is_not_matched_by_its_prefix():
    with pytest.raises(LookupError):
        _module().section(CHANGELOG + "\n## [1.1.0.1] - 2026-11-21\n- x\n", "1.1")


def test_the_command_line_prints_the_notes_of_the_projects_changelog():
    result = subprocess.run([sys.executable, str(SCRIPT), "1.0.0"], capture_output=True, text=True, cwd=ROOT,
                            check=True)

    assert result.stdout.startswith("### Highlights\n")
    assert "## [" not in result.stdout


def test_the_command_line_fails_for_an_unknown_version():
    result = subprocess.run([sys.executable, str(SCRIPT), "0.0.1"], capture_output=True, text=True, cwd=ROOT)

    assert result.returncode != 0 and "0.0.1" in result.stderr
