"""flaskspark.core: the core of a modular FlaskSpark application, and its runtime.

An application built on flaskspark.core is an installed package that delivers modules (entry points flaskspark.modules,
every installed one is loaded), optionally a theme (flaskspark.themes) and its config.yaml (its package, entry point
flaskspark.apps). FlaskSpark brings the rest: the web app, the command line (`flaskspark`), the services, the
migrations. The core knows no module and no theme: it reads their manifests (flaskspark.core.module.Module) and the
theme's description (flaskspark.core.theme.Theme). The classic layout (config.yaml, themes/ and web/ in the project,
modules in src/modules/) keeps working.

    discovery  what is installed: the application, its modules and themes (entry points)
    paths      where the application keeps its files (all overridable from the environment)
    config     config.yaml with the environment's secrets
    module(s)  the manifests of the modules and their loader
    theme      branding: name, logos, colours (tokens), icons
    db         the database API (sessions per module with their rights), migrations per module
    bus events NATS: connection of a service, events for the browser, requests between services
    service    base classes of the services (one process each)
    directory  the service directory: heartbeats of every instance over NATS (key-value bucket)
    systemd    sd_notify: READY and WATCHDOG
    leader     leadership of a service with several instances (NATS key-value)
    queue jobs the durable work queue (JetStream): workers (async), submit from synchronous code
    notify     notifications over channels (ntfy), queued or straight
    status     status tiles of the services (StatusTile, from the manifests); health: NATS and the queue
    backup     backups of the database and the state directory, with retention
    services/  the core's services: push (live data to the browser), router (one port in front of all),
               notifications and guardian (both optional, config.yaml)
    supervisor all services of the application in one process tree (a single container, development)
    web        the web base: layout, navigation from the manifests, access, theme; the built-in web app (web.wsgi)

The README of FlaskSpark («Modular apps») describes the structure.
"""

__version__ = "0.1.0"
