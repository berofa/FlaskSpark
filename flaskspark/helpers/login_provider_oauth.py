"""
Implements an OAuth-based login provider.
"""

from __future__ import annotations

import logging
import os

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, redirect, request, session, url_for
from flask_login import login_required, login_user, logout_user

from flaskspark import db
from flaskspark.helpers.login_provider import AbstractLoginProvider
from flaskspark.models.role import Role
from flaskspark.models.user import User

logger = logging.getLogger(__name__)


class OAuthLoginProvider(AbstractLoginProvider):
    """
    A login provider using OAuth authentication.
    """

    requires_user_model = True
    requires_role_model = True

    def __init__(self, app):
        """
        Initialize the OAuth provider and attach the Authlib client.

        Args:
            app (Flask): Flask application instance.

        Returns:
            None
        """
        super().__init__(app)
        self.oauth = OAuth()

    def check_configuration(self, config):
        """
        Check if all required OAuth configuration variables are set.

        Args:
            config (dict): Application configuration mapping.

        Returns:
            None
        """
        required_oauth_vars = [
            "OAUTH_NAME",
            "OAUTH_AUTHORIZE_URL",
            "OAUTH_ACCESS_TOKEN_URL",
            "OAUTH_USERINFO_ENDPOINT",
            "OAUTH_JWKS_URI",
            "OAUTH_CLIENT_ID",
            "OAUTH_CLIENT_SECRET",
            "OAUTH_SCOPE",
        ]

        missing_vars = [var for var in required_oauth_vars if not config.get(var)]
        if missing_vars:
            logger.warning(
                "The following OAuth configuration variables are missing: %s",
                ", ".join(missing_vars),
            )

    def configure(self):
        """
        Configures OAuth authentication for the application.

        Args:
            None

        Returns:
            None
        """
        self.login_manager.login_view = "auth.login"

        self.oauth.init_app(self.app)
        self.oauth.register(
            name=self.app.config["OAUTH_NAME"],
            authorize_url=self.app.config["OAUTH_AUTHORIZE_URL"],
            access_token_url=self.app.config["OAUTH_ACCESS_TOKEN_URL"],
            client_kwargs={
                "userinfo_endpoint": self.app.config["OAUTH_USERINFO_ENDPOINT"],
                "scope": self.app.config["OAUTH_SCOPE"],
            },
            jwks_uri=self.app.config["OAUTH_JWKS_URI"],
            client_id=self.app.config["OAUTH_CLIENT_ID"],
            client_secret=self.app.config["OAUTH_CLIENT_SECRET"],
        )

        auth_blueprint = Blueprint("auth", __name__)

        @self.login_manager.request_loader
        def request_loader(_request):
            """
            Load the logged-in user from the current session.

            Args:
                _request (Request): Flask request object (unused).

            Returns:
                User | None: Resolved user or None.
            """
            token = session.get("user")
            if token:
                user_id = token.get("id") if isinstance(token, dict) else None
                if user_id:
                    user = User.query.get(user_id)
                    if user:
                        return user
                user_info = User.verify_oauth_token(token)
                if user_info:
                    return User.query.filter_by(username=user_info["username"]).first()
            return None

        @auth_blueprint.route("/auth/login")
        def login():
            """
            Start the OAuth login flow.

            Returns:
                Response: Redirect response to the identity provider.
            """
            state = os.urandom(24).hex()
            nonce = os.urandom(24).hex()
            session["oauth_state"] = state
            session["nonce"] = nonce
            session["next"] = request.args.get("next")
            session.modified = True
            redirect_uri = self.app.config.get("OAUTH_REDIRECT_URI") or url_for(
                "auth.callback", _external=True
            )
            client = self.oauth.create_client(self.app.config["OAUTH_NAME"])
            return client.authorize_redirect(redirect_uri, state=state, nonce=nonce)

        @auth_blueprint.route("/auth/callback")
        def callback():
            """
            Handle the OAuth callback and establish a user session.

            Returns:
                Response: Redirect response to the configured next URL or home.
            """
            if request.args.get("state") != session.get("oauth_state"):
                return "State mismatch error", 400

            client = self.oauth.create_client(self.app.config["OAUTH_NAME"])
            token = client.authorize_access_token()
            user_info = token.get("userinfo")
            if not user_info:
                return "User info not found in token", 400

            username = user_info.get("username")
            if not username or "." not in username:
                return "Invalid username format", 400
            first_name, last_name = _extract_names_from_username(username)

            Role.ensure_defaults()
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username, email=user_info["email"])
                db.session.add(user)

            user.email = user_info["email"]
            user.first_name = first_name
            user.last_name = last_name
            groups_claim = self.app.config.get("OAUTH_GROUPS_CLAIM", "groups")
            groups = user_info.get(groups_claim) or []
            if isinstance(groups, str):
                groups = [item.strip() for item in groups.split(",") if item.strip()]
            role_priority = self.app.config.get("OAUTH_ROLE_PRIORITY") or []
            role_map = self.app.config.get("OAUTH_ROLE_MAP") or {}
            resolved_role = None
            if groups:
                for group in role_priority:
                    if group in groups and group in role_map:
                        role_name = role_map[group]
                        resolved_role = Role.get_or_create(
                            role_name, is_admin=role_name == "Administrator"
                        )
                        break
            if resolved_role:
                user.role = resolved_role
            else:
                total_users = User.query.count()
                admin_role = Role.query.filter_by(name="Administrators").first()
                guest_role = Role.query.filter_by(name="Guests").first()
                if total_users == 0 and admin_role:
                    user.role = admin_role
                elif guest_role:
                    user.role = guest_role
            if user.role:
                user.admin = user.role.is_admin

            db.session.commit()

            session["user"] = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "admin": user.admin,
                "role_id": user.role.id if user.role else None,
                "role_name": user.role.name if user.role else None,
            }

            login_user(user)
            return redirect(session.pop("next", None) or url_for("home"))

        @auth_blueprint.route("/auth/logout")
        @login_required
        def logout():
            """
            Clear the user session and log out.

            Returns:
                Response: Redirect response to the home page.
            """
            logout_user()
            session.clear()
            return redirect(url_for("home"))

        self.app.register_blueprint(auth_blueprint)


def _extract_names_from_username(username: str):
    """
    Extract first and last names from a username formatted as "first.last".

    Args:
        username (str): Username string in "first.last" format.

    Returns:
        tuple[str | None, str | None]: Capitalized first and last names.
    """
    if "." in username:
        first_name, last_name = username.split(".", 1)
        return first_name.capitalize(), last_name.capitalize()
    return None, None
