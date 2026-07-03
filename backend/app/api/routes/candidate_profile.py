from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile
from app.core.database import get_db
from app.models.candidate_profile import CandidateProfile
from app.schemas.candidate_profile import (
    CandidateProfileResponse,
    CandidateProfileUpsert,
)


router = APIRouter(
    prefix="/profile",
    tags=["Candidate Profile"],
)


@router.get(
    "",
    response_model=CandidateProfileResponse,
)
def get_candidate_profile(
    database: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_current_profile),
) -> CandidateProfile:
    return profile


@router.put(
    "",
    response_model=CandidateProfileResponse,
)
def create_or_update_candidate_profile(
    payload: CandidateProfileUpsert,
    database: Session = Depends(get_db),
    profile: CandidateProfile = Depends(get_current_profile),
) -> CandidateProfile:
    profile_data = payload.model_dump()

    for field_name, field_value in profile_data.items():
        setattr(profile, field_name, field_value)

    database.commit()
    database.refresh(profile)

    return profile
