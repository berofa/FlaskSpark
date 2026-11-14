"""The transitional SCSS build for host-app modules: no library include paths, libsass only when needed."""
from __future__ import annotations

import sys

import pytest

from webcomponents import PACKAGE_ROOT, build


def _module(root, name, files):
    for relative, content in files.items():
        path = root / name / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_include_paths_are_the_host_modules_scss_folders_only(tmp_path):
    _module(tmp_path, "shop", {"scss/_mixins.scss": "", "ui-cart/ui-cart.scss": ""})
    _module(tmp_path, "plain", {"ui-x/ui-x.css": ""})
    paths = build.include_paths([tmp_path])
    assert paths == [str(tmp_path / "shop" / "scss")]
    assert not any(path.startswith(str(PACKAGE_ROOT)) for path in paths)


def test_entries_skip_partials_and_scss_folders(tmp_path):
    _module(tmp_path, "shop", {"scss/base.scss": "", "ui-cart/_part.scss": "", "ui-cart/ui-cart.scss": ""})
    assert build.scss_entries(tmp_path) == [tmp_path / "shop" / "ui-cart" / "ui-cart.scss"]


def test_plain_css_modules_need_no_libsass(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "sass", None)  # import sass would fail
    _module(tmp_path, "plain", {"ui-x/ui-x.css": ":host { display: block; }"})
    assert build.compile_modules(tmp_path) == 0
    assert build.main([]) == 0
    assert build.main([str(tmp_path)]) == 0


def test_compiles_host_scss_with_its_own_partials(tmp_path):
    pytest.importorskip("sass")
    _module(tmp_path, "shop", {
        "scss/_mixins.scss": "@mixin host-base { :host { display: block; } }",
        "ui-cart/ui-cart.scss": '@import "mixins";\n@include host-base;\n',
    })
    assert build.compile_modules(tmp_path) == 1
    assert "display: block" in (tmp_path / "shop" / "ui-cart" / "ui-cart.css").read_text(encoding="utf-8")
