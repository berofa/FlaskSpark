"""Findings and checks of the guardian."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field

from flaskspark.core import directory, health

CRITICAL, WARNING = "critical", "warning"

#: settings of the guardian (config.yaml guardian:); the checks add theirs (GuardCheck.DEFAULTS)
DEFAULTS = {
    "interval": 30,  # seconds between checks
    "reminder_critical_minutes": 30,  # repeat lasting critical findings
    "reminder_warning_minutes": 240,  # repeat lasting warnings
    "failing_minutes": 5,  # the guardian's own checks failing this long
    "nats_grace": 60,  # seconds NATS may not answer
    "service_grace": 120,  # seconds a service may be without a live instance before it is reported
    "notify_stuck_minutes": 5,  # the oldest notification waiting in the work queue this long: nobody delivers
}


def render(text: str, params: dict | None, gettext) -> str:
    """A text of a finding in a language: `gettext(text, **params)` (flask_babel's in a request, flaskspark.core.i18n's
    outside); string params whose name ends in "label" (e.g. a module's label) are source texts and translated too."""
    if not text:
        return text or ""
    params = {k: (gettext(v) if k.endswith("label") and isinstance(v, str) else v) for k, v in (params or {}).items()}
    try:
        return gettext(text, **params) if params else gettext(text)
    except (KeyError, TypeError, ValueError):  # a translation that does not fit its params: the source text
        return text % params if params else text


@dataclass
class Finding:
    """What a check found. title and message: English source texts (N_(), with %(name)s for `params`), translated when
    the guardian reports them (the application's language, flaskspark.core.i18n) and on the status tile (the visitor's);
    a text that is no source text (already composed) stays as it is."""

    key: str  # stable identity, e.g. "service:push"
    level: str  # WARNING | CRITICAL
    title: str
    message: str
    grace: float = 0.0  # seconds it must last before it is reported
    action: object | None = None  # what the check's react() needs when it is reported
    check: GuardCheck | None = field(default=None, repr=False, compare=False)
    params: dict = field(default_factory=dict)  # the values of the texts' %(name)s

    def render(self, locale: str | None = None, cfg=None) -> tuple[str, str]:
        """(title, message) in `locale` (default: the application's language)."""
        from flaskspark.core import i18n

        def gettext(text, **params):
            return i18n.gettext(text, locale=locale, cfg=cfg, **params)

        return render(self.title, self.params, gettext), render(self.message, self.params, gettext)


class GuardContext:
    """What the checks of one run share: config, settings, time, NATS health and the service directory (asked once).
    read_directory / read_nats: instead of NATS (tests)."""

    USER = "guardian"

    def __init__(self, cfg, opt: dict, now: float | None = None, read_directory: Callable[[], dict] | None = None,
                 read_nats: Callable[[], dict] | None = None):
        self.cfg, self.opt, self.now = cfg, opt, now or time.time()
        self._read_directory = read_directory or (lambda: directory.read(self.USER))
        self._read_nats = read_nats or (lambda: health.nats_health(self.USER))
        self._nats: dict | None = None
        self._directory: dict | None = None

    def nats(self) -> dict:
        if self._nats is None:
            self._nats = self._read_nats()
        return self._nats

    def directory(self) -> dict:
        """The service directory: {ok, missing, error, instances}; not asked without NATS."""
        if self._directory is None:
            self._directory = (self._read_directory() if self.nats().get("ok") else
                               directory.unreachable("NATS not reachable"))
        return self._directory

    def directory_usable(self) -> bool:
        return directory.usable(self.directory())

    def all_instances(self, service: str) -> list[dict]:
        if not self.directory_usable():
            return []
        return directory.by_service(self.directory().get("instances") or []).get(service, [])

    def instances(self, service: str) -> list[dict]:
        """The live instances of a service, the leader first."""
        return directory.alive(self.all_instances(service))


class GuardCheck(ABC):
    """One check of the guardian. DEFAULTS: its settings (overridable in config.yaml guardian:)."""

    DEFAULTS: dict = {}

    @abstractmethod
    def run(self, ctx: GuardContext) -> list[Finding]:
        """The findings of now (empty: all good)."""

    def react(self, ctx: GuardContext, finding: Finding) -> str | None:
        """Called once when `finding` is reported: do something about it; returns a sentence for the message."""
        return None


def settings(cfg, checks=()) -> dict:
    out = dict(DEFAULTS)
    for check in checks:
        out.update(check.DEFAULTS)
    section = {k: v for k, v in (cfg.section("guardian") if cfg is not None else {}).items() if k != "enabled"}
    return {**out, **section}
