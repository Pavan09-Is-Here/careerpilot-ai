from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile_id
from app.core.database import get_db
from app.models.candidate_profile import (
    CandidateProfile,
)
from app.models.skill import Skill
from app.schemas.skill import (
    SkillCreate,
    SkillResponse,
    SkillUpdate,
)


router = APIRouter(
    prefix="/skills",
    tags=["Skills"],
)


def get_skill_or_404(
    skill_id: int,
    database: Session,
    candidate_profile_id: int,
) -> Skill:
    skill = database.get(
        Skill,
        skill_id,
    )

    if (
        skill is None
        or skill.candidate_profile_id != candidate_profile_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill record was not found.",
        )

    return skill


def skill_name_exists(
    name: str,
    database: Session,
    candidate_profile_id: int,
    excluded_skill_id: int | None = None,
) -> bool:
    statement = select(Skill).where(
        Skill.candidate_profile_id == candidate_profile_id,
        func.lower(Skill.name)
        == name.strip().lower(),
    )

    if excluded_skill_id is not None:
        statement = statement.where(
            Skill.id != excluded_skill_id
        )

    return database.scalar(statement) is not None


@router.get(
    "",
    response_model=list[SkillResponse],
)
def list_skills(
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> list[Skill]:
    statement = (
        select(Skill)
        .where(
            Skill.candidate_profile_id == profile_id
        )
        .order_by(
            Skill.is_primary.desc(),
            Skill.verified.desc(),
            Skill.name.asc(),
        )
    )

    return list(
        database.scalars(statement).all()
    )


@router.post(
    "",
    response_model=SkillResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_skill(
    payload: SkillCreate,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> Skill:
    profile = database.get(
        CandidateProfile,
        profile_id,
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Create the candidate profile "
                "before adding skills."
            ),
        )

    if skill_name_exists(
        payload.name,
        database,
        profile_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A skill with this name "
                "already exists."
            ),
        )

    skill = Skill(
        candidate_profile_id=profile_id,
        **payload.model_dump(),
    )

    database.add(skill)
    database.commit()
    database.refresh(skill)

    return skill


@router.put(
    "/{skill_id}",
    response_model=SkillResponse,
)
def update_skill(
    skill_id: int,
    payload: SkillUpdate,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> Skill:
    skill = get_skill_or_404(
        skill_id,
        database,
        profile_id,
    )

    if skill_name_exists(
        payload.name,
        database,
        profile_id,
        excluded_skill_id=skill_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Another skill with this name "
                "already exists."
            ),
        )

    for field_name, field_value in (
        payload.model_dump().items()
    ):
        setattr(
            skill,
            field_name,
            field_value,
        )

    database.commit()
    database.refresh(skill)

    return skill


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_skill(
    skill_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> Response:
    skill = get_skill_or_404(
        skill_id,
        database,
        profile_id,
    )

    database.delete(skill)
    database.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )