from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import ipaddress
import re
import unicodedata
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.job import (
    JobCompensation,
    JobLocation,
    JobSkillRequirement,
    JobSource,
    NormalizedJob,
)
from app.schemas.job import (
    JobCompensationCreate,
    JobLocationCreate,
    JobSkillRequirementCreate,
    JobSourceCreate,
    NormalizedJobCreate,
)


DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100
JOB_LIST_DESCRIPTION_EXCERPT_CHARS = 240
MAX_JOB_DESCRIPTION_CHARS = 20_000
MAX_JOB_SECTION_TEXT_CHARS = 10_000
MAX_JOB_SHORT_SOURCE_TEXT_CHARS = 1_000
MAX_RETENTION_DAYS = 365
APPROVED_FOR_CONFIGURED_USE = "approved_for_configured_use"
SERVER_FETCH_ACCESS_MODES = {"api", "approved_static_fetch"}
PUBLIC_URL_SCHEMES = {"http", "https"}
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
CONTENT_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
NORMALIZATION_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
SOURCE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,99}$")
LOCAL_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "0.0.0.0",
}
ALLOWED_CONTROL_CHARACTERS = {"\n", "\r", "\t"}
LIFECYCLE_TRANSITIONS = {
    "discovered": {
        "active",
        "possibly_stale",
        "expired",
        "removed",
        "unavailable",
    },
    "active": {
        "possibly_stale",
        "expired",
        "removed",
        "unavailable",
    },
    "possibly_stale": {
        "active",
        "expired",
        "removed",
        "unavailable",
    },
    "expired": {
        "active",
        "removed",
        "unavailable",
    },
    "removed": {
        "unavailable",
    },
    "unavailable": set(),
}


class JobServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


@dataclass(frozen=True)
class Page:
    items: list[object]
    total: int
    page: int
    page_size: int


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def contains_invalid_control_character(value: str) -> bool:
    for character in value:
        if character in ALLOWED_CONTROL_CHARACTERS:
            continue

        if unicodedata.category(character) == "Cc":
            return True

    return False


def validate_text(
    field_name: str,
    value: str | None,
    *,
    max_length: int,
    required: bool = False,
) -> str | None:
    if value is None:
        if required:
            raise JobServiceError(f"{field_name} is required.")
        return None

    if required and value.strip() == "":
        raise JobServiceError(f"{field_name} is required.")

    if len(value) > max_length:
        raise JobServiceError(f"{field_name} is too long.")

    if "\x00" in value or contains_invalid_control_character(value):
        raise JobServiceError(f"{field_name} contains invalid characters.")

    return value


def validate_source_key(source_key: str) -> None:
    if not SOURCE_KEY_RE.fullmatch(source_key):
        raise JobServiceError(
            "Job source key must be lowercase and stable.",
        )


def validate_retention_days(days: int) -> None:
    if days < 1 or days > MAX_RETENTION_DAYS:
        raise JobServiceError(
            "Job source retention days must be between 1 and 365.",
        )


def validate_public_reference_url(
    field_name: str,
    url: str | None,
    *,
    required: bool = False,
) -> str | None:
    validate_text(field_name, url, max_length=1000, required=required)

    if url is None:
        return None

    parsed = urlparse(url)
    if parsed.scheme.lower() not in PUBLIC_URL_SCHEMES:
        raise JobServiceError(f"{field_name} must be an http or https URL.")

    if parsed.username or parsed.password:
        raise JobServiceError(f"{field_name} must not contain credentials.")

    hostname = parsed.hostname
    if not hostname:
        raise JobServiceError(f"{field_name} must include a public host.")

    host = hostname.strip().strip("[]").lower().rstrip(".")
    if (
        host in LOCAL_HOSTNAMES
        or host.endswith(".localhost")
        or host.endswith(".local")
    ):
        raise JobServiceError(f"{field_name} must use a public host.")

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "\\" in host or " " in host:
            raise JobServiceError(f"{field_name} is malformed.")
        return url

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise JobServiceError(f"{field_name} must use a public host.")

    return url


def validate_content_hash(content_hash: str) -> None:
    if not CONTENT_HASH_RE.fullmatch(content_hash):
        raise JobServiceError(
            "Job content hash must be a lowercase SHA-256 hex digest.",
        )


def validate_normalization_version(version: str | None) -> None:
    if version is None:
        return

    if not NORMALIZATION_VERSION_RE.fullmatch(version):
        raise JobServiceError("Normalization version is invalid.")


def validate_currency(currency: str | None) -> None:
    if currency is None:
        return

    if not CURRENCY_RE.fullmatch(currency):
        raise JobServiceError("Compensation currency must be an ISO code.")


def validate_compensation_amounts(
    min_amount: Decimal | None,
    max_amount: Decimal | None,
) -> None:
    if (
        min_amount is not None
        and max_amount is not None
        and min_amount > max_amount
    ):
        raise JobServiceError(
            "Compensation minimum cannot be greater than maximum.",
        )


def validate_source_review_state(source: JobSource) -> None:
    unresolved_statuses = {
        source.terms_review_status,
        source.robots_review_status,
        source.commercial_use_review_status,
    }

    if unresolved_statuses != {APPROVED_FOR_CONFIGURED_USE}:
        raise JobServiceError(
            "Manual review must be resolved before enabling a job source.",
        )


def validate_job_source_compliance(source: JobSource) -> None:
    validate_source_key(source.source_key)
    validate_text(
        "Job source display name",
        source.display_name,
        max_length=200,
        required=True,
    )
    validate_public_reference_url("Job source base URL", source.base_url)
    validate_public_reference_url(
        "Job source attribution URL",
        source.attribution_url,
    )
    validate_text(
        "Job source attribution text",
        source.attribution_text,
        max_length=500,
    )
    validate_retention_days(source.configured_retention_days)

    if source.source_category == "user_supplied_url":
        if source.access_mode != "metadata_only":
            raise JobServiceError(
                "User-supplied URL sources must remain metadata-only.",
            )

        if source.server_fetch_allowed:
            raise JobServiceError(
                "User-supplied URL sources cannot allow server fetching.",
            )

    if source.server_fetch_allowed:
        if source.access_mode not in SERVER_FETCH_ACCESS_MODES:
            raise JobServiceError(
                "Server fetching is not permitted for this access mode.",
            )

    if not source.enabled:
        return

    if not source.allowlisted:
        raise JobServiceError(
            "Job sources cannot be enabled unless they are allowlisted.",
        )

    if source.manual_review_required:
        validate_source_review_state(source)

    if source.attribution_required and not (
        source.attribution_text or source.attribution_url
    ):
        raise JobServiceError(
            "Attribution information is required before enabling this source.",
        )


def build_job_source(data: JobSourceCreate) -> JobSource:
    source = JobSource(**data.model_dump())
    now = current_utc_time()
    source.created_at = now
    source.updated_at = now
    validate_job_source_compliance(source)
    return source


def create_job_source(
    data: JobSourceCreate,
    database: Session,
) -> JobSource:
    source = build_job_source(data)
    database.add(source)

    try:
        database.commit()
        database.refresh(source)
    except IntegrityError as exc:
        database.rollback()
        raise JobServiceError(
            "Job source could not be saved.",
            status_code=409,
        ) from exc

    return source


def validate_job_lifecycle_transition(
    current_status: str,
    next_status: str,
) -> None:
    if current_status == next_status:
        return

    allowed_statuses = LIFECYCLE_TRANSITIONS.get(current_status, set())
    if next_status not in allowed_statuses:
        raise JobServiceError("Job lifecycle transition is not allowed.")


def validate_normalized_job_data(data: NormalizedJobCreate) -> None:
    validate_text(
        "Source job ID",
        data.source_job_id,
        max_length=300,
        required=True,
    )
    validate_public_reference_url(
        "Job source URL",
        data.source_url,
        required=True,
    )
    validate_public_reference_url("Job canonical URL", data.canonical_url)
    validate_text(
        "Employer name",
        data.employer_name,
        max_length=250,
        required=True,
    )
    validate_text("Job title", data.title, max_length=250, required=True)
    validate_text(
        "Normalized job title",
        data.normalized_title,
        max_length=250,
    )
    validate_text(
        "Job description",
        data.description_text,
        max_length=MAX_JOB_DESCRIPTION_CHARS,
    )
    validate_text(
        "Job responsibilities",
        data.responsibilities_text,
        max_length=MAX_JOB_SECTION_TEXT_CHARS,
    )
    validate_text(
        "Job required qualifications",
        data.required_qualifications_text,
        max_length=MAX_JOB_SECTION_TEXT_CHARS,
    )
    validate_text(
        "Job preferred qualifications",
        data.preferred_qualifications_text,
        max_length=MAX_JOB_SECTION_TEXT_CHARS,
    )
    validate_text(
        "Job sponsorship or visa source text",
        data.source_sponsorship_visa_text,
        max_length=MAX_JOB_SHORT_SOURCE_TEXT_CHARS,
    )
    validate_text(
        "Job source attribution text",
        data.source_attribution_text,
        max_length=500,
    )
    validate_public_reference_url(
        "Job source attribution URL",
        data.source_attribution_url,
    )
    validate_text(
        "Job source license reference",
        data.source_license_reference,
        max_length=1000,
    )
    validate_content_hash(data.content_hash)
    validate_normalization_version(data.normalization_version)


def validate_job_location(data: JobLocationCreate) -> None:
    validate_text(
        "Raw job location",
        data.raw_location_text,
        max_length=500,
    )
    validate_text("Job country", data.country, max_length=100)
    validate_text("Job region", data.region, max_length=150)
    validate_text("Job city", data.city, max_length=150)
    validate_text("Job postal code", data.postal_code, max_length=50)
    validate_normalization_version(data.normalization_version)

    if not any(
        (
            data.raw_location_text,
            data.country,
            data.region,
            data.city,
            data.postal_code,
            data.remote_mode,
        )
    ):
        raise JobServiceError("Job location must include source data.")


def validate_job_compensation(data: JobCompensationCreate) -> None:
    validate_compensation_amounts(data.min_amount, data.max_amount)
    validate_currency(data.currency)
    validate_text(
        "Compensation source text",
        data.source_text,
        max_length=1000,
    )


def validate_job_skill_requirement(data: JobSkillRequirementCreate) -> None:
    validate_text(
        "Job skill requirement",
        data.skill_text,
        max_length=200,
        required=True,
    )
    validate_text(
        "Normalized skill key",
        data.normalized_skill_key,
        max_length=150,
    )
    validate_normalization_version(data.normalization_version)

    if not data.source_provided:
        raise JobServiceError(
            "Phase 4.1 stores only explicitly supplied skill requirements.",
        )


def ensure_unique_skill_requirements(
    skills: Sequence[JobSkillRequirementCreate],
) -> None:
    seen: set[tuple[str, str]] = set()

    for skill in skills:
        key = (
            skill.skill_text.strip().casefold(),
            skill.requirement_type,
        )
        if key in seen:
            raise JobServiceError(
                "Duplicate job skill requirements are not allowed.",
            )
        seen.add(key)


def build_normalized_job(
    data: NormalizedJobCreate,
    *,
    locations: Sequence[JobLocationCreate] = (),
    compensations: Sequence[JobCompensationCreate] = (),
    skill_requirements: Sequence[JobSkillRequirementCreate] = (),
) -> tuple[
    NormalizedJob,
    list[JobLocation],
    list[JobCompensation],
    list[JobSkillRequirement],
]:
    validate_normalized_job_data(data)

    for location in locations:
        validate_job_location(location)

    for compensation in compensations:
        validate_job_compensation(compensation)

    for skill in skill_requirements:
        validate_job_skill_requirement(skill)
    ensure_unique_skill_requirements(skill_requirements)

    now = current_utc_time()
    job_payload = data.model_dump()
    for field_name in ("first_seen_at", "last_seen_at", "ingested_at"):
        if job_payload[field_name] is None:
            job_payload[field_name] = now
    job_payload["created_at"] = now
    job_payload["updated_at"] = now
    job = NormalizedJob(**job_payload)

    location_records = [
        JobLocation(**location.model_dump(), created_at=now)
        for location in locations
    ]
    compensation_records = [
        JobCompensation(**compensation.model_dump(), created_at=now)
        for compensation in compensations
    ]
    skill_records = [
        JobSkillRequirement(**skill.model_dump(), created_at=now)
        for skill in skill_requirements
    ]
    return job, location_records, compensation_records, skill_records


def create_normalized_job(
    data: NormalizedJobCreate,
    database: Session,
    *,
    locations: Sequence[JobLocationCreate] = (),
    compensations: Sequence[JobCompensationCreate] = (),
    skill_requirements: Sequence[JobSkillRequirementCreate] = (),
) -> NormalizedJob:
    source = database.get(JobSource, data.job_source_id)
    if source is None:
        raise JobServiceError("Job source was not found.")

    job, location_records, compensation_records, skill_records = (
        build_normalized_job(
            data,
            locations=locations,
            compensations=compensations,
            skill_requirements=skill_requirements,
        )
    )
    try:
        database.add(job)
        database.flush()

        for record in location_records:
            record.job_id = job.id
        for record in compensation_records:
            record.job_id = job.id
        for record in skill_records:
            record.job_id = job.id

        database.add_all(
            [
                *location_records,
                *compensation_records,
                *skill_records,
            ]
        )
        database.commit()
        database.refresh(job)
    except IntegrityError as exc:
        database.rollback()
        raise JobServiceError(
            "Job could not be saved.",
            status_code=409,
        ) from exc

    return job


def paginate_scalars(
    statement: object,
    database: Session,
    *,
    page: int,
    page_size: int,
) -> Page:
    if page < 1:
        raise JobServiceError("Page must be greater than zero.")

    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise JobServiceError(
            f"Page size must be between 1 and {MAX_PAGE_SIZE}.",
        )

    total = database.scalar(
        select(func.count()).select_from(
            statement.order_by(None).subquery()  # type: ignore[attr-defined]
        )
    )
    items = list(
        database.scalars(
            statement.limit(page_size).offset((page - 1) * page_size)
        ).all()
    )
    return Page(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


def list_job_sources(
    database: Session,
    *,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> dict[str, object]:
    statement = select(JobSource).order_by(
        JobSource.display_name.asc(),
        JobSource.id.asc(),
    )
    result = paginate_scalars(
        statement,
        database,
        page=page,
        page_size=page_size,
    )
    return {
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
    }


def get_job_source_or_404(source_id: int, database: Session) -> JobSource:
    source = database.get(JobSource, source_id)
    if source is None:
        raise JobServiceError(
            "Job source was not found.",
            status_code=404,
        )
    return source


def build_description_excerpt(value: str | None) -> str | None:
    if value is None:
        return None

    clean_value = " ".join(value.split())
    if len(clean_value) <= JOB_LIST_DESCRIPTION_EXCERPT_CHARS:
        return clean_value

    return f"{clean_value[: JOB_LIST_DESCRIPTION_EXCERPT_CHARS - 3]}..."


def build_job_list_item(job: NormalizedJob) -> dict[str, object]:
    return {
        "id": job.id,
        "job_source_id": job.job_source_id,
        "source_job_id": job.source_job_id,
        "canonical_url": job.canonical_url,
        "source_url": job.source_url,
        "employer_name": job.employer_name,
        "title": job.title,
        "normalized_title": job.normalized_title,
        "remote_mode": job.remote_mode,
        "employment_type": job.employment_type,
        "seniority": job.seniority,
        "posted_at": job.posted_at,
        "expires_at": job.expires_at,
        "first_seen_at": job.first_seen_at,
        "last_seen_at": job.last_seen_at,
        "ingested_at": job.ingested_at,
        "lifecycle_status": job.lifecycle_status,
        "description_excerpt": build_description_excerpt(
            job.description_text
        ),
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def list_normalized_jobs(
    database: Session,
    *,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    source_id: int | None = None,
    lifecycle_status: str | None = None,
    employer: str | None = None,
    employment_type: str | None = None,
    remote_mode: str | None = None,
    posted_within_hours: int | None = None,
    updated_within_hours: int | None = None,
    search: str | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    statement = select(NormalizedJob)
    evaluation_time = now or datetime.now(timezone.utc)

    if search is not None and search.strip():
        pattern = f"%{search.strip().lower()}%"
        statement = statement.where(
            func.lower(NormalizedJob.title).like(pattern)
        )

    if source_id is not None:
        statement = statement.where(NormalizedJob.job_source_id == source_id)

    if posted_within_hours is not None:
        cutoff = evaluation_time - timedelta(hours=posted_within_hours)
        statement = statement.where(
            NormalizedJob.posted_at.is_not(None),
            NormalizedJob.posted_at >= cutoff,
        )

    if updated_within_hours is not None:
        cutoff = evaluation_time - timedelta(hours=updated_within_hours)
        statement = statement.where(
            NormalizedJob.last_seen_at >= cutoff,
        )

    if lifecycle_status is not None:
        statement = statement.where(
            NormalizedJob.lifecycle_status == lifecycle_status
        )

    if employer is not None:
        validate_text("Employer filter", employer, max_length=250)
        statement = statement.where(
            func.lower(NormalizedJob.employer_name) == employer.casefold()
        )

    if employment_type is not None:
        statement = statement.where(
            NormalizedJob.employment_type == employment_type
        )

    if remote_mode is not None:
        statement = statement.where(NormalizedJob.remote_mode == remote_mode)

    statement = statement.order_by(
        NormalizedJob.last_seen_at.desc(),
        NormalizedJob.id.desc(),
    )

    result = paginate_scalars(
        statement,
        database,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [
            build_job_list_item(job)
            for job in result.items
            if isinstance(job, NormalizedJob)
        ],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
    }


def get_normalized_job_or_404(
    job_id: int,
    database: Session,
) -> NormalizedJob:
    job = database.get(NormalizedJob, job_id)
    if job is None:
        raise JobServiceError("Job was not found.", status_code=404)
    return job


def list_job_locations(job_id: int, database: Session) -> list[JobLocation]:
    return list(
        database.scalars(
            select(JobLocation)
            .where(JobLocation.job_id == job_id)
            .order_by(
                JobLocation.sort_order.asc(),
                JobLocation.id.asc(),
            )
        ).all()
    )


def list_job_compensations(
    job_id: int,
    database: Session,
) -> list[JobCompensation]:
    return list(
        database.scalars(
            select(JobCompensation)
            .where(JobCompensation.job_id == job_id)
            .order_by(
                JobCompensation.sort_order.asc(),
                JobCompensation.id.asc(),
            )
        ).all()
    )


def list_job_skill_requirements(
    job_id: int,
    database: Session,
) -> list[JobSkillRequirement]:
    return list(
        database.scalars(
            select(JobSkillRequirement)
            .where(JobSkillRequirement.job_id == job_id)
            .order_by(
                JobSkillRequirement.sort_order.asc(),
                JobSkillRequirement.id.asc(),
            )
        ).all()
    )


def build_job_detail(job: NormalizedJob, database: Session) -> dict[str, object]:
    payload = build_job_list_item(job)
    payload.update(
        {
            "employer_external_id": job.employer_external_id,
            "description_text": job.description_text,
            "responsibilities_text": job.responsibilities_text,
            "required_qualifications_text": (
                job.required_qualifications_text
            ),
            "preferred_qualifications_text": (
                job.preferred_qualifications_text
            ),
            "source_sponsorship_visa_text": (
                job.source_sponsorship_visa_text
            ),
            "source_updated_at": job.source_updated_at,
            "source_attribution_text": job.source_attribution_text,
            "source_attribution_url": job.source_attribution_url,
            "source_license_reference": job.source_license_reference,
            "content_hash": job.content_hash,
            "normalization_version": job.normalization_version,
            "locations": list_job_locations(job.id, database),
            "compensations": list_job_compensations(job.id, database),
            "skill_requirements": list_job_skill_requirements(
                job.id,
                database,
            ),
        }
    )
    return payload
