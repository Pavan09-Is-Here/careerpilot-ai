"""add phase 16 auto-submit run consent and submission method

One-click auto-apply: an application run may now record when the
candidate gave explicit per-job consent (``consented_at``) and, once
submitted, which channel performed the submission
(``submission_method`` — e.g. ``manual`` or a provider adapter name).
Both columns are nullable additions; existing rows are unaffected and
the downgrade simply drops them.

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("application_runs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "consented_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "submission_method",
                sa.String(length=50),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("application_runs") as batch_op:
        batch_op.drop_column("submission_method")
        batch_op.drop_column("consented_at")
