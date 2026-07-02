from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CAREERPILOT_",
    )

    document_storage_dir: Path = (
        Path(__file__).resolve().parents[2] / "data" / "documents"
    )
    generated_cv_storage_dir: Path = (
        Path(__file__).resolve().parents[2] / "data" / "generated-cvs"
    )
    max_document_upload_size_bytes: int = 10 * 1024 * 1024
    max_generated_cv_file_size_bytes: int = 5 * 1024 * 1024
    max_document_extracted_text_characters: int = 200_000
    default_job_source_retention_days: int = 30
    max_source_snapshot_payload_bytes: int = 10 * 1024 * 1024
    job_stale_after_days: int = 14

    # Authentication and security (Phase 13).
    auth_pbkdf2_iterations: int = 480_000
    session_ttl_minutes: int = 720
    login_rate_limit_max_attempts: int = 10
    login_rate_limit_window_seconds: int = 300

    # Notifications / email delivery. Real sending is enabled only when
    # an SMTP host is configured; otherwise notifications are recorded
    # but not sent. Secrets belong in the environment, never in source.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    notification_from_address: str = "careerpilot@localhost"

    # Auto-apply pipeline daily bound on how many jobs to prepare.
    auto_apply_target_recency_hours: int = 168
