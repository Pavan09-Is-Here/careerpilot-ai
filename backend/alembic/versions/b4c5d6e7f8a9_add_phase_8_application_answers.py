"""Add Phase 8 verified application answer vault.

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-07-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


APPLICATION_ANSWER_CATEGORIES = (
    "work_authorization",
    "sponsorship",
    "availability",
    "notice_period",
    "relocation",
    "remote_preference",
    "expected_salary",
    "company_interest",
    "cover_letter",
    "other",
)


def category_check() -> str:
    quoted = ", ".join(f"'{value}'" for value in APPLICATION_ANSWER_CATEGORIES)
    return f"category IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "application_answers",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "candidate_profile_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column(
            "question_label",
            sa.String(length=300),
            nullable=False,
        ),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column(
            "verified",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "manually_confirmed",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "requires_manual_confirmation",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            category_check(),
            name="ck_application_answers_category",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_profile_id",
            "category",
            "question_label",
            name="uq_application_answers_identity",
        ),
    )
    op.create_index(
        "ix_application_answers_candidate_profile_id",
        "application_answers",
        ["candidate_profile_id"],
    )
    op.create_index(
        "ix_application_answers_category",
        "application_answers",
        ["category"],
    )
    op.create_index(
        "ix_application_answers_candidate_category",
        "application_answers",
        ["candidate_profile_id", "category"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_application_answers_candidate_category",
        table_name="application_answers",
    )
    op.drop_index(
        "ix_application_answers_category",
        table_name="application_answers",
    )
    op.drop_index(
        "ix_application_answers_candidate_profile_id",
        table_name="application_answers",
    )
    op.drop_table("application_answers")
