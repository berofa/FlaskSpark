"""systemd notifications (sd_notify) without a library: READY=1 once a process works, WATCHDOG=1 as a sign of life.

A unit with Type=notify waits for READY=1; with WatchdogSec= systemd restarts a process that stops sending WATCHDOG=1
(e.g. one that hangs). Outside systemd (no NOTIFY_SOCKET: development, a container) nothing happens.

The supervisor (flaskspark.core.supervisor) talks to systemd for the whole process tree and keeps NOTIFY_SOCKET from
its children, so a service only notifies when systemd started it itself.
"""

from __future__ import annotations

import logging
import os
import socket

log = logging.getLogger(__name__)


def notify(state: str) -> bool:
    """Send `state` (e.g. "READY=1") to systemd; False outside systemd or when it fails. Never raises."""
    path = os.environ.get("NOTIFY_SOCKET")
    if not path:
        return False
    if path.startswith("@"):
        path = "\0" + path[1:]  # abstract socket
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect(path)
            sock.sendall(state.encode())
        return True
    except OSError as exc:
        log.warning("sd_notify %s failed: %s", state, exc)
        return False


def ready() -> bool:
    return notify("READY=1")


def alive() -> bool:
    return notify("WATCHDOG=1")


def stopping() -> bool:
    return notify("STOPPING=1")


def watchdog_interval() -> float | None:
    """Seconds between two WATCHDOG=1 (half of WatchdogSec, from WATCHDOG_USEC), None without a watchdog."""
    try:
        usec = int(os.environ.get("WATCHDOG_USEC") or 0)
    except ValueError:
        return None
    pid = os.environ.get("WATCHDOG_PID")
    if usec <= 0 or (pid and pid != str(os.getpid())):
        return None
    return usec / 2e6
