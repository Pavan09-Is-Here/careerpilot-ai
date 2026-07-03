from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile_id
from app.core.database import get_db
from app.schemas.application_answer import (
    ApplicationAnswerCategory,
    ApplicationAnswerCreate,
    ApplicationAnswerResponse,
    ApplicationAnswerUpdate,
)
from app.services.application_answer import (
    ApplicationAnswerServiceError,
    create_application_answer,
    delete_application_answer,
    get_answer_or_404,
    list_application_answers,
    update_application_answer,
)


router = APIRouter(
    prefix="/application-answers",
    tags=["Application Answers"],
)


def raise_answer_http_error(
    error: ApplicationAnswerServiceError,
) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail=error.safe_message,
    ) from error


@router.get(
    "",
    response_model=list[ApplicationAnswerResponse],
)
def list_answers(
    category: ApplicationAnswerCategory | None = Query(default=None),
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> list[object]:
    return list(
        list_application_answers(database, profile_id, category=category)
    )


@router.get(
    "/{answer_id}",
    response_model=ApplicationAnswerResponse,
)
def get_answer(
    answer_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> object:
    try:
        return get_answer_or_404(answer_id, database, profile_id)
    except ApplicationAnswerServiceError as exc:
        raise_answer_http_error(exc)


@router.post(
    "",
    response_model=ApplicationAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_answer(
    payload: ApplicationAnswerCreate,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> object:
    try:
        return create_application_answer(payload, database, profile_id)
    except ApplicationAnswerServiceError as exc:
        raise_answer_http_error(exc)


@router.put(
    "/{answer_id}",
    response_model=ApplicationAnswerResponse,
)
def update_answer(
    answer_id: int,
    payload: ApplicationAnswerUpdate,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> object:
    try:
        return update_application_answer(
            answer_id,
            payload,
            database,
            profile_id,
        )
    except ApplicationAnswerServiceError as exc:
        raise_answer_http_error(exc)


@router.delete(
    "/{answer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_answer(
    answer_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> Response:
    try:
        delete_application_answer(answer_id, database, profile_id)
    except ApplicationAnswerServiceError as exc:
        raise_answer_http_error(exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
