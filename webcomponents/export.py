"""Export a snapshot of the browser assets for projects without Python.

Copies the runtime files (JS, compiled CSS) of the selected modules or
submodules together with ``core/`` and the vendor libraries named in the
module manifests, keeping the package layout, so relative imports and
stylesheet URLs keep working. A ``webcomponents.json`` records what was
exported and from which version.

Usage:
    python -m webcomponents.export TARGET_DIR                       # all modules
    python -m webcomponents.export TARGET_DIR bootstrap             # one module
    python -m webcomponents.export TARGET_DIR bootstrap/ui-tooltip  # single submodules (+ their requires)
    python -m webcomponents.export TARGET_DIR bootstrap --no-vendor # skip vendor libraries
"""

from __future__ import annotations

import argparse
import json
import shutil
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from . import PACKAGE_ROOT

MODULES_DIR = PACKAGE_ROOT / "modules"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def module_names() -> list[str]:
    return sorted(p.parent.name for p in MODULES_DIR.glob("*/module.json"))


def submodule_names(module: str) -> list[str]:
    return sorted(p.parent.name for p in (MODULES_DIR / module).glob("*/submodule.json"))


def resolve(selection: list[str]) -> dict[str, set[str]]:
    """Map module -> set of submodules, including submodule requirements."""
    wanted: dict[str, set[str]] = {}
    pending = []
    for item in selection or module_names():
        module, _, sub = item.partition("/")
        if not (MODULES_DIR / module / "module.json").is_file():
            raise SystemExit(f"Unknown module: {module}")
        wanted.setdefault(module, set())
        pending += [(module, s) for s in ([sub] if sub else submodule_names(module))]
    while pending:
        module, sub = pending.pop()
        if sub in wanted[module]:
            continue
        manifest = MODULES_DIR / module / sub / "submodule.json"
        if not manifest.is_file():
            raise SystemExit(f"Unknown submodule: {module}/{sub}")
        wanted[module].add(sub)
        pending += [(module, req) for req in load_json(manifest).get("requires", [])]
    return wanted


def copy(rel: Path, target: Path) -> None:
    source = PACKAGE_ROOT / rel
    destination = target / rel
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def export(target: Path, selection: list[str], with_vendor: bool = True) -> dict:
    wanted = resolve(selection)
    for pattern in ("*.js", "*.css"):
        for path in sorted((PACKAGE_ROOT / "core").glob(pattern)):
            copy(path.relative_to(PACKAGE_ROOT), target)
    vendors: set[str] = set()
    for module, subs in wanted.items():
        manifest = load_json(MODULES_DIR / module / "module.json")
        vendors.update(manifest.get("vendor", []))
        complete = subs == set(submodule_names(module))
        for name in manifest.get("files", []):
            # The module entry imports every submodule; only export it with the complete module.
            if name == manifest.get("entry") and not complete:
                continue
            copy(Path("modules", module, name), target)
        for sub in sorted(subs):
            sub_manifest = load_json(MODULES_DIR / module / sub / "submodule.json")
            for name in [*sub_manifest.get("files", []), "submodule.json"]:
                copy(Path("modules", module, sub, name), target)
        copy(Path("modules", module, "module.json"), target)
    if with_vendor:
        for vendor in sorted(vendors):
            copy(Path("vendor", vendor), target)
    try:
        package_version = version("FlaskSpark")
    except PackageNotFoundError:
        package_version = "unknown"
    summary = {
        "version": package_version,
        "modules": {module: sorted(subs) for module, subs in sorted(wanted.items())},
        "vendor": sorted(vendors) if with_vendor else [],
    }
    (target / "webcomponents.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", type=Path)
    parser.add_argument("selection", nargs="*", help="module or module/submodule (default: all)")
    parser.add_argument("--no-vendor", action="store_true")
    args = parser.parse_args()
    summary = export(args.target.resolve(), args.selection, with_vendor=not args.no_vendor)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
