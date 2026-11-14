"""Settings the admins change in the web app: the default is in config.yaml, a changed value lives in the database
(table core_settings) and is edited on the page «Settings», in the tab of its module.

- A module names its settings in its manifest (Module.CONFIG: Setting, a path into config.yaml such as
  "mail.interval"); only those are offered, checked (kind, choices, bounds) and stored.
- config.load() lays the stored values over config.yaml (overlaid()), so every process reads them like any other
  setting, without code of its own; config.load().defaults is config.yaml alone. A process sees a change at the latest
  after CHECK_SECONDS (the one that saved it at once). A service that reads a setting only when it starts needs a
  restart: the setting names those services (Setting.services; the page says so after saving).
- Never a setting here: secrets (they live in the environment), the list of modules, the theme, the access (PROTECTED).

Values are JSON in the table; an empty field takes the default again (the row goes).
"""

from __future__ import annotations

import copy
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from .module import N_

log = logging.getLogger(__name__)

KINDS = ("int", "float", "bool", "str", "text", "time", "choice", "ints", "texts", "json")
OFF = "off"  # the value of a "time" setting that is switched off
PROTECTED = frozenset({"modules", "theme", "auth"})  # top-level keys of config.yaml never changed from the web app
CHECK_SECONDS = 5.0  # how often a process looks for settings other processes changed


class SettingError(ValueError):
    """A value that does not fit its setting. template and params: the English source text and its values, for
    gettext (str() is the English message)."""

    def __init__(self, template: str, **params):
        self.template, self.params = template, params
        super().__init__(template % params)


@dataclass(frozen=True)
class Setting:
    """A setting of config.yaml the admins may change.

    path: where it is in config.yaml ("section.key", deeper too). label, help, group, unit: English source texts (N_()),
    translated when shown; settings of the same group share a box. kind: int | float | bool | str (also "text") |
    time ("HH:MM", or OFF) | choice (one of choices: values, or (value, label) pairs) | ints / texts (a list, comma
    separated in the form) | json (a list or an object, as JSON in the form). min, max: bounds of a number (of every
    number of "ints"). services: the names of the services that read it only when they start (a change needs their
    restart); () : it counts at once."""

    path: str
    label: str
    kind: str = "str"
    help: str = ""
    group: str = ""
    min: float | None = None
    max: float | None = None
    unit: str = ""
    choices: tuple = ()
    services: tuple[str, ...] = ()

    def __post_init__(self):
        if self.kind not in KINDS:
            raise TypeError(f"setting {self.path}: kind {self.kind!r} (known: {', '.join(KINDS)})")
        if not self.path or self.path.split(".")[0] in PROTECTED:
            raise TypeError(f"setting {self.path!r}: not a path the web app may change")
        if self.kind == "choice" and not self.choices:
            raise TypeError(f"setting {self.path}: a choice needs choices")

    def options(self) -> list[tuple[str, str]]:
        """The choices as (value, label)."""
        return [(c[0], c[1]) if isinstance(c, (tuple, list)) else (str(c), str(c)) for c in self.choices]

    def as_dict(self) -> dict:
        return {"path": self.path, "label": self.label, "kind": self.kind, "help": self.help, "group": self.group,
                "min": self.min, "max": self.max, "unit": self.unit,
                "choices": [{"value": v, "label": label} for v, label in self.options()],
                "services": list(self.services)}


# --- paths into the YAML ----------------------------------------------------------------------------------------
def _key(node: dict, part: str):
    """The key of `part` in `node`: as written, or as a number (YAML keys such as 60)."""
    if part in node:
        return part
    try:
        number = int(part)
    except ValueError:
        return part
    return number if number in node else part


def get(data: dict, path: str, default: Any = None) -> Any:
    """The value at `path` ("a.b.c") in `data`, `default` without one."""
    node: Any = data
    for part in path.split("."):
        if not isinstance(node, dict):
            return default
        k = _key(node, part)
        if k not in node:
            return default
        node = node[k]
    return node


def put(data: dict, path: str, value: Any) -> None:
    """Set the value at `path` in `data` (missing sections are created)."""
    parts = path.split(".")
    node = data
    for part in parts[:-1]:
        k = _key(node, part)
        if not isinstance(node.get(k), dict):
            node[k] = {}
        node = node[k]
    node[_key(node, parts[-1])] = value


# --- the stored values ------------------------------------------------------------------------------------------
def stored(url: str | None = None) -> dict[str, Any]:
    """path -> value of every stored setting ({} without the table, e.g. before the migration, or without a database:
    the defaults then, a process still starts)."""
    from . import db
    from .models import StoredSetting

    try:
        with db.session(db.for_module(db.CORE, url) if url else None) as s:
            return {row.path: json.loads(row.value) for row in s.scalars(db.select(StoredSetting))}
    except Exception as exc:  # noqa: BLE001 - see above
        log.debug("settings not read: %s", exc)
        return {}


def overlay(data: dict, values: dict[str, Any]) -> dict:
    """config.yaml (`data`) with the stored values laid over it (a copy; PROTECTED paths are left alone)."""
    if not values:
        return data
    out = copy.deepcopy(data)
    for path, value in values.items():
        if path.split(".")[0] not in PROTECTED:
            put(out, path, like(get(data, path), value))
    return out


def _number_key(default: dict, key):
    if isinstance(key, str) and key.lstrip("-").isdigit() and any(isinstance(k, int) for k in default):
        return int(key)
    return key


def like(default, value):
    """A stored structure in the form of its default: JSON knows text keys only, config.yaml has numbers too (e.g.
    {60: 3.0}); digit keys become numbers again where the default has numbers."""
    if isinstance(value, dict) and isinstance(default, dict):
        sample = next(iter(default.values()), None)
        return {_number_key(default, k): like(default.get(_number_key(default, k), sample), v)
                for k, v in value.items()}
    return value


_overlays: dict[str, dict] = {}  # config path -> {base, values, config, checked}


def overlaid(key: str, base):
    """The configuration `base` (config.yaml, flaskspark.core.config.Config) with the stored settings over it; looks for
    changes at most every CHECK_SECONDS (key: the path of config.yaml)."""
    from .config import Config

    now = time.monotonic()
    hit = _overlays.get(key)
    if hit is not None and hit["base"] is base and now - hit["checked"] < CHECK_SECONDS:
        return hit["config"]
    values = stored()
    if hit is not None and hit["base"] is base and hit["values"] == values:
        hit["checked"] = now
        return hit["config"]
    cfg = Config(overlay(base.data, values), defaults=base.data) if values else base
    _overlays[key] = {"base": base, "values": values, "config": cfg, "checked": now}
    return cfg


def invalidate() -> None:
    """Read the stored settings again at the next config.load() (after a save, tests)."""
    _overlays.clear()


# --- checking and saving ----------------------------------------------------------------------------------------
TRUE = ("1", "true", "on", "yes")
EXPECTED = {
    "int": N_("«%(label)s»: a whole number expected"),
    "float": N_("«%(label)s»: a number expected"),
    "bool": N_("«%(label)s»: on or off expected"),
    "time": N_("«%(label)s»: a time HH:MM or «off» expected"),
    "ints": N_("«%(label)s»: whole numbers expected, separated by commas"),
    "texts": N_("«%(label)s»: values expected, separated by commas"),
    "json": N_("«%(label)s»: valid JSON expected (a list or an object)"),
}
FALSE = ("0", "false", "off", "no")


def clean(setting: Setting, raw: Any) -> Any:
    """The value of a form field, checked (SettingError when it does not fit); None: empty, the default again."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    text = raw.strip() if isinstance(raw, str) else raw
    kind = setting.kind
    try:
        if kind == "int":
            if isinstance(text, bool) or (isinstance(text, float) and not text.is_integer()):
                raise ValueError
            value = int(text)
        elif kind == "float":
            if isinstance(text, bool):
                raise ValueError
            value = float(str(text).replace(",", ".").replace("'", ""))
        elif kind == "bool":
            if isinstance(text, bool):
                value = text
            elif str(text).lower() in TRUE:
                value = True
            elif str(text).lower() in FALSE:
                value = False
            else:
                raise ValueError
        elif kind == "time":
            value = str(text)
            if value.lower() == OFF:
                return OFF
            hh, mm = value.split(":")
            if not (hh.isdigit() and mm.isdigit() and 0 <= int(hh) < 24 and 0 <= int(mm) < 60 and len(mm) == 2):
                raise ValueError
            value = f"{int(hh):02d}:{mm}"
        elif kind == "choice":
            value = str(text)
            if value not in [v for v, _ in setting.options()]:
                raise SettingError(N_("«%(label)s»: not one of the choices"), label=setting.label)
        elif kind in ("ints", "texts"):
            items = text if isinstance(text, list) else [x.strip() for x in str(text).split(",") if x.strip()]
            if kind == "ints" and any(isinstance(x, bool) or (isinstance(x, float) and not x.is_integer())
                                      for x in items):
                raise ValueError
            value = [int(x) for x in items] if kind == "ints" else [str(x).strip() for x in items]
        elif kind == "json":
            value = text if isinstance(text, (dict, list)) else json.loads(str(text))
            if not isinstance(value, (dict, list)):
                raise ValueError
        else:
            value = str(text)
    except (ValueError, TypeError) as error:
        if isinstance(error, SettingError):
            raise
        raise SettingError(EXPECTED.get(kind, N_("«%(label)s»: invalid")), label=setting.label) from None
    numbers = value if kind == "ints" else [value] if kind in ("int", "float") else []
    for number in numbers:
        if (setting.min is not None and number < setting.min) or (setting.max is not None and number > setting.max):
            raise SettingError(N_("«%(label)s»: between %(min)s and %(max)s"), label=setting.label,
                               min=_num(setting.min), max=_num(setting.max))
    return value


def _num(x) -> str:
    return "…" if x is None else (str(int(x)) if float(x).is_integer() else str(x))


def save(settings: tuple[Setting, ...], values: dict[str, Any], user_id: int | None = None,
         url: str | None = None) -> list[str]:
    """The form's values of these settings stored (None or empty: the default again); the paths that changed. Every
    value is checked first: one wrong value stores none. Paths that are not among `settings` are refused."""
    from . import db
    from .models import StoredSetting

    by_path = {s.path: s for s in settings}
    unknown = [p for p in values if p not in by_path]
    if unknown:
        raise SettingError(N_("Unknown setting: %(path)s"), path=", ".join(sorted(unknown)))
    cleaned = {path: clean(by_path[path], raw) for path, raw in values.items()}
    changed = []
    with db.session(db.for_module(db.CORE, url) if url else None) as s:
        rows = {row.path: row for row in s.scalars(db.select(StoredSetting).where(StoredSetting.path.in_(list(cleaned))))}
        for path, value in cleaned.items():
            row = rows.get(path)
            if value is None:
                if row is not None:
                    s.delete(row)
                    changed.append(path)
            elif row is None or json.loads(row.value) != value:
                if row is None:
                    row = StoredSetting(path=path)
                    s.add(row)
                row.value, row.changed, row.user_id = json.dumps(value), time.time(), user_id
                changed.append(path)
    invalidate()
    return changed


def view(settings: tuple[Setting, ...], defaults: dict, url: str | None = None) -> list[dict]:
    """The settings for the form: each with its default (config.yaml) and its stored value (None: the default)."""
    values = stored(url)
    return [{**s.as_dict(), "default": get(defaults, s.path), "value": values.get(s.path)} for s in settings]


def of(cfg) -> dict[str, tuple[Setting, ...]]:
    """The settings of every module that has some: module name -> its Module.CONFIG."""
    from . import modules

    return {m.NAME: tuple(m.CONFIG) for m in modules.load(cfg) if m.CONFIG}
