"""Add Phase 13 authentication credentials and sessions.

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-07-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9b0c1d2e3f4"
down_revision: Union[str, None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_credentials",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "algorithm",
            sa.String(length=50),
            server_default="pbkdf2_sha256",
            nullable=False,
        ),
        sa.Column(
            "password_hash",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("salt", sa.String(length=64), nullable=False),
        sa.Column("iterations", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "auth_sessions",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_auth_sessions_token_hash",
        ),
    )
    op.create_index(
        "ix_auth_sessions_token_hash",
        "auth_sessions",
        ["token_hash"],
    )
    op.create_index(
        "ix_auth_sessions_expires_at",
        "auth_sessions",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_auth_sessions_expires_at",
        table_name="auth_sessions",
    )
    op.drop_index(
        "ix_auth_sessions_token_hash",
        table_name="auth_sessions",
    )
    op.drop_table("auth_sessions")
    op.drop_table("auth_credentials")
