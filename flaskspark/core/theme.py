"""Themes: the branding of an application built on flaskspark.core (name, logos, colours, icons, default colour mode).

A theme is a directory with

    theme.yaml   title, short_name, logos (light and dark), favicon, theme_color, default_mode (light|dark|system),
                 font (optional Google Fonts family), footer text; for the home screen: apple_touch_icon and manifest
                 (a file in images/, or its fields: the layout serves them as /theme/manifest.webmanifest)
    theme.css    the theme's tokens and overrides (plain CSS, light-dark() for both colour modes, no SCSS)
    images/      logos and icons

An application ships its theme as a package directory with an entry point (group flaskspark.themes: name -> package,
flaskspark.core.discovery); the classic layout keeps it in themes/<name>/ of the project. config.yaml `theme:` picks
one (APP_THEME overrides). The layout of flaskspark.core (flaskspark/core/web) only uses the theme's tokens
(--app-*, README «Themes») and the values of theme.yaml, so the same layout carries any brand.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import paths

MODES = ("light", "dark", "system")


@dataclass(frozen=True)
class Theme:
    name: str
    directory: Path
    title: str
    short_name: str
    logo: str  # path inside images/ (light mode)
    logo_dark: str  # path inside images/ (dark mode)
    favicon: str
    theme_color: str = "#ffffff"
    theme_color_dark: str = "#000000"
    default_mode: str = "system"
    footer: str = ""
    apple_touch_icon: str = ""  # path inside images/ ("": none)
    manifest: str | dict | None = None  # a file inside images/, the fields of a generated manifest, or None
    extra: dict = field(default_factory=dict)

    @property
    def stylesheet(self) -> Path:
        return self.directory / "theme.css"

    @property
    def manifest_file(self) -> str:
        """The manifest as a file inside images/ ("" when the manifest is generated or there is none)."""
        return self.manifest if isinstance(self.manifest, str) else ""


def manifest_data(theme: Theme, images_url: str) -> dict:
    """The web app manifest from theme.yaml `manifest:` (its fields; `true`: the defaults alone): name, short_name,
    start_url, display and the colours default to the theme's; icons name files inside images/ (absolute URLs and paths
    stay as they are). images_url: the URL of images/ (ends with a slash)."""
    fields = dict(theme.manifest) if isinstance(theme.manifest, dict) else {}
    data = {
        "name": theme.title,
        "short_name": theme.short_name,
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "theme_color": theme.theme_color_dark if theme.default_mode == "dark" else theme.theme_color,
        "background_color": theme.theme_color_dark if theme.default_mode == "dark" else theme.theme_color,
        **fields,
    }
    icons = []
    for icon in fields.get("icons") or ():
        icon = dict(icon) if isinstance(icon, dict) else {"src": str(icon)}
        src = str(icon.get("src", ""))
        if src and not src.startswith(("/", "http://", "https://", "data:")):
            icon["src"] = images_url + src
        icons.append(icon)
    if icons:
        data["icons"] = icons
    elif theme.apple_touch_icon:
        data["icons"] = [{"src": images_url + theme.apple_touch_icon, "sizes": "180x180", "type": "image/png"}]
    return data


class ThemeSource(ABC):
    """Where themes come from (today: directories on disk)."""

    @abstractmethod
    def get(self, name: str) -> Theme:
        """The theme `name`; KeyError if there is none."""

    @abstractmethod
    def names(self) -> list[str]:
        """Every theme this source has."""


BUILTIN_THEMES = Path(__file__).resolve().parent / "themes"


class DirectoryThemes(ThemeSource):
    """Themes as directories with a theme.yaml: the project's themes/<name>/ first, then the installed ones (entry
    points flaskspark.themes), then FlaskSpark's own (the neutral "default")."""

    def __init__(self, root: Path | None = None, installed: dict[str, Path] | None = None):
        from . import discovery

        self.roots = [Path(root or paths.THEMES_DIR), BUILTIN_THEMES]
        self.installed = discovery.themes() if installed is None else dict(installed)

    def _directory(self, name: str) -> Path | None:
        candidates = [self.roots[0] / name, self.installed.get(name), *(root / name for root in self.roots[1:])]
        return next((c for c in candidates if c is not None and (c / "theme.yaml").is_file()), None)

    def names(self) -> list[str]:
        found = {p.parent.name for root in self.roots for p in root.glob("*/theme.yaml")}
        return sorted(found | {n for n, d in self.installed.items() if (d / "theme.yaml").is_file()})

    def get(self, name: str) -> Theme:
        directory = self._directory(name)
        if directory is None:
            raise KeyError(f"no theme {name!r} (an entry point in flaskspark.themes, or themes/{name}/theme.yaml)")
        description = directory / "theme.yaml"
        data = yaml.safe_load(description.read_text()) or {}
        mode = data.get("default_mode", "system")
        if mode not in MODES:
            raise ValueError(f"theme {name!r}: default_mode must be one of {MODES}")
        known = {"title", "short_name", "logo", "logo_dark", "favicon", "theme_color", "theme_color_dark", "footer",
                 "apple_touch_icon", "manifest"}
        manifest = data.get("manifest")
        if manifest is True:
            manifest = {}
        elif manifest is False or manifest == "":
            manifest = None
        elif manifest is not None and not isinstance(manifest, (str, dict)):
            raise ValueError(f"theme {name!r}: manifest must be a file inside images/, its fields or true")
        return Theme(
            name=name,
            directory=directory,
            title=data.get("title") or name,
            short_name=data.get("short_name") or data.get("title") or name,
            logo=data.get("logo", "logo.svg"),
            logo_dark=data.get("logo_dark") or data.get("logo", "logo.svg"),
            favicon=data.get("favicon", "favicon.svg"),
            theme_color=data.get("theme_color", "#ffffff"),
            theme_color_dark=data.get("theme_color_dark", "#000000"),
            default_mode=mode,
            footer=data.get("footer", ""),
            apple_touch_icon=data.get("apple_touch_icon") or "",
            manifest=manifest,
            extra={k: v for k, v in data.items() if k not in known | {"default_mode"}},
        )


def load(cfg, source: ThemeSource | None = None) -> Theme:
    """The theme config.yaml names."""
    return (source or DirectoryThemes()).get(cfg.theme)
