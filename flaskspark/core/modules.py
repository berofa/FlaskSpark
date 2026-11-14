"""The modules of this installation: every installed module is loaded (flaskspark.core.discovery, entry point group
flaskspark.modules: name -> package). Nothing switches a module on or off; what a visitor may use decides the access
(the areas per role).

- Order: Module.POSITION, then NAME (the navigation, the tiles and areas of equal position follow it).
- An explicit list in config.yaml `modules:` (APP_MODULES overrides, comma separated) restricts the installed modules
  to those and orders them; a name without an entry point is looked up as the package modules.<name> (the classic
  layout, src/modules/<name>/).
- DEPENDS: a module whose dependency is not loaded is not loaded either (logged as an error, `<app> modules` shows it).
- OPTIONAL_DEPENDS: used when there; the module asks is_enabled(cfg, name) first.

load() imports the manifests (<package>.module, an flaskspark.core.module.Module subclass) and returns them after the
core's own. The core never imports a module otherwise.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path

from . import discovery
from .module import Module

log = logging.getLogger(__name__)

_loaded: dict[tuple, list[Module]] = {}
_skipped: dict[tuple, dict[str, str]] = {}


def _classic(name: str) -> str | None:
    package = f"modules.{name}"
    try:
        if importlib.util.find_spec("modules") is not None and importlib.util.find_spec(package) is not None:
            return package
    except (ImportError, ValueError):
        pass
    return None


def installed() -> dict[str, str]:
    """The installed modules: name -> package (entry points)."""
    return {e.name: e.package for e in discovery.modules()}


def package_of(name: str) -> str:
    """The package of the module `name`: its entry point, else modules.<name> (the classic layout)."""
    package = installed().get(name) or _classic(name)
    if package is None:
        raise ModuleNotFoundError(f"no module {name!r} (no entry point in flaskspark.modules, no package modules.{name})")
    return package


def selected(cfg) -> list[tuple[str, str]]:
    """(name, package) of the modules this installation loads, before their dependencies are checked: config.yaml
    `modules:` (APP_MODULES) when given, else every installed one. A name that is not installed is logged and left out."""
    found = installed()
    explicit = tuple(cfg.modules) if cfg is not None else ()
    if not explicit:
        return list(found.items())
    out = []
    for name in explicit:
        package = found.get(name) or _classic(name)
        if package is None:
            log.error("module %r (config.yaml modules: / APP_MODULES) is not installed: not loaded", name)
            continue
        out.append((name, package))
    return out


def _manifest(package: str) -> Module:
    mod = importlib.import_module(f"{package}.module")
    classes = [c for _, c in inspect.getmembers(mod, inspect.isclass) if issubclass(c, Module) and c is not Module
               and c.__module__ == mod.__name__]
    if len(classes) != 1:
        raise TypeError(f"{package}.module: exactly one Module subclass expected, found {len(classes)}")
    return classes[0]()


def load(cfg) -> list[Module]:
    """The core's manifest and those of the loaded modules (cached per set). A module whose DEPENDS names a module that
    is not loaded is left out (logged)."""
    chosen = selected(cfg)
    key = tuple(chosen)
    if key not in _loaded:
        from .core_module import Core

        found: list[Module] = []
        for name, package in chosen:
            module = _manifest(package)
            if module.NAME != name:
                raise TypeError(f"module {name!r} ({package}): its manifest is called {module.NAME!r}")
            module.PACKAGE = package
            found.append(module)
        if not (cfg is not None and cfg.modules):
            found.sort(key=lambda m: (m.POSITION, m.NAME))
        skipped: dict[str, str] = {}
        changed = True
        while changed:  # a module left out may leave out the ones that need it
            changed = False
            present = {m.NAME for m in found} | {"core"}
            for module in list(found):
                missing = [d for d in module.DEPENDS if d not in present]
                if missing:
                    found.remove(module)
                    skipped[module.NAME] = f"needs {', '.join(missing)}"
                    log.error("module %r is not loaded: it needs %s (not installed or not loaded)", module.NAME,
                              ", ".join(missing))
                    changed = True
        modules: list[Module] = [Core(cfg), *found]
        for module in modules:
            module.register()
        _loaded[key] = modules
        _skipped[key] = skipped
    return _loaded[key]


def skipped(cfg) -> dict[str, str]:
    """The installed modules that are not loaded: name -> why (a missing dependency)."""
    load(cfg)
    return dict(_skipped[tuple(selected(cfg))])


def delivered_names(cfg) -> set[str]:
    """The names of every module the application delivers, loaded or not (nothing is imported): the selected ones
    (config.yaml `modules:` / APP_MODULES, else every installed one) and every installed one."""
    return {name for name, _ in selected(cfg)} | set(installed())


def selected_manifests(cfg) -> list[Module]:
    """The manifests of the selected modules, loaded or not (a missing dependency), without the core's: the loaded
    ones, then the others (imported, not registered)."""
    out = list(load(cfg)[1:])
    have = {m.NAME for m in out}
    for name, package in selected(cfg):
        if name not in have:
            module = _manifest(package)
            module.PACKAGE = package
            out.append(module)
    return out


def delivered(cfg) -> list[Module]:
    """Every module the application delivers, loaded or not: the core's manifest, the selected modules'
    (selected_manifests), then the manifests of the installed ones config.yaml `modules:` leaves out. Those are only
    imported here (their manifest, not their models; e.g. «Settings › Data»), never at the start. One that cannot be
    imported is logged and left out."""
    out = [load(cfg)[0], *selected_manifests(cfg)]
    have = {m.NAME for m in out}
    for name, package in installed().items():
        if name in have:
            continue
        try:
            module = _manifest(package)
        except Exception:  # noqa: BLE001 - a broken module must not hide the others
            log.exception("module %r (%s): manifest not readable", name, package)
            continue
        module.PACKAGE = package
        out.append(module)
    return out


def version(module: Module) -> str:
    """The version of the distribution that delivers a module ("" when unknown, e.g. the classic layout)."""
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as dist_version

    if module.NAME == "core":
        names = ["flaskspark"]
    else:
        names = [e.distribution for e in discovery.modules() if e.name == module.NAME and e.distribution]
        found = discovery.app()
        if found is not None and found.distribution:
            names.append(found.distribution)
    for name in names:
        try:
            return dist_version(name)
        except PackageNotFoundError:
            continue
    return ""


def names(cfg) -> tuple[str, ...]:
    """The loaded modules (without the core), in their order."""
    return tuple(m.NAME for m in load(cfg)[1:]) if cfg is not None else ()


enabled = names  # the former name: the loaded modules are the enabled ones


def is_enabled(cfg, name: str) -> bool:
    """The module `name` is loaded here: a module checks it before it uses one of its OPTIONAL_DEPENDS."""
    return name in names(cfg)


def get(cfg, name: str) -> Module | None:
    return next((m for m in load(cfg) if m.NAME == name), None)


def directory(module: Module) -> Path | None:
    """The directory of a module's package (None for the core)."""
    return discovery.package_dir(module.PACKAGE) if module.PACKAGE else None


def internal(cfg) -> list[str]:
    """The loaded modules that are not Module.EXPOSURE PUBLIC: what an instance reachable from the internet must not
    have (the application decides what to do with it, e.g. refuse to start)."""
    from .module import PUBLIC

    return [m.NAME for m in load(cfg)[1:] if m.EXPOSURE != PUBLIC]


def services(cfg) -> list:
    """Every service (flaskspark.core.module.ServiceInfo) of the core and the loaded modules."""
    return [s for m in load(cfg) for s in m.SERVICES]


def web_packages(cfg) -> list[str]:
    """The web parts (<package>.web) of the loaded modules that have one, for FlaskSpark(modules=...)."""
    out = []
    for module in load(cfg)[1:]:
        package = f"{module.PACKAGE}.web"
        if importlib.util.find_spec(package) is not None:
            out.append(package)
    return out


def locale_dirs(cfg) -> list[Path]:
    """The catalogues of the loaded modules that have one (<package>/locales), in the modules' order."""
    out = []
    for module in load(cfg)[1:]:
        found = directory(module)
        if found is not None and (found / "locales").is_dir():
            out.append(found / "locales")
    return out


def resolve(spec: str):
    """The object a manifest names as "<python module>:<attribute>" (e.g. a Shareable class)."""
    path, _, name = spec.partition(":")
    if not path or not name:
        raise ValueError(f"{spec!r}: expected \"<python module>:<attribute>\"")
    return getattr(importlib.import_module(path), name)


def reset() -> None:
    """Forget the loaded manifests (tests that install modules), and with them where the catalogues are."""
    _loaded.clear()
    _skipped.clear()
    from . import i18n

    i18n.reset()
