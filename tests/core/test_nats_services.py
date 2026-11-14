"""The core's NATS building blocks against a real nats-server (skipped without one): the service directory, the
heartbeats of a service, leadership, the work queue, the notifications service, health; and that nothing breaks on a
NATS without JetStream."""
from __future__ import annotations

import asyncio
import os
import shutil
import socket
import subprocess
import time

import pytest

from flaskspark.core import bus, directory, health, leader, notify, queue
from flaskspark.core.service import AsyncService

SERVER = shutil.which("nats-server") or ("/usr/local/bin/nats-server" if os.path.exists("/usr/local/bin/nats-server")
                                         else None)
pytestmark = pytest.mark.skipif(SERVER is None, reason="no nats-server")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start(tmp_path_factory, jetstream: bool):
    port = _free_port()
    args = [SERVER, "-a", "127.0.0.1", "-p", str(port)]
    if jetstream:
        args += ["-js", "-sd", str(tmp_path_factory.mktemp("nats"))]
    process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close()
            break
        except OSError:
            time.sleep(0.05)
    else:
        process.kill()
        pytest.skip("nats-server did not start")
    time.sleep(0.3 if jetstream else 0)  # JetStream ready
    return process, f"nats://127.0.0.1:{port}"


@pytest.fixture(scope="module")
def nats_url(tmp_path_factory):
    process, url = _start(tmp_path_factory, jetstream=True)
    yield url
    process.terminate()
    process.wait(10)


@pytest.fixture(scope="module")
def plain_nats_url(tmp_path_factory):
    """A NATS without JetStream."""
    process, url = _start(tmp_path_factory, jetstream=False)
    yield url
    process.terminate()
    process.wait(10)


@pytest.fixture()
def env(nats_url, monkeypatch):
    monkeypatch.setenv("NATS_URL", nats_url)
    monkeypatch.delenv("NATS_MONITOR", raising=False)
    return nats_url


def run(coro):
    return asyncio.run(asyncio.wait_for(coro, 30))


async def connect(url: str):
    return await bus.connect("test", servers=[url], max_reconnect_attempts=0)


# --- service directory ------------------------------------------------------------------------------------------------
def test_heartbeats_into_the_directory_and_out(env):
    async def main():
        nc = await connect(env)
        try:
            registry = directory.Registry(nc)
            heard = []

            async def hear(msg):
                heard.append(bus.loads(msg.data))
            await nc.subscribe(directory.subject("worker"), cb=hear)
            assert await registry.publish(directory.beat("worker", "host-1", details={"n": 1}))
            found = await directory.read_with(nc)
            assert found["ok"] and not found["missing"]
            live = directory.live(found, "worker")
            assert [i["instance"] for i in live] == ["host-1"] and live[0]["details"] == {"n": 1}
            await registry.remove("worker", "host-1")
            assert directory.live(await directory.read_with(nc), "worker") == []
            await nc.flush()
            assert heard and heard[0]["service"] == "worker"
        finally:
            await nc.close()
    run(main())
    assert directory.read("web")["ok"]  # the synchronous reader on a connection of its own (NATS_URL)


def test_an_async_service_beats_and_leaves(env):
    class Worker(AsyncService):
        NAME, NATS_USER = "worker", "worker"

        @classmethod
        async def create(cls, nc):
            return cls()

        async def start(self):
            pass

        async def stop(self):
            pass

        def details(self):
            return {"leader": True, "jobs": 2}

    async def main():
        nc = await connect(env)
        try:
            service = Worker()
            assert await service.heartbeat(nc)
            (found,) = directory.live(await directory.read_with(nc), "worker")
            assert found["role"] == directory.LEADER and found["details"] == {"jobs": 2}
            await service.leave(nc)
            assert directory.live(await directory.read_with(nc), "worker") == []
        finally:
            await nc.close()
    run(main())


def test_without_jetstream_heartbeats_do_not_break(plain_nats_url, monkeypatch):
    monkeypatch.setenv("NATS_URL", plain_nats_url)

    async def main():
        nc = await connect(plain_nats_url)
        try:
            registry = directory.Registry(nc)
            assert await registry.publish(directory.beat("worker", "host-1"))  # the subject still has it
            assert registry.failed_at is not None
            assert await registry.publish(directory.beat("worker", "host-1"))  # no second try within KV_RETRY
            await registry.remove("worker", "host-1")
        finally:
            await nc.close()
    run(main())
    found = directory.read("web")
    assert not directory.usable(found)
    n = health.nats_health("web")
    assert n["ok"] and n["jetstream"] is False


# --- leadership -------------------------------------------------------------------------------------------------------
def test_one_instance_leads_and_hands_over(env):
    async def main():
        a_nc, b_nc = await connect(env), await connect(env)
        events = []

        def recorder(name, what):
            async def record():
                events.append((name, what))
            return record

        a = leader.Leadership(a_nc, "test_leader", "a", recorder("a", "lead"), recorder("a", "resign"), ttl=5,
                              refresh=1)
        b = leader.Leadership(b_nc, "test_leader", "b", recorder("b", "lead"), recorder("b", "resign"), ttl=5,
                              refresh=1)
        try:
            assert await a.step() is True
            assert await b.step() is False
            assert await a.step() is True  # renewed
            await a.release()
            assert await b.step() is True
            assert events == [("a", "lead"), ("a", "resign"), ("b", "lead")]
        finally:
            await b.release()
            await a_nc.close()
            await b_nc.close()
    run(main())


# --- work queue -------------------------------------------------------------------------------------------------------
def test_queue_priorities_retries_skips_and_keys(env):
    async def main():
        nc = await connect(env)
        try:
            worker = queue.Worker(nc, "testjob", ack_wait=5)
            await worker.start()
            await queue.submit(nc, "testjob", {"title": "low"}, priority=queue.LOW)
            await queue.submit(nc, "testjob", {"title": "high"}, priority=queue.HIGH, key="k1")
            await queue.submit(nc, "testjob", {"title": "high again"}, priority=queue.HIGH, key="k1")  # duplicate
            assert (await queue.waiting(nc, "testjob"))["waiting"] == 2
            job = await worker.take(wait=1)
            assert job.payload["title"] == "high" and job.tries == 1
            await worker.done(job)
            job = await worker.take(wait=1)
            assert job.payload["title"] == "low"
            await worker.done(job, RuntimeError("down"))  # again in 5 s
            assert await worker.take(wait=0.5) is None
            await queue.submit(nc, "testjob", {"title": "skip me"})
            job = await worker.take(wait=1)
            await worker.done(job, queue.Skip("no longer fits"))
            expired = queue.Job("testjob", {"title": "old"}, expires=time.time() - 1)
            await nc.jetstream().publish(expired.subject, bus.dumps(expired.to_dict()))
            assert await worker.take(wait=0.5) is None  # dropped on the way
            assert worker.stats == {"done": 1, "failed": 1, "expired": 1, "skipped": 1}
        finally:
            await nc.close()
    run(main())


def test_queue_submit_from_synchronous_code(env, monkeypatch):
    """flaskspark.core.jobs over the events connection (a connection of its own here, reset afterwards)."""
    from flaskspark.core import events, jobs

    assert jobs.submit("testsync", {"title": "x"}) is False  # no events.init: the caller decides

    loop = asyncio.new_event_loop()
    import threading

    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    nc = asyncio.run_coroutine_threadsafe(connect(env), loop).result(10)
    monkeypatch.setattr(events, "_loop", loop)
    monkeypatch.setattr(events, "_nc", nc)
    monkeypatch.setattr(events, "_user", "test")
    try:
        worker = jobs.SyncWorker("testsync")
        assert worker.take() is None  # starts the worker (and the stream)
        assert jobs.submit("testsync", {"title": "sync"}, key="once")
        job = worker.take()
        assert job is not None and job.payload["title"] == "sync" and job.origin == "test"
        worker.done(job)
    finally:
        asyncio.run_coroutine_threadsafe(nc.close(), loop).result(10)
        loop.call_soon_threadsafe(loop.stop)
        thread.join(5)


# --- notifications service ------------------------------------------------------------------------------------------
class Recorder(notify.NotificationChannel):
    kind = "recorder"

    def __init__(self):
        self.delivered = []

    def deliver(self, entry, title=None):
        self.delivered.append(title or entry["title"])


def test_notifications_service_delivers_from_the_queue(env):
    from flaskspark.core.services.notifications.service import NotificationsService

    async def main():
        nc = await connect(env)
        channel = Recorder()
        service = NotificationsService(nc, channels=[channel])
        try:
            await service.start()
            entry = {"ts": time.time(), "title": "Hello", "message": "World", "priority": 3, "channel": "recorder"}
            await queue.submit(nc, notify.KIND, entry, priority=queue.NORMAL)
            await queue.submit(nc, notify.KIND, {**entry, "title": "Nowhere", "channel": "other"})
            for _ in range(50):
                if channel.delivered and service.worker.stats["skipped"]:
                    break
                await asyncio.sleep(0.1)
            assert channel.delivered == ["Hello"]
            assert service.details()["channels"] == ["recorder"] and service.worker.stats["skipped"] == 1
        finally:
            await service.stop()
            await nc.close()
    run(main())
    q = health.queue_health("web", notify.KIND)
    assert q == {"ok": True, "waiting": 0, "oldest": None}


# --- health -----------------------------------------------------------------------------------------------------------
def test_nats_health_over_a_client_connection(env):
    n = health.nats_health("web")
    assert n["ok"] and n["jetstream"] and n["version"]
    from flaskspark.core import config, status

    ctx = status.StatusContext(config.load())
    tiles = status.collect(config.load(), ctx=ctx, shown=[status.NatsTile()])
    assert tiles[0]["level"] == "ok"


def test_nats_health_without_nats(monkeypatch):
    monkeypatch.setenv("NATS_URL", f"nats://127.0.0.1:{_free_port()}")
    monkeypatch.delenv("NATS_MONITOR", raising=False)
    n = health.nats_health("web", timeout=1)
    assert n["ok"] is False and n["error"]
    assert not directory.usable(directory.read("web", timeout=1))


# --- guardian service -------------------------------------------------------------------------------------------------
def test_guardian_runs_its_checks_and_tells_the_tiles(env, tmp_path):
    from flaskspark.core.config import Config
    from flaskspark.core.services.guardian import Guard
    from flaskspark.core.services.guardian.checks import NatsCheck
    from flaskspark.core.services.guardian.service import GuardianService

    class Notifier:
        sent = []

        def send(self, title, message, **kw):
            self.sent.append(title)

        def flush(self):
            return True

    async def main():
        nc = await connect(env)
        heard = asyncio.Event()

        async def hear(msg):
            heard.set()
        await nc.subscribe("ev.all.services", cb=hear)
        guard = Guard(Config({}), Notifier(), checks=[NatsCheck()], state_file=tmp_path / "findings.json")
        service = GuardianService(nc, guard)
        try:
            await service.check()
            await asyncio.wait_for(heard.wait(), 5)
            assert service.details()["last_check"] and service.details()["findings"] == []
        finally:
            await nc.close()
    run(main())


def test_guardian_watches_the_directory_between_its_runs(env, tmp_path):
    """A new instance in the service directory reloads the status tiles at once, not on the guardian's next run."""
    from flaskspark.core.config import Config
    from flaskspark.core.services.guardian import Guard, settings
    from flaskspark.core.services.guardian.service import GuardianService
    from flaskspark.core.services.guardian.watch import StatusWatch

    class Notifier:
        def send(self, *a, **kw):
            pass

        def flush(self):
            return True

    async def main():
        nc = await connect(env)
        writer = await connect(env)
        events = []

        async def hear(msg):
            events.append(time.time())
        await nc.subscribe("ev.all.services", cb=hear)
        opt = {**settings(Config({}), []), "interval": 60}
        guard = Guard(Config({}), Notifier(), checks=[], opt=opt, state_file=tmp_path / "findings.json")
        service = GuardianService(nc, guard)
        service.watch = StatusWatch(service.changed, min_gap=0, settle=0)
        try:
            await service.start()
            for _ in range(50):  # the first run tells the tiles
                if events:
                    break
                await asyncio.sleep(0.1)
            assert len(events) == 1
            registry = directory.Registry(writer)
            await registry.publish(directory.beat("worker", "host-1"))
            await asyncio.sleep(0.2)
            await registry.publish(directory.beat("worker", "host-2"))  # a new instance: a change
            for _ in range(50):
                if len(events) > 1:
                    break
                await asyncio.sleep(0.1)
            assert len(events) >= 2
            assert service.rerun.is_set()  # and the checks run again soon
        finally:
            await service.stop()
            await writer.close()
            await nc.close()
    run(main())


def test_a_status_request_to_a_service(env):
    async def main():
        nc = await connect(env)

        async def answer(msg):
            await msg.respond(bus.dumps({"ok": True, "asked": bus.loads(msg.data)}))
        await nc.subscribe("demo.health", cb=answer)
        await nc.flush()
        try:
            return await asyncio.to_thread(health.request, "web", "demo.health", 2.0, {"q": 1})
        finally:
            await nc.close()
    assert run(main()) == {"ok": True, "asked": {"q": 1}}
    with pytest.raises(Exception):
        health.request("web", "nobody.listens", 0.5)


# --- the router --------------------------------------------------------------------------------------------------
def test_the_router_proxies_without_nats_and_beats_once_it_is_there(env, monkeypatch):
    """The router works from the start without NATS; its heartbeats (user "router") follow once NATS is there."""
    from aiohttp import ClientSession, web

    from flaskspark.core.services.router import service as router_service

    async def main():
        async def page(_request):
            return web.Response(text="from web")

        upstream = web.Application()
        upstream.router.add_get("/", page)
        up = web.AppRunner(upstream)
        await up.setup()
        web_port, port = _free_port(), _free_port()
        await web.TCPSite(up, "127.0.0.1", web_port).start()
        router = router_service.Router([router_service.Target("/away", _free_port())], web_port=web_port)
        runner = await router.start("127.0.0.1", port)
        service = router_service.RouterService(router)
        monkeypatch.setattr(router_service, "NATS_RETRY", 0.1)
        try:
            # no NATS yet: it proxies anyway, and an upstream that is away counts
            monkeypatch.setenv("NATS_URL", f"nats://127.0.0.1:{_free_port()}")
            beats = asyncio.create_task(service.beat_with_nats())
            async with ClientSession() as http:
                async with http.get(f"http://127.0.0.1:{port}/") as response:
                    assert response.status == 200 and await response.text() == "from web"
                async with http.get(f"http://127.0.0.1:{port}/away") as response:
                    assert response.status == 502
            assert service.nc is None
            beats.cancel()
            await asyncio.gather(beats, return_exceptions=True)

            # NATS there: its heartbeats in the service directory, with what it carries
            monkeypatch.setenv("NATS_URL", env)
            beats = asyncio.create_task(service.beat_with_nats())
            nc = await connect(env)
            try:
                for _ in range(50):
                    live = directory.live(await directory.read_with(nc), "router")
                    if live:
                        break
                    await asyncio.sleep(0.1)
                (found,) = live
                assert found["details"]["routes"] == 1 and found["details"]["requests_per_minute"] == 2
                assert found["details"]["upstream_failures"] == 1 and found["details"]["open"] == 0
                await service.leave(service.nc)
                assert directory.live(await directory.read_with(nc), "router") == []
            finally:
                beats.cancel()
                await asyncio.gather(beats, return_exceptions=True)
                await nc.close()
        finally:
            await runner.cleanup()
            await router.close()
            await up.cleanup()
    run(main())
