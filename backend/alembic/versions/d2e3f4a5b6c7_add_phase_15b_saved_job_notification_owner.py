"""add phase 15b saved job / notification ownership

Completes multi-tenancy by scoping the two tables Phase 15A deferred to a
candidate profile: saved jobs are saved per profile, and notifications
belong to a profile. Each table gains a nullable
``candidate_profile_id`` foreign key (CASCADE on profile deletion) and an
index. For saved jobs, the old global unique constraint on ``job_id`` is
replaced by a per-profile unique constraint on
``(candidate_profile_id, job_id)`` so different accounts may each save the
same job.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-07-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Saved jobs are scoped to the candidate profile that saved them.
    with op.batch_alter_table("saved_jobs") as batch_op:
        batch_op.add_column(
            sa.Column("candidate_profile_id", sa.Integer(), nullable=True)
        )
        batch_op.drop_constraint(
            "uq_saved_jobs_job_id",
            type_="unique",
        )
        batch_op.create_foreign_key(
            "fk_saved_jobs_candidate_profile_id",
            "candidate_profiles",
            ["candidate_profile_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint(
            "uq_saved_jobs_profile_job",
            ["candidate_profile_id", "job_id"],
        )
        batch_op.create_index(
            "ix_saved_jobs_candidate_profile_id",
            ["candidate_profile_id"],
            unique=False,
        )

    # 2. Notifications belong to a candidate profile.
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(
            sa.Column("candidate_profile_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_notifications_candidate_profile_id",
            "candidate_profiles",
            ["candidate_profile_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_notifications_candidate_profile_id",
            ["candidate_profile_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_index("ix_notifications_candidate_profile_id")
        batch_op.drop_constraint(
            "fk_notifications_candidate_profile_id",
            type_="foreignkey",
        )
        batch_op.drop_column("candidate_profile_id")

    with op.batch_alter_table("saved_jobs") as batch_op:
        batch_op.drop_index("ix_saved_jobs_candidate_profile_id")
        batch_op.drop_constraint(
            "uq_saved_jobs_profile_job",
            type_="unique",
        )
        batch_op.drop_constraint(
            "fk_saved_jobs_candidate_profile_id",
            type_="foreignkey",
        )
        batch_op.create_unique_constraint(
            "uq_saved_jobs_job_id",
            ["job_id"],
        )
        batch_op.drop_column("candidate_profile_id")
