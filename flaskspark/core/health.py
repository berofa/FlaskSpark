"""Health of NATS and of the work queue, for the status tiles and the guardian. Synchronous (each opens a short
connection of its own), never raises: every answer is {ok, error, ...}.

- NATS: with NATS_MONITOR (the monitoring endpoints of the servers, comma separated, e.g. http://nats1:8222) every
  server's /healthz, /varz and /jsz: a cluster is ok while a majority of its servers is. Without: a short client
  connection (as the given NATS user) tells whether NATS answers, its version and whether JetStream is there.
- Work queue: how many jobs of a kind wait and since when (the oldest one).
"""

from __future__ import annotations

import asyncio

from . import bus


def _probe_name(user: str) -> str:
    """The name of a short health connection on the NATS server: "flaskspark-<user>-health"."""
    from .service import process_name

    return process_name(f"{user}-health")


def _node(monitor: str, timeout: float) -> dict:
    """One NATS server over its monitoring endpoint: {url, ok, name, error, version, connections, ...}."""
    import httpx

    out: dict = {"url": monitor, "ok": False, "name": monitor.split("//")[-1].split(":")[0]}
    try:
        with httpx.Client(timeout=timeout) as c:
            health = c.get(f"{monitor}/healthz")
            out["ok"] = health.status_code == 200
            if not out["ok"]:
                out["error"] = f"healthz {health.status_code}: {health.text[:200]}"
            v = c.get(f"{monitor}/varz").json()
            js = c.get(f"{monitor}/jsz").json()
        out.update(name=v.get("server_name") or out["name"], version=v.get("version"), connections=v.get("connections"),
                   in_msgs=v.get("in_msgs"), out_msgs=v.get("out_msgs"), slow_consumers=v.get("slow_consumers"),
                   jetstream=bool(js.get("config") or js.get("streams") is not None), js_storage=js.get("storage"),
                   js_streams=js.get("streams"))
    except Exception as exc:  # noqa: BLE001 - not reachable
        out["ok"] = False
        out["error"] = f"not reachable: {exc}"
    return out


def _from_monitors(monitors: list[str], timeout: float) -> dict:
    nodes = [_node(m, timeout) for m in monitors]
    up = [n for n in nodes if n["ok"]]
    out: dict = {"ok": len(up) * 2 > len(nodes), "nodes": nodes, "down": [n["name"] for n in nodes if not n["ok"]]}
    if not out["ok"]:
        out["error"] = "; ".join(f"{n['name']}: {n.get('error')}" for n in nodes if not n["ok"])
    first = next((n for n in nodes if n.get("version")), {})
    out.update(version=first.get("version"), jetstream=any(n.get("jetstream") for n in nodes),
               js_streams=max((n.get("js_streams") or 0 for n in nodes), default=0))
    for key in ("connections", "in_msgs", "out_msgs", "slow_consumers", "js_storage"):
        out[key] = sum(n.get(key) or 0 for n in nodes)
    return out


def _from_client(user: str, timeout: float, options: dict) -> dict:
    async def ask() -> dict:
        nc = await bus.probe(user, timeout=timeout, name=_probe_name(user), **options)
        try:
            info = getattr(nc, "_server_info", None) or {}
            name = info.get("server_name") or info.get("server_id") or ""
            out = {"ok": True, "version": nc.connected_server_version and str(nc.connected_server_version),
                   "nodes": [{"name": name, "ok": True}], "down": [], "jetstream": False}
            try:
                account = await nc.jetstream(timeout=timeout).account_info()
                out.update(jetstream=True, js_streams=account.streams, js_storage=account.storage)
            except Exception as exc:  # noqa: BLE001 - no JetStream (or no rights to ask)
                out["js_error"] = str(exc) or type(exc).__name__
            return out
        finally:
            await nc.close()

    try:
        return asyncio.run(asyncio.wait_for(ask(), 3 * timeout))
    except Exception as exc:  # noqa: BLE001 - NATS away, no rights, timeout
        return {"ok": False, "error": f"not reachable: {exc or type(exc).__name__}", "nodes": [], "down": []}


def nats_health(user: str = "web", timeout: float = 3.0, monitors: list[str] | None = None, **connect_options) -> dict:
    """{ok, error, version, jetstream, nodes, down, ...}: the monitoring endpoints when there are (NATS_MONITOR or
    `monitors`), else a client connection as `user`."""
    monitors = bus.monitors() if monitors is None else monitors
    if monitors:
        return _from_monitors(monitors, timeout)
    return _from_client(user, timeout, connect_options)


def queue_health(user: str, kind: str, timeout: float = 3.0, **connect_options) -> dict:
    """{ok, waiting, oldest (seconds the oldest waiting job of `kind` is queued, None without)}."""
    from . import queue

    async def ask() -> dict:
        nc = await bus.probe(user, timeout=timeout, name=_probe_name(user), **connect_options)
        try:
            return {"ok": True, **(await queue.waiting(nc, kind, timeout))}
        finally:
            await nc.close()

    try:
        return asyncio.run(asyncio.wait_for(ask(), 3 * timeout))
    except Exception as exc:  # noqa: BLE001 - NATS away, no JetStream, no rights, timeout
        return {"ok": False, "error": f"not reachable: {exc or type(exc).__name__}"}


def request(user: str, subject: str, timeout: float = 3.0, data: dict | None = None, **connect_options) -> dict:
    """One NATS request as `user` over a connection of its own (no reconnects), e.g. a status tile asking its service
    how it is (StatusContext.ask). Raises when nobody answers; never takes longer than twice `timeout` (a tile must not
    hang, e.g. without any NATS server)."""

    async def ask() -> dict:
        nc = await bus.probe(user, timeout=timeout, name=_probe_name(user), **connect_options)
        try:
            return bus.loads((await nc.request(subject, bus.dumps(data or {}), timeout=timeout)).data) or {}
        finally:
            await nc.close()

    return asyncio.run(asyncio.wait_for(ask(), 2 * timeout))
