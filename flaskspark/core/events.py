"""Events for the browser and requests between services, over NATS, from synchronous code (the web app).

    events.init("web")                         # once per process, its NATS user
    events.emit("notes", user_id=3, id=7)      # -> ev.user.3.notes
    events.emit("sync")                        # -> ev.all.sync
    events.publish("notes.state", {...})       # data on a subject of the module
    events.request("sync.rpc", {...})          # a request to a service and its answer (in the visitor's language)

The push service forwards the events to the tabs that subscribed (ev.user.<id>.* only to that user); the pages then
load the data through their usual API. Fire and forget: emit() and publish() never block or raise; without init()
(tests, CLI) or while NATS is away they do nothing, and the pages reload once their channel reconnects.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading

log = logging.getLogger(__name__)

_loop: asyncio.AbstractEventLoop | None = None
_nc = None
_user: str | None = None
_name: str | None = None


def init(user: str, name: str = "", **connect_options) -> None:
    """Connect this process as NATS user `user` in a background thread (retried until NATS answers). name: the
    connection's name on the NATS server, the process's service (default the user's: "flaskspark-<user>")."""
    global _loop, _user, _name
    if _loop is not None:
        return
    from flaskspark.core.service import process_name

    _user, _name = user, process_name(name or user)
    _loop = asyncio.new_event_loop()
    threading.Thread(target=_loop.run_forever, name=f"events-{user}", daemon=True).start()
    asyncio.run_coroutine_threadsafe(_connect(connect_options), _loop)


async def _connect(options: dict) -> None:
    global _nc
    from flaskspark.core import bus

    while _nc is None:
        try:
            _nc = await bus.connect(_user, name=_name, **options)
        except Exception as exc:  # noqa: BLE001 - NATS not there yet
            log.warning("events: NATS not reachable (%s), again in 5 s", exc)
            await asyncio.sleep(5)


def subject(topic: str, user_id: int | None = None) -> str:
    return f"ev.user.{int(user_id)}.{topic}" if user_id is not None else f"ev.all.{topic}"


def publish(subject: str, data: dict) -> None:
    """Data on a NATS subject. Never blocks, never raises."""
    if _loop is None:
        return
    raw = json.dumps(data, default=str).encode()

    async def send():
        if _nc is not None and _nc.is_connected:
            try:
                await _nc.publish(subject, raw)
            except Exception as exc:  # noqa: BLE001
                log.debug("publish %s: %s", subject, exc)
    try:
        _loop.call_soon_threadsafe(lambda: asyncio.ensure_future(send()))
    except RuntimeError:  # loop closed (process ending)
        pass


def call(fn) -> bool:
    """Run the coroutine function `fn(nc)` on this process's connection.
    Never blocks or raises; False without init() or while NATS is away (nothing runs then)."""
    if _loop is None or _nc is None or not _nc.is_connected:
        return False
    nc = _nc

    async def run():
        try:
            await fn(nc)
        except Exception as exc:  # noqa: BLE001
            log.debug("events call: %s", exc)
    try:
        _loop.call_soon_threadsafe(lambda: asyncio.ensure_future(run()))
    except RuntimeError:  # loop closed (process ending)
        return False
    return True


class RequestError(RuntimeError):
    """A request got no answer (no NATS connection, nobody listens, timeout)."""


def request(subject: str, data: dict, timeout: float = 10.0, headers: dict | None = None) -> dict:
    """A NATS request over this process's connection and its answer.
    Blocks up to timeout; raises RequestError without an answer. The current language goes along as the header
    Accept-Language (the visitor's in a request; flaskspark.core.i18n.request_headers), so a service answers in it
    (flaskspark.core.i18n.with_request_language); `headers` adds more (or names another language)."""
    from flaskspark.core import bus, i18n

    if _loop is None or _nc is None or not _nc.is_connected:
        raise RequestError("NATS not connected")
    sent = i18n.request_headers(headers)
    future = asyncio.run_coroutine_threadsafe(
        _nc.request(subject, bus.dumps(data), timeout=timeout, headers=sent or None), _loop)
    try:
        msg = future.result(timeout + 2)
    except Exception as exc:  # noqa: BLE001 - no responders, timeout
        raise RequestError(f"no answer on {subject}: {type(exc).__name__}") from exc
    return bus.loads(msg.data) or {}


def subscribe(subject: str, callback) -> callable:
    """Call `callback(data)` (decoded JSON) for every message on `subject`, in this process's NATS thread; returns a
    function that ends the subscription. Without a connection it does nothing (the returned function too)."""
    from flaskspark.core import bus

    if _loop is None or _nc is None or not _nc.is_connected:
        return lambda: None

    async def handler(msg):
        try:
            callback(bus.loads(msg.data))
        except Exception as exc:  # noqa: BLE001 - a callback must not end the subscription
            log.debug("subscriber of %s: %s", subject, exc)

    try:
        sub = asyncio.run_coroutine_threadsafe(_nc.subscribe(subject, cb=handler), _loop).result(5)
    except Exception as exc:  # noqa: BLE001
        log.debug("subscribe %s: %s", subject, exc)
        return lambda: None

    def unsubscribe():
        try:
            asyncio.run_coroutine_threadsafe(sub.unsubscribe(), _loop).result(5)
        except Exception:  # noqa: BLE001 - connection gone
            pass
    return unsubscribe


def connected() -> bool:
    """Is this process connected to NATS?"""
    return _nc is not None and _nc.is_connected


def emit(topic: str, user_id: int | None = None, **hints) -> None:
    """Tell the browsers that `topic` changed (for one user, or for all). Never blocks, never raises."""
    if _loop is None:
        return
    data = json.dumps(hints, default=str).encode()
    subj = subject(topic, user_id)

    async def publish():
        if _nc is not None and _nc.is_connected:
            try:
                await _nc.publish(subj, data)
            except Exception as exc:  # noqa: BLE001
                log.debug("events %s: %s", subj, exc)
    try:
        _loop.call_soon_threadsafe(lambda: asyncio.ensure_future(publish()))
    except RuntimeError:  # loop closed (process ending)
        pass


def emit_users(topic: str, user_ids, **hints) -> None:
    for uid in {u for u in user_ids if u is not None}:
        emit(topic, uid, **hints)
