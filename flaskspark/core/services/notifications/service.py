"""Notifications service: delivers the notifications from the durable work queue (job kind flaskspark.core.notify.KIND)
over their channel (flaskspark.core.notify.NotificationChannel; the core's: ntfy).

Switched on in config.yaml (`notifications: {enabled: true}`); off by default, so an application without a channel is
not affected. The processes queue every message (flaskspark.core.notify.Notifier); this service takes them, highest
priority first, and delivers them. A channel down: the job comes again later (growing pauses), for as long as the
message is valid (a day). A message that goes out more than notify.LATE_AFTER seconds after it was written says so in
its title. A message a channel refuses for good (notify.Undeliverable) is dropped with a log line. Several instances
may run (other hosts too): each message goes to one.

NATS user "notify" (NATS_NOTIFY_USER / NATS_NOTIFY_PASSWORD): the stream JOBS (consumers notify-p1..3), the bucket
jobs_done and its heartbeat ms.notifications.heartbeat.
"""

from __future__ import annotations

import asyncio
import logging

from flaskspark.core import notify
from flaskspark.core.queue import Job, Skip, Worker
from flaskspark.core.service import AsyncService

log = logging.getLogger(__name__)


class NotificationsService(AsyncService):
    NAME, NATS_USER = "notifications", "notify"
    START_RETRY = 5.0  # the stream needs NATS with JetStream: wait for it

    def __init__(self, nc, channels: list[notify.NotificationChannel] | None = None):
        self.nc = nc
        self.channels = {c.kind: c for c in (notify.channels() if channels is None else channels)}
        self.worker = Worker(nc, notify.KIND, self.deliver, ack_wait=60.0, max_tries=1000)
        self.tasks: list[asyncio.Task] = []

    async def deliver(self, job: Job) -> None:
        entry = job.payload
        if not entry.get("title") or "message" not in entry:
            raise Skip("not a message")
        channel = self.channels.get(entry.get("channel") or "")
        if channel is None:
            raise Skip(f"no channel {entry.get('channel')!r} configured")
        title = notify.late_title(entry)
        try:
            await asyncio.to_thread(channel.deliver, entry, title)
        except notify.Undeliverable as exc:
            log.error("%s refused %r: %s (dropped)", channel.kind, entry["title"], exc)
            raise Skip(str(exc)) from exc
        log.info("sent%s (%s): %s", " late" if title != entry["title"] else "", channel.kind, entry["title"])

    def details(self) -> dict:
        return {**self.worker.stats, "channels": sorted(self.channels), "ok": bool(self.channels)}

    @classmethod
    async def create(cls, nc) -> NotificationsService:
        return cls(nc)

    async def start(self) -> None:
        if not self.channels:
            log.warning("no notification channel configured (e.g. NTFY_URL and NTFY_TOPIC): messages wait in the queue")
            return
        await self.worker.start()
        self.tasks = [asyncio.create_task(self.worker.run())]

    async def stop(self) -> None:
        self.worker.stop()
        for t in self.tasks:
            t.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)


main = NotificationsService.main
