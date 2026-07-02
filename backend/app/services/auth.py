"""Single-user authentication and session management (Phase 13).

Passwords are stored only as PBKDF2-HMAC-SHA256 hashes (standard
library, no third-party crypto dependency). Session tokens are opaque
random strings; only their SHA-256 hash is persisted, so a database
read cannot recover a live token. Verification is constant-time. No
password or token is ever logged.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.auth import AuthCredential, AuthSession


CREDENTIAL_ID = 1
MIN_PASSWORD_LENGTH = 8
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


def validate_password_strength(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthServiceError(
            "Password must be at least "
            f"{MIN_PASSWORD_LENGTH} characters long.",
        )


def is_configured(database: Session) -> bool:
    return database.get(AuthCredential, CREDENTIAL_ID) is not None


def set_password(
    password: str,
    database: Session,
    settings: Settings,
) -> AuthCredential:
    validate_password_strength(password)

    salt_hex = secrets.token_bytes(16).hex()
    iterations = settings.auth_pbkdf2_iterations
    password_hash = _derive(password, salt_hex, iterations)

    now = current_utc_time()
    credential = database.get(AuthCredential, CREDENTIAL_ID)
    if credential is None:
        credential = AuthCredential(
            id=CREDENTIAL_ID,
            algorithm=PBKDF2_ALGORITHM,
            password_hash=password_hash,
            salt=salt_hex,
            iterations=iterations,
            created_at=now,
            updated_at=now,
        )
        database.add(credential)
    else:
        credential.password_hash = password_hash
        credential.salt = salt_hex
        credential.iterations = iterations
        credential.updated_at = now

    database.commit()
    database.refresh(credential)
    return credential


def verify_password(password: str, database: Session) -> bool:
    credential = database.get(AuthCredential, CREDENTIAL_ID)
    if credential is None:
        # Perform a dummy derivation to keep timing broadly similar
        # whether or not a credential exists.
        _derive(password, "00" * 16, 100_000)
        return False

    candidate = _derive(
        password,
        credential.salt,
        credential.iterations,
    )
    return secrets.compare_digest(candidate, credential.password_hash)


def require_configured(database: Session) -> None:
    if not is_configured(database):
        raise AuthServiceError(
            "Authentication is not set up yet.",
            status_code=409,
        )


def setup_password(
    password: str,
    database: Session,
    settings: Settings,
) -> AuthCredential:
    if is_configured(database):
        raise AuthServiceError(
            "Authentication is already set up. Use change-password "
            "instead.",
            status_code=409,
        )
    return set_password(password, database, settings)


def change_password(
    current_password: str,
    new_password: str,
    database: Session,
    settings: Settings,
) -> None:
    require_configured(database)
    if not verify_password(current_password, database):
        raise AuthServiceError(
            "Current password is incorrect.",
            status_code=401,
        )
    validate_password_strength(new_password)
    set_password(new_password, database, settings)
    # Changing the password invalidates all existing sessions.
    revoke_all_sessions(database)


def create_session(
    database: Session,
    settings: Settings,
) -> tuple[str, AuthSession]:
    token = secrets.token_urlsafe(32)
    now = current_utc_time()
    session = AuthSession(
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
    password: str,
    database: Session,
    settings: Settings,
) -> tuple[str, AuthSession]:
    require_configured(database)
    if not verify_password(password, database):
        raise AuthServiceError(
            "Invalid credentials.",
            status_code=401,
        )
    return create_session(database, settings)


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


def revoke_session(session: AuthSession, database: Session) -> None:
    if session.revoked_at is None:
        session.revoked_at = current_utc_time()
        database.commit()


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
