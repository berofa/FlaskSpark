"""
User model for FlaskSpark.
"""

from flaskspark import db

class User(db.Model):
    """
    User model representing a registered user.

    Attributes:
        id (int): Primary key.
        username (str): Unique username of the user.
        password (str): Encrypted password.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)