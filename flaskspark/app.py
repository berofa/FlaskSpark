"""
Flask application factory class with configurable login providers.
"""

from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from importlib import import_module
import pkgutil

# Global extensions
db = SQLAlchemy()
migrate = Migrate()

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
        # Load environment variables from .env
        load_dotenv(dotenv_path=dotenv_path)
        
        self.app_module = app_module

        # Create the Flask app instance
        self.app = Flask(__name__)

        # Load configuration
        self.app.config.from_object("config.Config")
        if config:
            self.app.config.update(config)

        # Initialize global extensions
        db.init_app(self.app)
        migrate.init_app(self.app, db)

        # Configure login provider if provided
        self.login_provider = login_provider
        if self.login_provider:
            self.login_provider.app = self.app
            self.login_provider.configure()

        # Automatically register models and views
        self.register_application_models()
        self.register_application_views()

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
        module = import_module(package)
        for finder, name, is_pkg in pkgutil.iter_modules(module.__path__, package + "."):
            imported_modules[name] = import_module(name)
        return imported_modules

    def register_application_models(self):
        """
        Automatically imports and registers all models.
        """
        models_package = f"{self.app_module}.models"
        self._import_submodules(models_package)

    def register_application_views(self):
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
