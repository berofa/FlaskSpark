"""
Flask application factory class with configurable login providers.
"""

from dotenv import load_dotenv
from flask import current_app, Flask, jsonify, request, send_from_directory, session, url_for
from flask_assets import Bundle, Environment
from flask_babel import Babel, gettext
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flaskspark.exceptions import DatabaseIncompleteError, DatabaseConnectionError
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import text
import importlib
import importlib.util
from jinja2 import TemplateNotFound
import logging
import os
import pkgutil
import sys
from typing import List
from webassets.filter import FilterError, get_filter

# Global extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

class FlaskSpark:
    """
    Configure and manage a Flask application with optional features.

    Attributes:
        app (Flask): The Flask application instance.
        app_module (str): Base module name for the application.
        app_base_dir (str): Absolute path to the application package.
        app_static_dir (str): Absolute path to the app's static directory.
        app_template_dir (str): Absolute path to the app's template directory.
        flaskspark_static_dir (str): Absolute path to FlaskSpark's static directory.
        flaskspark_template_dir (str): Absolute path to FlaskSpark's template directory.
        login_provider (AbstractLoginProvider | None): Configured login provider instance.
        module_packages (list[str]): Extra packages of the app's modules (see `modules`).
        static_dirs (list[str]): Static directories in lookup order: app, modules, FlaskSpark.
    """
    def __init__(self, app_module="app", config=None, login_provider=None, dotenv_path=".env", modules=None,
                 app_dir=None):
        """
        Initializes the Flask application.

        Args:
            app_module (str): The base module of the application (e.g., 'app').
            config (dict, optional): Custom configuration settings.
            login_provider (LoginProvider, optional): The login provider name or instance.
            dotenv_path (str, optional): Path to the .env file.
            app_dir (str, optional): The directory of the application package (its templates/ and static/);
                default: `app_module` in the working directory. An installed package passes its own directory.
            modules (list[str], optional): Packages of self-contained app modules (e.g. 'modules.mail.web').
                Each one is set up like the app itself: its `views` and `models` subpackages are registered,
                its `templates` directory is searched after the app's, its `static` directory is served under
                /static after the app's.

        Returns:
            None

        Raises:
            ValueError: If SECRET_KEY is missing.
            DatabaseIncompleteError: If the database is missing required tables.
            DatabaseConnectionError: If the database cannot be reached.
            ImportError: If the login provider cannot be loaded.
        """
        # Configure logging
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
        logger = logging.getLogger(__name__)
        
        # Load environment variables from .env
        load_dotenv(dotenv_path=dotenv_path)

        def initialization_logic():
            """
            Initializes the Flask application and handles initialization errors.

            Args:
                None

            Returns:
                None
            """
            self.app_module = app_module
            self.app_base_dir = os.path.abspath(app_dir or os.path.join(os.getcwd(), self.app_module))
            self.app_static_dir = os.path.join(self.app_base_dir, "static")
            self.app_template_dir = os.path.join(self.app_base_dir, "templates")
            self.flaskspark_static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
            self.flaskspark_template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))
            self.module_packages = list(modules or [])
            module_dirs = [self._package_dir(name) for name in self.module_packages]
            self.static_dirs = [self.app_static_dir,
                                *(d for d in (os.path.join(m, "static") for m in module_dirs) if os.path.isdir(d)),
                                self.flaskspark_static_dir]

            # Create the Flask app instance
            self.app = Flask(
                self.app_module,
                template_folder=self.app_template_dir,
                # Leave static_folder unset to avoid Flask's built-in static endpoint.
                # We register a custom /static route with fallback to FlaskSpark assets.
                static_folder=None,
            )
            # Assign static folder path for extensions (e.g. Flask-Assets) without
            # registering the default static endpoint.
            self.app.static_folder = self.app_static_dir
            self.app.static_url_path = "/static"
            
            # Add the templates of the modules, then the FlaskSpark templates
            for module_dir in module_dirs:
                if os.path.isdir(os.path.join(module_dir, "templates")):
                    self.app.jinja_loader.searchpath.append(os.path.join(module_dir, "templates"))
            self.app.jinja_loader.searchpath.append(self.flaskspark_template_dir)

            # Override the default static endpoint
            @self.app.route('/static/<path:filename>', endpoint='static')
            def serve_static(filename):
                """
                Serve static files from multiple directories.

                This function overrides the default static endpoint to look for the
                requested static file in the application's static directory, then in
                the static directories of the modules, then in FlaskSpark's.

                Args:
                    filename (str): The relative path to the requested static file.

                Returns:
                    Response: The static file if found, served using Flask's
                    `send_from_directory`. Returns a 404 response if the file is not found
                    in either directory.

                Note:
                    - The application's static directory is prioritized.
                    - The FlaskSpark static directory acts as a fallback.
                    - This custom route allows `url_for('static', filename=...)` to
                    function seamlessly.
                """
                for directory in self.static_dirs:
                    if os.path.exists(os.path.join(directory, filename)):
                        return send_from_directory(directory, filename)

                return "Static file not found", 404

            # Load configuration
            # Built now: variables loaded after FlaskSpark's import (the .env above, env files) count.
            from flaskspark.config import from_environment

            self.app.config.from_object(from_environment())
            if config:
                self.app.config.update(config)

            # Initialize i18n (Babel)
            self._init_babel()

            # Initialize assets (CSS/JS bundles)
            self._init_assets()

            # Check if SECRET_KEY is set, either in .env or config
            if not self.app.config.get("SECRET_KEY"):
                raise ValueError("SECRET_KEY is not set in the .env file.")

            # Initialize global extensions
            db.init_app(self.app)
            #self.migrate = Migrate(self.app, db)
            migrate.init_app(self.app, db)

            # Dynamically import and instantiate the login provider if provided
            self.login_provider = None
            if login_provider:
                self.login_provider = self._load_login_provider(login_provider)

                # If login provider requires a user table, import and register User model
                if getattr(self.login_provider, "requires_user_model", False):
                    from flaskspark.models.user import User
                    User.configure_fields(self.login_provider.__class__.__name__)

                # Configure the login provider after initialization.
                if hasattr(self.login_provider, "configure"):
                    self.login_provider.configure()

            # Automatically register models and views
            self._register_flaskspark_models()
            self._register_application_models()
            self._register_application_views()

            # Check if a database is required and perform integrity check
            if self._is_database_required():
                if not (len(sys.argv) > 1 and sys.argv[1] in ["db", "migrate", "upgrade", "downgrade"]):
                    self._check_database()

            # Register user layout context processor
            self._register_user_layout()

            # Opt-in web components with Bootstrap 6 (VENDOR_INCLUDE_WEBCOMPONENTS)
            self._register_webcomponents()

            # The Jinja filter «markdown» (flaskspark.markdown)
            self._register_markdown()

            # Return errors as JSON to clients that requested JSON
            self._register_error_handlers()

        # Handle errors during initialization
        self._handle_errors(initialization_logic)

    def __getattr__(self, name):
        """
        Enables access to Flask app attributes directly from FlaskSpark.

        Args:
            name (str): Attribute name.

        Returns:
            Any: The corresponding attribute from the Flask app.
        """
        return getattr(self.app, name)

    @staticmethod
    def _package_dir(package):
        """
        Directory of an importable package.

        Args:
            package (str): Dotted package name (e.g., 'modules.mail.web').

        Returns:
            str: Absolute path of the package directory.

        Raises:
            ModuleNotFoundError: If the package does not exist or is a plain module.
        """
        spec = importlib.util.find_spec(package)
        if spec is None or not spec.submodule_search_locations:
            raise ModuleNotFoundError(f"FlaskSpark module package '{package}' not found")
        return os.path.abspath(list(spec.submodule_search_locations)[0])

    def _module_subpackages(self, name):
        """
        The subpackage `name` (e.g. 'views') of every module package that has one.

        Args:
            name (str): Name of the subpackage.

        Returns:
            list[str]: Dotted names of the existing subpackages.
        """
        return [f"{package}.{name}" for package in self.module_packages
                if importlib.util.find_spec(f"{package}.{name}") is not None]

    def _import_submodules(self, package):
        """
        Dynamically imports all submodules in a given package (recursively).

        With STRICT_IMPORTS a submodule that fails to import stops the start instead of
        being skipped with a warning (a view would otherwise be missing silently).
        
        Args:
            package (str): The package path to import from (e.g., 'app.models').
        
        Returns:
            dict: A dictionary of imported modules.

        Raises:
            ModuleNotFoundError: If the base package does not exist.
        """
        imported_modules = {}

        try:
            if importlib.util.find_spec(package) is None:  # the package has no such part (e.g. no models)
                return imported_modules
        except ModuleNotFoundError:
            pass
        try:
            module = importlib.import_module(package)
        except ModuleNotFoundError as e:
            logging.warning(f"[FlaskSpark] Could not import base package '{package}': {e}")
            return imported_modules

        if not hasattr(module, "__path__"):
            # It's a plain module, not a package – nothing to import
            return imported_modules

        for finder, name, is_pkg in pkgutil.walk_packages(module.__path__, package + "."):
            try:
                imported_module = importlib.import_module(name)
                imported_modules[name] = imported_module
            except Exception as e:
                if self.app.config.get("STRICT_IMPORTS"):
                    raise
                logging.warning(f"[FlaskSpark] Failed to import submodule '{name}': {e}")

        return imported_modules

    def _load_login_provider(self, login_provider_name):
        """
        Dynamically imports, initializes, and returns the specified LoginProvider.

        Args:
            login_provider_name (str): The name of the LoginProvider class.

        Returns:
            object: An instance of the LoginProvider.

        Raises:
            ImportError: If the LoginProvider class cannot be found.
        """
        module_name = f"login_provider_{login_provider_name.lower()}"
        class_name = f"{login_provider_name}LoginProvider"
        candidate_modules = [
            f"{self.app_module}.helpers.{module_name}",
            f"flaskspark.helpers.{module_name}",
        ]
        last_error = None

        for module_path in candidate_modules:
            try:
                module = importlib.import_module(module_path)
                login_provider_class = getattr(module, class_name)
                return login_provider_class(self.app)
            except (ImportError, AttributeError) as exc:
                last_error = exc

        if login_provider_name.lower() == "default":
            raise ImportError(
                "FlaskSpark has no built-in login provider 'Default' (it was a stub and is gone since 1.0). "
                "Use 'OAuth' or a provider of the app "
                f"({self.app_module}.helpers.{module_name}, class {class_name})."
            ) from last_error
        raise ImportError(
            f"Could not load LoginProvider '{login_provider_name}'. "
            f"Tried modules: {', '.join(candidate_modules)}. "
            f"Expected class name: '{class_name}'."
        ) from last_error

    def _register_flaskspark_models(self):
        """
        Automatically imports and registers all models defined in FlaskSpark excluding the User model.

        Args:
            None

        Returns:
            None
        """
        models_package = "flaskspark.models"
        for _, module_name, _ in pkgutil.iter_modules([os.path.join(os.path.dirname(__file__), "models")]):
            if module_name != "user":
                if module_name == "role" and not (
                    self.login_provider
                    and getattr(self.login_provider, "requires_role_model", False)
                ):
                    continue
                importlib.import_module(f"{models_package}.{module_name}")

    def _register_application_models(self):
        """
        Automatically imports and registers all models.

        Args:
            None

        Returns:
            None
        """
        for package in [f"{self.app_module}.models", *self._module_subpackages("models")]:
            self._import_submodules(package)

    def _register_application_views(self):
        """
        Automatically imports and registers all views.

        Args:
            None

        Raises:
            ValueError: If a view requires login but no login provider is configured.

        Returns:
            None
        """
        views = {}
        for package in [f"{self.app_module}.views", *self._module_subpackages("views")]:
            views.update(self._import_submodules(package))
        found = []
        for module_name, module in views.items():
            # Register views dynamically
            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                # Only classes defined in this module: an imported base class (FlaskSparkMethodView) or a view
                # imported from elsewhere would otherwise get a route of its own (/<module_name>).
                if isinstance(attribute, type) and hasattr(attribute, "as_view") and attribute.__module__ == module.__name__:
                    # If the class is a view, register it
                    endpoint = getattr(attribute, "endpoint", module_name)
                    url = getattr(attribute, "url", f"/{module_name}")
                    require_login = getattr(attribute, "require_login", False)

                    if require_login and not self.login_provider:
                        raise ValueError(f"Login is required for view {endpoint}, but no login provider is configured.")

                    found.append((url, endpoint, attribute))
        # A view with `fallback = True` (e.g. a default start page) gives way to any other view on the same URL.
        claimed = {url for url, _endpoint, view in found if not getattr(view, "fallback", False)}
        for url, endpoint, view in found:
            if getattr(view, "fallback", False) and url in claimed:
                continue
            self.app.add_url_rule(url, view_func=view.as_view(endpoint))

    def _register_error_handlers(self):
        """
        Registers error handlers that answer JSON clients with a JSON error body.

        HTML clients keep Flask's default error pages.

        Args:
            None

        Returns:
            None
        """
        from werkzeug.exceptions import HTTPException, InternalServerError
        from flaskspark.helpers.content_negotiation import wants_json

        def json_error(error):
            if not wants_json():
                return error
            return jsonify({"error": error.name, "message": error.description, "status": error.code}), error.code

        self.app.register_error_handler(HTTPException, json_error)
        # Unhandled exceptions arrive as InternalServerError (500).
        self.app.register_error_handler(InternalServerError, json_error)

    def _is_database_required(self):
        """
        Checks if a database is required based on the application setup.

        Args:
            None

        Returns:
            bool: True if a database is required, False otherwise.
        """
        with self.app.app_context():
            # Check if any login provider is registered
            if self.login_provider:
                return True

            # Check if there are any defined database models
            registered_tables = db.metadata.tables.keys()
            if registered_tables:
                return True

        # No database is required
        return False

    def _check_database(self):
        """
        Checks if all database models are present in the database.

        Args:
            None

        Raises:
            DatabaseIncompleteError: If registered tables are missing.
            DatabaseConnectionError: If the database cannot be reached.

        Returns:
            None
        """
        with self.app.app_context():
            try:
                # Attempt to connect to the database
                db.session.execute(text("SELECT 1"))

                # Retrieve all registered tables
                registered_tables = db.metadata.tables.keys()

                # Retrieve all existing tables in the database
                inspector = inspect(db.engine)
                existing_tables = inspector.get_table_names()

                # Find missing tables
                missing_tables = set(registered_tables) - set(existing_tables)
                if missing_tables:
                    raise DatabaseIncompleteError(list(missing_tables))

            except OperationalError:
                raise DatabaseConnectionError()

    def _register_webcomponents(self):
        """
        Opt-in web components with Bootstrap 6 (``VENDOR_INCLUDE_WEBCOMPONENTS``).

        The web components are part of FlaskSpark (package ``webcomponents``). When enabled, FlaskSpark registers their
        blueprint (``/webcomponents/…``, versioned URLs cached for a year) and ``layouts/framework.html`` loads the
        Bootstrap 6 CSS for the page and the ``bootstrap`` module of the components. Templates get
        ``vendor_include_webcomponents`` and ``webcomponents_url(filename)``. An app must not register the blueprint
        itself any more.

        """
        enabled = bool(self.app.config.get("VENDOR_INCLUDE_WEBCOMPONENTS", False))
        if enabled and "webcomponents" not in self.app.blueprints:
            from webcomponents import create_blueprint

            self.app.register_blueprint(create_blueprint())

        def webcomponents_url(filename):
            return url_for("webcomponents.static", filename=filename)

        @self.app.context_processor
        def inject_webcomponents():
            return {"vendor_include_webcomponents": enabled, "webcomponents_url": webcomponents_url}

    def _register_markdown(self):
        """
        The Jinja filter ``markdown``: Markdown as sanitised HTML (``flaskspark.markdown.render``), e.g.
        ``{{ text|markdown }}`` or ``{{ text|markdown(base_url=project_url) }}``.
        """
        from flaskspark import markdown

        self.app.jinja_env.filters.setdefault("markdown", markdown.template_filter)

    def _register_user_layout(self):
        """
        Registers a context processor to inject the user's chosen layout into templates.

        Args:
            None

        Returns:
            None
        """
        @self.app.context_processor
        def inject_user_layout():
            """
            Injects the user's chosen layout into all templates.

            Uses APP_LAYOUT_TEMPLATE if a template folder (the app's, a module's or
            FlaskSpark's) has it, otherwise 'layouts/framework.html'.

            Args:
                None

            Returns:
                dict: Layout mapping for template context.
            """
            # Any template folder counts (the app's, the modules', FlaskSpark's): ask the Jinja loader.
            user_layout = self.app.config.get("APP_LAYOUT_TEMPLATE", "layouts/framework.html")
            try:
                self.app.jinja_env.loader.get_source(self.app.jinja_env, user_layout)
            except TemplateNotFound:
                logging.getLogger(__name__).warning("Layout %r not found, using layouts/framework.html", user_layout)
                user_layout = "layouts/framework.html"

            return {'layout': user_layout}

    def _init_babel(self):
        """
        Initialize Flask-Babel with cookie + browser language selection.

        Args:
            None

        Returns:
            None
        """
        self.app.config.setdefault("BABEL_DEFAULT_LOCALE", "en")
        self.app.config.setdefault("BABEL_SUPPORTED_LOCALES", ["en"])
        self.app.config.setdefault("BABEL_TRANSLATION_DIRECTORIES", "locales")

        # Callables asked before the cookie (e.g. flaskspark.core: the signed-in user's language in the profile):
        # the first code of BABEL_SUPPORTED_LOCALES one returns wins.
        if not hasattr(self, "locale_preferences"):
            self.locale_preferences = []

        def select_locale():
            cookie_lang = request.cookies.get("lang")
            supported = self.app.config.get("BABEL_SUPPORTED_LOCALES", ["en"])
            for preference in self.locale_preferences:
                chosen = preference()
                if chosen in supported:
                    return chosen
            if cookie_lang in supported:
                return cookie_lang
            return request.accept_languages.best_match(supported) or self.app.config.get(
                "BABEL_DEFAULT_LOCALE", "en"
            )

        self.babel = Babel(self.app, locale_selector=select_locale)

        @self.app.context_processor
        def inject_html_lang():
            """The language of the page for <html lang> (layouts/framework.html)."""
            from flask_babel import get_locale

            locale = get_locale()
            return {"html_lang": locale.language if locale else self.app.config.get("BABEL_DEFAULT_LOCALE", "en")}
        self._register_i18n_endpoint()

    def _register_i18n_endpoint(self):
        """
        Register a JSON endpoint to translate message IDs for client-side usage.

        Query Parameters:
            keys (str): Comma-separated list of message IDs.

        Args:
            None

        Returns:
            JSON mapping of message IDs to localized strings.
        """
        @self.app.get("/_flaskspark/i18n", endpoint="flaskspark_i18n")
        def flaskspark_i18n():
            keys_param = request.args.get("keys", "")
            keys = [key.strip() for key in keys_param.split(",") if key.strip()]
            translations = {key: gettext(key) for key in keys}
            return jsonify(translations)

    def _init_assets(self):
        """
        Initialize Flask-Assets bundles for CSS and JS if enabled.

        Plain CSS, no preprocessor: the bundle "css" concatenates ``ASSETS_CSS_ENTRY`` (default ``css/app.css``, the
        app's own or FlaskSpark's) and minifies it with rcssmin in production; modern CSS (nesting, custom properties,
        ``light-dark()``, ``color-mix()``) goes to the browser as written.

        Notes:
            - `ASSETS_AUTO_BUILD` enables build-on-request (on-demand) behavior.
            - `ASSETS_BUILD_ON_START` forces a build at application startup.
            - `ASSETS_BUNDLES` can define additional bundles (type "css" or "js") beyond the defaults.

        Raises:
            ValueError: If a setting of the former SCSS pipeline or Bootstrap 5 is still set, or an extra bundle has
                the type "scss".

        Args:
            None

        Returns:
            None
        """
        self._reject_retired_asset_settings()
        enabled = self.app.config.get("ASSETS_ENABLE", True)
        if not enabled:
            return

        assets = Environment(self.app)
        # Ensure bundle source resolution works for both app-local assets and
        # FlaskSpark-provided vendored assets.
        assets.load_path = list(self.static_dirs)
        environment = (self.app.config.get("ENVIRONMENT") or "development").lower()
        if environment == "production":
            assets.auto_build = False
            assets.debug = False
            # The filter cache is keyed on the entry file's content; apps can turn it off via ASSETS_CACHE.
            assets.cache = self.app.config.get("ASSETS_CACHE", True)
            assets.manifest = "file"
            self.app.config.setdefault("ASSETS_BUILD_ON_START", True)
        else:
            assets.auto_build = True
            assets.debug = True
            assets.cache = False
            assets.manifest = False
            self.app.config.setdefault("ASSETS_BUILD_ON_START", False)
            self.app.config.setdefault("ASSETS_CSS_FILTERS", "")
            self.app.config.setdefault("ASSETS_JS_FILTERS", "")

        static_root = self.app.static_folder
        css_entry = self.app.config.get("ASSETS_CSS_ENTRY", "css/app.css")
        js_entry = self.app.config.get("ASSETS_JS_ENTRY", "js/app.js")
        css_output = self.app.config.get("ASSETS_CSS_OUTPUT", "styles/app.min.css")
        js_output = self.app.config.get("ASSETS_JS_OUTPUT", "scripts/app.min.js")
        css_filters = self.app.config.get("ASSETS_CSS_FILTERS", "rcssmin")
        js_filters = self.app.config.get("ASSETS_JS_FILTERS", "rjsmin")

        self._validate_asset_filters(css_filters)
        self._validate_asset_filters(js_filters)
        self._ensure_asset_output_dirs(static_root, [css_output, js_output])

        assets.register("css", Bundle(css_entry, filters=css_filters, output=css_output))
        assets.register("js", Bundle(js_entry, filters=js_filters, output=js_output))

        extra_bundles = self.app.config.get("ASSETS_BUNDLES", [])
        for bundle_config in extra_bundles:
            name = bundle_config.get("name")
            bundle_type = bundle_config.get("type", "js")
            entry = bundle_config.get("entry")
            output = bundle_config.get("output")
            filters = bundle_config.get("filters")

            if not name or not entry or not output:
                continue

            if bundle_type not in ("css", "js"):
                raise ValueError(
                    f"ASSETS_BUNDLES: bundle '{name}' has the type '{bundle_type}'; only 'css' and 'js' exist "
                    "(no SCSS any more: write plain CSS)."
                )
            if not filters:
                filters = css_filters if bundle_type == "css" else js_filters

            self._validate_asset_filters(filters)
            self._ensure_asset_output_dirs(static_root, [output])

            bundle = Bundle(
                entry,
                filters=filters,
                output=output,
            )
            assets.register(name, bundle)

        bundle_keys = list(getattr(assets, "_named_bundles", {}).keys())
        for key in bundle_keys:
            bundle = assets[key]
            original_build = bundle.build

            def _wrapped_build(*args, _bundle_key=key, _original=original_build, **kwargs):
                try:
                    result = _original(*args, **kwargs)
                    if self.app.debug:
                        logging.info("[FlaskSpark] Built asset bundle '%s'", _bundle_key)
                    return result
                except Exception as exc:
                    raise RuntimeError(
                        f"Asset build failed for bundle '{_bundle_key}': {exc.__class__.__name__}: {exc}"
                    ) from exc

            bundle.build = _wrapped_build

        if self.app.config.get("ASSETS_BUILD_ON_START", False):
            with self.app.app_context():
                for key in bundle_keys:
                    force = self.app.config.get("ASSETS_FORCE_BUILD", False) or self.app.debug
                    assets[key].build(force=force)

    # Settings of the former SCSS pipeline and of Bootstrap 5 (removed in 1.0.0) and what replaces them.
    RETIRED_ASSET_SETTINGS = {
        "ASSETS_SCSS_ENTRY": "ASSETS_CSS_ENTRY (a plain CSS file, default css/app.css)",
        "ASSETS_SCSS_OUTPUT": "ASSETS_CSS_OUTPUT",
        "ASSETS_SCSS_FILTERS": "ASSETS_CSS_FILTERS (default rcssmin)",
        "ASSETS_SCSS_INCLUDE_PATHS": "nothing (plain CSS has no imports to resolve at build time)",
        "LIBSASS_INCLUDES": "nothing (libsass is no longer used)",
        "VENDOR_INCLUDE_BOOTSTRAP": "VENDOR_INCLUDE_WEBCOMPONENTS (Bootstrap 6 and the web components)",
    }

    def _reject_retired_asset_settings(self) -> None:
        """
        Stop the start when a setting of the former SCSS pipeline or of Bootstrap 5 is still set (app config or
        environment), naming what replaces it, instead of silently building something else.

        Raises:
            ValueError: If a retired setting is set.
        """
        retired = [name for name in self.RETIRED_ASSET_SETTINGS
                   if self.app.config.get(name) not in (None, "", [], False) or os.environ.get(name)]
        if retired:
            hints = "; ".join(f"{name} -> {self.RETIRED_ASSET_SETTINGS[name]}" for name in retired)
            raise ValueError(f"FlaskSpark no longer builds SCSS and no longer ships Bootstrap 5. Replace: {hints}.")

    @staticmethod
    def _validate_asset_filters(filters: str) -> None:
        """
        Validate asset filters and raise a clear error if dependencies are missing.

        Args:
            filters (str): Comma-separated filter list.

        Returns:
            None

        Raises:
            RuntimeError: If a filter cannot be loaded.
        """
        for name in [item.strip() for item in filters.split(",") if item.strip()]:
            try:
                get_filter(name)
            except FilterError as exc:
                raise RuntimeError(
                    f"Asset filter '{name}' is not available. "
                    "Install the corresponding package (e.g. rcssmin, rjsmin)."
                ) from exc

    @staticmethod
    def _ensure_asset_output_dirs(static_root: str, outputs: List[str]) -> None:
        """
        Ensure directories exist for asset bundle outputs.

        Args:
            static_root (str): Root static directory.
            outputs (list[str]): Output paths relative to the static root.

        Returns:
            None
        """
        if not static_root:
            return
        for output in outputs:
            directory = os.path.join(static_root, os.path.dirname(output))
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

    @staticmethod
    def search_directory(filename, dir_type="template"):
        """
        Searches for a file first in the specified directory of the application
        and then in the corresponding directory of FlaskSpark.

        Args:
            filename (str): The relative path to the file (e.g., 'layouts/framework.html' or 'css/style.css').
            dir_type (str): The type of directory ('template' or 'static').

        Returns:
            str: Absolute path to the file if it is found.

        Raises:
            ValueError: If an invalid dir_type is provided.
            FileNotFoundError: If the file does not exist in either the application or FlaskSpark directories.
        """
        if dir_type == "template":
            app_dir = os.path.abspath(current_app.template_folder)  # Applikation
            flaskspark_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))  # FlaskSpark
        elif dir_type == "static":
            app_dir = os.path.abspath(current_app.static_folder)  # Applikation
            flaskspark_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))  # FlaskSpark
        else:
            raise ValueError(f"Invalid dir_type '{dir_type}'. Expected 'template' or 'static'.")

        # Check if the file exists in the application directory
        app_file_path = os.path.join(app_dir, filename)
        if os.path.exists(app_file_path):
            return app_file_path

        # Check if the file exists in the FlaskSpark directory
        flaskspark_file_path = os.path.join(flaskspark_dir, filename)
        if os.path.exists(flaskspark_file_path):
            return flaskspark_file_path

        raise FileNotFoundError(f"File '{filename}' not found in {dir_type} directories of application or FlaskSpark.")

    def _handle_errors(self, initialization_function):
        """
        Handles errors during FlaskSpark initialization.

        Args:
            initialization_function (callable): A function that contains the initialization logic.

        Raises:
            Any exception that is not explicitly handled.

        Returns:
            None
        """
        try:
            initialization_function()
        except DatabaseIncompleteError as e:
            self._print_error("Database Incomplete", str(e))
            exit(1)
        except DatabaseConnectionError as e:
            self._print_error("Database Connection Error", str(e))
            exit(1)
        except Exception as e:
            self._print_error("Unexpected Error", str(e))
            exit(1)

    def _print_error(self, title, message):
        """
        Prints a formatted error message to the console.

        Args:
            title (str): The title of the error.
            message (str): The detailed error message.

        Returns:
            None
        """
        print("\n" + "=" * 80)
        print(f"ERROR: {title}")
        print("=" * 80)
        print(message)
        print("=" * 80 + "\n" )
