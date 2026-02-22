"""
Flask application factory class with configurable login providers.
"""

from dotenv import load_dotenv
from flask import current_app, Flask, jsonify, request, send_from_directory, session
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
    """
    def __init__(self, app_module="app", config=None, login_provider=None, dotenv_path=".env"):
        """
        Initializes the Flask application.

        Args:
            app_module (str): The base module of the application (e.g., 'app').
            config (dict, optional): Custom configuration settings.
            login_provider (LoginProvider, optional): The login provider name or instance.
            dotenv_path (str, optional): Path to the .env file.

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
            self.app_base_dir = os.path.abspath(os.path.join(os.getcwd(), self.app_module))
            self.app_static_dir = os.path.join(self.app_base_dir, "static")
            self.app_template_dir = os.path.join(self.app_base_dir, "templates")
            self.flaskspark_static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
            self.flaskspark_template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))

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
            
            # Add the FlaskSpark templates
            self.app.jinja_loader.searchpath.append(self.flaskspark_template_dir)

            # Override the default static endpoint
            @self.app.route('/static/<path:filename>', endpoint='static')
            def serve_static(filename):
                """
                Serve static files from multiple directories.

                This function overrides the default static endpoint to first look for
                the requested static file in the application's static directory. If the
                file is not found there, it falls back to the FlaskSpark static directory.

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
                app_static_file = os.path.join(self.app_static_dir, filename)
                if os.path.exists(app_static_file):
                    return send_from_directory(self.app_static_dir, filename)
                
                flaskspark_static_file = os.path.join(self.flaskspark_static_dir, filename)
                if os.path.exists(flaskspark_static_file):
                    return send_from_directory(self.flaskspark_static_dir, filename)
                
                return "Static file not found", 404

            # Load configuration
            self.app.config.from_object("flaskspark.config.Config")
            if config:
                self.app.config.update(config)

            # Initialize i18n (Babel)
            self._init_babel()

            # Initialize assets (SCSS/JS bundles)
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

    def _import_submodules(self, package):
        """
        Dynamically imports all submodules in a given package (recursively).
        
        Args:
            package (str): The package path to import from (e.g., 'app.models').
        
        Returns:
            dict: A dictionary of imported modules.

        Raises:
            ModuleNotFoundError: If the base package does not exist.
        """
        imported_modules = {}

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
        models_package = f"{self.app_module}.models"
        self._import_submodules(models_package)

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
        views_package = f"{self.app_module}.views"
        for module_name, module in self._import_submodules(views_package).items():
            # Register views dynamically
            for attribute_name in dir(module):
                attribute = getattr(module, attribute_name)
                if isinstance(attribute, type) and hasattr(attribute, "as_view"):
                    # If the class is a view, register it
                    endpoint = getattr(attribute, "endpoint", module_name)
                    url = getattr(attribute, "url", f"/{module_name}")
                    require_login = getattr(attribute, "require_login", False)

                    if require_login and not self.login_provider:
                        raise ValueError(f"Login is required for view {endpoint}, but no login provider is configured.")

                    self.app.add_url_rule(url, view_func=attribute.as_view(endpoint))

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

    # Get the layout from the session
    # @todo: Implement this functionality. Currently it is static...
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

            Checks if the layout specified in the session exists in the 
            'app/resources/templates/layouts' directory. If not found or 
            invalid, defaults to 'layouts/framework.html'.

            Args:
                None

            Returns:
                dict: Layout mapping for template context.
            """
            layouts_dir = os.path.join(self.app.root_path, 'templates', 'layouts')
            user_layout = self.app.config.get("APP_LAYOUT_TEMPLATE", "layouts/framework.html")

            try:
                self.search_directory(user_layout, dir_type="template")
            except FileNotFoundError as e:
                print(e)
            
            # Validate the user-selected layout.
            layout_path = os.path.join(layouts_dir, user_layout)
            if not os.path.isfile(layout_path):
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

        def select_locale():
            cookie_lang = request.cookies.get("lang")
            supported = self.app.config.get("BABEL_SUPPORTED_LOCALES", ["en"])
            if cookie_lang in supported:
                return cookie_lang
            return request.accept_languages.best_match(supported) or self.app.config.get(
                "BABEL_DEFAULT_LOCALE", "en"
            )

        self.babel = Babel(self.app, locale_selector=select_locale)
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
        Initialize Flask-Assets bundles for SCSS and JS if enabled.

        Notes:
            - `ASSETS_AUTO_BUILD` enables build-on-request (on-demand) behavior.
            - `ASSETS_BUILD_ON_START` forces a build at application startup.
            - `ASSETS_BUNDLES` can define additional bundles beyond the defaults.

        Args:
            None

        Returns:
            None
        """
        enabled = self.app.config.get("ASSETS_ENABLE", True)
        if not enabled:
            return

        assets = Environment(self.app)
        # Ensure bundle source resolution works for both app-local assets and
        # FlaskSpark-provided vendored assets.
        assets.load_path = [self.app_static_dir, self.flaskspark_static_dir]
        environment = (self.app.config.get("ENVIRONMENT") or "development").lower()
        if environment == "production":
            assets.auto_build = False
            assets.debug = False
            assets.cache = True
            assets.manifest = "file"
            self.app.config.setdefault("ASSETS_BUILD_ON_START", True)
        else:
            assets.auto_build = True
            assets.debug = True
            assets.cache = False
            assets.manifest = False
            self.app.config.setdefault("ASSETS_BUILD_ON_START", False)
            self.app.config.setdefault("ASSETS_SCSS_FILTERS", "libsass")
            self.app.config.setdefault("ASSETS_JS_FILTERS", "")

        static_root = self.app.static_folder
        scss_entry = self.app.config.get("ASSETS_SCSS_ENTRY", "scss/app.scss")
        js_entry = self.app.config.get("ASSETS_JS_ENTRY", "js/app.js")
        scss_output = self.app.config.get("ASSETS_SCSS_OUTPUT", "styles/app.min.css")
        js_output = self.app.config.get("ASSETS_JS_OUTPUT", "scripts/app.min.js")
        scss_filters = self.app.config.get("ASSETS_SCSS_FILTERS", "libsass,rcssmin")
        js_filters = self.app.config.get("ASSETS_JS_FILTERS", "rjsmin")

        self._validate_asset_filters(scss_filters)
        self._validate_asset_filters(js_filters)
        self._configure_scss_include_paths(scss_filters)
        self._ensure_asset_output_dirs(static_root, [scss_output, js_output])

        scss_sources = [scss_entry]
        js_sources = [js_entry]

        # If enabled, merge framework-provided Bootstrap sources into the
        # app bundles so outputs stay app-local (styles/app.min.css and
        # scripts/app.min.js) and follow the same minification pipeline.
        if self.app.config.get("VENDOR_INCLUDE_BOOTSTRAP", False):
            scss_sources = ["vendor/bootstrap/scss/bootstrap.scss", *scss_sources]
            js_sources = ["vendor/bootstrap/js/bootstrap.bundle.js", *js_sources]

        scss_bundle = Bundle(
            *scss_sources,
            filters=scss_filters,
            output=scss_output,
        )
        js_bundle = Bundle(
            *js_sources,
            filters=js_filters,
            output=js_output,
        )

        assets.register("scss", scss_bundle)
        assets.register("js", js_bundle)

        extra_bundles = self.app.config.get("ASSETS_BUNDLES", [])
        for bundle_config in extra_bundles:
            name = bundle_config.get("name")
            bundle_type = bundle_config.get("type", "js")
            entry = bundle_config.get("entry")
            output = bundle_config.get("output")
            filters = bundle_config.get("filters")

            if not name or not entry or not output:
                continue

            if not filters:
                filters = scss_filters if bundle_type == "scss" else js_filters

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
                    "Install the corresponding package (e.g. rcssmin, rjsmin, libsass)."
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

    def _configure_scss_include_paths(self, scss_filters: str) -> None:
        """
        Configure libsass include paths for shorter and more robust SCSS imports.

        Args:
            scss_filters (str): Comma-separated SCSS filter list.

        Returns:
            None
        """
        filter_names = [item.strip() for item in scss_filters.split(",") if item.strip()]
        if "libsass" not in filter_names:
            return

        include_paths: List[str] = []
        configured_paths = self.app.config.get("ASSETS_SCSS_INCLUDE_PATHS", [])
        if isinstance(configured_paths, str):
            configured_paths = [item.strip() for item in configured_paths.split(",") if item.strip()]

        for path in configured_paths:
            include_paths.append(self._resolve_asset_path(path))

        # Always include app vendor assets. Include FlaskSpark vendor assets so
        # imports like "bootstrap/scss/..." resolve without relative path hacks.
        include_paths.append(os.path.join(self.app_static_dir, "vendor"))
        include_paths.append(os.path.join(self.flaskspark_static_dir, "vendor"))

        existing = self.app.config.get("LIBSASS_INCLUDES", [])
        if isinstance(existing, str):
            existing = [item.strip() for item in existing.split(",") if item.strip()]

        merged = []
        for path in [*existing, *include_paths]:
            if path and path not in merged:
                merged.append(path)
        self.app.config["LIBSASS_INCLUDES"] = merged

    def _resolve_asset_path(self, path: str) -> str:
        """
        Resolve asset include path candidates to an absolute path.

        Resolution order:
            1. absolute path
            2. app base directory
            3. app static directory
            4. current working directory
        """
        if os.path.isabs(path):
            return path

        candidates = [
            os.path.join(self.app_base_dir, path),
            os.path.join(self.app_static_dir, path),
            os.path.join(os.getcwd(), path),
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return os.path.abspath(candidate)
        return os.path.abspath(candidates[0])

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
