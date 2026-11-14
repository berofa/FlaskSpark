"""NATS connection of a service.

Credentials per service user (web, push, notify, ...): NATS_URL and NATS_<USER>_USER / NATS_<USER>_PASSWORD, from the
environment (filled from the env files by flaskspark.core.config) or NATS_ENV_FILE. Without credentials the connection is
anonymous (a single local node, e.g. in the container). NATS_URL may name several servers (a cluster:
"tls://nats1:4222,tls://nats2:4222"): the client connects to one and moves to another when it goes away. NATS_REPLICAS:
copies of JetStream streams and key-value buckets (1 on a single node). Messages are JSON (dumps/loads); subjects are
built in the module that owns them. Never logs a credential.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import nats
from nats.aio.client import Client

log = logging.getLogger(__name__)


class _TlsCloseNoise(logging.Filter):
    """Python's asyncio warns about every TLS connection nats-py closes ("returning true from eof_received() has no
    effect when using ssl"): harmless, but the short health probes would write it every few seconds."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "eof_received() has no effect when using ssl" not in record.getMessage()


logging.getLogger("asyncio").addFilter(_TlsCloseNoise())

#: the env file with NATS_* settings; None: NATS_ENV_FILE, read when it is needed (it may come from CONFIG_DIR/app.env)
ENV_FILE: Path | None = None


def env_file() -> Path:
    """The env file with NATS_* settings: ENV_FILE, else NATS_ENV_FILE (after the env files were loaded)."""
    if ENV_FILE is not None:
        return ENV_FILE
    from . import config

    try:
        config.load_env()
    except OSError:  # no config.yaml (a process outside an application): the environment as it is
        pass
    return Path(os.environ.get("NATS_ENV_FILE") or "/nonexistent").expanduser()


def _values() -> dict[str, str]:
    """NATS_* settings: the env file, the environment wins."""
    values: dict[str, str] = {}
    try:
        for line in env_file().read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
    values.update({k: v for k, v in os.environ.items() if k.startswith("NATS_")})
    return values


def replicas() -> int:
    """Copies of a new JetStream stream or key-value bucket (NATS_REPLICAS; 1 without)."""
    try:
        return max(1, int(_values().get("NATS_REPLICAS") or 1))
    except ValueError:
        return 1


def monitors(default: str | None = None) -> list[str]:
    """Monitoring endpoints of the NATS servers (NATS_MONITOR, comma separated), else [default]."""
    urls = [u.strip() for u in (_values().get("NATS_MONITOR") or "").split(",") if u.strip()]
    return urls or ([default] if default else [])


def credentials(user: str) -> dict:
    """{servers, user, password} of a service user; the environment wins over the env file."""
    values = _values()
    key = user.upper()
    out = {"servers": [s.strip() for s in (values.get("NATS_URL") or f"nats://127.0.0.1:{os.environ.get('NATS_PORT') or 4222}").split(",")]}
    if values.get(f"NATS_{key}_USER"):
        out.update(user=values[f"NATS_{key}_USER"], password=values.get(f"NATS_{key}_PASSWORD", ""))
    return out


async def connect(user: str, name: str | None = None, **options) -> Client:
    """Connect as `user`; reconnects forever (a service outlives a NATS restart). Options go to
    nats.connect and win over these defaults (e.g. servers in tests, no reconnects for a short probe)."""
    creds = {**credentials(user), **options}

    async def disconnected():
        log.warning("nats: disconnected")

    async def reconnected():
        log.info("nats: reconnected")

    async def error(exc):
        if "APPLICATION_DATA_AFTER_CLOSE_NOTIFY" in str(exc):
            return  # the server's last bytes after closing a TLS connection: harmless
        log.warning("nats: %s", exc)

    # Replies come to inboxes of the user's own prefix: NATS lets each user read only its own (role nats).
    params = dict(name=name or user, max_reconnect_attempts=-1, reconnect_time_wait=1, inbox_prefix=f"_INBOX.{user}",
                  disconnected_cb=disconnected, reconnected_cb=reconnected, error_cb=error)
    return await nats.connect(**{**params, **creds})


async def probe(user: str, timeout: float = 3.0, **options) -> Client:
    """A short connection as `user` for one question (status, health): no reconnects, no log lines when it fails."""
    async def quiet(*_):
        pass

    params = dict(max_reconnect_attempts=0, allow_reconnect=False, connect_timeout=timeout, disconnected_cb=quiet,
                  reconnected_cb=quiet, error_cb=quiet)
    return await connect(user, **{**params, **options})


def dumps(obj) -> bytes:
    return json.dumps(obj, separators=(",", ":")).encode()


def loads(data: bytes):
    return json.loads(data) if data else None
