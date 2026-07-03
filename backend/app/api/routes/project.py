from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile_id
from app.core.database import get_db
from app.models.candidate_profile import (
    CandidateProfile,
)
from app.models.project import Project
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)


router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


def get_project_or_404(
    project_id: int,
    database: Session,
    candidate_profile_id: int,
) -> Project:
    project = database.get(
        Project,
        project_id,
    )

    if (
        project is None
        or project.candidate_profile_id != candidate_profile_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project record was not found.",
        )

    return project


@router.get(
    "",
    response_model=list[ProjectResponse],
)
def list_projects(
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> list[Project]:
    statement = (
        select(Project)
        .where(
            Project.candidate_profile_id == profile_id
        )
        .order_by(
            Project.start_date.desc(),
            Project.id.desc(),
        )
    )

    return list(
        database.scalars(statement).all()
    )


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    payload: ProjectCreate,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> Project:
    profile = database.get(
        CandidateProfile,
        profile_id,
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Create the candidate profile "
                "before adding projects."
            ),
        )

    project = Project(
        candidate_profile_id=profile_id,
        **payload.model_dump(),
    )

    database.add(project)
    database.commit()
    database.refresh(project)

    return project


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> Project:
    project = get_project_or_404(
        project_id,
        database,
        profile_id,
    )

    for field_name, field_value in (
        payload.model_dump().items()
    ):
        setattr(
            project,
            field_name,
            field_value,
        )

    database.commit()
    database.refresh(project)

    return project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_project(
    project_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> Response:
    project = get_project_or_404(
        project_id,
        database,
        profile_id,
    )

    database.delete(project)
    database.commit()

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )