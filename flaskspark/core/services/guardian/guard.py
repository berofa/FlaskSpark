"""Keeping, reporting and reminding the guardian's findings."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from flaskspark.core import i18n
from flaskspark.core.module import N_
from flaskspark.core.notify import clock

from .base import CRITICAL, Finding, GuardCheck, GuardContext, render, settings

log = logging.getLogger(__name__)

PRIORITY = {"critical": 5, "warning": 4, "resolved": 2}
TAGS = {"critical": ["rotating_light"], "warning": ["warning"], "resolved": ["white_check_mark"]}


def default_checks(cfg) -> list[GuardCheck]:
    """The checks of the core and of every enabled module (their manifests' guard_checks())."""
    from flaskspark.core import modules

    return [c for m in modules.load(cfg) for c in m.guard_checks()]


def findings(cfg, checks: list[GuardCheck], ctx: GuardContext) -> list[Finding]:
    out: list[Finding] = []
    for check in checks:
        for f in check.run(ctx):
            f.check = check
            out.append(f)
    return out


class Guard:
    """Keeps the findings between runs (findings.json) and reports new, lasting and resolved ones."""

    def __init__(self, cfg, notifier, checks: list[GuardCheck] | None = None, opt: dict | None = None,
                 state_file: Path | None = None, context=GuardContext):
        self.cfg = cfg
        self.notifier = notifier
        self.checks = default_checks(cfg) if checks is None else checks
        self.opt = opt or settings(cfg, self.checks)
        self.context = context  # GuardContext or a factory (cfg, opt, now) -> context (tests)
        if state_file is None:
            from flaskspark.core import paths

            state_file = paths.state_dir("guardian") / "findings.json"
        self.path = Path(state_file)
        try:
            self.state = json.loads(self.path.read_text())
        except (OSError, ValueError):
            self.state = {}
        self.state.setdefault("findings", {})

    def _t(self, text: str, params: dict | None = None) -> str:
        """A text in the application's language (flaskspark.core.i18n)."""

        def gettext(source, **values):
            return i18n.gettext(source, cfg=self.cfg, **values)

        return render(text, params, gettext)

    def run_once(self, now: float | None = None) -> list[dict]:
        """One check; returns the notifications sent (their texts in the application's language)."""
        now = now or time.time()
        sent: list[dict] = []
        ctx = self.context(self.cfg, self.opt, now)
        try:
            current = {f.key: f for f in findings(self.cfg, self.checks, ctx)}
        except Exception as exc:  # noqa: BLE001 - report only when it lasts
            log.exception("guardian checks failed")
            current = {"guard:failing": Finding("guard:failing", CRITICAL, N_("Guardian can't check"),
                                                N_("The checks fail: %(error)s"),
                                                grace=self.opt["failing_minutes"] * 60, params={"error": str(exc)})}
            # Keep the other findings as they are: unknown is not resolved.
            current.update({k: Finding(k, v["level"], v["title"], v["message"], v.get("grace", 0.0),
                                       params=dict(v.get("params") or {}))
                            for k, v in self.state["findings"].items() if k != "guard:failing"})
        known = self.state["findings"]
        for key, f in current.items():
            entry = known.get(key) or {"first": now, "alerted": None}
            entry.update(level=f.level, title=f.title, message=f.message, params=dict(f.params), grace=f.grace,
                         seen=now)
            known[key] = entry
            reminder = self.opt[f"reminder_{f.level}_minutes"] * 60
            title, message = self._t(f.title, f.params), self._t(f.message, f.params)
            if entry["alerted"] is None and now - entry["first"] >= f.grace:
                if f.check is not None:
                    try:
                        note = f.check.react(ctx, f)
                    except Exception:  # noqa: BLE001 - the report goes out anyway
                        log.exception("guardian: react of %s", key)
                        note = None
                    if note:
                        message += " " + self._t(note)
                sent.append(self._send(title, message, f.level))
                entry["alerted"] = now
            elif entry["alerted"] and now - entry["alerted"] >= reminder:
                sent.append(self._send(self._t(N_("%(title)s (still)"), {"title": title}),
                                       self._t(N_("Since %(time)s: %(message)s"),
                                               {"time": clock(entry["first"], now), "message": message}), f.level))
                entry["alerted"] = now
        for key in [k for k in known if k not in current]:
            entry = known.pop(key)
            if entry.get("alerted"):
                title = self._t(entry["title"], entry.get("params"))
                sent.append(self._send(self._t(N_("Resolved: %(title)s"), {"title": title}),
                                       self._t(N_("Fine again since %(now)s (since %(first)s)."),
                                               {"now": clock(now, now), "first": clock(entry["first"], now)}),
                                       "resolved"))
        self.state["last_check"] = now
        self._save()
        return sent

    def summary(self) -> dict:
        """What the heartbeat carries to the status tile: the findings in the application's language, with their
        source texts (source: {title, message, params}) for the visitor's."""
        out = []
        for k, f in list(self.state["findings"].items()):
            params = f.get("params") or {}
            out.append({"key": k, "level": f.get("level"), "title": self._t(f.get("title") or "", params),
                        "message": self._t(f.get("message") or "", params), "alerted": f.get("alerted"),
                        "source": {"title": f.get("title"), "message": f.get("message"), "params": params}})
        return {"last_check": self.state.get("last_check"), "interval": self.opt["interval"], "findings": out}

    def _send(self, title: str, message: str, level: str) -> dict:
        self.notifier.send(self._t(N_("Guardian: %(title)s"), {"title": title}), message, priority=PRIORITY[level],
                           tags=TAGS[level])
        return {"title": title, "message": message, "level": level}

    def _save(self) -> None:
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=1))
            tmp.replace(self.path)
        except OSError:
            log.exception("guardian: findings not saved")
