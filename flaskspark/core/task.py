"""Tasks: a run once, without a process that stays (e.g. a systemd timer or a cron job starts it, like a backup). A
task does its work in run(cfg), returns what it did and ends; main() prints that as JSON and ends with exit code 0, or
logs the failure and ends with 1.

    class CleanupTask(Task):
        NAME = "cleanup"

        def run(self, cfg) -> dict:
            return {"removed": tidy(cfg)}

    main = CleanupTask.main        # the entry of a console script or ServiceInfo
"""

from __future__ import annotations

import json
import logging
import sys
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)


class Task(ABC):
    NAME: str = ""

    @abstractmethod
    def run(self, cfg) -> dict:
        """Do the work; returns what was done (printed as JSON). Raises on failure."""

    @classmethod
    def main(cls) -> None:
        from . import config
        from .service import configure_logging

        configure_logging()
        try:
            result = cls().run(config.load())
        except Exception:  # noqa: BLE001 - the exit code tells the timer
            log.exception("%s failed", cls.NAME or cls.__name__)
            sys.exit(1)
        print(json.dumps(result, indent=1, default=str))
