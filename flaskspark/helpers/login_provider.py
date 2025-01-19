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
    def __init__(self, app: Flask):
        """
        Initializes the LoginProvider.

        Args:
            app (Flask): The Flask application instance.
        """
        self.app = app
        self.login_manager = LoginManager()  # Initialize LoginManager
        self.login_manager.init_app(app)  # Attach LoginManager to the Flask app

    @abstractmethod
    def configure(self):
        """
        Configures the login provider.

        This method should initialize and configure all necessary login functionality.
        """
        pass
