"""The built-in WSGI entry of the web app (`<app> service web` serves it with gunicorn): the installed application's
web app (flaskspark.core.web.app.create) with the modules' start in the web process (Module.start_web, NATS).

    gunicorn flaskspark.core.web.wsgi:app
"""

from __future__ import annotations

from flaskspark.core.web.app import create, start_modules

flask_spark_instance, app = create()
start_modules()
