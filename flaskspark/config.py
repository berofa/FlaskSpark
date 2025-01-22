"""
Default configuration for the application.
"""

import os

class Config:
    """
    Flask configuration
    """
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
    FLASK_ENV = os.environ.get("FLASK_ENV", "production")

    """
    Database
    """
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    """
    OAuth configuration
    """
    OAUTH_NAME = os.environ.get("OAUTH_NAME")
    OAUTH_AUTHORIZE_URL = os.environ.get("OAUTH_AUTHORIZE_URL")
    OAUTH_ACCESS_TOKEN_URL = os.environ.get("OAUTH_ACCESS_TOKEN_URL")
    OAUTH_USERINFO_ENDPOINT = os.environ.get("OAUTH_USERINFO_ENDPOINT")
    OAUTH_JWKS_URI = os.environ.get("OAUTH_JWKS_URI")
    OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID")
    OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET")
    OAUTH_SCOPE = os.environ.get("OAUTH_SCOPE")