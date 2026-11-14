"""Router: the one port in front of the application's services (in a single container and in development).

Every request goes to the web app, except the paths the manifests route to a service of their own (Module.ROUTES,
e.g. /events to the push service, /ws/devices to a module's service). Plain HTTP is streamed through
(Server-Sent Events arrive at once), WebSockets are bridged message by message. The client's address goes along in
X-Forwarded-For / X-Real-IP (the web app trusts it from the router only, flaskspark.core.web).

Later, with one container per service, a reverse proxy (e.g. nginx, Traefik) takes over with the same routes
(`<app> routes` prints them).

A service of the core like web and push (ServiceInfo "router", process flaskspark-router, unit
flaskspark-router.service; `<app> service router`, also `<app> router`): it proxies from the start, NATS or not.
Once NATS is reachable (user "router", optional) it sends heartbeats into the service directory with its routes, the
connections it holds open (requests in flight, WebSockets) and its requests and upstream failures of the last
minute; the status tile RouterTile shows them and the guardian's ServicesCheck watches it like every service.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import deque
from dataclasses import dataclass

import aiohttp
from aiohttp import web

from flaskspark.core import bus, directory, systemd
from flaskspark.core.service import AsyncService, configure_logging, process_name

log = logging.getLogger(__name__)

HOST = os.environ.get("ROUTER_HOST", "0.0.0.0")
PORT = int(os.environ.get("APP_PORT") or os.environ.get("ROUTER_PORT") or "8100")
WEB_PORT = int(os.environ.get("WEB_PORT", "8101"))
WINDOW = 60.0  # seconds of the counts in the heartbeat (requests and upstream failures per minute)
NATS_RETRY = 5.0  # seconds between attempts to reach NATS while it is not there
HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
               "transfer-encoding", "upgrade", "host", "content-length"}


@dataclass(frozen=True)
class Target:
    prefix: str
    port: int
    websocket: bool = False

    def matches(self, path: str) -> bool:
        return path == self.prefix or path.startswith(self.prefix.rstrip("/") + "/")


def targets(manifests) -> list[Target]:
    """The routes of the manifests, longest prefix first."""
    out = [Target(r.prefix, int(os.environ.get(r.port_env) or r.default_port), r.websocket)
           for m in manifests for r in m.ROUTES]
    return sorted(out, key=lambda t: len(t.prefix), reverse=True)


class Router:
    def __init__(self, routes: list[Target], web_port: int = WEB_PORT):
        self.routes = routes
        self.web_port = web_port
        self.http: aiohttp.ClientSession | None = None
        self.open = 0  # HTTP requests in flight (an event stream stays open as long as its tab)
        self.websockets = 0  # WebSockets bridged right now
        self._requests: deque[float] = deque()  # when each request of the last WINDOW seconds came
        self._failures: deque[float] = deque()  # upstream not reachable (502) in the last WINDOW seconds

    @staticmethod
    def _recent(times: deque, now: float) -> int:
        while times and now - times[0] > WINDOW:
            times.popleft()
        return len(times)

    def details(self, now: float | None = None) -> dict:
        """What the heartbeat carries: its routes, what it holds open, requests and upstream failures per minute."""
        now = now or time.monotonic()
        return {"routes": len(self.routes), "open": self.open, "websockets": self.websockets,
                "requests_per_minute": self._recent(self._requests, now),
                "upstream_failures": self._recent(self._failures, now)}

    def port_for(self, path: str) -> int:
        return next((t.port for t in self.routes if t.matches(path)), self.web_port)

    @staticmethod
    def _headers(request: web.Request) -> dict[str, str]:
        headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_HEADERS}
        peer = request.remote or ""
        forwarded = request.headers.get("X-Forwarded-For")
        headers["X-Forwarded-For"] = f"{forwarded}, {peer}" if forwarded else peer
        headers["X-Real-IP"] = request.headers.get("X-Real-IP") or peer
        headers["X-Forwarded-Proto"] = request.headers.get("X-Forwarded-Proto") or request.scheme
        headers["X-Forwarded-Host"] = request.headers.get("X-Forwarded-Host") or request.host
        return headers

    async def handle(self, request: web.Request) -> web.StreamResponse:
        port = self.port_for(request.path)
        url = f"http://127.0.0.1:{port}{request.rel_url}"
        now = time.monotonic()
        self._requests.append(now)
        self._recent(self._requests, now)
        if request.headers.get("Upgrade", "").lower() == "websocket":
            self.websockets += 1
            try:
                return await self._websocket(request, url)
            finally:
                self.websockets -= 1
        self.open += 1
        try:
            return await self._http(request, url, port)
        finally:
            self.open -= 1

    async def _http(self, request: web.Request, url: str, port: int) -> web.StreamResponse:
        body = await request.read() if request.can_read_body else None
        try:
            upstream = await self.http.request(request.method, url, headers=self._headers(request), data=body,
                                               allow_redirects=False)
        except aiohttp.ClientError as exc:
            log.warning("%s %s -> %d: %s", request.method, request.path, port, exc)
            self._failures.append(time.monotonic())
            return web.Response(status=502, text="service not reachable\n")
        response = web.StreamResponse(status=upstream.status, reason=upstream.reason)
        for key, value in upstream.headers.items():
            if key.lower() not in HOP_HEADERS and key.lower() != "content-encoding":
                response.headers.add(key, value)
        if "Content-Encoding" in upstream.headers:  # passed on as is (aiohttp does not decompress: auto_decompress off)
            response.headers["Content-Encoding"] = upstream.headers["Content-Encoding"]
        try:
            await response.prepare(request)
            async for chunk in upstream.content.iter_any():
                await response.write(chunk)
            await response.write_eof()
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            upstream.release()
        return response

    async def _websocket(self, request: web.Request, url: str) -> web.StreamResponse:
        client = web.WebSocketResponse(autoping=True, heartbeat=None)
        await client.prepare(request)
        headers = {k: v for k, v in self._headers(request).items() if not k.lower().startswith("sec-websocket")}
        try:
            upstream = await self.http.ws_connect(url.replace("http://", "ws://", 1), headers=headers, autoping=True)
        except aiohttp.ClientError as exc:
            log.warning("websocket %s: %s", request.path, exc)
            self._failures.append(time.monotonic())
            await client.close(code=1011, message=b"service not reachable")
            return client

        async def pump(source, sink):
            async for msg in source:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await sink.send_str(msg.data)
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    await sink.send_bytes(msg.data)
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                    break
            await sink.close()

        tasks = [asyncio.create_task(pump(client, upstream)), asyncio.create_task(pump(upstream, client))]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for t in tasks:
                t.cancel()
            await upstream.close()
            await client.close()
        return client

    async def start(self, host: str = HOST, port: int = PORT) -> web.AppRunner:
        self.http = aiohttp.ClientSession(auto_decompress=False, timeout=aiohttp.ClientTimeout(total=None, sock_connect=10))
        app = web.Application(client_max_size=256 * 1024 * 1024)
        app.router.add_route("*", "/{tail:.*}", self.handle)
        runner = web.AppRunner(app, access_log=None, handle_signals=True, handler_cancellation=True)
        await runner.setup()
        await web.TCPSite(runner, host, port).start()
        log.info("router on %s:%d (web %d, %s)", host, port, self.web_port,
                 ", ".join(f"{t.prefix} -> {t.port}" for t in self.routes) or "no routes")
        return runner

    async def close(self) -> None:
        if self.http is not None:
            await self.http.close()


class RouterService(AsyncService):
    """The router as a service: it proxies at once; NATS (user "router") only carries its heartbeats and is optional:
    while it is not reachable the router keeps proxying and tries again every NATS_RETRY seconds."""

    NAME = NATS_USER = "router"

    def __init__(self, router: Router):
        self.router = router
        self.nc = None

    @classmethod
    async def create(cls, nc):  # pragma: no cover - the router starts without NATS (run())
        raise NotImplementedError("the router connects to NATS by itself (RouterService.run)")

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def details(self) -> dict:
        return self.router.details()

    async def connect(self, **options):
        """NATS as user "router": tried until it is there (the first failure logged, the next ones not)."""
        warned = False
        while True:
            try:
                # no reconnects of its own (beat_with_nats connects again), quiet while NATS is away; nats-py
                # retries a refused server within one attempt unless it may give up (max_reconnect_attempts > 0)
                return await asyncio.wait_for(bus.probe(self.NATS_USER, timeout=3.0, name=process_name(self.NAME),
                                                        max_reconnect_attempts=1, **options), 15)
            except Exception as exc:  # noqa: BLE001 - no NATS: the router proxies anyway
                if not warned:
                    log.warning("router: NATS not reachable (%s), proxying without heartbeats; trying again every "
                                "%.0f s", exc or type(exc).__name__, NATS_RETRY)
                    warned = True
            await asyncio.sleep(NATS_RETRY)

    async def beat_with_nats(self) -> None:
        """Connect (until NATS is there), then heartbeats; a connection that ends is made again."""
        while True:
            self.nc = await self.connect()
            log.info("router: NATS connected, heartbeats into the service directory")
            try:
                while self.nc.is_connected:
                    await self.heartbeat(self.nc)
                    await asyncio.sleep(directory.EVERY)
            finally:
                try:
                    await self.nc.close()
                except Exception:  # noqa: BLE001
                    pass

    @classmethod
    async def run(cls) -> None:
        import signal

        from flaskspark.core import config, modules

        router = Router(targets(modules.load(config.load())))
        runner = await router.start()
        service = cls(router)
        systemd.ready()
        tasks = [asyncio.create_task(service.beat_with_nats()), asyncio.create_task(_watchdog())]
        stopped = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stopped.set)
        await stopped.wait()
        systemd.stopping()
        for task in tasks:
            task.cancel()
        if service.nc is not None and service.nc.is_connected:
            await service.leave(service.nc)
            await service.nc.close()
        await runner.cleanup()
        await router.close()


async def _watchdog() -> None:
    """systemd's watchdog while the router's loop runs (it proxies without NATS too)."""
    every = systemd.watchdog_interval()
    if every is None:
        return
    while True:
        systemd.alive()
        await asyncio.sleep(every)


def main() -> None:
    configure_logging()
    asyncio.run(RouterService.run())
