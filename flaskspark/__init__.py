"""
Initialization for the FlaskSpark package.
"""

from .app import FlaskSpark, db, migrate, login_manager

# Export key symbols for convenience.
__all__ = ["FlaskSpark", "db", "migrate", "login_manager"]
