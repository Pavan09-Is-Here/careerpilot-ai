from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.candidate_profile import CandidateProfile
from app.models.experience import Experience
from app.schemas.experience import (
    ExperienceCreate,
    ExperienceResponse,
    ExperienceUpdate,
)


router = APIRouter(
    prefix="/experience",
    tags=["Work Experience"],
)


def get_experience_or_404(
    experience_id: int,
    database: Session,
) -> Experience:
    experience = database.get(
        Experience,
        experience_id,
    )

    if (
        experience is None
        or experience.candidate_profile_id != 1
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Work experience record was not found.",
        )

    return experience


@router.get(
    "",
    response_model=list[ExperienceResponse],
)
def list_experience(
    database: Session = Depends(get_db),
) -> list[Experience]:
    statement = (
        select(Experience)
        .where(
            Experience.candidate_profile_id == 1
        )
        .order_by(
            Experience.start_date.desc(),
            Experience.id.desc(),
        )
    )

    return list(
        database.scalars(statement).all()
    )


@router.post(
    "",
    response_model=ExperienceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_experience(
    payload: ExperienceCreate,
    database: Session = Depends(get_db),
) -> Experience:
    profile = database.get(
        CandidateProfile,
        1,
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Create the candidate profile before "
                "adding work experience."
            ),
        )

    experience = Experience(
        candidate_profile_id=1,
        **payload.model_dump(),
    )

    database.add(experience)
    database.commit()
    database.refresh(experience)

    return experience


@router.put(
    "/{experience_id}",
    response_model=ExperienceResponse,
)
def update_experience(
    experience_id: int,
    payload: ExperienceUpdate,
    database: Session = Depends(get_db),
) -> Experience:
    experience = get_experience_or_404(
        experience_id,
        database,
    )

    for field_name, field_value in (
        payload.model_dump().items()
    ):
        setattr(
            experience,
            field_name,
            field_value,
        )

    database.commit()
    database.refresh(experience)

    return experience


@router.delete(
    "/{experience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_experience(
    experience_id: int,
    database: Session = Depends(get_db),
) -> Response:
    experience = get_experience_or_404(
        experience_id,
        database,
    )

    database.delete(experience)
    database.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )