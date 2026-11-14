"""Where the application keeps its files: the one place for every path, each can be set from the environment (another
host, a container with volumes).

- APP, APP_DIR: the installed application (entry point group flaskspark.apps, flaskspark.core.discovery) and its
  package's directory, None in the classic layout (config.yaml, themes/ and web/ in the project directory).
- PROJECT_DIR (APP_PROJECT_DIR): where the processes run (.env for development; in the classic layout config.yaml,
  themes/ and web/); default with an installed application: the working directory; in the classic layout the first
  directory with a config.yaml from the working directory upwards, else the working directory.
- CONFIG_FILE (APP_CONFIG_FILE): config.yaml; default: the one of the application's package, in the classic layout
  PROJECT_DIR/config.yaml.
- CONFIG_DIR (APP_CONFIG_DIR, default ~/.config/<app>): secrets per module, <module>.env.
- STATE_DIR (APP_STATE_DIR, default $XDG_STATE_HOME/<app> or ~/.local/state/<app>): the database (local disk, never
  NFS) and the state of each module in <module>/.

<app> is the application's name (APP_NAME, default: its entry point's name, in the classic layout the name of the
project directory). In a container both point to
volumes (e.g. APP_STATE_DIR=/data/state).
"""

from __future__ import annotations

import os
from pathlib import Path

from . import discovery

APP = discovery.app()
APP_DIR = discovery.package_dir(APP.package) if APP is not None else None


def _project_dir() -> Path:
    if os.environ.get("APP_PROJECT_DIR"):
        return Path(os.environ["APP_PROJECT_DIR"]).expanduser().resolve()
    here = Path.cwd().resolve()
    if APP is not None:
        return here
    for directory in (here, *here.parents):
        if (directory / "config.yaml").is_file():
            return directory
    return here


PROJECT_DIR = _project_dir()
APP_NAME = os.environ.get("APP_NAME") or (APP.name if APP is not None else PROJECT_DIR.name)


def _dir(env: str, default: Path) -> Path:
    return Path(os.environ.get(env) or default).expanduser()


CONFIG_DIR = _dir("APP_CONFIG_DIR", Path("~/.config") / APP_NAME)
STATE_DIR = _dir("APP_STATE_DIR", Path(os.environ.get("XDG_STATE_HOME") or "~/.local/state") / APP_NAME)
DATABASE = STATE_DIR / "app.db"
CONFIG_FILE = Path(os.environ.get("APP_CONFIG_FILE") or (APP_DIR or PROJECT_DIR) / "config.yaml")
THEMES_DIR = _dir("APP_THEMES_DIR", PROJECT_DIR / "themes")
WEB_DIR = PROJECT_DIR / "web"  # the classic layout's web app (web/app, web/wsgi.py, web/migrations)


def classic_web() -> bool:
    """The project brings its own web app (web/wsgi.py, the classic layout) instead of FlaskSpark's built-in one."""
    return (WEB_DIR / "wsgi.py").is_file()


def env_file(module: str) -> Path:
    """The secrets and settings of a module (or "app" for the core): CONFIG_DIR/<module>.env."""
    return CONFIG_DIR / f"{module}.env"


def state_dir(module: str, create: bool = True) -> Path:
    """The state directory of a module: STATE_DIR/<module>/."""
    path = STATE_DIR / module
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path
