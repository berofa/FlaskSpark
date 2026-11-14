"""Push service: the browser's channel for live data, as Server-Sent Events.

A tab opens one event stream (GET /events, the router routes it here) and subscribes to topics with POST /events/sub;
the service subscribes to them on NATS once, however many tabs want them, and forwards every message. The stream is
plain HTTP (over HTTP/2 it shares the page's connection).

Every service that has news for the browser publishes it on NATS (ev.*, or a data topic of its module with the rights
in its manifest, PUSH_TOPICS) and leaves the delivery to this service: the event streams, the latest update for a new
tab, rights, sign-in and reconnects come with it.

Topics served on demand: a module may serve some of its topics itself (Module.push_sources(nc), a TopicSource of
flaskspark.core.services.push.sources), e.g. data a service only sends while someone leases it. The push service asks
the source to start such a topic when its first tab wants it and to end it LINGER seconds after the last tab left; a
tab that subscribes later gets the latest update at once while it is younger than the source's max_age().

Sign-in stays with the web app: on connect (and again every RECHECK seconds) the service asks it (SESSION_URL,
GET /api/push/session) with the cookie the browser sent along; the answer names the user and the topics they may
subscribe to (NATS patterns). No answer or 401: the stream is refused (401) or ended (event "signed-out").

Event stream (text/event-stream): first "event: hello" {user, stream} (stream: the id for /events/sub), then every
message as "data: {topic, data}", "event: ping" every PING seconds, "event: refused" {error, topics} for topics the
user may not have, "event: signed-out" when the session ended. POST /events/sub {stream, sub: [...], unsub: [...]} with
the same cookie -> {ok, refused}; 404 for a stream that is gone (the client reconnects).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from http import HTTPStatus

import secrets

import httpx
from aiohttp import web

from flaskspark.core import bus
from flaskspark.core.service import AsyncService

from .sources import TopicSource

log = logging.getLogger(__name__)

HOST = os.environ.get("PUSH_HOST", "127.0.0.1")
PORT = int(os.environ.get("PUSH_PORT", "8102"))
SESSION_URL = os.environ.get("PUSH_SESSION_URL") or f"http://127.0.0.1:{os.environ.get('WEB_PORT', '8101')}/api/push/session"
RECHECK = 300.0  # seconds between session checks of an open connection
MAX_TOPICS = 200  # per stream
LINGER = 30.0  # seconds a topic stays subscribed after its last tab left (page reloads, switching pages)
PING = 15.0  # seconds between pings on an event stream
QUEUE = 2000  # messages an event stream may lag behind before it is closed (the browser reconnects)


def allowed(topic: str, patterns: list[str]) -> bool:
    """NATS wildcards: * one token, > the rest (at least one token)."""
    tokens = topic.split(".")

    def match(parts: list[str]) -> bool:
        for i, part in enumerate(parts):
            if part == ">":
                return len(tokens) > i
            if i >= len(tokens) or (part != "*" and part != tokens[i]):
                return False
        return len(tokens) == len(parts)
    return any(match(p.split(".")) for p in patterns)


def browser(agent: str) -> str:
    return "Mac" if "Macintosh" in agent else "iPhone" if "iPhone" in agent else "Linux" if "Linux" in agent else agent[:40]


class Tab:
    """A browser tab's event stream: what it wants; messages go through a queue that the response writes out."""

    def __init__(self, user: dict, cookie: str, agent: str = ""):
        self.user, self.cookie, self.browser = user, cookie, browser(agent)
        self.topics: set[str] = set()
        self.checked = time.time()
        self.id = secrets.token_urlsafe(18)
        self.queue: asyncio.Queue[str | None] = asyncio.Queue(QUEUE)

    def _put(self, chunk: str | None) -> None:
        try:
            self.queue.put_nowait(chunk)
        except asyncio.QueueFull:  # far behind (a stalled connection): end it, the browser reconnects
            self.queue = asyncio.Queue(1)
            self.queue.put_nowait(None)

    async def send(self, text: str) -> None:
        self._put(f"data: {text}\n\n")

    async def event(self, name: str, data) -> None:
        self._put(f"event: {name}\ndata: {json.dumps(data)}\n\n")

    async def refuse(self, topics: list[str]) -> None:
        await self.event("refused", {"error": "topic not allowed", "topics": topics})

    async def end(self) -> None:
        """The session ended: tell the browser and close."""
        await self.event("signed-out", {})
        self._put(None)


class PushService(AsyncService):
    NAME, NATS_USER = "push", "push"

    def __init__(self, nc, http: httpx.AsyncClient | None = None, session_url: str = SESSION_URL, manifests=None):
        self.nc = nc
        self.http = http or httpx.AsyncClient(timeout=10)
        self.session_url = session_url
        if manifests is None:
            from flaskspark.core import config, modules

            manifests = modules.load(config.load())
        # the modules' topics served on demand (Module.push_sources) and those of states: their latest update goes to a
        # new tab (PushTopic latest, {uid} any user)
        self.sources: list[TopicSource] = [src for m in manifests for src in m.push_sources(nc)]
        self.states = [t.pattern.replace("{uid}", "*") for m in manifests for t in m.PUSH_TOPICS if t.latest]
        self.tabs: set[Tab] = set()
        self.streams: dict[str, Tab] = {}  # stream id -> event stream
        self.subs: dict[str, object] = {}  # topic -> NATS subscription, or (source, its handle)
        self.users: dict[str, set[Tab]] = {}  # topic -> tabs
        self.latest: dict[str, tuple[float, str]] = {}  # topic -> (received, data as JSON) of its latest update
        self.lingering: dict[str, asyncio.Task] = {}  # topics without tabs, released after LINGER
        self.stopped = asyncio.Event()

    async def session(self, cookie: str) -> dict | None:
        """{user, topics} of the cookie's session, None if it isn't signed in (or the web app can't tell). Without
        sign-in (flaskspark.core.web.access.OpenAccess) the web app answers for a request without a cookie too."""
        try:
            r = await self.http.get(self.session_url, headers={"Cookie": cookie, "Accept": "application/json",
                                                               "X-Requested-With": "fetch"}, follow_redirects=False)
        except httpx.HTTPError as exc:
            log.warning("session check: %s", exc)
            return None
        if r.status_code != 200:
            return None
        try:
            d = r.json()
            return {"user": d["user"], "topics": list(d["topics"])}
        except (ValueError, KeyError, TypeError):
            return None

    def details(self) -> dict:
        return {"tabs": len(self.tabs), "topics": len(self.subs)}

    # --- topics on NATS, shared by the tabs ----------------------------------------------------------
    def source_of(self, topic: str) -> TopicSource | None:
        """The module's source of a topic served on demand, None for a plain NATS topic."""
        return next((src for src in self.sources if src.handles(topic)), None)

    async def _want(self, topic: str, tab: Tab) -> None:
        self.users.setdefault(topic, set()).add(tab)
        lingering = self.lingering.pop(topic, None)
        if lingering is not None:
            lingering.cancel()
        if topic in self.subs:
            await self._replay(topic, tab)
            return
        source = self.source_of(topic)

        async def forward(msg, topic=topic):
            await self._fan_out(topic, msg.data)
        if source is not None:
            async def payload(p, topic=topic):
                await self._fan_out(topic, bus.dumps(p))

            async def last(p, topic=topic):
                if topic not in self.latest:  # a live update came first: that one is newer
                    await self._fan_out(topic, bus.dumps(p))
            self.subs[topic] = (source, None)  # taken before the await: a second tab doesn't start it again
            self.subs[topic] = (source, await source.subscribe(topic, payload, last))
        else:
            self.subs[topic] = await self.nc.subscribe(topic, cb=forward)

    async def _drop(self, topic: str, tab: Tab) -> None:
        tabs = self.users.get(topic)
        if tabs is None:
            return
        tabs.discard(tab)
        if tabs:
            return
        del self.users[topic]
        if topic not in self.lingering:
            self.lingering[topic] = asyncio.create_task(self._release(topic))

    async def _release(self, topic: str) -> None:
        """No tab came back for the topic within LINGER: unsubscribe (and end the lease)."""
        await asyncio.sleep(LINGER)
        if self.lingering.get(topic) is not asyncio.current_task() or topic in self.users:
            return
        del self.lingering[topic]
        self.latest.pop(topic, None)
        sub = self.subs.pop(topic, None)
        if isinstance(sub, tuple):
            await sub[0].unsubscribe(sub[1])
        elif sub is not None:
            await sub.unsubscribe()

    async def _replay(self, topic: str, tab: Tab) -> None:
        """The topic's latest update to a tab that just subscribed: a state's (PushTopic latest) always, a source's
        while it is younger than the source's max_age()."""
        source, latest = self.source_of(topic), self.latest.get(topic)
        if latest is None or (source is None and not allowed(topic, self.states)):
            return
        max_age = source.max_age(topic) if source is not None else None
        if max_age is not None and time.time() - latest[0] > max_age:
            return
        await tab.send('{"topic":' + json.dumps(topic) + ',"data":' + latest[1] + "}")

    async def _fan_out(self, topic: str, raw: bytes) -> None:
        data = raw.decode()
        if topic in self.subs and (isinstance(self.subs[topic], tuple) or allowed(topic, self.states)):
            self.latest[topic] = (time.time(), data)
        text = '{"topic":' + json.dumps(topic) + ',"data":' + data + "}"
        for tab in list(self.users.get(topic, ())):
            await tab.send(text)

    # --- browser connections -------------------------------------------------------------------------
    async def _opened(self, tab: Tab) -> None:
        self.tabs.add(tab)
        log.info("tab open: user %s, %s, %d streams", tab.user["user"], tab.browser, len(self.tabs))

    async def _closed(self, tab: Tab) -> None:
        self.tabs.discard(tab)
        self.streams.pop(tab.id, None)
        log.info("tab closed: user %s, %s, %d streams", tab.user["user"], tab.browser, len(self.tabs))
        for topic in list(tab.topics):
            await self._drop(topic, tab)

    async def events(self, request: web.Request) -> web.StreamResponse:
        """GET /events: the event stream of a tab."""
        cookie = request.headers.get("Cookie", "")
        session = await self.session(cookie)
        if session is None:
            return web.Response(status=401, text="not signed in\n")
        tab = Tab(session, cookie, request.headers.get("User-Agent", ""))
        response = web.StreamResponse(headers={"Content-Type": "text/event-stream", "Cache-Control": "no-store",
                                               "X-Accel-Buffering": "no"})  # nginx: pass every message on at once
        await response.prepare(request)
        self.streams[tab.id] = tab
        await self._opened(tab)
        await tab.event("hello", {"user": tab.user["user"], "stream": tab.id})
        try:
            await response.write(b"retry: 2000\n\n")
            while True:
                try:
                    chunk = await asyncio.wait_for(tab.queue.get(), PING)
                except TimeoutError:
                    chunk = "event: ping\ndata: {}\n\n"
                if chunk is None:
                    break
                await response.write(chunk.encode())
                if time.time() - tab.checked > RECHECK:
                    await self._recheck(tab)  # session ended: "signed-out" and the end come through the queue
        except ConnectionError:
            pass
        finally:  # also when the browser goes away (handler cancelled, see serve)
            await self._closed(tab)
        return response

    async def subscribe(self, request: web.Request) -> web.Response:
        """POST /events/sub {stream, sub, unsub}: topics of a tab's event stream (same cookie as the stream)."""
        try:
            body = await request.json()
        except ValueError:
            return web.json_response({"error": "JSON expected"}, status=400)
        tab = self.streams.get(str(body.get("stream") or ""))
        if tab is None:
            return web.json_response({"error": "unknown stream"}, status=404)
        cookie = request.headers.get("Cookie", "")
        if cookie != tab.cookie:
            session = await self.session(cookie)
            if session is None or session["user"] != tab.user["user"]:
                return web.json_response({"error": "not signed in"}, status=403)
        refused = []
        for op in ("unsub", "sub"):
            topics = [str(t) for t in body.get(op) or []][:MAX_TOPICS]
            if topics:
                refused += await self._topics(tab, op, topics)
        if refused:
            await tab.refuse(refused)
        return web.json_response({"ok": True, "refused": refused})

    async def _topics(self, tab: Tab, op: str, topics: list[str]) -> list[str]:
        refused = []
        for topic in topics:
            if op == "unsub":
                if topic in tab.topics:
                    tab.topics.discard(topic)
                    await self._drop(topic, tab)
            elif not allowed(topic, tab.user["topics"]) or (
                    (source := self.source_of(topic)) is not None and not source.valid(topic)):
                refused.append(topic)
            elif topic not in tab.topics and len(tab.topics) < MAX_TOPICS:
                tab.topics.add(topic)
                await self._want(topic, tab)
        return refused

    async def _recheck(self, tab: Tab) -> bool:
        tab.checked = time.time()
        session = await self.session(tab.cookie)
        if session is None or session["user"] != tab.user["user"]:
            await tab.end()
            return False
        tab.user = session
        for topic in [t for t in tab.topics if not allowed(t, session["topics"])]:  # rights taken away meanwhile
            tab.topics.discard(topic)
            await self._drop(topic, tab)
        return True

    async def _rechecking(self) -> None:
        while not self.stopped.is_set():
            await asyncio.sleep(30)
            for tab in [t for t in list(self.tabs) if time.time() - t.checked > RECHECK]:
                await self._recheck(tab)

    async def serve(self, host: str = HOST, port: int = PORT):
        app = web.Application()
        app.router.add_get("/events", self.events)
        app.router.add_post("/events/sub", self.subscribe)
        # handler_cancellation: a closed event stream ends its handler at once (topics freed), not at the next write
        self.runner = web.AppRunner(app, access_log=None, handle_signals=False, handler_cancellation=True)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host, port)
        await self.site.start()
        self.tasks = [asyncio.create_task(self._rechecking())]
        return self.site

    async def stop(self) -> None:
        self.stopped.set()
        for tab in list(self.streams.values()):
            tab._put(None)  # end the streams (the runner waits for open requests)
        await self.runner.cleanup()
        for t in [*self.tasks, *self.lingering.values()]:
            t.cancel()
        self.lingering = {}
        for source in self.sources:
            try:
                await source.close()
            except Exception:  # noqa: BLE001 - the others still close
                log.exception("push source %s not closed", type(source).__name__)
        await self.http.aclose()

    @classmethod
    async def create(cls, nc) -> PushService:
        return cls(nc)

    async def start(self) -> None:
        await self.serve()
        log.info("push service on %s:%d", HOST, PORT)


main = PushService.main
