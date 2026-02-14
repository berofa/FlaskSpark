"""
Defines the abstract base class for Login Providers.
"""

from abc import ABC, abstractmethod
from flask_login import LoginManager
from flask import Flask

class AbstractLoginProvider(ABC):
    """
    Abstract base class for implementing a login provider.

    Attributes:
        app (Flask): The Flask application instance.
        login_manager (LoginManager): The Flask-Login manager instance.
    """
    requires_user_model = True
    requires_role_model = False

    def __init__(self, app: Flask):
        """
        Initializes the LoginProvider.

        Args:
            app (Flask): The Flask application instance.

        Returns:
            None
        """
        self.app = app
        self.login_manager = LoginManager()  # Initialize LoginManager
        self.login_manager.init_app(app)  # Attach LoginManager to the Flask app
        self.check_configuration(app.config)

    @abstractmethod
    def check_configuration(self, config):
        """
        Check the configuration of the login provider.

        Args:
            config (dict): The Flask application configuration.

        Returns:
            None

        Raises:
            ValueError: If the configuration is invalid.
        """
        pass

    @abstractmethod
    def configure(self):
        """
        Configures the login provider.

        This method should initialize and configure all necessary login functionality.

        Args:
            None

        Returns:
            None
        """
        pass
