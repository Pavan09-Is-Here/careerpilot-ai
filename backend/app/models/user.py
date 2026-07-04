from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """A login account.

    Each account owns exactly one candidate profile and all data hanging
    off it. Passwords are stored only as a PBKDF2-HMAC-SHA256 derived
    hash plus its salt — never the password itself. The iteration count
    is stored per account so it can be raised over time without
    invalidating existing hashes.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    username: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
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

    # Email verification (non-blocking). Only the SHA-256 hash of the
    # verification token is stored — never the raw token.
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    email_verification_token_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    # Password reset. Only the SHA-256 hash of the reset token is stored,
    # alongside its expiry. A cleared hash means no pending reset.
    password_reset_token_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    password_reset_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
