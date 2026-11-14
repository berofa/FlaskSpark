"""core tables

The core's own tables (flaskspark.core.models): the settings of config.yaml the admins changed, the role x area
matrix, the users' personal settings and the roles set by hand per user. The first revision of the history "core":
`<app> db adopt` stamps it on a database that has these tables already.

Revision ID: 3b9e0c71a5d2
Revises:
Create Date: 2026-11-13 20:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3b9e0c71a5d2"
down_revision = None
branch_labels = ("core",)
depends_on = None


def upgrade():
    op.create_table(
        "core_role_area",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("area", sa.String(length=64), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "area"),
    )
    with op.batch_alter_table("core_role_area", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_core_role_area_role_id"), ["role_id"], unique=False)

    op.create_table(
        "core_settings",
        sa.Column("path", sa.String(length=160), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("changed", sa.Float(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("path"),
    )

    op.create_table(
        "core_user_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("updated", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "key"),
    )
    with op.batch_alter_table("core_user_settings", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_core_user_settings_user_id"), ["user_id"], unique=False)

    op.create_table(
        "core_user_role",
        sa.Column("user_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=True),
        sa.Column("sso_role_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade():
    op.drop_table("core_user_role")

    with op.batch_alter_table("core_user_settings", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_core_user_settings_user_id"))
    op.drop_table("core_user_settings")

    op.drop_table("core_settings")

    with op.batch_alter_table("core_role_area", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_core_role_area_role_id"))
    op.drop_table("core_role_area")
