"""add email verification and password reset columns to users

Adds four columns to the ``users`` table supporting non-blocking email
verification on sign-up and forgot/reset password:

* ``email_verified`` — whether the account email has been confirmed.
* ``email_verification_token_hash`` — SHA-256 hash of the pending
  verification token (raw token is never stored).
* ``password_reset_token_hash`` — SHA-256 hash of the pending reset
  token.
* ``password_reset_expires_at`` — expiry of the pending reset token.

Only token hashes are persisted; raw tokens live only in the emailed
link. Plain ``add_column`` operations (no FKs), so no batch mode is
needed. ``email_verified`` gets a server default of false so existing
rows are backfilled.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_verification_token_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_reset_token_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_reset_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "password_reset_expires_at")
    op.drop_column("users", "password_reset_token_hash")
    op.drop_column("users", "email_verification_token_hash")
    op.drop_column("users", "email_verified")
