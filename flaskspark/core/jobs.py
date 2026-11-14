"""The durable work queue (flaskspark.core.queue) for synchronous code: the web app, the CLI, threads.

    jobs.submit("mail", {...}, priority=queue.HIGH, valid_for=86400, key="...")   # True: queued (on disk)
    worker = jobs.SyncWorker("report", ack_wait=900)                               # in a synchronous loop:
    job = worker.take(); ...; worker.done(job, error)

Over the process's NATS connection of flaskspark.core.events (events.init before). submit() returns False when the
queue can't take the job (no init, NATS away, no JetStream, no stream yet): the caller decides what to do then (e.g. do
it at once, or later again).
"""

from __future__ import annotations

import asyncio
import logging
import time

from . import events, queue
from .queue import Job, Skip  # noqa: F401 - for the callers

log = logging.getLogger(__name__)

SUBMIT_TIMEOUT = 3.0
START_RETRY = 60.0  # seconds between attempts to start a worker that could not


def _run(coro, timeout: float):
    return asyncio.run_coroutine_threadsafe(coro, events._loop).result(timeout)


def available() -> bool:
    return events.connected() and events._loop is not None


def submit(kind: str, payload: dict, priority: int = queue.NORMAL, valid_for: float = 3600.0,
           key: str | None = None) -> bool:
    """Queue a job; False (logged) if the queue can't take it now. Blocks at most SUBMIT_TIMEOUT seconds."""
    if not available():
        return False
    try:
        return _run(queue.submit(events._nc, kind, payload, priority, valid_for, key, origin=events._user or "",
                                 timeout=SUBMIT_TIMEOUT), SUBMIT_TIMEOUT + 1)
    except Exception as exc:  # noqa: BLE001 - no stream, no rights, timeout
        log.warning("job %s not queued: %s", kind, exc or type(exc).__name__)
        return False


class SyncWorker:
    """A queue.Worker for a synchronous loop: take() a job, run it, done() it. Started lazily on the events connection;
    while a job runs, JetStream is told it still does (no second delivery)."""

    def __init__(self, kind: str, ack_wait: float = 60.0, max_tries: int = queue.MAX_TRIES):
        self.kind, self.ack_wait, self.max_tries = kind, ack_wait, max_tries
        self.worker: queue.Worker | None = None
        self._alive = None
        self._tried = 0.0

    def _ready(self) -> bool:
        if self.worker is not None:
            return True
        if not available() or time.time() - self._tried < START_RETRY:
            return False
        self._tried = time.time()
        worker = queue.Worker(events._nc, self.kind, ack_wait=self.ack_wait, max_tries=self.max_tries)
        try:
            _run(worker.start(), 10)
        except Exception as exc:  # noqa: BLE001 - next round
            log.warning("jobs %s: worker not started: %s", self.kind, exc)
            return False
        self.worker = worker
        return True

    def take(self) -> Job | None:
        """The next job (not waiting), or None."""
        if not self._ready():
            return None
        try:
            job = _run(self.worker.take(wait=0), 10)
        except Exception as exc:  # noqa: BLE001 - NATS away
            log.warning("jobs %s: %s", self.kind, exc)
            return None
        if job is not None:
            self._alive = asyncio.run_coroutine_threadsafe(self.worker.keep_alive(job), events._loop)
        return job

    def done(self, job: Job, error: BaseException | None = None) -> None:
        if self._alive is not None:
            self._alive.cancel()
            self._alive = None
        try:
            _run(self.worker.done(job, error), 10)
        except Exception as exc:  # noqa: BLE001 - not acked: it comes again after ack_wait
            log.warning("job %s not acknowledged: %s", job.id, exc)
