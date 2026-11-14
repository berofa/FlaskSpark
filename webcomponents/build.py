"""Compile the SCSS of host-app modules to CSS (transitional, until they are plain CSS).

The library itself is plain CSS and ships no SCSS (no mixins, no vendored
Bootstrap sources). This tool stays for host applications whose own modules
still have ``*.scss`` files: every non-partial ``*.scss`` below a modules
directory is compiled to a ``.css`` file next to it; the ``scss/`` folders of
the given modules directories are the include paths.

Usage:
    python -m webcomponents.build path/to/modules ...  # needs libsass (a dependency of FlaskSpark)
"""

from __future__ import annotations

import sys
from pathlib import Path


def include_paths(modules_dirs: list[Path]) -> list[str]:
    paths: list[Path] = []
    for modules_dir in modules_dirs:
        paths += sorted(p for p in modules_dir.glob("*/scss") if p.is_dir())
    return [str(p) for p in paths]


def scss_entries(modules_dir: Path) -> list[Path]:
    return sorted(p for p in modules_dir.rglob("*.scss") if not p.name.startswith("_") and p.parent.name != "scss")


def compile_modules(modules_dir: Path, extra_modules_dirs: list[Path] | None = None) -> int:
    entries = scss_entries(modules_dir)
    if not entries:
        return 0
    import sass  # libsass, a dependency of FlaskSpark

    includes = include_paths([modules_dir, *(extra_modules_dirs or [])])
    for entry in entries:
        css = sass.compile(filename=str(entry), include_paths=includes, output_style="expanded")
        entry.with_suffix(".css").write_text(css, encoding="utf-8")
        print(f"{entry.relative_to(modules_dir)} -> {entry.with_suffix('.css').name} ({len(css)} bytes)")
    return len(entries)


def main(argv: list[str]) -> int:
    if not argv:
        print("The library is plain CSS, nothing to build. Usage: python -m webcomponents.build path/to/modules ...",
              file=sys.stderr)
        return 0
    for target in (Path(arg).resolve() for arg in argv):
        if not target.is_dir():
            print(f"Not a directory: {target}", file=sys.stderr)
            return 1
        if not compile_modules(target):
            print(f"No SCSS entries under {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
