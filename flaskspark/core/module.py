"""Modules (README «Modular apps»): every theme of the application (e.g. calendar, mail, shop) is a module with a
manifest, a subclass of Module in <package>/module.py. The core reads the manifests of the installed modules
(flaskspark.core.modules) and learns from them what each module brings: its services, areas (access), entries in the
navigation, tables, NATS topics for the browser, routes in front of its services and what it adds to pages. Its web
part (views, templates, static files) lives in <package>/web and is registered with FlaskSpark; its migrations in
<package>/migrations/versions (flaskspark.core.db.migrations), its translations in <package>/locales.
"""

from __future__ import annotations

import re
from abc import ABC
from dataclasses import dataclass

#: Module.EXPOSURE: INTERNAL (the default) for a trusted network only; PUBLIC: may be part of an instance on the internet
INTERNAL, PUBLIC = "internal", "public"


def N_(text: str) -> str:
    """Marks a text of a manifest for translation (pybabel extracts it with the keyword N_, README «Translations»; the
    web app translates it when shown)."""
    return text


@dataclass(frozen=True)
class ServiceInfo:
    """A service of a module: a long-running process of its own (a systemd unit or a container later; in a single
    container the supervisor starts it). entry: "<module>:<function>" started without arguments."""

    name: str  # e.g. "sync" -> process "flaskspark-sync" (flaskspark.core.service.process_name)
    label: str
    entry: str  # e.g. "myapp.modules.notes.service:main"
    single: bool = False  # never more than one instance
    unit: str = ""  # its systemd unit, default "flaskspark-<name>.service" (flaskspark.core.service.unit_name): the
    # status falls back to systemd on this host while the service directory can't be read (NATS away)

    def __post_init__(self):
        if not self.unit:
            from .service import unit_name

            object.__setattr__(self, "unit", unit_name(self.name))


@dataclass(frozen=True)
class Route:
    """A path the router sends to a service instead of the web app (e.g. a WebSocket served by a service of its own). port_env: the
    environment variable with the service's port, default its default port."""

    prefix: str  # e.g. "/ws/devices"
    port_env: str
    default_port: int
    websocket: bool = False


@dataclass(frozen=True)
class Area:
    """An access area (with sign-in: role x area, flaskspark.core.web.access.RoleAccess). defaults: the names of the
    roles that get it until an admin changes it. start: the area's start page (default: its first navigation entry).
    parent: the key of the area this one is a page of (e.g. "warehouse.tracking" of "warehouse"): its own right, listed
    right below its area on «Settings › Access»; a new one starts with the rights its area has then."""

    key: str
    label: str
    description: str = ""
    defaults: frozenset[str] = frozenset()
    start: str = ""
    position: int = 100  # order of the areas (matrix, start page: the first one a visitor may use); equal ones in the
    # order of the modules; a page (parent) among the pages of its area
    parent: str = ""


@dataclass(frozen=True)
class NavItem:
    """An entry of the navigation in the group `group` (created after the existing ones if new). The group "" has no
    heading: its entries stand right below «Home», before every group.

    icon: the name of a Bootstrap Icon (e.g. "journal"), optional."""

    group: str
    label: str
    href: str
    area: str
    icon: str = ""
    position: int = 100  # order within the group
    badge: str | None = None  # [data-nav-badge] a script of the module fills


@dataclass(frozen=True)
class NavBadge:
    """A count a module shows on a menu entry of any module (by its href), for users with `area` only; the module's
    script (LAYOUT) fills [data-nav-badge="<badge>"] (e.g. the open tasks of a project on the entry «Projects»)."""

    href: str
    badge: str
    area: str


@dataclass(frozen=True)
class PushTopic:
    """A NATS topic the push service forwards to the browser for users with `area`; {uid} stands for the user's id."""

    pattern: str  # e.g. "notes.state"
    area: str
    latest: bool = False  # a state: its latest update goes to a tab that subscribes


@dataclass(frozen=True)
class Tile:
    """A tile of the module on the start page: a link with a short text."""

    label: str
    href: str
    area: str
    description: str = ""
    icon: str = ""
    position: int = 100


@dataclass(frozen=True)
class Section:
    """A template a module adds to a page (Module.PAGE_SECTIONS) at a position of its own, e.g. between two sections
    of another module. A plain template name has its module's POSITION; equal positions keep the order of the
    modules."""

    template: str
    position: int


def page_sections(manifests, page: str) -> list[str]:
    """The templates the modules add to `page` (Module.PAGE_SECTIONS), in the order of their positions (Section)."""
    entries = [(entry.position, entry.template) if isinstance(entry, Section) else (module.POSITION, entry)
               for module in manifests for entry in module.PAGE_SECTIONS.get(page, ())]
    return [template for _, template in sorted(entries, key=lambda entry: entry[0])]


@dataclass(frozen=True)
class Screen:
    """A page for an info screen (a display on the wall that nobody operates): /screen/<key>, without navigation, page
    chrome, buttons or context menus, filling the viewport (designed for 1920 x 1080). What it shows are the sections
    the modules add to the page "screen:<key>" (Module.PAGE_SECTIONS, in the order of the modules); any module may add
    to a screen another module declares. Visitors need `area` (each section asks for its own area too).

    mode: the colour mode of the screen ("light", "dark", "system"; "" follows the app: the browser's stored choice, else
    the theme's default); ?mode=… in the URL wins. reload_at: a local time ("04:00") at which the screen loads itself
    anew every day (new code after a deployment, a fresh start), "" never. show_title: the title beside the logo in the
    head row (False: only the logo; the title stays for screen readers)."""

    key: str  # letters, digits, "-" and "_" (the URL /screen/<key>)
    title: str
    area: str
    description: str = ""
    icon: str = ""  # a Bootstrap Icons name (the list of screens, /screen)
    mode: str = ""
    reload_at: str = "04:00"
    position: int = 100  # order in the list of screens
    show_title: bool = True

    def __post_init__(self):
        if not SCREEN_KEY.fullmatch(self.key or ""):
            raise ValueError(f"screen key {self.key!r}: letters, digits, '-' and '_' only")
        if self.mode not in SCREEN_MODES:
            raise ValueError(f"screen {self.key!r}: mode must be one of {SCREEN_MODES}")
        if self.reload_at and not RELOAD_AT.fullmatch(self.reload_at):
            raise ValueError(f"screen {self.key!r}: reload_at must be HH:MM or empty")

    @property
    def page(self) -> str:
        """The key of its sections in Module.PAGE_SECTIONS ("screen:<key>")."""
        return screen_page(self.key)


SCREEN_KEY = re.compile(r"[A-Za-z0-9_-]+")
SCREEN_MODES = ("", "light", "dark", "system")
RELOAD_AT = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


def screen_page(key: str) -> str:
    """The page of a screen's sections in Module.PAGE_SECTIONS: "screen:<key>"."""
    return f"screen:{key}"


class Module(ABC):
    """The manifest of a module. Subclasses set NAME (the name of its entry point in flaskspark.modules) and LABEL; the
    rest is optional.

    Labels are English source texts; the web app translates them (gettext, the app's catalogue).

    EXPOSURE: INTERNAL (default) or PUBLIC: whether the module may be part of an instance reachable from the internet
    (flaskspark.core.modules.internal() lists the enabled modules that are not PUBLIC; the core declares it only)."""

    NAME: str = ""
    LABEL: str = ""
    EXPOSURE: str = INTERNAL
    POSITION: int = 100  # order of the modules (navigation, tiles of equal position, areas of equal position); equal
    # ones by NAME. An explicit list in config.yaml `modules:` (or APP_MODULES) orders them instead.
    DEPENDS: tuple[str, ...] = ()  # modules it needs: without all of them it is not loaded (logged)
    OPTIONAL_DEPENDS: tuple[str, ...] = ()  # modules it uses when they are there: it asks
    # flaskspark.core.modules.is_enabled(cfg, name) before it does
    SERVICES: tuple[ServiceInfo, ...] = ()
    ROUTES: tuple[Route, ...] = ()
    AREAS: tuple[Area, ...] = ()
    NAVIGATION: tuple[NavItem, ...] = ()
    NAV_BADGES: tuple[NavBadge, ...] = ()  # its counts on menu entries of other modules
    TILES: tuple[Tile, ...] = ()
    PUSH_TOPICS: tuple[PushTopic, ...] = ()
    MODELS: tuple[str, ...] = ()  # its Python modules with tables (e.g. "myapp.modules.notes.models")
    TABLES: tuple[str, ...] = ()  # its own tables: its sessions reach only these and SHARED_TABLES
    SHARED_TABLES: tuple[str, ...] = ()
    ACCOUNT_TYPES: tuple[str, ...] = ()  # the account types it uses (flaskspark.core.accounts, e.g. ("imap", "smtp")):
    # the profile offers only types a loaded module names, and accounts.for_module(NAME) reads only these
    APP_ACCOUNT_TYPES: tuple[str, ...] = ()  # the account types it reads as accounts of the application (e.g.
    # ("gitlab",)): kept by the admins in «Settings» → «Accounts», read with accounts.for_module(NAME).app(type)
    SHAREABLES: tuple[str, ...] = ()  # "<python module>:<class>" of its flaskspark.core.shares.Shareable types
    ATTACHMENT_OWNERS: tuple[str, ...] = ()  # "<python module>:<class>" of its
    # flaskspark.core.attachments.AttachmentOwner types (items with files)
    CONFIG: tuple = ()  # its settings of config.yaml the admins change (flaskspark.core.settings.Setting)
    SETTINGS: tuple[str, ...] = ()  # templates of its own sections in its tab of «Settings» (admins; e.g.
    # "shop/settings.html"), above the generated form of CONFIG; each brings its own script
    PUBLIC_ENDPOINTS: tuple[str, ...] = ()  # endpoints reachable without a session once sign-in comes (e.g. agents)
    PAGE_SECTIONS: dict[str, tuple] = {}  # page -> templates it adds there (e.g. "home", "profile", "screen:<key>"
    # for a screen of any module); a Section(template, position) instead of a name places one elsewhere
    SCREENS: tuple[Screen, ...] = ()  # its pages for info screens (/screen/<key>, sections: PAGE_SECTIONS["screen:<key>"])
    LAYOUT: tuple[str, ...] = ()  # templates included in every page (dialogs, scripts of the navigation)
    CLI: str = ""  # "<module>:<click group or command>" added to the flask CLI
    PACKAGE: str = ""  # set by the loader: the module's package (e.g. "myapp.modules.notes")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.NAME or not cls.LABEL:
            raise TypeError(f"{cls.__name__}: NAME and LABEL are required")
        if cls.EXPOSURE not in (INTERNAL, PUBLIC):
            raise TypeError(f"{cls.__name__}: EXPOSURE must be {INTERNAL!r} or {PUBLIC!r}")

    def register(self) -> None:
        """Called once by flaskspark.core.modules.load(): import what registers the module's types in the core."""

    def template_filters(self) -> dict:
        """Jinja filters its templates need (name -> function)."""
        return {}

    def template_globals(self) -> dict:
        """Jinja globals its templates need (name -> value or function)."""
        return {}

    def nav_disabled(self) -> tuple[str, ...]:
        """Hrefs of menu entries (of any module) that can't be used right now, asked for every page (e.g. pages that
        need a device the visitor has not connected): shown greyed out and not clickable (aria-disabled). A script of
        the module (LAYOUT) may switch them live ([aria-disabled] and tabindex="-1" on the .app-nav-link)."""
        return ()

    def start_web(self, cfg) -> None:
        """Once in the web app's process (not in tests), e.g. its connections to other services."""

    def status_tiles(self) -> list:
        """Its tiles in the services' status (flaskspark.core.status.StatusTile), in the order shown. A service without
        a tile gets a plain one."""
        return []

    def guard_checks(self) -> list:
        """Its checks for the guardian (flaskspark.core.services.guardian.GuardCheck)."""
        return []

    def push_sources(self, nc) -> list:
        """Its topics the push service serves on demand (flaskspark.core.services.push.sources.TopicSource), on the
        push service's NATS connection `nc` (e.g. data a service only sends while someone leases it)."""
        return []

    def backup_paths(self, cfg) -> list:
        """Directories (or files) outside the state directory that belong into every backup (flaskspark.core.backup:
        the archive state-<stamp>.tar.gz, under extra/<absolute path>), e.g. files it keeps where config.yaml says."""
        return []

    def account_change_veto(self, change) -> str | None:
        """Before an account changes (flaskspark.core.accounts.AccountChange: connected, changed, removed, activated,
        deactivated, shared): a reason (an English source text, N_()) refuses the change, None lets it happen. E.g. an
        account a running job still needs may not be removed. Called in the transaction of the change; told after it
        is committed: accounts.listen()."""
        return None
