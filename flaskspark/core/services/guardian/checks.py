"""The guardian's checks of the core: NATS, the services in the service directory, the notification queue."""

from __future__ import annotations

from collections.abc import Callable

from flaskspark.core import health
from flaskspark.core.module import N_
from flaskspark.core.service import process_name

from .base import CRITICAL, WARNING, Finding, GuardCheck, GuardContext


def _describe(instances: list[dict]) -> str:
    return ", ".join(str(i.get("host") or i.get("instance")) for i in instances)


class NatsCheck(GuardCheck):
    """The message bus. Without it the other checks that need NATS find nothing: the cause, not every consequence."""

    def run(self, ctx: GuardContext) -> list[Finding]:
        n = ctx.nats()
        if not n.get("ok"):
            return [Finding("nats:down", CRITICAL, N_("NATS not reachable"),
                            N_("The services' message bus does not answer (%(error)s)."),
                            grace=ctx.opt["nats_grace"], params={"error": str(n.get("error"))})]
        down, nodes = n.get("down") or [], n.get("nodes") or []
        if down:  # a cluster without some of its nodes: still running, one more and it stops
            return [Finding("nats:degraded", WARNING, N_("NATS nodes down"),
                            N_("%(down)s of %(nodes)s nodes do not answer (%(names)s). The cluster runs on with the "
                               "others; without a majority the message bus stops."), grace=ctx.opt["nats_grace"],
                            params={"down": len(down), "nodes": len(nodes), "names": ", ".join(down)})]
        return []


class ServicesCheck(GuardCheck):
    """Every service of the core and the enabled modules runs, wherever it runs: at least one instance with a fresh
    heartbeat in the service directory, never two of a service that allows only one (ServiceInfo.single), not every
    instance reporting errors. The findings' texts name a service "flaskspark-<service>", their keys keep the short
    name (service:<name>, as the findings kept so far)."""

    def __init__(self, services=None):
        self._services = None if services is None else list(services)

    def services(self, ctx: GuardContext) -> list:
        if self._services is not None:
            return self._services
        from flaskspark.core import modules

        return modules.services(ctx.cfg)

    def run(self, ctx: GuardContext) -> list[Finding]:
        if not ctx.nats().get("ok"):
            return []  # NatsCheck reports it
        if not ctx.directory_usable():
            d = ctx.directory()
            if d.get("missing"):
                return []  # nobody wrote a heartbeat yet (a fresh start)
            return [Finding("directory:unreadable", WARNING, N_("Service directory not readable"),
                            N_("The services can't be watched: %(error)s (NATS without JetStream?)."),
                            grace=ctx.opt["service_grace"], params={"error": str(d.get("error"))})]
        out = []
        for s in self.services(ctx):
            name = process_name(s.name)
            found = ctx.all_instances(s.name)
            live = ctx.instances(s.name)
            label = s.label  # translated with the texts (a module's label is a source text too)
            if not live:
                last = max(found, key=lambda i: i.get("ts") or 0, default=None)
                if last and last.get("ts"):
                    text = N_("No instance of the service %(name)s reports in the service directory (not running, "
                              "hanging or without NATS). Last heartbeat %(minutes)s min ago from %(host)s.")
                else:
                    text = N_("No instance of the service %(name)s reports in the service directory (not running, "
                              "hanging or without NATS).")
                out.append(Finding(f"service:{s.name}", CRITICAL, N_("%(label)s: no heartbeat"), text,
                                   grace=ctx.opt["service_grace"],
                                   params={"label": label, "name": name, "host": str(last.get("host")) if last else "",
                                           "minutes": f"{(ctx.now - last['ts']) / 60:.0f}"
                                           if last and last.get("ts") else ""}))
            elif s.single and len(live) > 1:
                out.append(Finding(f"service:{s.name}:twice", CRITICAL, N_("%(label)s: %(count)s instances"),
                                   N_("The service %(name)s may run only once, but %(count)s instances report: "
                                      "%(instances)s."), grace=ctx.opt["service_grace"],
                                   params={"label": label, "name": name, "count": len(live),
                                           "instances": _describe(live)}))
            elif all(i.get("ok") is False for i in live):
                out.append(Finding(f"service:{s.name}:failing", WARNING, N_("%(label)s: reports errors"),
                                   N_("The service %(name)s runs, but reports that it can't work (%(instances)s)."),
                                   grace=ctx.opt["service_grace"],
                                   params={"label": label, "name": name, "instances": _describe(live)}))
        return out


class NotifyQueueCheck(GuardCheck):
    """Notifications waiting in the work queue: nobody delivers them (the notifications service is away)."""

    def __init__(self, read_queue: Callable[[GuardContext], dict] | None = None):
        self.read_queue = read_queue

    def run(self, ctx: GuardContext) -> list[Finding]:
        from flaskspark.core import notify

        if not ctx.nats().get("ok"):
            return []
        q = self.read_queue(ctx) if self.read_queue else health.queue_health(ctx.USER, notify.KIND)
        if q.get("ok") and q.get("oldest") is not None and q["oldest"] >= ctx.opt["notify_stuck_minutes"] * 60:
            return [Finding("notify:stuck", CRITICAL, N_("Notifications pile up"),
                            N_("%(waiting)s notifications wait in the queue, the oldest for %(minutes)s min: the "
                               "notifications service delivers nothing. They go out once it runs again (valid for a "
                               "day)."), params={"waiting": q["waiting"], "minutes": f"{q['oldest'] / 60:.0f}"})]
        return []
