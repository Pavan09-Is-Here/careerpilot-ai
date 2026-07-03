from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_current_user, get_settings
from app.core.database import get_db
from app.core.security import RateLimiter
from app.models.auth import AuthSession
from app.models.user import User
from app.schemas.auth import (
    AuthStatusResponse,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RegisterRequest,
    SessionResponse,
)
from app.services.auth import (
    AuthServiceError,
    change_password,
    create_account,
    login,
    revoke_session,
    user_count,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


_settings = get_settings()
login_rate_limiter = RateLimiter(
    _settings.login_rate_limit_max_attempts,
    _settings.login_rate_limit_window_seconds,
)


def raise_auth_http_error(error: AuthServiceError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail=error.safe_message,
    ) from error


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(
    database: Session = Depends(get_db),
) -> dict[str, object]:
    return {
        "configured": user_count(database) > 0,
        "registration_open": True,
    }


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    request: Request,
    database: Session = Depends(get_db),
) -> LoginResponse:
    client = request.client.host if request.client else "unknown"
    allowed, retry_after = login_rate_limiter.check(f"register:{client}")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        user, _profile = create_account(
            payload.username,
            payload.password,
            payload.full_name,
            payload.email,
            database,
            get_settings(),
        )
        token, session, _user = login(
            payload.username,
            payload.password,
            database,
            get_settings(),
        )
    except AuthServiceError as exc:
        raise_auth_http_error(exc)

    return LoginResponse(
        token=token,
        expires_at=session.expires_at,
        username=user.username,
    )


@router.post("/login", response_model=LoginResponse)
def login_route(
    payload: LoginRequest,
    request: Request,
    database: Session = Depends(get_db),
) -> LoginResponse:
    client = request.client.host if request.client else "unknown"
    allowed, retry_after = login_rate_limiter.check(f"login:{client}")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        token, session, user = login(
            payload.username,
            payload.password,
            database,
            get_settings(),
        )
    except AuthServiceError as exc:
        raise_auth_http_error(exc)

    return LoginResponse(
        token=token,
        expires_at=session.expires_at,
        username=user.username,
    )


@router.get("/session", response_model=SessionResponse)
def current_session(
    session: AuthSession = Depends(get_current_session),
    user: User = Depends(get_current_user),
) -> SessionResponse:
    return SessionResponse(
        username=user.username,
        created_at=session.created_at,
        expires_at=session.expires_at,
        last_used_at=session.last_used_at,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    session: AuthSession = Depends(get_current_session),
    database: Session = Depends(get_db),
) -> dict[str, str]:
    revoke_session(session, database)
    return {"message": "Logged out."}


@router.post("/change-password", response_model=MessageResponse)
def change_password_route(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        change_password(
            user,
            payload.current_password,
            payload.new_password,
            database,
            get_settings(),
        )
    except AuthServiceError as exc:
        raise_auth_http_error(exc)
    return {
        "message": (
            "Password changed. All sessions have been signed out."
        )
    }
