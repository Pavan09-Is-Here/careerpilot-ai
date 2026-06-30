from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class CVVersion(Base):
    __tablename__ = "cv_versions"
    __table_args__ = (
        CheckConstraint(
            "version_type IN ('original', 'parsed', 'verified_master', "
            "'tailored')",
            name="ck_cv_versions_version_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'ready', 'archived', 'failed')",
            name="ck_cv_versions_status",
        ),
        UniqueConstraint(
            "source_document_id",
            name="uq_cv_versions_source_document_id",
        ),
        Index(
            "ix_cv_versions_candidate_type",
            "candidate_profile_id",
            "version_type",
        ),
        Index(
            "uq_cv_versions_generation_key",
            "candidate_profile_id",
            "parent_version_id",
            "version_type",
            "generation_key",
            unique=True,
        ),
        Index(
            "uq_cv_versions_primary_per_type",
            "candidate_profile_id",
            "version_type",
            unique=True,
            sqlite_where=text("is_primary = 1"),
            postgresql_where=text("is_primary = true"),
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey(
            "candidate_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "documents.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    parent_version_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "cv_versions.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    version_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    display_name: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    job_reference: Mapped[str | None] = mapped_column(
        String(250),
        nullable=True,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    storage_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    file_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    generation_key: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    generation_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    source_summary: Mapped[dict[str, object] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    generated_at: Mapped[datetime | None] = mapped_column(
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

    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
