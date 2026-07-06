"""add per-profile ownership for packages, applications, tailored CVs

Multi-tenant hardening: application packages, tracked applications,
and job-tailored-CV links were unique per job GLOBALLY, so two
accounts could not each apply to the same job and one account could
reach another's records. This migration:

1. replaces the global ``job_id`` unique constraints on
   ``application_packages`` and ``applications`` with per-profile
   ``(job_id, candidate_profile_id)`` constraints;
2. adds a nullable ``candidate_profile_id`` to ``job_tailored_cvs``
   (FK to candidate_profiles, CASCADE), backfills it from the linked
   CV version's owner, and replaces the global ``job_id`` unique
   constraint with ``(job_id, candidate_profile_id)``.

Downgrade restores the original constraints and drops the new column.
Note: the downgrade's global unique constraints can only be recreated
if no job has rows for multiple profiles (true for any database that
never ran multi-profile flows).

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-07-06 00:00:00.000001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("application_packages") as batch_op:
        batch_op.drop_constraint(
            "uq_application_packages_job_id",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_application_packages_job_profile",
            ["job_id", "candidate_profile_id"],
        )

    with op.batch_alter_table("applications") as batch_op:
        batch_op.drop_constraint(
            "uq_applications_job_id",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_applications_job_profile",
            ["job_id", "candidate_profile_id"],
        )

    with op.batch_alter_table("job_tailored_cvs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "candidate_profile_id",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "fk_job_tailored_cvs_candidate_profile_id",
            "candidate_profiles",
            ["candidate_profile_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            "ix_job_tailored_cvs_candidate_profile_id",
            ["candidate_profile_id"],
        )
        batch_op.drop_constraint(
            "uq_job_tailored_cvs_job_id",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_job_tailored_cvs_job_profile",
            ["job_id", "candidate_profile_id"],
        )

    # Backfill ownership from the linked CV version's owner.
    op.execute(
        "UPDATE job_tailored_cvs SET candidate_profile_id = ("
        "SELECT cv_versions.candidate_profile_id FROM cv_versions "
        "WHERE cv_versions.id = job_tailored_cvs.cv_version_id)"
    )


def downgrade() -> None:
    with op.batch_alter_table("job_tailored_cvs") as batch_op:
        batch_op.drop_constraint(
            "uq_job_tailored_cvs_job_profile",
            type_="unique",
        )
        batch_op.drop_index(
            "ix_job_tailored_cvs_candidate_profile_id"
        )
        batch_op.drop_constraint(
            "fk_job_tailored_cvs_candidate_profile_id",
            type_="foreignkey",
        )
        batch_op.drop_column("candidate_profile_id")
        batch_op.create_unique_constraint(
            "uq_job_tailored_cvs_job_id",
            ["job_id"],
        )

    with op.batch_alter_table("applications") as batch_op:
        batch_op.drop_constraint(
            "uq_applications_job_profile",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_applications_job_id",
            ["job_id"],
        )

    with op.batch_alter_table("application_packages") as batch_op:
        batch_op.drop_constraint(
            "uq_application_packages_job_profile",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_application_packages_job_id",
            ["job_id"],
        )
