"""The core's own manifest: its services and the routes in front of them."""

from __future__ import annotations

from .module import N_, Module, Route, ServiceInfo


class Core(Module):
    NAME = "core"
    LABEL = N_("Core")
    SERVICES = (
        ServiceInfo("web", N_("Web"), "flaskspark.core.services.web:main", single=True),
        ServiceInfo("push", N_("Live channel"), "flaskspark.core.services.push.service:main", single=True),
        # The one port in front of the others (APP_PORT); the supervisor starts it last.
        ServiceInfo("router", N_("Router"), "flaskspark.core.services.router.service:main"),
    )
    # The push service's event stream (Server-Sent Events) and its subscriptions.
    ROUTES = (Route("/events", "PUSH_PORT", 8102),)
    # Its tables (flaskspark.core.models): the admins' settings, the role x area matrix, the users' settings, the
    # accounts, shares and attachments. They come into the application's migrations with db.load_models()
    # (flaskspark.core.db.migrations).
    MODELS = ("flaskspark.core.models",)
    TABLES = ("core_settings", "core_role_area", "core_user_settings", "core_user_role", "core_module_chains",
              "core_accounts", "core_account_types", "core_shares", "core_share_members", "core_share_notices",
              "core_attachments")
    # An account as an item to share (flaskspark.core.accounts.sharing).
    SHAREABLES = ("flaskspark.core.accounts.sharing:AccountShareable",)
    # Services switched on in config.yaml (<section>: {enabled: true}); off by default.
    OPTIONAL_SERVICES = {
        "notifications": ServiceInfo("notifications", N_("Notifications"),
                                     "flaskspark.core.services.notifications.service:main"),
        "guardian": ServiceInfo("guardian", N_("Guardian"), "flaskspark.core.services.guardian.service:main", single=True),
    }

    def __init__(self, cfg=None):
        self.cfg = cfg
        self.SERVICES = (*type(self).SERVICES, *(s for section, s in self.OPTIONAL_SERVICES.items()
                                                 if enabled(cfg, section)))

    def status_tiles(self) -> list:
        from . import status

        out = [status.WebTile(), status.RouterTile(), status.NatsTile(), status.ModulesTile()]
        if enabled(self.cfg, "notifications"):
            out.append(status.NotificationsTile())
        if enabled(self.cfg, "guardian"):
            out.append(status.GuardianTile())
        if self.cfg is not None and self.cfg.get("backup") is not None:
            out.append(status.BackupTile())
        return out

    def guard_checks(self) -> list:
        from .services.guardian import checks

        out = [checks.NatsCheck(), checks.ServicesCheck()]
        if enabled(self.cfg, "notifications"):
            out.append(checks.NotifyQueueCheck())
        return out


def enabled(cfg, section: str) -> bool:
    """An optional part of the core is switched on (config.yaml <section>: {enabled: true})."""
    return bool(cfg is not None and (cfg.section(section) or {}).get("enabled", False))
