"""Provider-agnostic job normalization, dedup, and freshness (4.4).

Upserts provider-supplied job data into normalized_jobs with
deterministic content refresh, detects duplicates using exact
signals only (no fuzzy matching, no inference), and evaluates
lifecycle freshness without ever deleting job provenance.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.job import (
    JobDuplicate,
    JobLocation,
    JobSource,
    NormalizedJob,
)
from app.schemas.job import JobLocationCreate, NormalizedJobCreate
from app.services.job import (
    JobServiceError,
    build_normalized_job,
    validate_job_lifecycle_transition,
)


REACTIVATABLE_STATUSES = {"discovered", "possibly_stale", "expired"}
STALE_EVALUATION_STATUSES = {"discovered", "active"}


class JobNormalizationError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def get_settings() -> Settings:
    return Settings()


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """Treat naive datetimes from SQLite storage as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def promote_reseen_job(job: NormalizedJob) -> None:
    if job.lifecycle_status in REACTIVATABLE_STATUSES:
        validate_job_lifecycle_transition(
            job.lifecycle_status,
            "active",
        )
        job.lifecycle_status = "active"


def refresh_job_content(
    job: NormalizedJob,
    data: NormalizedJobCreate,
    locations: Sequence[JobLocationCreate],
    database: Session,
    now: datetime,
) -> None:
    """Apply provider-supplied field changes deterministically."""
    job.title = data.title
    job.normalized_title = data.normalized_title
    job.canonical_url = data.canonical_url
    job.source_url = data.source_url
    job.description_text = data.description_text
    job.responsibilities_text = data.responsibilities_text
    job.required_qualifications_text = (
        data.required_qualifications_text
    )
    job.preferred_qualifications_text = (
        data.preferred_qualifications_text
    )
    job.source_sponsorship_visa_text = (
        data.source_sponsorship_visa_text
    )
    job.source_updated_at = data.source_updated_at
    job.source_attribution_text = data.source_attribution_text
    job.source_attribution_url = data.source_attribution_url
    job.source_license_reference = data.source_license_reference
    job.content_hash = data.content_hash
    job.normalization_version = data.normalization_version

    database.execute(
        delete(JobLocation).where(JobLocation.job_id == job.id),
        execution_options={"synchronize_session": "fetch"},
    )
    for location in locations:
        database.add(
            JobLocation(
                **location.model_dump(),
                job_id=job.id,
                created_at=now,
            )
        )


def upsert_provider_jobs(
    source: JobSource,
    entries: Sequence[
        tuple[NormalizedJobCreate, list[JobLocationCreate]]
    ],
    database: Session,
) -> tuple[int, int]:
    """Create unseen jobs, touch seen ones, refresh changed content.

    Single transaction: either every entry lands or none do.
    Returns (jobs_discovered, jobs_updated).
    """
    discovered = 0
    updated = 0
    now = current_utc_time()

    try:
        for data, locations in entries:
            existing = database.scalar(
                select(NormalizedJob).where(
                    NormalizedJob.job_source_id == source.id,
                    NormalizedJob.source_job_id == data.source_job_id,
                )
            )

            if existing is None:
                record, location_records, _, _ = build_normalized_job(
                    data,
                    locations=locations,
                )
                database.add(record)
                database.flush()
                for location_record in location_records:
                    location_record.job_id = record.id
                database.add_all(location_records)
                discovered += 1
                continue

            existing.last_seen_at = now
            existing.ingested_at = now
            existing.updated_at = now
            promote_reseen_job(existing)

            if existing.content_hash != data.content_hash:
                refresh_job_content(
                    existing,
                    data,
                    locations,
                    database,
                    now,
                )
            updated += 1

        database.commit()
    except JobServiceError as exc:
        database.rollback()
        raise JobNormalizationError(
            "Provider job data failed validation.",
        ) from exc
    except IntegrityError as exc:
        database.rollback()
        raise JobNormalizationError(
            "Provider jobs could not be saved.",
        ) from exc

    return discovered, updated


def evaluate_job_freshness(
    database: Session,
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    """Apply lifecycle freshness transitions. Never deletes rows."""
    current_time = now or current_utc_time()
    stale_cutoff = current_time - timedelta(
        days=get_settings().job_stale_after_days,
    )
    expired_count = 0
    stale_count = 0

    jobs = database.scalars(select(NormalizedJob)).all()
    for job in jobs:
        if (
            job.expires_at is not None
            and as_utc(job.expires_at) <= current_time
            and job.lifecycle_status
            in ("discovered", "active", "possibly_stale")
        ):
            validate_job_lifecycle_transition(
                job.lifecycle_status,
                "expired",
            )
            job.lifecycle_status = "expired"
            job.updated_at = current_time
            expired_count += 1
            continue

        if (
            as_utc(job.last_seen_at) <= stale_cutoff
            and job.lifecycle_status in STALE_EVALUATION_STATUSES
        ):
            validate_job_lifecycle_transition(
                job.lifecycle_status,
                "possibly_stale",
            )
            job.lifecycle_status = "possibly_stale"
            job.updated_at = current_time
            stale_count += 1

    database.commit()
    return {
        "jobs_marked_expired": expired_count,
        "jobs_marked_possibly_stale": stale_count,
    }


def record_duplicate_pair(
    newer: NormalizedJob,
    canonical: NormalizedJob,
    method: str,
    existing_pairs: set[tuple[int, int, str]],
    database: Session,
    now: datetime,
) -> int:
    key = (newer.id, canonical.id, method)
    if key in existing_pairs:
        return 0

    database.add(
        JobDuplicate(
            job_id=newer.id,
            duplicate_of_job_id=canonical.id,
            detection_method=method,
            detected_at=now,
            created_at=now,
        )
    )
    existing_pairs.add(key)
    return 1


def detect_job_duplicates(
    database: Session,
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    """Link duplicates using exact signals only.

    Signals: identical canonical_url, or identical content_hash.
    Fuzzy matching is deliberately excluded — an incorrect duplicate
    link could hide a real job, violating the no-inference rule.
    The earliest-seen job in a group is the canonical record.
    Links are additive; jobs are never merged or deleted.
    """
    current_time = now or current_utc_time()
    existing_pairs = {
        (pair.job_id, pair.duplicate_of_job_id, pair.detection_method)
        for pair in database.scalars(select(JobDuplicate)).all()
    }
    new_links = 0

    jobs = list(
        database.scalars(
            select(NormalizedJob).order_by(
                NormalizedJob.first_seen_at.asc(),
                NormalizedJob.id.asc(),
            )
        ).all()
    )

    by_canonical_url: dict[str, NormalizedJob] = {}
    by_content_hash: dict[str, NormalizedJob] = {}

    for job in jobs:
        if job.canonical_url:
            canonical = by_canonical_url.get(job.canonical_url)
            if canonical is None:
                by_canonical_url[job.canonical_url] = job
            elif canonical.id != job.id:
                new_links += record_duplicate_pair(
                    job,
                    canonical,
                    "canonical_url",
                    existing_pairs,
                    database,
                    current_time,
                )

        canonical = by_content_hash.get(job.content_hash)
        if canonical is None:
            by_content_hash[job.content_hash] = job
        elif canonical.id != job.id:
            new_links += record_duplicate_pair(
                job,
                canonical,
                "content_hash",
                existing_pairs,
                database,
                current_time,
            )

    try:
        database.commit()
    except IntegrityError as exc:
        database.rollback()
        raise JobNormalizationError(
            "Duplicate links could not be saved.",
        ) from exc

    return {"duplicate_links_created": new_links}


def run_job_maintenance(
    database: Session,
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    """Run freshness evaluation and duplicate detection together."""
    current_time = now or current_utc_time()
    results = evaluate_job_freshness(database, now=current_time)
    results.update(detect_job_duplicates(database, now=current_time))
    return results


def list_job_duplicates(
    job_id: int,
    database: Session,
) -> list[JobDuplicate]:
    return list(
        database.scalars(
            select(JobDuplicate)
            .where(
                (JobDuplicate.job_id == job_id)
                | (JobDuplicate.duplicate_of_job_id == job_id)
            )
            .order_by(JobDuplicate.id.asc())
        ).all()
    )
