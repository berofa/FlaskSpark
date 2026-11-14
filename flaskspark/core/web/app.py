"""The web app of an application built on flaskspark.core: FlaskSpark with the web parts of the modules, the theme,
the layout (navigation from the manifests), access and the webcomponents (Bootstrap 6).

    gunicorn flaskspark.core.web.wsgi:app                    # the built-in web app (`<app> service web` starts it)
    flask_spark, app = flaskspark.core.web.app.create("app") # the classic layout: in web/app/__init__.py

No SCSS and no asset build: the layout's CSS (flaskspark/css/frame.css), the theme (themes/<name>/theme.css) and the
modules' CSS and JS are plain files, served versioned (webcomponents.delivery) and preloaded.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from flask import abort, Blueprint, jsonify, redirect, render_template, request, send_from_directory, url_for
from flaskspark import FlaskSpark
from werkzeug.middleware.proxy_fix import ProxyFix

from flaskspark.core import config as _config, db, modules as _modules, paths, theme as _theme
from flaskspark.core import web
from flaskspark.core.web import access as _access

log = logging.getLogger(__name__)

#: the core's own catalogue (layout, settings, status, access; scripts/core-i18n updates it)
CORE_LOCALES = Path(__file__).resolve().parent.parent / "locales"


def translation_directories(directories: str, modules: list | None = None) -> str:
    """BABEL_TRANSLATION_DIRECTORIES: the core's catalogue first, then the modules' (<package>/locales, in their
    order), then the app's own (`directories`): Flask-Babel merges the directories in order and a later one overrides an
    earlier one, so a module's catalogue wins over the core's and the app's over all for every text it translates."""
    module_dirs = [str(d) for d in modules or ()]
    own = [d for d in directories.split(";") if d and Path(d) != CORE_LOCALES and d not in module_dirs]
    return ";".join([str(CORE_LOCALES), *module_dirs, *own])


def _theme_blueprint(theme) -> Blueprint:
    """The theme's files under /theme/ (theme.css, images/) and, when theme.yaml has the manifest's fields, the web app
    manifest at /theme/manifest.webmanifest."""
    blueprint = Blueprint("theme", __name__, url_prefix="/theme")

    def serve(filename: str):
        if filename.endswith((".yaml", ".py")):
            abort(404)
        return send_from_directory(theme.directory, filename)

    def manifest():
        if not isinstance(theme.manifest, dict):
            abort(404)
        images = url_for("theme.static", filename="images/x")[:-1]
        response = jsonify(_theme.manifest_data(theme, images))
        response.mimetype = "application/manifest+json"
        return response

    blueprint.add_url_rule("/manifest.webmanifest", endpoint="manifest", view_func=manifest)
    blueprint.add_url_rule("/<path:filename>", endpoint="static", view_func=serve)
    return blueprint


def _check_migrations(app, cfg) -> None:
    """Refuse to start on an outdated schema: `<app> db upgrade` (the web service and the supervisor run it at their
    start), in the classic layout `flask db upgrade` first."""
    if sys.argv[1:2] == ["db"] or os.environ.get("APP_SKIP_MIGRATION_CHECK"):
        return
    from flaskspark.core.db import migrations

    if not migrations.classic():
        found = migrations.state(cfg)
        problem = migrations._refusal(found) or (found.pending and f"{', '.join(found.pending)} not at the head")
        if problem:
            raise SystemExit(f"Database schema: {problem}. Run `{cfg.app_name} db upgrade`.")
        return
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory

    migrate = app.extensions["migrate"]
    with app.app_context(), db.session() as s:
        heads = set(ScriptDirectory.from_config(migrate.migrate.get_config(migrate.directory)).get_heads())
        current = set(MigrationContext.configure(s.connection()).get_current_heads())
    if current != heads:
        raise SystemExit(f"Database schema {sorted(current) or 'unversioned'} is not at {sorted(heads)}: "
                         "run `flask db upgrade` (in web/).")


def _check_tables() -> None:
    """Log the tables of the database API (core, modules) the database lacks: a migration is missing
    (flaskspark.core.db.migrations)."""
    if sys.argv[1:2] == ["db"] or os.environ.get("APP_SKIP_MIGRATION_CHECK"):
        return
    from flaskspark.core.db import migrations

    try:
        missing = migrations.missing()
    except Exception as exc:  # noqa: BLE001 - only a hint
        log.debug("tables not checked: %s", exc)
        return
    if missing:
        log.warning("Tables missing in the database: %s. A module's migration is missing (`<app> db revision "
                    "--module <name>`; the classic layout: `flask db migrate` in web/), README «Migrations».",
                    ", ".join(missing))


def _server_sessions(app) -> None:
    """Sessions on the server (Flask-Session, files in STATE_DIR/sessions): the browser only keeps the session id.
    Workflows keep secrets (passwords, keys) and longer state in the session, which must not travel in a cookie (a
    signed cookie is readable, and limited to 4 KB)."""
    from cachelib.file import FileSystemCache
    from flask_session import Session

    app.config.setdefault("SESSION_TYPE", "cachelib")
    app.config.setdefault("SESSION_CACHELIB", FileSystemCache(str(paths.state_dir("sessions")), threshold=5000,
                                                              default_timeout=0))
    app.config.setdefault("SESSION_PERMANENT", True)
    app.config.setdefault("PERMANENT_SESSION_LIFETIME", 7 * 24 * 3600)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    Session(app)


def _application(app_module: str | None) -> tuple[str, str | None, Path | None]:
    """The FlaskSpark application package: (its name, its directory or None for FlaskSpark's default, its catalogue).

    app_module given (the classic layout): web/<app_module>, the working directory is web/. Else the installed
    application's package (its templates/, static/, views/ and locales/ are the app's own), or none at all."""
    if app_module is not None:
        return app_module, None, paths.WEB_DIR / app_module / "locales"
    if paths.APP is not None and paths.APP_DIR is not None:
        return paths.APP.package, str(paths.APP_DIR), paths.APP_DIR / "locales"
    return "flaskspark_app", str(paths.PROJECT_DIR / "flaskspark_app"), None


def flask_settings(cfg) -> dict:
    """config.yaml `flask:`: Flask and FlaskSpark settings by their names (e.g. PERMANENT_SESSION_LIFETIME in seconds,
    ROLE_DEFAULTS as "Name:rank[:admin]" texts, a comma separated text or [name, admin, rank] lists)."""
    from flaskspark.config import _parse_role_defaults

    out = dict(cfg.section("flask"))
    roles = out.get("ROLE_DEFAULTS")
    if isinstance(roles, str):
        out["ROLE_DEFAULTS"] = _parse_role_defaults(roles)
    elif isinstance(roles, (list, tuple)):
        parsed = []
        for role in roles:
            parsed += [tuple(role)] if isinstance(role, (list, tuple)) else _parse_role_defaults(str(role))
        out["ROLE_DEFAULTS"] = parsed
    return out


def create(app_module: str | None = None, extra_config: dict | None = None, auth: str | None = None):
    """FlaskSpark and its Flask app: the built-in web app of the installed application (app_module None), or the
    classic layout's in web/<app_module> (the working directory is web/).

    auth: the access (flaskspark.core.web.access.ACCESS), default config.yaml `auth:` ("none"). config.yaml `flask:`
    sets Flask's and FlaskSpark's settings (flask_settings(); extra_config wins over it). FlaskSpark reads its settings
    from the environment after config.load() loaded the env files (CONFIG_DIR/app.env counts, e.g. ROLE_DEFAULTS)."""
    cfg = _config.load()
    app_module, app_dir, app_locales = _application(app_module)
    access_class = _access.access_class(auth or cfg.get("auth") or "none")
    theme = _theme.load(cfg)
    manifests = _modules.load(cfg)
    locales = cfg.section("app").get("locales") or ["en"]
    flask_config = {
        "VENDOR_INCLUDE_WEBCOMPONENTS": True,
        "ASSETS_ENABLE": False,  # plain CSS and ES modules, nothing to build
        "STRICT_IMPORTS": True,  # a view that fails to import stops the start instead of missing silently
        "SQLALCHEMY_DATABASE_URI": db.default_url(),
        "BABEL_DEFAULT_LOCALE": locales[0],
        "BABEL_SUPPORTED_LOCALES": locales,
        "BABEL_TRANSLATION_DIRECTORIES": str(app_locales or ""),
        "APP_LAYOUT_TEMPLATE": "layouts/main.html",
        **flask_settings(cfg),
        **(extra_config or {}),
    }
    flask_config["BABEL_TRANSLATION_DIRECTORIES"] = translation_directories(
        flask_config["BABEL_TRANSLATION_DIRECTORIES"], _modules.locale_dirs(cfg))
    flask_config.setdefault("APP_LOCALES_DIR", str(app_locales or ""))  # the app's own catalogue (scripts: "app")
    flask_spark = FlaskSpark(
        app_module=app_module,
        app_dir=app_dir,
        config=flask_config,
        dotenv_path=str(paths.PROJECT_DIR / (".env.none" if os.environ.get("APP_NO_DOTENV") else ".env")),
        modules=["flaskspark.core.web", *_modules.web_packages(cfg)],
        login_provider=access_class.LOGIN_PROVIDER,
    )
    app = flask_spark.app
    from . import language as _language

    # the signed-in user's language in the profile comes before the cookie and the browser's
    flask_spark.locale_preferences.append(lambda: _language.profile_language(locales))
    _server_sessions(app)
    # FlaskSpark logs at DEBUG; keep the HTTP clients quiet.
    for noisy in ("urllib3", "httpx", "httpcore", "werkzeug"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    # Behind the router (one hop): the visitor's address from X-Forwarded-For (apps may match clients by it).
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    _check_migrations(app, cfg)
    _check_tables()

    access = access_class()
    access.init_app(flask_spark, manifests)
    app.extensions[web.EXTENSION] = access
    web.use(access)

    from webcomponents import PACKAGE_ROOT as WEBCOMPONENTS_ROOT  # its blueprint: FlaskSpark (VENDOR_INCLUDE_WEBCOMPONENTS)
    from webcomponents.delivery import install_preload, version_static

    app.register_blueprint(_theme_blueprint(theme))
    static_dirs = flask_spark.static_dirs[:-1]  # the app's and the modules' (FlaskSpark's own are no ES modules)
    version_static(app, "static", static_dirs)
    install_preload(app, {f"{app.static_url_path}/": static_dirs, "/webcomponents/": WEBCOMPONENTS_ROOT})

    public = set(access.PUBLIC) | {e for m in manifests for e in m.PUBLIC_ENDPOINTS}

    @app.before_request
    def _check_access():
        """The access decides: a sign-in first (RoleAccess), then the area of the view. A page without the right
        shows «no access»; the start page goes to the first area the visitor may use instead."""
        if request.endpoint in public or request.endpoint is None:
            return None
        view_class = getattr(app.view_functions.get(request.endpoint), "view_class", None)
        response = access.check(request.endpoint, view_class, request.method)
        if response is not None:
            return response
        if view_class is None:
            return None
        if access.can(_access.area_of(view_class, request.method)):
            return None
        if _access.background():
            abort(403)
        if request.endpoint in web.start_endpoints():
            start = access.start_page()
            if start and start != request.path:
                return redirect(start)
        return render_template("flaskspark/no_access.html", denied=True), 403

    from flaskspark.core.markdown_labels import markdown_editor_labels

    # the texts of <ui-markdown-editor> in the page's language: labels='{{ markdown_editor_labels()|tojson }}'
    app.jinja_env.globals["markdown_editor_labels"] = markdown_editor_labels
    for module in manifests:
        app.jinja_env.filters.update(module.template_filters())
        app.jinja_env.globals.update(module.template_globals())
        if module.CLI:  # its commands in the flask CLI (e.g. imports)
            import importlib

            path, _, name = module.CLI.partition(":")
            app.cli.add_command(getattr(importlib.import_module(path), name))

    from .navigation import context

    @app.context_processor
    def _layout_context():
        return context(cfg, theme, manifests, locales)

    @app.get("/language/<code>", endpoint="set_language")
    def _set_language(code: str):
        """The visitor's language (cookie "lang"; "system": the browser's); a signed-in user's also in the profile
        (flaskspark.core.web.language)."""
        target = request.args.get("next") or "/"
        if not target.startswith("/") or target.startswith("//"):
            target = "/"
        response = redirect(target)
        if code in locales:
            response.set_cookie("lang", code, max_age=365 * 24 * 3600, samesite="Lax")
        else:
            response.delete_cookie("lang")
        try:
            _language.remember(code, locales)
        except Exception as exc:  # noqa: BLE001 - e.g. the table before the migration: the cookie still counts
            logging.getLogger(__name__).warning("language not kept in the profile: %s", exc)
        return response

    return flask_spark, app


def create_app():
    """The built-in web app as a Flask app factory, for the `flask` command line (the modules' Module.CLI commands):

        flask --app flaskspark.core.web.app:create_app <command>
    """
    return create()[1]


def start_modules() -> None:
    """What the modules need in the web process (Module.start_web; wsgi.py, not in tests)."""
    from flaskspark.core import events

    events.init("web")
    from flaskspark.core import directory

    directory.Beacon("web").start()  # the web app's heartbeats in the service directory
    cfg = _config.load()
    for module in _modules.load(cfg):
        module.start_web(cfg)


__all__ = ["CORE_LOCALES", "create", "create_app", "flask_settings", "start_modules", "translation_directories"]
