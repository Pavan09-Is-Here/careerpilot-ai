from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
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
