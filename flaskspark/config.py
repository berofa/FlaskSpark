"""
Default configuration for FlaskSpark applications.
"""

import os
from typing import List, Optional


def _split_csv(value: Optional[str]) -> List[str]:
    """
    Split a comma-separated string into a list.

    Args:
        value (str | None): Input string.

    Returns:
        list[str]: List of trimmed values.
    """
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_role_map(value: Optional[str]) -> dict:
    """
    Parse a role map string into a dict.

    Expected format: "group:Role,group2:Role2"

    Args:
        value (str | None): Map string.

    Returns:
        dict: Mapping of group name to role name.
    """
    mapping = {}
    if not value:
        return mapping
    for item in value.split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        group, role = item.split(":", 1)
        group = group.strip()
        role = role.strip()
        if group and role:
            mapping[group] = role
    return mapping

class Config:
    """
    Base FlaskSpark configuration.

    Environment variables are read at import time.

    Attributes:
        SECRET_KEY (str | None): Flask secret key.
        DEBUG (bool): Debug flag.
        FLASK_ENV (str): Flask environment.
        SQLALCHEMY_DATABASE_URI (str): Database connection URI.
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): SQLAlchemy modification tracking flag.
        OAUTH_* (str | None): OAuth/OIDC configuration values.
        ASSETS_*: Asset pipeline configuration values.
    """
    SECRET_KEY = os.environ.get("SECRET_KEY")
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
    FLASK_ENV = "production" if ENVIRONMENT.lower() == "production" else "development"
    DEBUG = ENVIRONMENT.lower() != "production"

    """Database configuration."""
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "SQLALCHEMY_DATABASE_URI",
        os.environ.get("DATABASE_URL", "sqlite:///app.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    """OAuth configuration."""
    OAUTH_NAME = os.environ.get("OAUTH_NAME")
    OAUTH_AUTHORIZE_URL = os.environ.get("OAUTH_AUTHORIZE_URL")
    OAUTH_ACCESS_TOKEN_URL = os.environ.get("OAUTH_ACCESS_TOKEN_URL")
    OAUTH_USERINFO_ENDPOINT = os.environ.get("OAUTH_USERINFO_ENDPOINT")
    OAUTH_JWKS_URI = os.environ.get("OAUTH_JWKS_URI")
    OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID")
    OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET")
    OAUTH_SCOPE = os.environ.get("OAUTH_SCOPE")
    OAUTH_GROUPS_CLAIM = os.environ.get("OAUTH_GROUPS_CLAIM", "groups")
    OAUTH_ROLE_PRIORITY = _split_csv(os.environ.get("OAUTH_ROLE_PRIORITY"))
    OAUTH_ROLE_MAP = _parse_role_map(os.environ.get("OAUTH_ROLE_MAP"))

    """Babel (i18n) configuration."""
    BABEL_DEFAULT_LOCALE = os.environ.get("BABEL_DEFAULT_LOCALE", "en")
    BABEL_SUPPORTED_LOCALES = _split_csv(os.environ.get("BABEL_SUPPORTED_LOCALES")) or ["en"]
    BABEL_TRANSLATION_DIRECTORIES = os.environ.get("BABEL_TRANSLATION_DIRECTORIES", "locales")

    """Asset pipeline configuration."""
    ASSETS_ENABLE = os.environ.get("ASSETS_ENABLE", "True").lower() == "true"
    ASSETS_AUTO_BUILD = os.environ.get("ASSETS_AUTO_BUILD", "True").lower() == "true"
    ASSETS_DEBUG = os.environ.get("ASSETS_DEBUG", "False").lower() == "true"
    ASSETS_BUILD_ON_START = os.environ.get("ASSETS_BUILD_ON_START", "False").lower() == "true"
    ASSETS_FORCE_BUILD = os.environ.get("ASSETS_FORCE_BUILD", "False").lower() == "true"
    ASSETS_SCSS_ENTRY = os.environ.get("ASSETS_SCSS_ENTRY", "scss/app.scss")
    ASSETS_JS_ENTRY = os.environ.get("ASSETS_JS_ENTRY", "js/app.js")
    ASSETS_SCSS_OUTPUT = os.environ.get("ASSETS_SCSS_OUTPUT", "styles/app.min.css")
    ASSETS_JS_OUTPUT = os.environ.get("ASSETS_JS_OUTPUT", "scripts/app.min.js")
    ASSETS_SCSS_FILTERS = os.environ.get("ASSETS_SCSS_FILTERS", "libsass,rcssmin")
    ASSETS_JS_FILTERS = os.environ.get("ASSETS_JS_FILTERS", "rjsmin")
    ASSETS_BUNDLES = []

    """Server configuration."""
    APP_HOST = os.environ.get("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.environ.get("APP_PORT", "5067"))
