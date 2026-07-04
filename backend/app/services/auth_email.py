"""Transactional auth emails (verification + password reset).

These helpers build and send the two account emails using the shared
SMTP sender in ``app.services.notification``. Sending is best-effort: if
SMTP is not configured or delivery fails the helper returns silently, so
registration and forgot-password stay non-blocking. Only the raw token
travels in the emailed link; the database stores only its SHA-256 hash.
No secrets are stored in source.
"""

from __future__ import annotations

from app.core.config import Settings
from app.services.notification import send_email_best_effort


def _verify_link(base_url: str, token: str) -> str:
    return f"{base_url}/auth/verify?token={token}"


def _reset_link(base_url: str, token: str) -> str:
    return f"{base_url}/auth/reset?token={token}"


def send_verification_email(
    recipient: str,
    token: str,
    settings: Settings,
) -> bool:
    """Send the email-verification link. Best effort; never raises."""
    link = _verify_link(settings.resolved_frontend_base_url, token)
    subject = "Verify your CareerPilot email address"
    body = (
        "Welcome to CareerPilot AI.\n\n"
        "Please confirm your email address by opening the link below:\n\n"
        f"{link}\n\n"
        "If you did not create this account you can ignore this email."
    )
    return send_email_best_effort(recipient, subject, body, settings)


def send_password_reset_email(
    recipient: str,
    token: str,
    settings: Settings,
) -> bool:
    """Send the password-reset link. Best effort; never raises."""
    link = _reset_link(settings.resolved_frontend_base_url, token)
    subject = "Reset your CareerPilot password"
    body = (
        "We received a request to reset your CareerPilot password.\n\n"
        "Open the link below to choose a new password. It expires in one "
        "hour:\n\n"
        f"{link}\n\n"
        "If you did not request this, you can safely ignore this email; "
        "your password will not change."
    )
    return send_email_best_effort(recipient, subject, body, settings)
