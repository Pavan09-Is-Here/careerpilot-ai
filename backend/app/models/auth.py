from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class AuthCredential(Base):
    """Single-user login credential.

    Stores only a PBKDF2-HMAC-SHA256 derived hash and its salt — never
    the password itself. The iteration count is stored per credential
    so it can be raised over time without invalidating existing hashes.
    """

    __tablename__ = "auth_credentials"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    algorithm: Mapped[str] = mapped_column(
        String(50),
        default="pbkdf2_sha256",
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    salt: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    iterations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        onupdate=current_utc_time,
        nullable=False,
    )


class AuthSession(Base):
    """An opaque session. Only the SHA-256 hash of the token is stored.

    The raw token is returned to the client exactly once at login and
    never persisted, so a database read cannot recover a live token.
    Sessions expire and can be revoked (logout).
    """

    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
