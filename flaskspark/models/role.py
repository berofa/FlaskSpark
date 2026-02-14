"""
Role model and helpers for FlaskSpark.
"""

from __future__ import annotations

from flaskspark import db
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError


class Role(db.Model):
    """
    Represents an authorization role.

    Attributes:
        id (int): Primary key for the role.
        name (str): Human-readable role name.
        is_admin (bool): Whether the role grants administrative permissions.
        rank (int): Role ordering for minimum access checks.
    """

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    rank = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        """
        Return a string representation of the role.

        Args:
            None

        Returns:
            str: Role name.
        """
        return f"<Role {self.name}>"

    @staticmethod
    def ensure_defaults():
        """
        Ensure the default roles exist.

        Creates the default portal roles if they are missing.

        Args:
            None

        Returns:
            dict[str, Role]: Mapping of role names to role instances.
        """
        try:
            bind = db.session.get_bind()
            inspector = inspect(bind)
            if not inspector.has_table("roles"):
                return {}
            columns = [col["name"] for col in inspector.get_columns("roles")]
            if "rank" not in columns:
                return {}
        except OperationalError:
            return {}
        defaults = [
            ("Administrators", True, 100),
            ("Editors", False, 80),
            ("Users", False, 50),
            ("Guests", False, 10),
        ]
        roles = {}
        for name, is_admin, rank in defaults:
            role = Role.query.filter_by(name=name).first()
            if not role:
                role = Role(name=name, is_admin=is_admin, rank=rank)
                db.session.add(role)
            else:
                role.is_admin = bool(role.is_admin or is_admin)
                if not role.rank:
                    role.rank = rank
            roles[name] = role

        db.session.commit()
        return roles

    @staticmethod
    def get_or_create(name: str, is_admin: bool = False, rank: int = 0):
        """
        Fetch a role by name or create it if missing.

        Args:
            name (str): Role name.
            is_admin (bool): Admin flag for newly created roles.

        Returns:
            Role: Resolved or created role.
        """
        role = Role.query.filter_by(name=name).first()
        if role:
            return role
            role = Role(name=name, is_admin=is_admin, rank=rank)
        db.session.add(role)
        db.session.commit()
        return role
