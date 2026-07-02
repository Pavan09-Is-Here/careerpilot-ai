from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


NOTIFICATION_CATEGORIES = (
    "application_prepared",
    "application_submitted",
    "manual_action_required",
    "new_matching_jobs",
)

NOTIFICATION_CHANNELS = ("email",)

NOTIFICATION_STATUSES = (
    "pending",
    "sent",
    "failed",
    "suppressed",
)


class Notification(Base):
    """An outbound notification (currently email).

    Notifications are recorded here first. Actual delivery is performed
    by a configured notifier; when no email transport is configured the
    message stays 'pending' (recorded but not sent) rather than being
    lost. No candidate data is fabricated — bodies are built from real
    events.
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    channel: Mapped[str] = mapped_column(
        String(20),
        default="email",
        nullable=False,
    )

    recipient: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    subject: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )

    related_job_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "normalized_jobs.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    dedupe_key: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        unique=True,
    )

    error: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "category IN ("
            + ", ".join(
                f"'{value}'" for value in NOTIFICATION_CATEGORIES
            )
            + ")",
            name="ck_notifications_category",
        ),
        CheckConstraint(
            "status IN ("
            + ", ".join(f"'{value}'" for value in NOTIFICATION_STATUSES)
            + ")",
            name="ck_notifications_status",
        ),
    )
