"""sign-in tables

FlaskSpark's users and roles (flaskspark.models, Flask-SQLAlchemy) as the OAuth sign-in (RoleAccess) needs them. Only
an installation with sign-in (config.yaml auth: oauth / sso) runs the history "signin".

Revision ID: 8a41d6c2f0e7
Revises:
Create Date: 2026-11-13 20:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "8a41d6c2f0e7"
down_revision = None
branch_labels = ("signin",)
depends_on = None


def upgrade():
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("admin", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("username"),
    )


def downgrade():
    op.drop_table("user")
    op.drop_table("roles")
