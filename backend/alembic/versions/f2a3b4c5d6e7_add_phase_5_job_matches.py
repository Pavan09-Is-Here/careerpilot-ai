"""Add Phase 5 job matches.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def enum_check(column_name: str, values: tuple[str, ...]) -> str:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} IN ({quoted_values})"


def score_check(column_name: str) -> str:
    return (
        f"{column_name} IS NULL OR "
        f"({column_name} >= 0 AND {column_name} <= 100)"
    )


JOB_MATCH_ELIGIBILITY_STATUSES = (
    "eligible",
    "conditionally_eligible",
    "ineligible",
)

SCORE_COLUMNS = (
    "match_score",
    "skills_match",
    "experience_match",
    "education_match",
    "projects_match",
    "location_match",
    "work_auth_match",
)


def upgrade() -> None:
    op.create_table(
        "job_matches",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column(
            "candidate_profile_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column("match_score", sa.Integer(), nullable=True),
        sa.Column("skills_match", sa.Integer(), nullable=True),
        sa.Column(
            "experience_match",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "education_match",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column("projects_match", sa.Integer(), nullable=True),
        sa.Column("location_match", sa.Integer(), nullable=True),
        sa.Column(
            "work_auth_match",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "eligibility_status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "blocker_reason",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "algorithm_version",
            sa.String(length=100),
            nullable=False,
        ),
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
            enum_check(
                "eligibility_status",
                JOB_MATCH_ELIGIBILITY_STATUSES,
            ),
            name="ck_job_matches_eligibility_status",
        ),
        sa.CheckConstraint(
            score_check("match_score"),
            name="ck_job_matches_match_score_range",
        ),
        sa.CheckConstraint(
            score_check("skills_match"),
            name="ck_job_matches_skills_range",
        ),
        sa.CheckConstraint(
            score_check("experience_match"),
            name="ck_job_matches_experience_range",
        ),
        sa.CheckConstraint(
            score_check("education_match"),
            name="ck_job_matches_education_range",
        ),
        sa.CheckConstraint(
            score_check("projects_match"),
            name="ck_job_matches_projects_range",
        ),
        sa.CheckConstraint(
            score_check("location_match"),
            name="ck_job_matches_location_range",
        ),
        sa.CheckConstraint(
            score_check("work_auth_match"),
            name="ck_job_matches_work_auth_range",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["normalized_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            "candidate_profile_id",
            name="uq_job_matches_job_profile",
        ),
    )
    op.create_index(
        "ix_job_matches_job_id",
        "job_matches",
        ["job_id"],
    )
    op.create_index(
        "ix_job_matches_candidate_profile_id",
        "job_matches",
        ["candidate_profile_id"],
    )
    op.create_index(
        "ix_job_matches_eligibility_status",
        "job_matches",
        ["eligibility_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_job_matches_eligibility_status",
        table_name="job_matches",
    )
    op.drop_index(
        "ix_job_matches_candidate_profile_id",
        table_name="job_matches",
    )
    op.drop_index(
        "ix_job_matches_job_id",
        table_name="job_matches",
    )
    op.drop_table("job_matches")
