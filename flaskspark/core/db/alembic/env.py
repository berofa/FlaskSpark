"""Alembic's environment of flaskspark.core: the histories of the core and the modules (flaskspark.core.db.migrations)."""

from alembic import context

from flaskspark.core.db.migrations import run_env

run_env(context)
