"""
Configuration settings for FlaskSpark.
"""

import os

class Config:
    """
    Default configuration for FlaskSpark applications.
    """
    SECRET_KEY = os.environ.get("SECRET_KEY", "default_secret_key")
    SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False