"""Bulk verification of a candidate's own facts-vault records.

This is an explicit, user-initiated confirmation: the account owner
reviews their profile and confirms that the (CV-derived or manually
entered) records are correct. It only ever operates on the caller's own
candidate profile. It does not create or alter any values — it only flips
the ``verified`` flag from False to True on records the user is
confirming.
"""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.certification import Certification
from app.models.education import Education
from app.models.experience import Experience
from app.models.project import Project
from app.models.skill import Skill


_VERIFIABLE = (
    ("education", Education),
    ("experience", Experience),
    ("projects", Project),
    ("skills", Skill),
    ("certifications", Certification),
)


def verify_all_facts(
    database: Session,
    candidate_profile_id: int,
) -> dict[str, int]:
    """Mark every unverified record on this profile as verified.

    Returns the number of records newly verified per category.
    """

    newly_verified: dict[str, int] = {}
    for label, model in _VERIFIABLE:
        unverified_ids = list(
            database.scalars(
                select(model.id).where(
                    model.candidate_profile_id == candidate_profile_id,
                    model.verified.is_(False),
                )
            ).all()
        )
        if unverified_ids:
            database.execute(
                update(model)
                .where(model.id.in_(unverified_ids))
                .values(verified=True)
            )
        newly_verified[label] = len(unverified_ids)

    profile = database.get(CandidateProfile, candidate_profile_id)
    if profile is not None:
        profile.facts_verified = True

    database.commit()
    return newly_verified
