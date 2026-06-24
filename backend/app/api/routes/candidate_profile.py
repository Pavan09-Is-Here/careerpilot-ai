from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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
) -> CandidateProfile:
    profile = database.get(CandidateProfile, 1)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile has not been created yet.",
        )

    return profile


@router.put(
    "",
    response_model=CandidateProfileResponse,
)
def create_or_update_candidate_profile(
    payload: CandidateProfileUpsert,
    database: Session = Depends(get_db),
) -> CandidateProfile:
    profile = database.get(CandidateProfile, 1)
    profile_data = payload.model_dump()

    if profile is None:
        profile = CandidateProfile(
            id=1,
            **profile_data,
        )

        database.add(profile)
    else:
        for field_name, field_value in profile_data.items():
            setattr(profile, field_name, field_value)

    database.commit()
    database.refresh(profile)

    return profile