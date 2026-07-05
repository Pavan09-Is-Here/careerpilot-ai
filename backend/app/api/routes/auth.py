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
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    SessionResponse,
    VerifyEmailRequest,
)
from app.services.auth import (
    AuthServiceError,
    change_password,
    create_account,
    get_profile_for_user,
    get_user_by_profile_email,
    login,
    regenerate_verification_token,
    reset_password,
    revoke_session,
    start_password_reset,
    user_count,
    verify_email,
)
from app.services.auth_email import (
    send_password_reset_email,
    send_verification_email,
)
from app.services.notification import send_test_email


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

    settings = get_settings()
    try:
        user, profile, verification_token = create_account(
            payload.username,
            payload.password,
            payload.full_name,
            payload.email,
            database,
            settings,
        )
        token, session, _user = login(
            payload.username,
            payload.password,
            database,
            settings,
        )
    except AuthServiceError as exc:
        raise_auth_http_error(exc)

    # Non-blocking: registration succeeds regardless of email delivery.
    send_verification_email(profile.email, verification_token, settings)

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
    database: Session = Depends(get_db),
) -> SessionResponse:
    email: str | None = None
    try:
        email = get_profile_for_user(user, database).email
    except AuthServiceError:
        email = None
    return SessionResponse(
        username=user.username,
        email=email,
        email_verified=user.email_verified,
        created_at=session.created_at,
        expires_at=session.expires_at,
        last_used_at=session.last_used_at,
    )


@router.post("/verify-email", response_model=MessageResponse)
def verify_email_route(
    payload: VerifyEmailRequest,
    database: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        verify_email(payload.token, database)
    except AuthServiceError as exc:
        raise_auth_http_error(exc)
    return {"message": "Your email address has been verified."}


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification_route(
    user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> dict[str, str]:
    settings = get_settings()
    if user.email_verified:
        return {"message": "Your email address is already verified."}
    token = regenerate_verification_token(user, database)
    try:
        email = get_profile_for_user(user, database).email
    except AuthServiceError:
        email = ""
    if email:
        send_verification_email(email, token, settings)
    return {"message": "A new verification email has been sent."}


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password_route(
    payload: ForgotPasswordRequest,
    request: Request,
    database: Session = Depends(get_db),
) -> dict[str, str]:
    client = request.client.host if request.client else "unknown"
    allowed, retry_after = login_rate_limiter.check(
        f"forgot-password:{client}"
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    settings = get_settings()
    user = get_user_by_profile_email(payload.email, database)
    if user is not None:
        token = start_password_reset(user, database)
        send_password_reset_email(payload.email, token, settings)
    # Always return the same message so account existence is not revealed.
    return {
        "message": (
            "If that email is registered, a reset link has been sent."
        )
    }


@router.post("/reset-password", response_model=MessageResponse)
def reset_password_route(
    payload: ResetPasswordRequest,
    database: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        reset_password(
            payload.token,
            payload.new_password,
            database,
            get_settings(),
        )
    except AuthServiceError as exc:
        raise_auth_http_error(exc)
    return {
        "message": (
            "Your password has been reset. All sessions have been "
            "signed out. Please sign in with your new password."
        )
    }


@router.post("/logout", response_model=MessageResponse)
def logout(
    session: AuthSession = Depends(get_current_session),
    database: Session = Depends(get_db),
) -> dict[str, str]:
    revoke_session(session, database)
    return {"message": "Logged out."}


@router.post("/test-email")
def test_email_route(
    user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> dict[str, object]:
    settings = get_settings()
    try:
        email = get_profile_for_user(user, database).email
    except AuthServiceError:
        email = ""
    ok, detail = send_test_email(email, settings)
    return {"ok": ok, "detail": detail, "recipient": email}


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
