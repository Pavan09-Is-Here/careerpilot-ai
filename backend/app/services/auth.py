"""Account authentication and session management (Phase 15).

Each login account (``users`` row) owns exactly one candidate profile
and all data hanging off it. Passwords are stored only as
PBKDF2-HMAC-SHA256 hashes (standard library, no third-party crypto
dependency). Session tokens are opaque random strings; only their
SHA-256 hash is persisted, so a database read cannot recover a live
token. Verification is constant-time. No password or token is ever
logged.
"""

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.auth import AuthSession
from app.models.candidate_profile import CandidateProfile
from app.models.user import User


MIN_PASSWORD_LENGTH = 8
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 150
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
PBKDF2_ALGORITHM = "pbkdf2_sha256"


class AuthServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def _derive(password: str, salt_hex: str, iterations: int) -> str:
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        iterations,
    )
    return derived.hex()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token() -> str:
    """Generate an opaque URL-safe token for email/reset flows."""
    return secrets.token_urlsafe(32)


PASSWORD_RESET_TTL = timedelta(hours=1)


def normalize_username(username: str) -> str:
    return username.strip().lower()


def validate_password_strength(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthServiceError(
            "Password must be at least "
            f"{MIN_PASSWORD_LENGTH} characters long.",
        )


def validate_username(username: str) -> None:
    if not (MIN_USERNAME_LENGTH <= len(username) <= MAX_USERNAME_LENGTH):
        raise AuthServiceError(
            "Username must be between "
            f"{MIN_USERNAME_LENGTH} and {MAX_USERNAME_LENGTH} characters.",
        )
    if not USERNAME_PATTERN.match(username):
        raise AuthServiceError(
            "Username may only contain letters, numbers, and the "
            "characters . _ -",
        )


def user_count(database: Session) -> int:
    return int(database.scalar(select(func.count(User.id))) or 0)


def get_user_by_username(username: str, database: Session) -> User | None:
    return database.scalar(
        select(User).where(User.username == normalize_username(username))
    )


def _set_user_password(
    user: User,
    password: str,
    settings: Settings,
) -> None:
    salt_hex = secrets.token_bytes(16).hex()
    iterations = settings.auth_pbkdf2_iterations
    user.algorithm = PBKDF2_ALGORITHM
    user.salt = salt_hex
    user.iterations = iterations
    user.password_hash = _derive(password, salt_hex, iterations)
    user.updated_at = current_utc_time()


def create_account(
    username: str,
    password: str,
    full_name: str,
    email: str,
    database: Session,
    settings: Settings,
) -> tuple[User, CandidateProfile, str]:
    """Create a login account and its owned candidate profile.

    The profile is created with only the details supplied at
    registration; no candidate facts are invented. Returns the created
    user, its profile, and the raw email-verification token (the caller
    emails it; only its hash is persisted).
    """

    normalized = normalize_username(username)
    validate_username(normalized)
    validate_password_strength(password)

    if not full_name.strip():
        raise AuthServiceError("Full name is required.")
    if not email.strip():
        raise AuthServiceError("Email is required.")

    if get_user_by_username(normalized, database) is not None:
        raise AuthServiceError(
            "That username is already taken.",
            status_code=409,
        )

    now = current_utc_time()
    verification_token = generate_token()
    user = User(
        username=normalized,
        created_at=now,
        updated_at=now,
        # placeholder values overwritten immediately below
        algorithm=PBKDF2_ALGORITHM,
        password_hash="",
        salt="",
        iterations=settings.auth_pbkdf2_iterations,
        email_verified=False,
        email_verification_token_hash=hash_token(verification_token),
    )
    _set_user_password(user, password, settings)
    database.add(user)
    database.flush()

    profile = CandidateProfile(
        user_id=user.id,
        full_name=full_name.strip(),
        email=email.strip(),
        created_at=now,
        updated_at=now,
    )
    database.add(profile)
    database.commit()
    database.refresh(user)
    database.refresh(profile)
    return user, profile, verification_token


def verify_password(user: User, password: str) -> bool:
    candidate = _derive(password, user.salt, user.iterations)
    return secrets.compare_digest(candidate, user.password_hash)


def authenticate(
    username: str,
    password: str,
    database: Session,
) -> User:
    user = get_user_by_username(username, database)
    if user is None:
        # Dummy derivation to keep timing broadly similar whether or not
        # the username exists.
        _derive(password, "00" * 16, 100_000)
        raise AuthServiceError("Invalid credentials.", status_code=401)
    if not verify_password(user, password):
        raise AuthServiceError("Invalid credentials.", status_code=401)
    return user


def create_session(
    user: User,
    database: Session,
    settings: Settings,
) -> tuple[str, AuthSession]:
    token = secrets.token_urlsafe(32)
    now = current_utc_time()
    session = AuthSession(
        user_id=user.id,
        token_hash=hash_token(token),
        created_at=now,
        expires_at=now + timedelta(minutes=settings.session_ttl_minutes),
        last_used_at=now,
        revoked_at=None,
    )
    database.add(session)
    database.commit()
    database.refresh(session)
    return token, session


def login(
    username: str,
    password: str,
    database: Session,
    settings: Settings,
) -> tuple[str, AuthSession, User]:
    user = authenticate(username, password, database)
    token, session = create_session(user, database, settings)
    return token, session, user


def _is_active(session: AuthSession, now: datetime) -> bool:
    if session.revoked_at is not None:
        return False
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > now


def validate_token(
    token: str,
    database: Session,
) -> AuthSession:
    now = current_utc_time()
    session = database.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == hash_token(token)
        )
    )
    if session is None or not _is_active(session, now):
        raise AuthServiceError(
            "Not authenticated.",
            status_code=401,
        )
    session.last_used_at = now
    database.commit()
    database.refresh(session)
    return session


def get_user_for_session(
    session: AuthSession,
    database: Session,
) -> User:
    user = database.get(User, session.user_id)
    if user is None:
        raise AuthServiceError("Not authenticated.", status_code=401)
    return user


def get_profile_for_user(
    user: User,
    database: Session,
) -> CandidateProfile:
    profile = database.scalar(
        select(CandidateProfile).where(
            CandidateProfile.user_id == user.id
        )
    )
    if profile is None:
        raise AuthServiceError(
            "No candidate profile for this account.",
            status_code=404,
        )
    return profile


def change_password(
    user: User,
    current_password: str,
    new_password: str,
    database: Session,
    settings: Settings,
) -> None:
    if not verify_password(user, current_password):
        raise AuthServiceError(
            "Current password is incorrect.",
            status_code=401,
        )
    validate_password_strength(new_password)
    _set_user_password(user, new_password, settings)
    database.add(user)
    database.commit()
    # Changing the password invalidates all of this account's sessions.
    revoke_user_sessions(user.id, database)


def revoke_session(session: AuthSession, database: Session) -> None:
    if session.revoked_at is None:
        session.revoked_at = current_utc_time()
        database.commit()


def revoke_user_sessions(user_id: int, database: Session) -> int:
    now = current_utc_time()
    sessions = list(
        database.scalars(
            select(AuthSession).where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
        ).all()
    )
    for session in sessions:
        session.revoked_at = now
    database.commit()
    return len(sessions)


# --- Email verification --------------------------------------------------


def verify_email(token: str, database: Session) -> User:
    """Confirm an account email from its verification token.

    On success sets ``email_verified`` and clears the stored token hash.
    An invalid, missing, or already-used token raises a 400.
    """
    if not token:
        raise AuthServiceError("Invalid or expired verification link.")
    user = database.scalar(
        select(User).where(
            User.email_verification_token_hash == hash_token(token)
        )
    )
    if user is None:
        raise AuthServiceError("Invalid or expired verification link.")
    user.email_verified = True
    user.email_verification_token_hash = None
    user.updated_at = current_utc_time()
    database.add(user)
    database.commit()
    database.refresh(user)
    return user


def regenerate_verification_token(user: User, database: Session) -> str:
    """Issue a fresh verification token for ``user`` and store its hash.

    Returns the raw token so the caller can email it; only the hash is
    persisted.
    """
    token = generate_token()
    user.email_verification_token_hash = hash_token(token)
    user.updated_at = current_utc_time()
    database.add(user)
    database.commit()
    return token


# --- Password reset ------------------------------------------------------


def get_user_by_profile_email(
    email: str,
    database: Session,
) -> User | None:
    """Find the account whose candidate profile has ``email`` (case-insensitive)."""
    normalized = email.strip().lower()
    if not normalized:
        return None
    return database.scalar(
        select(User)
        .join(CandidateProfile, CandidateProfile.user_id == User.id)
        .where(func.lower(CandidateProfile.email) == normalized)
    )


def start_password_reset(user: User, database: Session) -> str:
    """Create a password-reset token for ``user`` and store its hash + expiry.

    Returns the raw token so the caller can email it; only the hash and
    expiry are persisted.
    """
    token = generate_token()
    now = current_utc_time()
    user.password_reset_token_hash = hash_token(token)
    user.password_reset_expires_at = now + PASSWORD_RESET_TTL
    user.updated_at = now
    database.add(user)
    database.commit()
    return token


def reset_password(
    token: str,
    new_password: str,
    database: Session,
    settings: Settings,
) -> User:
    """Set a new password from a valid, unexpired reset token.

    Validates password strength, sets the new password, clears the reset
    token, and revokes all of the account's sessions. Invalid or expired
    tokens raise a 400.
    """
    if not token:
        raise AuthServiceError("Invalid or expired reset link.")
    now = current_utc_time()
    user = database.scalar(
        select(User).where(
            User.password_reset_token_hash == hash_token(token)
        )
    )
    if user is None or user.password_reset_expires_at is None:
        raise AuthServiceError("Invalid or expired reset link.")
    expires_at = user.password_reset_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise AuthServiceError("Invalid or expired reset link.")

    validate_password_strength(new_password)
    _set_user_password(user, new_password, settings)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    database.add(user)
    database.commit()
    # A password reset invalidates all of this account's sessions.
    revoke_user_sessions(user.id, database)
    database.refresh(user)
    return user


def revoke_all_sessions(database: Session) -> int:
    now = current_utc_time()
    sessions = list(
        database.scalars(
            select(AuthSession).where(AuthSession.revoked_at.is_(None))
        ).all()
    )
    for session in sessions:
        session.revoked_at = now
    database.commit()
    return len(sessions)
