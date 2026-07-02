"""Greenhouse Job Board API adapter (Phase 4.3).

First approved provider adapter. Reads public, keyless Greenhouse
job-board data for explicitly approved, compliance-gated job sources
only. Never uses credentials, never bypasses the source policy gates,
and never infers job facts that the provider did not supply.
"""

from datetime import datetime, timezone
from hashlib import sha256
import html
import json
import re

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.ingestion import IngestionRun
from app.models.job import JobSource
from app.schemas.ingestion import (
    IngestionRunCompletion,
    IngestionRunCreate,
    SourceSnapshotCreate,
)
from app.schemas.job import JobLocationCreate, NormalizedJobCreate
from app.services.ingestion import (
    IngestionServiceError,
    complete_ingestion_run,
    create_ingestion_run,
    record_source_snapshot,
    start_ingestion_run,
)
from app.services.job_normalization import (
    JobNormalizationError,
    upsert_provider_jobs,
)


GREENHOUSE_PROVIDER_TYPE = "greenhouse"
GREENHOUSE_ACCESS_MODE = "api"
GREENHOUSE_BASE_URL_RE = re.compile(
    r"^https://boards-api\.greenhouse\.io/v1/boards/[a-z0-9][a-z0-9_-]{0,99}$"
)
APPROVED_REVIEW_STATUS = "approved_for_configured_use"
FETCH_TIMEOUT_SECONDS = 15.0
MAX_TITLE_CHARS = 250
MAX_DESCRIPTION_CHARS = 20_000
MAX_LOCATION_CHARS = 500
NORMALIZATION_VERSION = "greenhouse-adapter-1"
HTML_TAG_RE = re.compile(r"<[^>]+>")


class GreenhouseAdapterError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def get_settings() -> Settings:
    return Settings()


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def build_http_client() -> httpx.Client:
    return httpx.Client(
        timeout=FETCH_TIMEOUT_SECONDS,
        follow_redirects=False,
    )


def validate_greenhouse_source(source: JobSource) -> None:
    """Enforce every compliance gate before any server fetch."""
    if source.provider_type != GREENHOUSE_PROVIDER_TYPE:
        raise GreenhouseAdapterError(
            "Job source is not configured for the Greenhouse provider.",
        )

    if not source.enabled:
        raise GreenhouseAdapterError(
            "Job source is not enabled.",
        )

    if not source.allowlisted:
        raise GreenhouseAdapterError(
            "Job source is not allowlisted.",
        )

    if not source.server_fetch_allowed:
        raise GreenhouseAdapterError(
            "Server fetching is not allowed for this job source.",
        )

    if source.access_mode != GREENHOUSE_ACCESS_MODE:
        raise GreenhouseAdapterError(
            "Job source access mode does not permit API fetching.",
        )

    review_statuses = {
        source.terms_review_status,
        source.robots_review_status,
        source.commercial_use_review_status,
    }
    if review_statuses != {APPROVED_REVIEW_STATUS}:
        raise GreenhouseAdapterError(
            "Job source policy review is not approved for configured use.",
        )

    if not source.base_url or not GREENHOUSE_BASE_URL_RE.fullmatch(
        source.base_url
    ):
        raise GreenhouseAdapterError(
            "Job source base URL is not an approved Greenhouse board URL.",
        )


def strip_html_to_text(value: str) -> str:
    unescaped = html.unescape(value)
    without_tags = HTML_TAG_RE.sub(" ", unescaped)
    return " ".join(without_tags.split())


def truncate_text(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


def fetch_greenhouse_payload(
    source: JobSource,
    http_client: httpx.Client,
) -> bytes:
    fetch_url = f"{source.base_url}/jobs?content=true"

    try:
        response = http_client.get(fetch_url)
    except httpx.HTTPError as exc:
        raise GreenhouseAdapterError(
            "Provider request failed before a response was received.",
        ) from exc

    if response.status_code != 200:
        raise GreenhouseAdapterError(
            f"Provider returned HTTP status {response.status_code}.",
        )

    content_type = response.headers.get("content-type", "")
    if not content_type.lower().startswith("application/json"):
        raise GreenhouseAdapterError(
            "Provider response was not JSON.",
        )

    max_bytes = get_settings().max_source_snapshot_payload_bytes
    if len(response.content) > max_bytes:
        raise GreenhouseAdapterError(
            "Provider payload exceeded the permitted size.",
        )

    return response.content


def parse_greenhouse_jobs(payload: bytes) -> list[dict[str, object]]:
    try:
        document = json.loads(payload)
    except ValueError as exc:
        raise GreenhouseAdapterError(
            "Provider payload was not valid JSON.",
        ) from exc

    jobs = document.get("jobs") if isinstance(document, dict) else None
    if not isinstance(jobs, list):
        raise GreenhouseAdapterError(
            "Provider payload did not contain a job list.",
        )

    parsed: list[dict[str, object]] = []
    for job in jobs:
        if not isinstance(job, dict):
            raise GreenhouseAdapterError(
                "Provider payload contained an invalid job entry.",
            )

        job_id = job.get("id")
        absolute_url = job.get("absolute_url")
        title = job.get("title")
        if job_id is None or not absolute_url or not title:
            raise GreenhouseAdapterError(
                "Provider job entry was missing required fields.",
            )

        parsed.append(job)

    return parsed


def parse_source_updated_at(job: dict[str, object]) -> datetime | None:
    raw_value = job.get("updated_at")
    if not isinstance(raw_value, str):
        return None

    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


def build_job_create(
    source: JobSource,
    job: dict[str, object],
) -> tuple[NormalizedJobCreate, list[JobLocationCreate]]:
    title = truncate_text(
        strip_html_to_text(str(job["title"])),
        MAX_TITLE_CHARS,
    )

    description_text: str | None = None
    raw_content = job.get("content")
    if isinstance(raw_content, str) and raw_content.strip():
        description_text = truncate_text(
            strip_html_to_text(raw_content),
            MAX_DESCRIPTION_CHARS,
        )

    locations: list[JobLocationCreate] = []
    raw_location = job.get("location")
    if isinstance(raw_location, dict):
        location_name = raw_location.get("name")
        if isinstance(location_name, str) and location_name.strip():
            locations.append(
                JobLocationCreate(
                    raw_location_text=truncate_text(
                        location_name.strip(),
                        MAX_LOCATION_CHARS,
                    ),
                    source_provided=True,
                    normalization_version=NORMALIZATION_VERSION,
                )
            )

    job_hash = sha256(
        json.dumps(job, sort_keys=True, default=str).encode()
    ).hexdigest()

    data = NormalizedJobCreate(
        job_source_id=source.id,
        source_job_id=str(job["id"]),
        source_url=str(job["absolute_url"]),
        canonical_url=str(job["absolute_url"]),
        employer_name=source.display_name,
        title=title,
        description_text=description_text,
        source_updated_at=parse_source_updated_at(job),
        source_attribution_text=source.attribution_text,
        source_attribution_url=source.attribution_url,
        content_hash=job_hash,
        normalization_version=NORMALIZATION_VERSION,
    )
    return data, locations


def upsert_normalized_jobs(
    source: JobSource,
    jobs: list[dict[str, object]],
    database: Session,
) -> tuple[int, int]:
    """Normalize and upsert via the shared provider-agnostic path."""
    entries = [build_job_create(source, job) for job in jobs]

    try:
        return upsert_provider_jobs(source, entries, database)
    except JobNormalizationError as exc:
        raise GreenhouseAdapterError(exc.safe_message) from exc


def fail_run_safely(
    run_id: int,
    summary: str,
    database: Session,
) -> IngestionRun:
    return complete_ingestion_run(
        run_id,
        IngestionRunCompletion(
            run_status="failed",
            failure_summary=summary,
        ),
        database,
    )


def ingest_greenhouse_source(
    source_id: int,
    database: Session,
    *,
    http_client: httpx.Client | None = None,
) -> IngestionRun:
    """Run one compliance-gated Greenhouse ingestion for a source."""
    source = database.get(JobSource, source_id)
    if source is None:
        raise GreenhouseAdapterError(
            "Job source was not found.",
            status_code=404,
        )

    validate_greenhouse_source(source)

    try:
        run = create_ingestion_run(
            IngestionRunCreate(job_source_id=source.id),
            database,
        )
        run = start_ingestion_run(run.id, database)
    except IngestionServiceError as exc:
        raise GreenhouseAdapterError(
            exc.safe_message,
            status_code=exc.status_code,
        ) from exc

    client = http_client or build_http_client()
    owns_client = http_client is None

    try:
        payload = fetch_greenhouse_payload(source, client)
    except GreenhouseAdapterError as exc:
        return fail_run_safely(run.id, exc.safe_message, database)
    finally:
        if owns_client:
            client.close()

    try:
        record_source_snapshot(
            SourceSnapshotCreate(
                ingestion_run_id=run.id,
                content_hash=sha256(payload).hexdigest(),
                payload_size_bytes=len(payload),
                payload_media_type="application/json",
            ),
            database,
        )
    except IngestionServiceError as exc:
        return fail_run_safely(run.id, exc.safe_message, database)

    try:
        jobs = parse_greenhouse_jobs(payload)
        discovered, updated = upsert_normalized_jobs(
            source,
            jobs,
            database,
        )
    except GreenhouseAdapterError as exc:
        return fail_run_safely(run.id, exc.safe_message, database)

    return complete_ingestion_run(
        run.id,
        IngestionRunCompletion(
            run_status="succeeded",
            jobs_discovered=discovered,
            jobs_updated=updated,
        ),
        database,
    )
