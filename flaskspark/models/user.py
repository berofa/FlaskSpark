"""
User model for FlaskSpark.
"""

from flask_login import UserMixin
from flaskspark import db

class User(db.Model, UserMixin):
    """
    Represents a user in the application.

    This class defines the database schema for users, including attributes such as
    username, email, first name, last name, admin status, and role assignment. It also
    provides utility methods for user-related operations, such as OAuth token verification.

    Attributes:
        id (int): The primary key for the user.
        username (str): The unique username of the user.
        email (str): The unique email address of the user.
        first_name (str, optional): The user's first name.
        last_name (str, optional): The user's last name.
        admin (bool): Indicates whether the user is an administrator (legacy flag).
        role_id (int | None): Foreign key to the roles table.
    """

    # Database schema for the User table
    id = db.Column(db.Integer, primary_key=True, unique=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=True)
    role = db.relationship("Role", backref="users")

    def __repr__(self):
        """
        Provides a string representation of the user object.

        Args:
            None

        Returns:
            str: A string containing the username of the user.
        """
        return f'<User {self.username}>'
    
    def __init__(self, username, email, role=None):
        """
        Initializes a new User instance.

        Args:
            username (str): The unique username of the user.
            email (str): The unique email address of the user.
            role (Role | None): Optional role assignment for the user.

        Returns:
            None
        """
        self.username = username
        self.email = email
        if role is not None:
            self.role = role

    @property
    def is_admin(self):
        """
        Check whether the user is an administrator.

        Args:
            None

        Returns:
            bool: True if the user has an admin role or admin flag.
        """
        return bool(getattr(self, "role", None) and self.role.is_admin) or bool(
            getattr(self, "admin", False)
        )

    @staticmethod
    def configure_fields(login_provider):
        """
        Dynamically configures fields based on the login provider.

        Args:
            login_provider (str): The name of the login provider (e.g., 'OAuth', 'Default').

        Returns:
            None
        """
        if login_provider == "Default":
            User.password = db.Column(db.String(255), nullable=False)
        elif login_provider == "OAuth":
            User.first_name = db.Column(db.String(255), nullable=True)
            User.last_name = db.Column(db.String(255), nullable=True)
            User.admin = db.Column(db.Boolean, default=False)

    @staticmethod
    def verify_oauth_token(token):
        """
        Verifies the structure of an OAuth token.

        This method checks if the token contains the required fields ('username' and 'email').
        If valid, the token is returned. If invalid, an error is logged, and None is returned.

        Args:
            token (dict): The OAuth token to verify.

        Returns:
            dict: The validated token if valid.
            None: If the token is invalid or verification fails.

        Raises:
            ValueError: If the token is missing required fields.
        """
        try:
            if 'username' in token and 'email' in token:
                return token
            else:
                raise ValueError("Invalid token structure: 'username' or 'email' missing.")
            
        except Exception as e:
            print(f"Token verification failed: {e}")
        
        return None
