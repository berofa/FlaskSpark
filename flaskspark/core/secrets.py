"""Secrets a module stores (API keys, passwords of accounts it signs in to): encrypted in the database with a key from
the environment, never in plain text.

The key: the environment variable APP_SECRET_KEY (its name can be changed with APP_SECRET_KEY_ENV, e.g. an application
that already has a variable of its own for it). Like every secret it lives in an env file (CONFIG_DIR/app.env, loaded
by config.load(); flaskspark.core.config), or in the container's environment. Changing it makes the stored secrets
unreadable.

Scheme: Fernet (AES-128-CBC with HMAC-SHA256, cryptography) with the key urlsafe_b64(SHA-256(<the variable's value>)).
Any text of any length is a key; the same text gives the same key, so secrets stored by another program with this
scheme stay readable.

A module takes its box with for_module(name): today every module gets the same key, unless the environment has one of
its own (<the key's variable>_<MODULE>, e.g. APP_SECRET_KEY_SHOP), so a key need only live where its module runs.

    box = secrets.for_module("shop")
    token = box.encrypt("api-key")      # into the database
    box.decrypt(token)                  # -> "api-key"; SecretKeyError with another key
"""

from __future__ import annotations

import base64
import hashlib
import os
import re

DEFAULT_ENV_KEY = "APP_SECRET_KEY"


class SecretKeyError(RuntimeError):
    """No key in the environment, or a stored secret that the key can't read (the key changed)."""


def env_key() -> str:
    """The name of the variable with the key: APP_SECRET_KEY_ENV, default APP_SECRET_KEY."""
    return os.environ.get("APP_SECRET_KEY_ENV") or DEFAULT_ENV_KEY


def module_env_key(module: str) -> str:
    """The variable with a module's own key: <env_key()>_<MODULE> (other characters than letters and digits: _)."""
    return f"{env_key()}_{re.sub(r'[^A-Za-z0-9]', '_', module).upper()}"


def _load_env_files(module: str | None = None) -> None:
    """The env files of the core and of `module` into the environment (existing variables win)."""
    from . import paths
    from .config import load_env_file

    load_env_file(paths.env_file("app"))
    if module:
        load_env_file(paths.env_file(module))


def derive(raw: str) -> bytes:
    """The Fernet key of a key text: urlsafe_b64(SHA-256(text))."""
    return base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())


def _raw_key(module: str | None = None) -> str:
    # the env files first: they may also name the variable (APP_SECRET_KEY_ENV)
    _load_env_files(module)
    names = ([module_env_key(module)] if module else []) + [env_key()]
    for name in names:
        if os.environ.get(name):
            return os.environ[name]
    raise SecretKeyError(f"{env_key()} is missing (the environment or an env file, flaskspark.core.config)")


def fernet(key: str | None = None, module: str | None = None):
    """The Fernet of `key` (a key text), else of the environment's key (of `module` if it has one of its own)."""
    from cryptography.fernet import Fernet

    return Fernet(derive(key or _raw_key(module)))


def encrypt(secret: str, key: str | None = None, module: str | None = None) -> str:
    return fernet(key, module).encrypt(secret.encode()).decode()


def decrypt(token: str, key: str | None = None, module: str | None = None) -> str:
    from cryptography.fernet import InvalidToken

    try:
        return fernet(key, module).decrypt(token.encode()).decode()
    except (InvalidToken, ValueError) as exc:
        raise SecretKeyError(f"secret not readable ({env_key()} changed?)") from exc


def mask(value: str, visible: int = 4) -> str:
    """A secret for people: its first characters only ("sk-a…")."""
    return value[:visible] + "…" if len(value) > visible else "…"


class SecretBox:
    """The encryption of one module (for_module): its own key when the environment has one, else the shared one."""

    def __init__(self, module: str, key: str | None = None):
        self.module = module
        self.key = key

    def encrypt(self, secret: str) -> str:
        return encrypt(secret, self.key, self.module)

    def decrypt(self, token: str) -> str:
        return decrypt(token, self.key, self.module)


def for_module(module: str) -> SecretBox:
    """The secrets of a module (e.g. "shop")."""
    return SecretBox(module)
