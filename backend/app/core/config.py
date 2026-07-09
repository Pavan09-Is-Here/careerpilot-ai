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

    # Base URL of the frontend, used to build links in verification and
    # password-reset emails (e.g. "https://app.example.com"). When unset
    # it falls back to the first configured CORS origin, then to the local
    # development origin. See ``resolved_frontend_base_url``.
    frontend_base_url: str | None = None

    # Auto-apply pipeline daily bound on how many jobs to prepare.
    auto_apply_target_recency_hours: int = 168

    # Aggregator provider credentials (Phase 17). Free keys, supplied
    # via the environment only — never stored in the database, never
    # logged, never echoed in API responses. Without them the Adzuna
    # and Reed connectors stay inert with a clear message.
    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None
    reed_api_key: str | None = None

    # Deployment / infrastructure (Phase 14).
    # Deployment tier: "development", "staging", or "production".
    environment: str = "development"
    # Extra allowed CORS origins (comma-separated), e.g. the deployed
    # frontend URL. Local development origins are always allowed.
    cors_origins: str = ""
    # Optional regex matching allowed origins. Useful for hosts that
    # issue rotating per-deployment URLs (e.g. Vercel preview domains).
    # Example: https://.*\.vercel\.app
    cors_origin_regex: str | None = None
    # Full SQLAlchemy database URL. When unset, the local SQLite
    # development database is used. In production set this to a
    # PostgreSQL URL, e.g. postgresql+psycopg://user:pass@host/db.
    database_url: str | None = None
    # Error reporting. Sentry is initialised only when a DSN is set;
    # otherwise it stays inert. Secrets belong in the environment.
    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.0
    # Object storage for uploaded documents and generated CVs.
    # "local" uses the filesystem paths above; "s3" uses the S3
    # settings below (requires boto3 to be installed).
    storage_backend: str = "local"
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_prefix: str = ""
    s3_endpoint_url: str | None = None

    @property
    def resolved_frontend_base_url(self) -> str:
        """The base URL used to build links in outgoing emails.

        Uses ``frontend_base_url`` when set, otherwise the first entry of
        ``cors_origins``, otherwise the local development origin. The
        trailing slash is stripped so callers can append ``/auth/...``.
        """
        if self.frontend_base_url:
            base = self.frontend_base_url
        else:
            first_origin = next(
                (
                    origin.strip()
                    for origin in self.cors_origins.split(",")
                    if origin.strip()
                ),
                "",
            )
            base = first_origin or "http://localhost:3000"
        return base.rstrip("/")
