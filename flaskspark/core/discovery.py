"""What is installed: the application, its modules and themes, found through Python entry points (importlib.metadata).

An application is a Python distribution that declares, in its pyproject.toml:

    [project.entry-points."flaskspark.apps"]
    myapp = "myapp"                                  # the app's package (with config.yaml, locales/, templates/, ...)

    [project.entry-points."flaskspark.modules"]
    notes = "myapp.modules.notes"                    # name -> the module's package (manifest in <package>.module)

    [project.entry-points."flaskspark.themes"]
    mybrand = "myapp.theme"                          # name -> a package directory with theme.yaml, theme.css, images/

Every installed module is loaded (flaskspark.core.modules); nothing is switched on or off. One installation runs
exactly one application: with several distributions that declare one, APP_NAME picks it.

Nothing here imports a package: only its location is looked up (importlib.util.find_spec), so this runs early (paths).
"""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path

APPS, MODULES, THEMES = "flaskspark.apps", "flaskspark.modules", "flaskspark.themes"


@dataclass(frozen=True)
class Entry:
    """An entry point: its name and the dotted package it names."""

    name: str
    package: str
    distribution: str = ""


def entries(group: str) -> list[Entry]:
    """Every entry point of `group`, in the order of the installed distributions (a name declared twice: the first)."""
    out: dict[str, Entry] = {}
    for ep in entry_points(group=group):
        if ep.name not in out:
            dist = getattr(ep, "dist", None)
            out[ep.name] = Entry(ep.name, ep.value.split(":", 1)[0].strip(), getattr(dist, "name", "") or "")
    return list(out.values())


def package_dir(package: str) -> Path | None:
    """The directory of a package, None if it is not installed (its parent packages are imported, the package not)."""
    try:
        spec = importlib.util.find_spec(package)
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.submodule_search_locations:
        return None
    return Path(list(spec.submodule_search_locations)[0]).resolve()


class AppError(RuntimeError):
    """Several applications are installed and APP_NAME names none of them."""


def app(name: str | None = None) -> Entry | None:
    """The application of this installation (entry point group flaskspark.apps): the only one, with several the one
    APP_NAME names; None without one (a project in the classic layout, config.yaml in the project directory)."""
    found = entries(APPS)
    if len(found) <= 1:
        return found[0] if found else None
    name = name if name is not None else os.environ.get("APP_NAME")
    match = next((e for e in found if e.name == name), None)
    if match is None:
        raise AppError(f"several applications are installed ({', '.join(e.name for e in found)}): "
                       "APP_NAME picks one")
    return match


def modules() -> list[Entry]:
    """The installed modules (entry point group flaskspark.modules)."""
    return entries(MODULES)


def themes() -> dict[str, Path]:
    """The installed themes: name -> directory (entry point group flaskspark.themes)."""
    out = {}
    for entry in entries(THEMES):
        directory = package_dir(entry.package)
        if directory is not None:
            out[entry.name] = directory
    return out
