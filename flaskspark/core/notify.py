"""Notifications: messages of the application's processes to people (an alert, a finished report), over channels.

    notifier = notify.Notifier()
    notifier.send("Backup failed", "The database copy did not pass its check.", priority=notify.HIGH)

- A channel (NotificationChannel) is a way a message reaches people; the core brings NtfyChannel (an ntfy server,
  configured from the environment: NTFY_URL, NTFY_TOPIC, NTFY_TOKEN optional). Modules add channels of their own with
  register_channel() (in Module.register()). channels() are the configured ones; without any, send() only logs.
- Delivery: with the notifications service switched on (config.yaml `notifications: {enabled: true}`), a message
  goes into the durable work queue (job kind KIND, flaskspark.core.queue) and the service delivers it, with retries
  (flaskspark.core.services.notifications). Otherwise, when the queue can't take it (no NATS, a process without
  events.init) or for a Notifier with queue=False (the guardian: it reports on the system the queue runs on), it goes
  out at once; a message that can't be sent then waits in the outbox (STATE_DIR/notify/outbox.jsonl, shared by the
  processes under a file lock) and is sent later, before the next message or on flush().
- A message delivered more than LATE_AFTER seconds after it was written says so in its title.
- Categories and their mute switches belong to the module that sends: it hands the Notifier a check
  `enabled(category)`; the core knows none.
- Texts: title and message may be English source texts (N_(), with %(name)s for `params`): send() translates them into
  the application's language (flaskspark.core.i18n: config.yaml notifications.language, else the first of
  app.locales); a text that is no source text stays as it is.
- History (opt-in, config.yaml `notifications.history: true`): every message sent goes into
  STATE_DIR/notifications/history.jsonl (muted ones too, marked); history() reads the latest. The file is cut to its
  newer half beyond HISTORY_MAX_BYTES.

A message: {ts, title, message, priority (1 min ... 5 urgent, ntfy's scale), tags, click, category}.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

KIND = "notify"  # the job kind in the work queue
OUTBOX = "outbox.jsonl"
OUTBOX_MAX_AGE = 24 * 3600.0  # a message older than this is dropped (in the outbox and in the queue)
LATE_AFTER = 120  # seconds: a message delivered later than this says so in its title
HISTORY = "history.jsonl"
HISTORY_MAX_BYTES = 2 * 1024 * 1024  # beyond this, the history keeps its newer half
MIN, LOW, DEFAULT, HIGH, URGENT = 1, 2, 3, 4, 5


class Undeliverable(Exception):
    """A channel refuses a message for good (e.g. it is malformed): never tried again."""


class NotificationChannel(ABC):
    """A way a notification reaches people. deliver() raises when it did not go out (the caller tries again later),
    Undeliverable when it never will."""

    kind: str = ""

    @abstractmethod
    def deliver(self, entry: dict, title: str | None = None) -> None:
        """Send one message {ts, title, message, priority, tags, click}; title overrides entry["title"] (e.g. late)."""


class NtfyChannel(NotificationChannel):
    """An ntfy server and topic (with an access token, optional)."""

    kind = "ntfy"

    def __init__(self, url: str, topic: str, token: str = "", timeout: float = 15.0, post=None):
        if not url or not topic:
            raise ValueError("ntfy needs a URL and a topic")
        self.endpoint = f"{url.rstrip('/')}/{topic}"
        self.token = token
        self.timeout = timeout
        self._post = post

    @classmethod
    def from_env(cls, environ=None) -> NtfyChannel | None:
        """The channel of NTFY_URL / NTFY_TOPIC / NTFY_TOKEN, None without URL or topic."""
        env = os.environ if environ is None else environ
        if not env.get("NTFY_URL") or not env.get("NTFY_TOPIC"):
            return None
        return cls(env["NTFY_URL"], env["NTFY_TOPIC"], env.get("NTFY_TOKEN", ""))

    def headers(self, entry: dict, title: str | None = None) -> dict:
        headers = {"Title": (title or entry["title"]).encode("utf-8"), "Priority": str(entry.get("priority") or DEFAULT)}
        if entry.get("tags"):
            headers["Tags"] = ",".join(entry["tags"])
        if entry.get("click"):
            headers["Click"] = entry["click"]
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def deliver(self, entry: dict, title: str | None = None) -> None:
        import httpx

        post = self._post or httpx.post
        try:
            r = post(self.endpoint, content=entry["message"].encode("utf-8"), headers=self.headers(entry, title),
                     timeout=self.timeout)
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if 400 <= code < 500 and code != 429:
                raise Undeliverable(f"ntfy refused the message ({code})") from exc
            raise


_factories: list[Callable[[], NotificationChannel | None]] = [NtfyChannel.from_env]


def register_channel(factory: Callable[[], NotificationChannel | None]) -> None:
    """A further kind of channel: `factory()` returns the configured channel, or None when it isn't configured."""
    if factory not in _factories:
        _factories.append(factory)


def channels() -> list[NotificationChannel]:
    """The configured channels (one per kind)."""
    out: dict[str, NotificationChannel] = {}
    for factory in _factories:
        try:
            channel = factory()
        except Exception as exc:  # noqa: BLE001 - a broken setting must not stop the others
            log.warning("notification channel not configured: %s", exc)
            continue
        if channel is not None and channel.kind not in out:
            out[channel.kind] = channel
    return list(out.values())


def queued(cfg) -> bool:
    """The notifications service is switched on (config.yaml notifications.enabled): messages go through the queue."""
    return bool(cfg is not None and (cfg.section("notifications") or {}).get("enabled", False))


def job_priority(priority: int) -> int:
    """Queue priority of a message's priority: urgent and high first, the quiet ones last."""
    from . import queue

    return queue.HIGH if priority >= HIGH else queue.NORMAL if priority == DEFAULT else queue.LOW


def clock(ts: float, now: float | None = None) -> str:
    dt = datetime.fromtimestamp(ts)
    today = datetime.fromtimestamp(now) if now else datetime.now()
    return dt.strftime("%H:%M") if dt.date() == today.date() else dt.strftime("%Y-%m-%d %H:%M")


def late_title(entry: dict, now: float | None = None) -> str:
    from . import i18n
    from .module import N_

    now = now or time.time()
    if now - entry["ts"] > LATE_AFTER:
        return i18n.gettext(N_("%(title)s (late, %(time)s)"), title=entry["title"], time=clock(entry["ts"], now))
    return entry["title"]


# --- the history (opt-in) ---------------------------------------------------------------------------------------------
def history_enabled(cfg) -> bool:
    return bool(cfg is not None and (cfg.section("notifications") or {}).get("history", False))


def history_file() -> Path:
    from . import paths

    return paths.state_dir("notifications") / HISTORY


def record(entry: dict, path: Path | None = None) -> None:
    """Append a message to the history (never raises)."""
    path = path or history_file()
    try:
        with path.open("a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            f.flush()
            if f.tell() > HISTORY_MAX_BYTES:
                f.seek(0)
                lines = f.readlines()
                f.seek(0)
                f.truncate()
                f.writelines(lines[len(lines) // 2:])
    except OSError as exc:
        log.warning("notification history not written: %s", exc)


def history(limit: int = 100, path: Path | None = None) -> list[dict]:
    """The latest messages of the history, newest first ([] without one)."""
    path = path or history_file()
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return []
    out = []
    for line in reversed(lines):
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
        if len(out) >= limit:
            break
    return out


class Notifier:
    def __init__(self, cfg=None, queue: bool = True, enabled: Callable[[str], bool] | None = None,
                 channels_: list[NotificationChannel] | None = None, outbox_dir: Path | None = None,
                 click: str = ""):
        """queue: through the work queue when the notifications service is on; enabled: the sending module's mute
        switches (category -> on?); channels_: instead of the configured ones (tests); outbox_dir: default
        STATE_DIR/notify."""
        if cfg is None:
            from . import config

            cfg = config.load()
        self.cfg = cfg
        self.queue = queue and queued(cfg)
        self.history = history_enabled(cfg)
        self.enabled = enabled
        self.channels = channels() if channels_ is None else list(channels_)
        self.click = click or (cfg.section("notifications") or {}).get("click", "")
        self._outbox_dir = outbox_dir
        self.sent: list[dict] = []

    @property
    def outbox_dir(self) -> Path:
        if self._outbox_dir is None:
            from . import paths

            self._outbox_dir = paths.state_dir("notify")
        return self._outbox_dir

    def send(self, title: str, message: str, priority: int = DEFAULT, tags: list[str] | None = None,
             click: str | None = None, category: str | None = None, key: str | None = None,
             params: dict | None = None) -> bool:
        """Send (or queue) a message over every channel. title and message: source texts (with %(name)s of `params`)
        translated into the application's language, or texts as they are. key: the same key is not sent twice (through
        the queue, within its duplicate window). True when every channel has it (sent, queued or waiting in the
        outbox)."""
        from . import i18n

        title = i18n.gettext(title, cfg=self.cfg, **(params or {}))
        message = i18n.gettext(message, cfg=self.cfg, **(params or {}))
        entry = {"ts": time.time(), "title": title, "message": message, "priority": priority, "tags": tags or [],
                 "click": click or self.click, "category": category}
        self.sent.append(entry)
        muted = self.enabled is not None and category and not self.enabled(category)
        if self.history:
            record({**entry, "muted": True} if muted else entry)
        if muted:
            log.info("muted (%s): %s", category, title)
            return True
        if not self.channels:
            log.info("no notification channel: %s", title)
            return False
        ok = True
        for channel in self.channels:
            if self.queue and self._submit(channel, entry, key):
                log.info("queued (%s): %s", channel.kind, title)
                continue
            # Older messages first, so the order stays; while they can't go out, this one waits too.
            if self.flush() and self._deliver(channel, entry):
                log.info("sent (%s): %s", channel.kind, title)
            else:
                ok = self._keep(channel, entry) and ok
        return ok

    def _submit(self, channel: NotificationChannel, entry: dict, key: str | None) -> bool:
        from . import jobs

        return jobs.submit(KIND, {**entry, "channel": channel.kind}, priority=job_priority(entry["priority"]),
                           valid_for=OUTBOX_MAX_AGE, key=f"{key}:{channel.kind}" if key else None)

    def _deliver(self, channel: NotificationChannel, entry: dict, title: str | None = None) -> bool:
        try:
            channel.deliver(entry, title)
            return True
        except Undeliverable as exc:
            log.error("%s refused %r: %s (dropped)", channel.kind, entry["title"], exc)
            return True  # never again: as good as sent for the order of the others
        except Exception as exc:  # noqa: BLE001 - the server or the network down
            log.warning("%s: not sent (%s): %s", channel.kind, entry["title"], exc)
            return False

    def flush(self) -> bool:
        """Send what waits in the outbox for this notifier's channels; False when one of them could not go out."""
        path = self.outbox_dir / OUTBOX
        if not path.is_file():
            return True
        by_kind = {c.kind: c for c in self.channels}
        with self._outbox() as (waiting, keep):
            for k, entry in enumerate(waiting):
                if time.time() - entry["ts"] > OUTBOX_MAX_AGE:
                    log.warning("notification outbox: dropped (too old): %s", entry["title"])
                    continue
                channel = by_kind.get(entry.get("channel"))
                if channel is None:
                    keep.append(entry)  # another process's channel: it sends it
                    continue
                if not self._deliver(channel, entry, late_title(entry)):
                    keep.extend(waiting[k:])
                    return False
                log.info("sent late (%s): %s", channel.kind, entry["title"])
        return True

    def _keep(self, channel: NotificationChannel, entry: dict) -> bool:
        try:
            with self._outbox() as (waiting, keep):
                keep.extend(waiting + [{**entry, "channel": channel.kind}])
        except OSError as exc:
            log.error("notification lost (%s): %s", exc, entry["title"])
            return False
        log.warning("notification outbox: %s waits", entry["title"])
        return True

    @contextmanager
    def _outbox(self):
        """The waiting messages under a file lock (several processes share it); `keep` is written back."""
        path = self.outbox_dir / OUTBOX
        with path.open("a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            waiting = []
            for line in f:
                try:
                    waiting.append(json.loads(line))
                except ValueError:
                    continue
            keep: list[dict] = []
            yield waiting, keep
            f.seek(0)
            f.truncate()
            f.writelines(json.dumps(e, ensure_ascii=False) + "\n" for e in keep)
