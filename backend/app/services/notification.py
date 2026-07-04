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


class NotificationServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def candidate_recipient(
    database: Session,
    candidate_profile_id: int,
) -> str | None:
    profile = database.get(CandidateProfile, candidate_profile_id)
    if profile is None or not profile.email:
        return None
    return profile.email


def create_notification(
    database: Session,
    *,
    candidate_profile_id: int,
    category: str,
    subject: str,
    body: str,
    recipient: str | None = None,
    related_job_id: int | None = None,
    dedupe_key: str | None = None,
) -> Notification | None:
    """Record a notification. Returns None if a duplicate (dedupe_key)
    already exists or no recipient is available."""
    to_address = recipient or candidate_recipient(
        database,
        candidate_profile_id,
    )
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
        candidate_profile_id=candidate_profile_id,
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


def _send_email(
    recipient: str,
    subject: str,
    body: str,
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
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)


def send_email_best_effort(
    recipient: str,
    subject: str,
    body: str,
    settings: Settings,
) -> bool:
    """Best-effort email send used for transactional auth emails.

    Returns True if the message was handed to the SMTP transport, False
    if SMTP is not configured or sending failed. Never raises, so callers
    (e.g. registration) stay non-blocking: an email failure must not fail
    the request. No secrets are logged.
    """
    if not recipient or not smtp_configured(settings):
        return False
    try:
        _send_email(recipient, subject, body, settings)
        return True
    except Exception:  # noqa: BLE001 - best effort, never propagate
        return False


def _send_via_smtp(
    notification: Notification,
    settings: Settings,
) -> None:
    _send_email(
        notification.recipient,
        notification.subject,
        notification.body,
        settings,
    )


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
    candidate_profile_id: int,
    category: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, object]:
    filters = [
        Notification.candidate_profile_id == candidate_profile_id
    ]
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
    candidate_profile_id: int,
) -> Notification:
    notification = database.get(Notification, notification_id)
    if (
        notification is None
        or notification.candidate_profile_id != candidate_profile_id
    ):
        raise NotificationServiceError(
            "Notification was not found.",
            status_code=404,
        )
    return notification
