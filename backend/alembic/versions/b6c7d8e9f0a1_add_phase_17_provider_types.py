"""add phase 17 provider types (remotive, arbeitnow, reed)

Extends the ``job_sources.provider_type`` CHECK constraint with the
three new free providers. Purely a constraint change — no data is
modified. The downgrade restores the previous list and is safe as long
as no job source rows use the new provider types.

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-07-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, Sequence[str], None] = "a5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_TYPES = (
    "none",
    "greenhouse",
    "lever",
    "ashby",
    "workable",
    "adzuna",
    "usajobs",
    "generic_api",
    "company_career_page",
    "manual",
    "other",
)
NEW_TYPES = (
    "none",
    "greenhouse",
    "lever",
    "ashby",
    "workable",
    "adzuna",
    "usajobs",
    "remotive",
    "arbeitnow",
    "reed",
    "generic_api",
    "company_career_page",
    "manual",
    "other",
)


def _condition(values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"provider_type IN ({quoted})"


def upgrade() -> None:
    with op.batch_alter_table("job_sources") as batch_op:
        batch_op.drop_constraint(
            "ck_job_sources_provider_type",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_job_sources_provider_type",
            _condition(NEW_TYPES),
        )


def downgrade() -> None:
    with op.batch_alter_table("job_sources") as batch_op:
        batch_op.drop_constraint(
            "ck_job_sources_provider_type",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_job_sources_provider_type",
            _condition(OLD_TYPES),
        )
