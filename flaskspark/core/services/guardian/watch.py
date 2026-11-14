"""Status changes as they happen: the guardian tells the browsers at once that the status tiles changed.

Between its runs the guardian watches what the tiles show and sends ev.all.services on a change, so a page reloads the
status right away instead of on the guardian's next round:

- the service directory: every heartbeat and every clean stop arrives on $KV.services.<service>.<instance>; a new
  instance, a stopped one, a change of `ok` or of the role, and a heartbeat that went stale count;
- the NATS servers (with NATS_MONITOR): their /healthz every few seconds (cheap; NATS's own server events only exist
  in the system account).

Changes are throttled (at most one event per MIN_GAP seconds; a pending one goes out once the gap is over), so a
restart of all services does not make every tab reload all the time. A change also brings the guardian's next run of
the checks forward (at most one per RUN_GAP seconds), so its own tile shows a new or resolved finding at once. Its
notifications stay as they are (after their grace time): a short blip shows on the tiles but alerts nobody.

The guardian's NATS user needs the right to subscribe to $KV.services.>; without it only the servers are watched.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable, Iterable

from flaskspark.core import directory

log = logging.getLogger(__name__)

SUBJECT = f"$KV.{directory.BUCKET}.>"
PROBE_EVERY = 3.0  # seconds between two looks at the NATS servers
PROBE_TIMEOUT = 1.5  # seconds a server may take for /healthz
MIN_GAP = 2.0  # seconds at least between two events
RUN_GAP = 5.0  # seconds at least between the starts of two runs of the checks (a change brings the next one forward)
TICK = 0.5  # seconds between two ticks in the guardian's wait
DELETED = ("DEL", "PURGE")


def nodes_up(monitors: Iterable[str], timeout: float = PROBE_TIMEOUT) -> frozenset[str]:
    """The NATS servers whose /healthz answers 200 (by monitoring URL). Never raises."""
    import httpx

    up = set()
    with httpx.Client(timeout=timeout) as c:
        for m in monitors:
            try:
                if c.get(f"{m}/healthz").status_code == 200:
                    up.add(m)
            except Exception:  # noqa: BLE001 - down or not reachable
                pass
    return frozenset(up)


class StatusWatch:
    """Notices changes of what the status tiles show and calls emit() for them, throttled.

    beat() takes the messages of the directory (from the NATS callback), tick() runs in the guardian's wait between its
    runs (probes the servers, finds stale heartbeats, sends what is pending). Thread-safe."""

    def __init__(self, emit: Callable[[], None], probe: Callable[[], frozenset[str]] | None = None,
                 clock: Callable[[], float] = time.time, probe_every: float = PROBE_EVERY, min_gap: float = MIN_GAP,
                 stale: float = directory.STALE, settle: float = directory.EVERY * 1.5):
        self.emit = emit
        self.probe = probe
        self.clock = clock
        self.probe_every = probe_every
        self.min_gap = min_gap
        self.stale = stale
        self.started: float | None = None  # the first heartbeat heard (the subscription may come late)
        self.settle = settle  # instances heard this soon after the first heartbeat were there before: no change
        self._lock = threading.Lock()
        self._instances: dict[str, dict] = {}  # key -> {ok, role, ts, stale}
        self._nodes: frozenset[str] | None = None
        self._probed: float | None = None
        self._sent = 0.0
        self.pending: set[str] = set()  # why an event is due (for the log)

    def beat(self, key: str, data: dict | None) -> None:
        """A message of the directory: the heartbeat under `key` or (data None) its deletion."""
        now = self.clock()
        with self._lock:
            if self.started is None:
                self.started = now
            old = self._instances.get(key)
            if data is None:
                if self._instances.pop(key, None) is not None:
                    self.pending.add(f"{key} stopped")
                return
            state = {"ok": bool(data.get("ok", True)), "role": data.get("role"), "ts": now, "stale": False}
            self._instances[key] = state
            if old is None:
                if now - self.started > self.settle:
                    self.pending.add(f"{key} new")
            elif old["stale"]:
                self.pending.add(f"{key} back")
            elif (old["ok"], old["role"]) != (state["ok"], state["role"]):
                self.pending.add(f"{key} {'ok' if state['ok'] else 'not ok'}, role {state['role']}")

    def tick(self) -> bool:
        """Probe the servers when due, mark stale heartbeats, send a pending event; True when one went out."""
        now = self.clock()
        if self.probe is not None and (self._probed is None or now - self._probed >= self.probe_every):
            self._probed = now
            try:
                nodes = self.probe()
            except Exception:  # noqa: BLE001 - a broken probe must not stop the guardian
                log.debug("status watch: probe failed", exc_info=True)
                nodes = None
            if nodes is not None:
                with self._lock:
                    if self._nodes is not None and nodes != self._nodes:
                        self.pending.add("NATS nodes")
                    self._nodes = nodes
        with self._lock:
            for key, state in self._instances.items():
                if not state["stale"] and now - state["ts"] > self.stale:
                    state["stale"] = True
                    self.pending.add(f"{key} without heartbeat")
            if not self.pending or now - self._sent < self.min_gap:
                return False
            why, self.pending = sorted(self.pending), set()
            self._sent = now
        log.info("status changed: %s", ", ".join(why))
        self.emit()
        return True

    def sent(self) -> None:
        """An event went out otherwise (after a run of the checks): nothing pending, the gap starts anew."""
        with self._lock:
            self.pending.clear()
            self._sent = self.clock()


def message(subject: str, headers: dict | None, data: bytes) -> tuple[str, dict | None]:
    """A message of the directory's bucket as (key, heartbeat or None for a deletion)."""
    key = subject.split(".", 2)[2] if subject.count(".") >= 2 else subject
    if (headers or {}).get("KV-Operation") in DELETED or not data:
        return key, None
    try:
        beat = json.loads(data)
    except ValueError:
        return key, {}
    return key, beat if isinstance(beat, dict) else {}
