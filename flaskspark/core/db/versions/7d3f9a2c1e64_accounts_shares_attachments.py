"""accounts, shares and attachments

The tables of the core's accounts (core_accounts, core_account_types), shares (core_shares, core_share_members,
core_share_notices) and attachments (core_attachments): flaskspark.core.accounts, .shares, .attachments.

Revision ID: 7d3f9a2c1e64
Revises: 5c2d8e41b7a9
Create Date: 2026-11-13 23:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7d3f9a2c1e64"
down_revision = "5c2d8e41b7a9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "core_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_enc", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name"),
    )
    with op.batch_alter_table("core_accounts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_core_accounts_user_id"), ["user_id"], unique=False)

    op.create_table(
        "core_account_types",
        sa.Column("account_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("checked", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("account_id", "type"),
    )

    op.create_table(
        "core_shares",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("object_type", sa.String(length=64), nullable=False),
        sa.Column("object_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission", sa.String(length=5), nullable=False),
        sa.Column("created", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_type", "object_id", "role_id"),
    )
    with op.batch_alter_table("core_shares", schema=None) as batch_op:
        batch_op.create_index("ix_core_shares_object", ["object_type", "object_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_core_shares_role_id"), ["role_id"], unique=False)

    op.create_table(
        "core_share_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("object_type", sa.String(length=64), nullable=False),
        sa.Column("object_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("created", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_type", "object_id", "user_id"),
    )
    with op.batch_alter_table("core_share_members", schema=None) as batch_op:
        batch_op.create_index("ix_core_share_members_object", ["object_type", "object_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_core_share_members_user_id"), ["user_id"], unique=False)

    op.create_table(
        "core_share_notices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("object_type", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("created", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("core_share_notices", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_core_share_notices_user_id"), ["user_id"], unique=False)

    op.create_table(
        "core_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("owner_type", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("mime", sa.String(length=100), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("sorting", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("uploaded", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("core_attachments", schema=None) as batch_op:
        batch_op.create_index("ix_core_attachments_owner", ["owner_type", "owner_id"], unique=False)


def downgrade():
    with op.batch_alter_table("core_attachments", schema=None) as batch_op:
        batch_op.drop_index("ix_core_attachments_owner")
    op.drop_table("core_attachments")
    with op.batch_alter_table("core_share_notices", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_core_share_notices_user_id"))
    op.drop_table("core_share_notices")
    with op.batch_alter_table("core_share_members", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_core_share_members_user_id"))
        batch_op.drop_index("ix_core_share_members_object")
    op.drop_table("core_share_members")
    with op.batch_alter_table("core_shares", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_core_shares_role_id"))
        batch_op.drop_index("ix_core_shares_object")
    op.drop_table("core_shares")
    op.drop_table("core_account_types")
    with op.batch_alter_table("core_accounts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_core_accounts_user_id"))
    op.drop_table("core_accounts")
