"""module chains

The table core_module_chains (flaskspark.core.models.ModuleChain): the modules seen at the start, with their
history's revision and their tables, so a module the application no longer delivers can still be named.

Revision ID: 5c2d8e41b7a9
Revises: 3b9e0c71a5d2
Create Date: 2026-11-13 22:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "5c2d8e41b7a9"
down_revision = "3b9e0c71a5d2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "core_module_chains",
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("revision", sa.String(length=32), nullable=True),
        sa.Column("tables", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("seen", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )


def downgrade():
    op.drop_table("core_module_chains")
