from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_settings
from app.core.database import get_db
from app.core.security import RateLimiter
from app.models.auth import AuthSession
from app.schemas.auth import (
    AuthStatusResponse,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    SessionResponse,
    SetupRequest,
)
from app.services.auth import (
    AuthServiceError,
    change_password,
    is_configured,
    login,
    revoke_session,
    setup_password,
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
    return {"configured": is_configured(database)}


@router.post(
    "/setup",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def setup(
    payload: SetupRequest,
    database: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        setup_password(payload.password, database, get_settings())
    except AuthServiceError as exc:
        raise_auth_http_error(exc)
    return {"message": "Authentication configured."}


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
        token, session = login(payload.password, database, get_settings())
    except AuthServiceError as exc:
        raise_auth_http_error(exc)

    return LoginResponse(token=token, expires_at=session.expires_at)


@router.get("/session", response_model=SessionResponse)
def current_session(
    session: AuthSession = Depends(get_current_session),
) -> AuthSession:
    return session


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
    _session: AuthSession = Depends(get_current_session),
    database: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        change_password(
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
