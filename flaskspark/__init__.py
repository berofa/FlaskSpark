"""
Initialization for the FlaskSpark package.
"""

from .app import FlaskSpark, db, migrate, login_manager

# Optional: Exportiere alle wichtigen Symbole
__all__ = ["FlaskSpark", "db", "migrate", "login_manager"]