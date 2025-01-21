"""
Flask application factory class with configurable login providers.
"""

from dotenv import load_dotenv
from flask import Flask, session
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module
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
        # Load environment variables from .env
        load_dotenv(dotenv_path=dotenv_path)
        
        self.app_module = app_module

        # Create the Flask app instance
        self.app = Flask(__name__, template_folder="templates")

        # Add the FlaskSpark templates
        flaskspark_template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))
        self.app.jinja_loader.searchpath.append(flaskspark_template_dir)

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
            login_manager.init_app(self.app)
            self.login_provider = self.login_provider(self.app)
            self.login_provider.configure()

        # Automatically register models and views
        self._register_application_models()
        self._register_application_views()

        # Register user layout context processor
        self._register_user_layout()

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
            user_layout = session.get('layout', 'layouts/default.html')  # Default layout
            
            # Validate the user-selected layout
            layout_path = os.path.join(layouts_dir, user_layout)
            if not os.path.isfile(layout_path):
                user_layout = 'layouts/default.html'

            return {'layout': user_layout}