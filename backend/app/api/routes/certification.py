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
from app.models.certification import Certification
from app.schemas.certification import (
    CertificationCreate,
    CertificationResponse,
    CertificationUpdate,
)


router = APIRouter(
    prefix="/certifications",
    tags=["Certifications"],
)


def get_certification_or_404(
    certification_id: int,
    database: Session,
) -> Certification:
    certification = database.get(
        Certification,
        certification_id,
    )

    if (
        certification is None
        or certification.candidate_profile_id != 1
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Certification record was not found."
            ),
        )

    return certification


@router.get(
    "",
    response_model=list[CertificationResponse],
)
def list_certifications(
    database: Session = Depends(get_db),
) -> list[Certification]:
    statement = (
        select(Certification)
        .where(
            Certification.candidate_profile_id == 1
        )
        .order_by(
            Certification.issue_date.desc(),
            Certification.id.desc(),
        )
    )

    return list(
        database.scalars(statement).all()
    )


@router.post(
    "",
    response_model=CertificationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_certification(
    payload: CertificationCreate,
    database: Session = Depends(get_db),
) -> Certification:
    profile = database.get(
        CandidateProfile,
        1,
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Create the candidate profile "
                "before adding certifications."
            ),
        )

    certification = Certification(
        candidate_profile_id=1,
        **payload.model_dump(),
    )

    database.add(certification)
    database.commit()
    database.refresh(certification)

    return certification


@router.put(
    "/{certification_id}",
    response_model=CertificationResponse,
)
def update_certification(
    certification_id: int,
    payload: CertificationUpdate,
    database: Session = Depends(get_db),
) -> Certification:
    certification = get_certification_or_404(
        certification_id,
        database,
    )

    for field_name, field_value in (
        payload.model_dump().items()
    ):
        setattr(
            certification,
            field_name,
            field_value,
        )

    database.commit()
    database.refresh(certification)

    return certification


@router.delete(
    "/{certification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_certification(
    certification_id: int,
    database: Session = Depends(get_db),
) -> Response:
    certification = get_certification_or_404(
        certification_id,
        database,
    )

    database.delete(certification)
    database.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )