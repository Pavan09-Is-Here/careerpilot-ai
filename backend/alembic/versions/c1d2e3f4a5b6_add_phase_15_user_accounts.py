"""add phase 15 user accounts (multi-tenant)

Introduces a users table (login accounts) and ties ownership of data to
it: every candidate profile belongs to a user, every session belongs to
a user, and saved jobs and notifications are scoped to a candidate
profile. Replaces the previous single global credential.

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-07-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b0c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. New login accounts table.
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=150), nullable=False),
        sa.Column("algorithm", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=128), nullable=False),
        sa.Column("salt", sa.String(length=64), nullable=False),
        sa.Column("iterations", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # 2. The old single global credential is superseded by users.
    op.drop_table("auth_credentials")

    # 3. Each candidate profile is owned by a user (one-to-one).
    with op.batch_alter_table("candidate_profiles") as batch_op:
        batch_op.add_column(
            sa.Column("user_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_candidate_profiles_user_id",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_candidate_profiles_user_id",
            ["user_id"],
            unique=True,
        )

    # 4. Sessions belong to a user. Existing sessions are ephemeral and
    #    are invalidated by this reset, so they can be cleared before the
    #    NOT NULL owner column is added.
    op.execute("DELETE FROM auth_sessions")
    with op.batch_alter_table("auth_sessions") as batch_op:
        batch_op.add_column(
            sa.Column("user_id", sa.Integer(), nullable=False)
        )
        batch_op.create_foreign_key(
            "fk_auth_sessions_user_id",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_auth_sessions_user_id",
            ["user_id"],
            unique=False,
        )


def downgrade() -> None:
    op.execute("DELETE FROM auth_sessions")
    with op.batch_alter_table("auth_sessions") as batch_op:
        batch_op.drop_index("ix_auth_sessions_user_id")
        batch_op.drop_constraint(
            "fk_auth_sessions_user_id",
            type_="foreignkey",
        )
        batch_op.drop_column("user_id")

    with op.batch_alter_table("candidate_profiles") as batch_op:
        batch_op.drop_index("ix_candidate_profiles_user_id")
        batch_op.drop_constraint(
            "fk_candidate_profiles_user_id",
            type_="foreignkey",
        )
        batch_op.drop_column("user_id")

    op.create_table(
        "auth_credentials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("algorithm", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=128), nullable=False),
        sa.Column("salt", sa.String(length=64), nullable=False),
        sa.Column("iterations", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
