"""sign-in tables: the columns older tables lack

The first revision describes FlaskSpark's users and roles as they are today. An application that kept these tables in
an earlier history (`db adopt` stamps the first revision when both tables exist) may have them without the columns
added later: the user's role, names and admin flag, the role's admin flag and rank. This revision adds whichever of
them is missing and does nothing on tables the first revision created.

Revision ID: 29f594d439bf
Revises: 8a41d6c2f0e7
Create Date: 2026-11-14 10:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "29f594d439bf"
down_revision = "8a41d6c2f0e7"
branch_labels = None
depends_on = None

ROLE_COLUMNS = (
    ("is_admin", lambda: sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false())),
    ("rank", lambda: sa.Column("rank", sa.Integer(), nullable=False, server_default="0")),
)
USER_COLUMNS = (
    ("role_id", lambda: sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", name="fk_user_role_id"),
                                  nullable=True)),
    ("first_name", lambda: sa.Column("first_name", sa.String(length=255), nullable=True)),
    ("last_name", lambda: sa.Column("last_name", sa.String(length=255), nullable=True)),
    ("admin", lambda: sa.Column("admin", sa.Boolean(), nullable=True)),
)


def _add_missing(table: str, columns) -> None:
    have = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
    missing = [make() for name, make in columns if name not in have]
    if missing:
        with op.batch_alter_table(table) as batch:
            for column in missing:
                batch.add_column(column)


def upgrade():
    _add_missing("roles", ROLE_COLUMNS)
    _add_missing("user", USER_COLUMNS)


def downgrade():
    pass  # the columns belong to the tables of the first revision
