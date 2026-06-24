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
from app.models.candidate_profile import (
    CandidateProfile,
)
from app.models.education import Education
from app.schemas.education import (
    EducationCreate,
    EducationResponse,
    EducationUpdate,
)


router = APIRouter(
    prefix="/education",
    tags=["Education"],
)


def get_education_or_404(
    education_id: int,
    database: Session,
) -> Education:
    education = database.get(
        Education,
        education_id,
    )

    if (
        education is None
        or education.candidate_profile_id != 1
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record was not found.",
        )

    return education


@router.get(
    "",
    response_model=list[EducationResponse],
)
def list_education(
    database: Session = Depends(get_db),
) -> list[Education]:
    statement = (
        select(Education)
        .where(
            Education.candidate_profile_id == 1
        )
        .order_by(
            Education.start_date.desc(),
            Education.id.desc(),
        )
    )

    return list(
        database.scalars(statement).all()
    )


@router.post(
    "",
    response_model=EducationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_education(
    payload: EducationCreate,
    database: Session = Depends(get_db),
) -> Education:
    profile = database.get(
        CandidateProfile,
        1,
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Create the candidate profile "
                "before adding education."
            ),
        )

    education = Education(
        candidate_profile_id=1,
        **payload.model_dump(),
    )

    database.add(education)
    database.commit()
    database.refresh(education)

    return education


@router.put(
    "/{education_id}",
    response_model=EducationResponse,
)
def update_education(
    education_id: int,
    payload: EducationUpdate,
    database: Session = Depends(get_db),
) -> Education:
    education = get_education_or_404(
        education_id,
        database,
    )

    for field_name, field_value in (
        payload.model_dump().items()
    ):
        setattr(
            education,
            field_name,
            field_value,
        )

    database.commit()
    database.refresh(education)

    return education


@router.delete(
    "/{education_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_education(
    education_id: int,
    database: Session = Depends(get_db),
) -> Response:
    education = get_education_or_404(
        education_id,
        database,
    )

    database.delete(education)
    database.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )