"""Notifications outbox and delivery (email).

Every notification is recorded in the database first, then delivered by
the configured notifier. When no SMTP transport is configured the
message stays 'pending' — recorded but not sent — rather than being
lost or silently dropped. A `dedupe_key` prevents duplicate notices for
the same event (e.g. re-running the pipeline).

No secrets are stored in source; SMTP settings come from the
environment. No candidate data is fabricated — bodies are built from
real recorded events.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.candidate_profile import CandidateProfile
from app.models.notification import Notification


CANDIDATE_PROFILE_ID = 1


class NotificationServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def candidate_recipient(database: Session) -> str | None:
    profile = database.get(CandidateProfile, CANDIDATE_PROFILE_ID)
    if profile is None or not profile.email:
        return None
    return profile.email


def create_notification(
    database: Session,
    *,
    category: str,
    subject: str,
    body: str,
    recipient: str | None = None,
    related_job_id: int | None = None,
    dedupe_key: str | None = None,
) -> Notification | None:
    """Record a notification. Returns None if a duplicate (dedupe_key)
    already exists or no recipient is available."""
    to_address = recipient or candidate_recipient(database)
    if to_address is None:
        return None

    if dedupe_key is not None:
        existing = database.scalar(
            select(Notification).where(
                Notification.dedupe_key == dedupe_key
            )
        )
        if existing is not None:
            return existing

    notification = Notification(
        category=category,
        channel="email",
        recipient=to_address,
        subject=subject[:300],
        body=body,
        status="pending",
        related_job_id=related_job_id,
        dedupe_key=dedupe_key,
        created_at=current_utc_time(),
    )
    database.add(notification)
    try:
        database.commit()
        database.refresh(notification)
    except IntegrityError:
        database.rollback()
        return database.scalar(
            select(Notification).where(
                Notification.dedupe_key == dedupe_key
            )
        )
    return notification


# --- Delivery -------------------------------------------------------------


def smtp_configured(settings: Settings) -> bool:
    return bool(settings.smtp_host)


def _send_via_smtp(
    notification: Notification,
    settings: Settings,
) -> None:
    """Send one email over SMTP. Only called when SMTP is configured.

    Kept import-local so the notification module has no hard dependency
    on network libraries at import time.
    """
    import smtplib
    from email.message import EmailMessage

    message = EmailMessage()
    message["From"] = settings.notification_from_address
    message["To"] = notification.recipient
    message["Subject"] = notification.subject
    message.set_content(notification.body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)


def deliver_pending(
    database: Session,
    settings: Settings,
    *,
    limit: int = 50,
) -> dict[str, int]:
    """Attempt delivery of pending notifications.

    With no SMTP transport configured, pending notifications are left
    pending (reported as 'skipped') so nothing is lost.
    """
    pending = list(
        database.scalars(
            select(Notification)
            .where(Notification.status == "pending")
            .order_by(Notification.id.asc())
            .limit(limit)
        ).all()
    )

    if not smtp_configured(settings):
        return {
            "sent": 0,
            "failed": 0,
            "skipped": len(pending),
        }

    sent = 0
    failed = 0
    for notification in pending:
        try:
            _send_via_smtp(notification, settings)
            notification.status = "sent"
            notification.sent_at = current_utc_time()
            notification.error = None
            sent += 1
        except Exception as exc:  # noqa: BLE001 - recorded, not raised
            notification.status = "failed"
            notification.error = str(exc)[:1000]
            failed += 1
    database.commit()
    return {"sent": sent, "failed": failed, "skipped": 0}


def list_notifications(
    database: Session,
    *,
    category: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, object]:
    filters = []
    if category is not None:
        filters.append(Notification.category == category)
    if status is not None:
        filters.append(Notification.status == status)

    total = int(
        database.scalar(
            select(func.count())
            .select_from(Notification)
            .where(*filters)
        )
        or 0
    )
    items = list(
        database.scalars(
            select(Notification)
            .where(*filters)
            .order_by(Notification.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_notification_or_404(
    notification_id: int,
    database: Session,
) -> Notification:
    notification = database.get(Notification, notification_id)
    if notification is None:
        raise NotificationServiceError(
            "Notification was not found.",
            status_code=404,
        )
    return notification
