"""Configuration: config.yaml (defaults, theme, services; the application's package brings it, flaskspark.core.paths)
and secrets from the environment.

Secrets never live in config.yaml. They come from the environment, filled from env files at the start of every process
(the first value of a name wins, the real environment over all files):

1. CONFIG_DIR/app.env and CONFIG_DIR/<module>.env of every module (flaskspark.core.paths),
2. PROJECT_DIR/.env (development; in a container the variables come from the container's environment; APP_NO_DOTENV
   skips it, e.g. in tests).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from . import paths


def load_env_file(path: Path) -> None:
    """Variables of an env file into the environment (existing ones win)."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class Config:
    """config.yaml as a read-only mapping with a few helpers. data: config.yaml with the settings the admins changed
    laid over it (flaskspark.core.settings); defaults: config.yaml alone."""

    def __init__(self, data: dict[str, Any], defaults: dict[str, Any] | None = None):
        self.data = data
        self.defaults = data if defaults is None else defaults

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def section(self, name: str) -> dict[str, Any]:
        """A section of config.yaml (e.g. the one of a module), {} without one."""
        return self.data.get(name) or {}

    def enabled(self, name: str, default: bool = True) -> bool:
        """A section's `enabled:` (e.g. a part of a module that can be switched off), `default` without one."""
        return bool(self.section(name).get("enabled", default))

    @property
    def app_name(self) -> str:
        return self.section("app").get("name") or paths.APP_NAME

    @property
    def title(self) -> str:
        return self.section("app").get("title") or self.app_name

    @property
    def theme(self) -> str:
        return os.environ.get("APP_THEME") or self.data.get("theme") or "default"

    @property
    def modules(self) -> tuple[str, ...]:
        """The explicit list of modules (config.yaml `modules:`, APP_MODULES comma separated overrides it), () without
        one: every installed module is loaded (flaskspark.core.modules). With a list only those, in its order."""
        override = os.environ.get("APP_MODULES")
        if override is not None:
            return tuple(m.strip() for m in override.split(",") if m.strip())
        return tuple(self.data.get("modules") or ())

    @staticmethod
    def secret(name: str, default: str = "") -> str:
        return os.environ.get(name, default)


def read(path: Path | None = None) -> Config:
    """config.yaml without touching the environment (tests)."""
    with Path(path or paths.CONFIG_FILE).open() as f:
        return Config(yaml.safe_load(f) or {})


@lru_cache(maxsize=None)
def _load(path: str) -> Config:
    cfg = read(Path(path))
    from . import modules

    load_env_file(paths.env_file("app"))
    for module, _ in modules.selected(cfg):
        load_env_file(paths.env_file(module))
    if not os.environ.get("APP_NO_DOTENV"):
        load_env_file(paths.PROJECT_DIR / ".env")
    return cfg


def load_env(path: str | Path | None = None) -> None:
    """The env files into the environment (once per process, like load()) without the settings of the database: for
    what is read from the environment before the configuration is needed (secrets, NATS_ENV_FILE)."""
    _load(str(path or paths.CONFIG_FILE))


def load(path: str | Path | None = None) -> Config:
    """config.yaml (cached per path) after the env files went into the environment, with the settings the admins
    changed in the web app laid over it (flaskspark.core.settings; `.defaults` is config.yaml alone)."""
    from . import settings

    key = str(path or paths.CONFIG_FILE)
    return settings.overlaid(key, _load(key))


def reload() -> None:
    """Forget the cached configuration (tests)."""
    from . import settings

    _load.cache_clear()
    settings.invalidate()
