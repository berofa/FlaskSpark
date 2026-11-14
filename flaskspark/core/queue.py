"""Durable work queue for jobs that are not critical in time (notifications, long analyses, mails to send), on NATS
JetStream. The async side: submit() and Worker; synchronous code (the web app) submits through
flaskspark.core.jobs.

JetStream stream STREAM (subjects job.<kind>.p<priority>, work queue: a job is gone once a worker acked it, on disk,
kept at most MAX_AGE). A job:

    {id, kind, key, priority, created, expires, payload, origin}

- Priority 1 (high), 2 (normal), 3 (low): one subject and durable consumer per kind and priority; a worker always
  takes the highest waiting priority first, within one priority the oldest. Each kind has its own queue, so a long
  job of one kind never holds up another kind.
- Valid until (expires): a job taken after that is dropped with a log line instead of run.
- Key against running twice: the same key submitted again within DUPLICATE_WINDOW is not queued again (JetStream
  Nats-Msg-Id); a job whose key ran already (key-value bucket DONE_BUCKET, DONE_TTL) is not run again (a redelivery
  after the worker died between running and acking).
- Retries: a failed job comes again after a growing pause (RETRY_DELAYS), at most max_tries times; a handler raises
  Skip when the job no longer fits (acked, logged).

Several workers (other processes, other hosts) share a kind: each job goes to one of them. Handlers must be made for
a second run (at least once delivery).
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from . import bus

log = logging.getLogger(__name__)

STREAM = "JOBS"
MAX_AGE = 7 * 86400.0  # a job older than this is gone, run or not
DUPLICATE_WINDOW = 600.0  # seconds a key keeps a second submission out
DONE_BUCKET = "jobs_done"
DONE_TTL = 7 * 86400.0
PRIORITIES = (1, 2, 3)
HIGH, NORMAL, LOW = PRIORITIES
RETRY_DELAYS = (5, 15, 30, 60, 120, 300)  # seconds before the n-th retry (the last one for all after)
MAX_TRIES = 50
FETCH_WAIT = 0.5  # seconds a worker waits on its lowest priority when nothing is there
_KIND = re.compile(r"^[A-Za-z0-9_-]+$")


class Skip(Exception):
    """The job no longer fits (e.g. superseded): acked without running again, with this reason in the log."""


@dataclass
class Job:
    kind: str
    payload: dict
    priority: int = NORMAL
    expires: float = 0.0
    key: str | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created: float = field(default_factory=time.time)
    origin: str = ""
    tries: int = 1  # delivery number (set by the worker)

    @property
    def subject(self) -> str:
        return subject(self.kind, self.priority)

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "key": self.key, "priority": self.priority, "created": self.created,
                "expires": self.expires, "payload": self.payload, "origin": self.origin}

    @classmethod
    def from_dict(cls, d: dict) -> Job:
        return cls(kind=d["kind"], payload=d.get("payload") or {}, priority=int(d.get("priority") or NORMAL),
                   expires=float(d.get("expires") or 0), key=d.get("key"), id=d.get("id") or uuid.uuid4().hex,
                   created=float(d.get("created") or time.time()), origin=d.get("origin") or "")


def subject(kind: str, priority: int) -> str:
    if not _KIND.match(kind or "") or priority not in PRIORITIES:
        raise ValueError(f"invalid job: {kind!r} p{priority}")
    return f"job.{kind}.p{priority}"


def retry_delay(tries: int) -> int:
    """Seconds before the next try after the `tries`-th failed."""
    return RETRY_DELAYS[min(max(tries, 1), len(RETRY_DELAYS)) - 1]


def _done_key(job: Job) -> str:
    return f"{job.kind}.{hashlib.sha1(job.key.encode()).hexdigest()}"


async def ensure_stream(js) -> None:
    """The stream (created by the workers; submitters just publish), with NATS_REPLICAS copies."""
    from nats.js.api import RetentionPolicy, StorageType, StreamConfig
    from nats.js.errors import NotFoundError

    config = StreamConfig(name=STREAM, subjects=["job.>"], retention=RetentionPolicy.WORK_QUEUE, storage=StorageType.FILE,
                          max_age=MAX_AGE, duplicate_window=DUPLICATE_WINDOW, num_replicas=bus.replicas())
    try:
        await js.stream_info(STREAM)
        await js.update_stream(config)
    except NotFoundError:
        await js.add_stream(config)


async def submit(nc, kind: str, payload: dict, priority: int = NORMAL, valid_for: float = 3600.0,
                 key: str | None = None, origin: str = "", timeout: float = 3.0) -> bool:
    """Queue a job; True once JetStream has it on disk (also when the key was there already: not twice). Raises when
    it could not (no JetStream, no stream yet: no worker ever started, no rights, timeout)."""
    job = Job(kind, payload, priority, time.time() + valid_for, key, origin=origin)
    headers = {"Nats-Msg-Id": f"{kind}:{key}"} if key else None
    ack = await nc.jetstream(timeout=timeout).publish(job.subject, bus.dumps(job.to_dict()), timeout=timeout,
                                                      headers=headers)
    if ack.duplicate:
        log.info("job %s %s: already queued", kind, key)
    return True


async def waiting(nc, kind: str, timeout: float = 3.0) -> dict:
    """{waiting: jobs of `kind` in the queue, oldest: seconds the oldest of them waits (None without)}."""
    from nats.js.errors import NotFoundError

    js = nc.jetstream(timeout=timeout)
    try:
        info = await js.stream_info(STREAM, subjects_filter=f"job.{kind}.>")
    except NotFoundError:
        return {"waiting": 0, "oldest": None}
    counts = (info.state.subjects or {}) if info.state else {}
    created = []
    for subj in counts:
        try:
            msg = await js.get_msg(STREAM, seq=1, subject=subj, next=True)
            created.append(float((bus.loads(msg.data) or {}).get("created") or time.time()))
        except NotFoundError:
            pass
    return {"waiting": sum(counts.values()), "oldest": round(time.time() - min(created)) if created else None}


class Worker:
    """Takes the jobs of one kind, highest priority first.

        worker = Worker(nc, "notify", handler)   # async handler(job); raise to retry, Skip to drop
        await worker.start(); await worker.run()  # or: job = await worker.take(); ...; await worker.done(job, error)
    """

    def __init__(self, nc, kind: str, handler: Callable[[Job], Awaitable[None]] | None = None, ack_wait: float = 60.0,
                 max_tries: int = MAX_TRIES):
        subject(kind, NORMAL)  # a valid kind
        self.nc, self.kind, self.handler = nc, kind, handler
        self.ack_wait, self.max_tries = ack_wait, max_tries
        self.subs: dict[int, object] = {}
        self.kv = None
        self.msgs: dict[str, object] = {}  # job id -> its message while it runs
        self.stats = {"done": 0, "failed": 0, "expired": 0, "skipped": 0}
        self.stopped = asyncio.Event()

    async def start(self) -> None:
        from nats.js.api import AckPolicy, ConsumerConfig
        from nats.js.errors import BucketNotFoundError

        js = self.nc.jetstream()
        await ensure_stream(js)
        try:
            self.kv = await js.key_value(DONE_BUCKET)
        except BucketNotFoundError:
            self.kv = await js.create_key_value(bucket=DONE_BUCKET, ttl=DONE_TTL, history=1, replicas=bus.replicas())
        for p in PRIORITIES:
            durable = f"{self.kind}-p{p}"
            config = ConsumerConfig(durable_name=durable, ack_policy=AckPolicy.EXPLICIT, ack_wait=self.ack_wait,
                                    max_deliver=-1, filter_subject=subject(self.kind, p))
            self.subs[p] = await js.pull_subscribe(subject(self.kind, p), durable=durable, stream=STREAM, config=config)

    async def take(self, wait: float = FETCH_WAIT) -> Job | None:
        """The next job to run (highest priority first), or None after `wait` seconds without one. Expired jobs and
        jobs whose key ran already are acked and logged on the way."""
        from nats.errors import TimeoutError as NatsTimeout

        while True:
            msg = None
            for p in PRIORITIES:
                last = p == PRIORITIES[-1]
                try:
                    msg = (await self.subs[p].fetch(1, timeout=wait if last and wait > 0 else 0.05))[0]
                    break
                except (NatsTimeout, asyncio.TimeoutError):
                    continue
            if msg is None:
                return None
            try:
                job = Job.from_dict(bus.loads(msg.data) or {})
            except (KeyError, TypeError, ValueError):
                log.error("job %s: unreadable, dropped", msg.subject)
                await msg.term()
                continue
            job.tries = msg.metadata.num_delivered
            if job.expires and time.time() > job.expires:
                self.stats["expired"] += 1
                log.warning("job %s %s expired (valid until %s), dropped: %s", job.kind, job.id,
                            time.strftime("%Y-%m-%d %H:%M", time.localtime(job.expires)), _brief(job))
                await msg.ack()
                continue
            if job.key and await self._ran(job):
                log.info("job %s %s: key %s ran already", job.kind, job.id, job.key)
                await msg.ack()
                continue
            self.msgs[job.id] = msg
            return job

    async def done(self, job: Job, error: BaseException | None = None) -> None:
        """The job ran (error None), no longer fits (Skip) or failed (anything else: again later, up to max_tries)."""
        msg = self.msgs.pop(job.id, None)
        if msg is None:
            return
        if error is None or isinstance(error, Skip):
            if error is not None:
                self.stats["skipped"] += 1
                log.info("job %s %s skipped: %s", job.kind, job.id, error)
            else:
                self.stats["done"] += 1
            if job.key:
                try:
                    await self.kv.put(_done_key(job), bus.dumps({"id": job.id, "ts": time.time()}))
                except Exception as exc:  # noqa: BLE001 - the duplicate window still covers a second submission
                    log.warning("job %s: done key not saved: %s", job.id, exc)
            await msg.ack()
            return
        self.stats["failed"] += 1
        if job.tries >= self.max_tries:
            log.error("job %s %s given up after %d tries: %s (%s)", job.kind, job.id, job.tries, error, _brief(job))
            await msg.term()
            return
        delay = retry_delay(job.tries)
        log.warning("job %s %s failed (try %d, again in %d s): %s", job.kind, job.id, job.tries, delay, error)
        await msg.nak(delay=delay)

    async def working(self, job: Job) -> None:
        """Tell JetStream the job still runs (a long one: call it more often than ack_wait)."""
        msg = self.msgs.get(job.id)
        if msg is not None:
            await msg.in_progress()

    async def _ran(self, job: Job) -> bool:
        from nats.js.errors import KeyNotFoundError

        try:
            entry = await self.kv.get(_done_key(job))
            return entry is not None and bool(entry.value)
        except KeyNotFoundError:
            return False
        except Exception as exc:  # noqa: BLE001 - not readable: run it (the handlers are made for a second run)
            log.warning("job %s: done key not readable: %s", job.id, exc)
            return False

    async def run(self) -> None:
        """Take and run jobs until stop(); a handler that runs long is kept alive (working)."""
        while not self.stopped.is_set():
            try:
                job = await self.take()
            except Exception as exc:  # noqa: BLE001 - NATS away: try again
                log.warning("jobs %s: %s", self.kind, exc)
                await asyncio.sleep(1)
                continue
            if job is None:
                continue
            alive = asyncio.create_task(self.keep_alive(job))
            error = None
            try:
                await self.handler(job)
            except Exception as exc:  # noqa: BLE001 - Skip or a retry
                error = exc
            finally:
                alive.cancel()
            try:
                await self.done(job, error)
            except Exception as exc:  # noqa: BLE001 - not acked: JetStream brings it again after ack_wait
                log.warning("job %s: not acknowledged: %s", job.id, exc)

    async def keep_alive(self, job: Job) -> None:
        while True:
            await asyncio.sleep(max(self.ack_wait / 3, 1.0))
            try:
                await self.working(job)
            except Exception:  # noqa: BLE001
                pass

    def stop(self) -> None:
        self.stopped.set()


def _brief(job: Job) -> str:
    return str(job.payload.get("title") or "")[:80]
