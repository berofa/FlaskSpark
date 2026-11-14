"""Snapshot export: a submodule brings core (JS and CSS), its module's shared files and the vendor libraries."""
from __future__ import annotations

import json

from webcomponents.export import export


def test_export_of_a_submodule_contains_everything_it_loads(tmp_path):
    summary = export(tmp_path, ["bootstrap/ui-alert"])

    for rel in [
        "core/shadow-component-element.js",
        "core/shadow-sheet-transforms.js",
        "core/ui-shadow-base.css",
        "modules/bootstrap/shadow-styles.js",
        "modules/bootstrap/ui-alert/ui-alert.js",
        "modules/bootstrap/ui-alert/ui-alert.css",
        "vendor/bootstrap6/css/bootstrap.min.css",
        "vendor/bootstrap6/LICENSE",
    ]:
        assert (tmp_path / rel).is_file(), rel
    assert summary["modules"] == {"bootstrap": ["ui-alert"]}
    assert json.loads((tmp_path / "webcomponents.json").read_text())["vendor"] == summary["vendor"]


def test_partial_export_leaves_out_the_module_entry(tmp_path):
    export(tmp_path, ["bootstrap/ui-alert"])

    assert not (tmp_path / "modules/bootstrap/bootstrap.js").exists()


def test_export_without_vendor(tmp_path):
    summary = export(tmp_path, ["bootstrap/ui-alert"], with_vendor=False)

    assert summary["vendor"] == []
    assert not (tmp_path / "vendor").exists()
