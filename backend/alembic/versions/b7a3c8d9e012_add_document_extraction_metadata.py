"""add document extraction metadata

Revision ID: b7a3c8d9e012
Revises: 6a528be87510
Create Date: 2026-06-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7a3c8d9e012"
down_revision: Union[str, Sequence[str], None] = "6a528be87510"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "documents",
        sa.Column(
            "extraction_status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "documents",
        sa.Column("extracted_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("extraction_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "extracted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column("page_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "extracted_character_count",
            sa.Integer(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column("documents", "extracted_character_count")
    op.drop_column("documents", "page_count")
    op.drop_column("documents", "extracted_at")
    op.drop_column("documents", "extraction_error")
    op.drop_column("documents", "extracted_text")
    op.drop_column("documents", "extraction_status")
