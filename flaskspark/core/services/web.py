"""The web service: the web app (FlaskSpark) under gunicorn on WEB_PORT (behind the router).

The built-in web app (flaskspark.core.web.wsgi:app); the classic layout's own web/wsgi.py when the project has one.
Before gunicorn starts, the database is brought to the heads of the migrations (flaskspark.core.db.migrations).

One worker with threads (long requests, no worker timeout); several instances are possible once the web app keeps
no state of its own (state belongs into services).
"""

from __future__ import annotations

import logging
import os
import sys

from flaskspark.core import paths
from flaskspark.core.service import process_name


def main() -> None:
    from flaskspark.core.db import migrations

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    migrations.upgrade_on_start()
    port = os.environ.get("WEB_PORT", "8101")
    host = os.environ.get("WEB_HOST", "127.0.0.1")
    threads = os.environ.get("WEB_THREADS", "24")
    gunicorn = os.path.join(os.path.dirname(sys.executable), "gunicorn")
    if paths.classic_web():
        where, target = paths.WEB_DIR, "wsgi:app"
    else:
        where, target = paths.PROJECT_DIR, "flaskspark.core.web.wsgi:app"
    args = [gunicorn, "--chdir", str(where), "--workers", "1", "--threads", threads, "--timeout", "0", "--name", process_name("web"),
            "-b", f"{host}:{port}", "--access-logfile", "-", "--forwarded-allow-ips", "127.0.0.1", target]
    os.execv(gunicorn, args)
