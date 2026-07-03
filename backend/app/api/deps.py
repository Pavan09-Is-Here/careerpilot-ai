from functools import lru_cache

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_db
from app.models.auth import AuthSession
from app.models.candidate_profile import CandidateProfile
from app.models.user import User
from app.services.auth import (
    AuthServiceError,
    get_profile_for_user,
    get_user_for_session,
    validate_token,
)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_current_session(
    authorization: str | None = Header(default=None),
    database: Session = Depends(get_db),
) -> AuthSession:
    if not authorization or not authorization.lower().startswith(
        "bearer "
    ):
        raise HTTPException(
            status_code=401,
            detail="Not authenticated.",
        )

    token = authorization.split(" ", 1)[1].strip()
    try:
        return validate_token(token, database)
    except AuthServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.safe_message,
        ) from exc


def get_current_user(
    session: AuthSession = Depends(get_current_session),
    database: Session = Depends(get_db),
) -> User:
    try:
        return get_user_for_session(session, database)
    except AuthServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.safe_message,
        ) from exc


def get_current_profile(
    user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> CandidateProfile:
    try:
        return get_profile_for_user(user, database)
    except AuthServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.safe_message,
        ) from exc


def get_current_profile_id(
    profile: CandidateProfile = Depends(get_current_profile),
) -> int:
    return profile.id
