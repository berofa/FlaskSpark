"""
Flask application factory class with configurable login providers.
"""

from dotenv import load_dotenv
from flask import current_app, Flask, send_from_directory, session
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

# Global extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

class FlaskSpark:
    """
    A class to configure and manage a Flask application with optional features.
    """
    def __init__(self, app_module="app", config=None, login_provider=None, dotenv_path=".env"):
        """
        Initializes the Flask application.

        Args:
            app_module (str): The base module of the application (e.g., 'app').
            config (dict, optional): Custom configuration settings.
            login_provider (LoginProvider, optional): An instance of a login provider.
            dotenv_path (str, optional): Path to the .env file.
        """
        # Configure logging
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
        logger = logging.getLogger(__name__)
        
        # Load environment variables from .env
        load_dotenv(dotenv_path=dotenv_path)

        def initialization_logic():
            """
            Initializes the Flask application and handles initialization errors.
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
                static_folder=None, # Leave this to 'None' as we deliver static files with serve_static() method.
            )
            
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

                # Import user module and configure fields based on the login provider
                from flaskspark.models.user import User
                User.configure_fields(self.login_provider.__class__.__name__)

            # Automatically register models and views
            self._register_flaskspark_models()
            self._register_application_models()
            self._register_application_views()

            # Check if a database is required and perform integrity check
            if self._is_database_required():
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
        Dynamically imports all submodules in a given package.

        Args:
            package (str): The package path to import from.

        Returns:
            dict: A dictionary of imported modules.
        """
        imported_modules = {}

        try:
            module = importlib.import_module(package)
        except ModuleNotFoundError:
            return
        
        for finder, name, is_pkg in pkgutil.iter_modules(module.__path__, package + "."):
            imported_modules[name] = importlib.import_module(name)
        
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
        try:
            # Convert the class name to the corresponding module name
            module_name = f"login_provider_{login_provider_name.lower()}"
            module_path = f"flaskspark.helpers.{module_name}"

            # Dynamically import the module
            module = importlib.import_module(module_path)

            # Construct the class name dynamically
            class_name = f"{login_provider_name}LoginProvider"

            # Retrieve the class dynamically
            login_provider_class = getattr(module, class_name)

            # Instantiate the class with the Flask app
            return login_provider_class(self.app)

        except (ImportError, AttributeError) as e:
            raise ImportError(
                f"Could not load LoginProvider '{login_provider_name}'. Ensure the module is named "
                f"'login_provider_{login_provider_name.lower()}' and the class is named '{login_provider_name}LoginProvider'."
            ) from e

    def _register_flaskspark_models(self):
        """
        Automatically imports and registers all models defined in FlaskSpark excluding the User model.
        """
        models_package = "flaskspark.models"
        for _, module_name, _ in pkgutil.iter_modules([os.path.join(os.path.dirname(__file__), "models")]):
            if module_name != "user":
                importlib.import_module(f"{models_package}.{module_name}")

    def _register_application_models(self):
        """
        Automatically imports and registers all models.
        """
        models_package = f"{self.app_module}.models"
        self._import_submodules(models_package)

    def _register_application_views(self):
        """
        Automatically imports and registers all views.
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

        Raises:
            RuntimeError: If the database is missing or incomplete.
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
        """
        @self.app.context_processor
        def inject_user_layout():
            """
            Injects the user's chosen layout into all templates.

            Checks if the layout specified in the session exists in the 
            'app/resources/templates/layouts' directory. If not found or 
            invalid, defaults to 'layouts/default.html'.
            """
            layouts_dir = os.path.join(self.app.root_path, 'templates', 'layouts')
            #user_layout = session.get('layout', 'layouts/default.html')
            user_layout = 'layouts/test.html'

            try:
                template_path = self.search_directory("layouts/test.html", dir_type="template")
                print(f"Template gefunden: {template_path}")
            except FileNotFoundError as e:
                print(e)
            
            # Validate the user-selected layout
            layout_path = os.path.join(layouts_dir, user_layout)
            if not os.path.isfile(layout_path):
                user_layout = 'layouts/default.html'

            return {'layout': user_layout}

    @staticmethod
    def search_directory(filename, dir_type="template"):
        """
        Searches for a file first in the specified directory of the application
        and then in the corresponding directory of FlaskSpark.

        Args:
            filename (str): The relative path to the file (e.g., 'views/main/get.html' or 'css/style.css').
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
        """
        print("\n" + "=" * 80)
        print(f"ERROR: {title}")
        print("=" * 80)
        print(message)
        print("=" * 80 + "\n" )