from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class CVVersionArtifact(Base):
    __tablename__ = "cv_version_artifacts"
    __table_args__ = (
        CheckConstraint(
            "artifact_type IN ('docx', 'pdf')",
            name="ck_cv_version_artifacts_artifact_type",
        ),
        UniqueConstraint(
            "cv_version_id",
            "artifact_type",
            name="uq_cv_version_artifacts_version_type",
        ),
        Index(
            "ix_cv_version_artifacts_cv_version_id",
            "cv_version_id",
        ),
        Index(
            "ix_cv_version_artifacts_artifact_type",
            "artifact_type",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    cv_version_id: Mapped[int] = mapped_column(
        ForeignKey(
            "cv_versions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    artifact_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    safe_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
    )

    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    renderer_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    content_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )
