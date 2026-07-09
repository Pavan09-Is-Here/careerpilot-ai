"""Free public job-source adapters (Phase 17).

One shared, compliance-gated connect/ingest pipeline serving six free
providers alongside the original Greenhouse adapter:

- ``lever`` and ``ashby``: per-company ATS boards with public,
  keyless JSON APIs (same model as Greenhouse).
- ``remotive`` and ``arbeitnow``: free, keyless remote-job feeds —
  one global source each.
- ``adzuna`` and ``reed``: aggregator APIs that require free API
  keys, supplied via environment settings only (never stored in the
  database, never logged, never echoed in responses).

Every source passes the same policy gates as Greenhouse before any
server fetch (enabled, allowlisted, fetch permission, approved
terms/robots/commercial review, pinned base-URL shape). Adapters map
only fields the provider actually supplied — nothing is inferred or
invented. Compensation data is deliberately not mapped in this
version.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Callable
from urllib.parse import quote, urlencode

import httpx
from sqlalchemy.exc import IntegrityError
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


ACCESS_MODE = "api"
SOURCE_CATEGORY = "provider_api"
APPROVED_REVIEW_STATUS = "approved_for_configured_use"
CONNECT_RETENTION_DAYS = 30
FETCH_TIMEOUT_SECONDS = 15.0
MAX_TITLE_CHARS = 250
MAX_DESCRIPTION_CHARS = 20_000
MAX_LOCATION_CHARS = 500
MAX_JOBS_PER_INGEST = 500

BOARD_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
QUERY_TEXT_RE = re.compile(r"^[A-Za-z0-9 ,+&/'()._-]{0,100}$")
ADZUNA_COUNTRIES = frozenset(
    {
        "at", "au", "be", "br", "ca", "ch", "de", "es", "fr", "gb",
        "in", "it", "mx", "nl", "nz", "pl", "sg", "us", "za",
    }
)
HTML_TAG_RE = re.compile(r"<[^>]+>")


class ProviderCatalogError(RuntimeError):
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


def strip_html_to_text(value: str) -> str:
    unescaped = html.unescape(value)
    without_tags = HTML_TAG_RE.sub(" ", unescaped)
    return " ".join(without_tags.split())


def truncate_text(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


def clean_text(value: object, max_length: int) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return truncate_text(strip_html_to_text(value), max_length)


def location_entries(value: object) -> list[JobLocationCreate]:
    text = clean_text(value, MAX_LOCATION_CHARS)
    if text is None:
        return []
    return [
        JobLocationCreate(
            raw_location_text=text,
            source_provided=True,
            normalization_version=NORMALIZATION_VERSION,
        )
    ]


def parse_iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_epoch(value: object) -> datetime | None:
    if not isinstance(value, (int, float)):
        return None
    try:
        # Lever uses millisecond epochs; Arbeitnow uses seconds.
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def content_hash(job: dict[str, object]) -> str:
    return sha256(
        json.dumps(job, sort_keys=True, default=str).encode()
    ).hexdigest()


def required_str(job: dict[str, object], key: str) -> str:
    value = job.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ProviderCatalogError(
            "Provider job entry was missing required fields.",
        )
    return str(value)


NORMALIZATION_VERSION = "provider-catalog-1"


# --- Per-provider payload parsing and mapping -------------------------------


def _job_list(payload: bytes, key: str | None) -> list[dict[str, object]]:
    try:
        document = json.loads(payload)
    except ValueError as exc:
        raise ProviderCatalogError(
            "Provider payload was not valid JSON.",
        ) from exc

    items: object
    if key is None:
        items = document
    else:
        items = document.get(key) if isinstance(document, dict) else None

    if not isinstance(items, list):
        raise ProviderCatalogError(
            "Provider payload did not contain a job list.",
        )
    for item in items:
        if not isinstance(item, dict):
            raise ProviderCatalogError(
                "Provider payload contained an invalid job entry.",
            )
    return items[:MAX_JOBS_PER_INGEST]


def parse_lever(payload: bytes) -> list[dict[str, object]]:
    return _job_list(payload, None)


def map_lever(
    source: JobSource,
    job: dict[str, object],
) -> tuple[NormalizedJobCreate, list[JobLocationCreate]]:
    categories = job.get("categories")
    location = (
        categories.get("location")
        if isinstance(categories, dict)
        else None
    )
    description = job.get("descriptionPlain") or job.get("description")
    data = NormalizedJobCreate(
        job_source_id=source.id,
        source_job_id=required_str(job, "id"),
        source_url=required_str(job, "hostedUrl"),
        canonical_url=str(job["hostedUrl"]),
        employer_name=source.display_name,
        title=clean_text(required_str(job, "text"), MAX_TITLE_CHARS)
        or "Untitled role",
        description_text=clean_text(
            description, MAX_DESCRIPTION_CHARS
        ),
        source_updated_at=parse_epoch(job.get("createdAt")),
        source_attribution_text=source.attribution_text,
        source_attribution_url=source.attribution_url,
        content_hash=content_hash(job),
        normalization_version=NORMALIZATION_VERSION,
    )
    return data, location_entries(location)


def parse_ashby(payload: bytes) -> list[dict[str, object]]:
    return _job_list(payload, "jobs")


def map_ashby(
    source: JobSource,
    job: dict[str, object],
) -> tuple[NormalizedJobCreate, list[JobLocationCreate]]:
    url = job.get("jobUrl") or job.get("applyUrl")
    if not url:
        raise ProviderCatalogError(
            "Provider job entry was missing required fields.",
        )
    description = job.get("descriptionPlain") or job.get(
        "descriptionHtml"
    )
    remote_mode = "remote" if job.get("isRemote") is True else None
    data = NormalizedJobCreate(
        job_source_id=source.id,
        source_job_id=required_str(job, "id"),
        source_url=str(url),
        canonical_url=str(url),
        employer_name=source.display_name,
        title=clean_text(required_str(job, "title"), MAX_TITLE_CHARS)
        or "Untitled role",
        description_text=clean_text(
            description, MAX_DESCRIPTION_CHARS
        ),
        source_updated_at=parse_iso_datetime(job.get("publishedAt")),
        source_attribution_text=source.attribution_text,
        source_attribution_url=source.attribution_url,
        content_hash=content_hash(job),
        normalization_version=NORMALIZATION_VERSION,
        **({"remote_mode": remote_mode} if remote_mode else {}),
    )
    return data, location_entries(job.get("location"))


def parse_remotive(payload: bytes) -> list[dict[str, object]]:
    return _job_list(payload, "jobs")


def map_remotive(
    source: JobSource,
    job: dict[str, object],
) -> tuple[NormalizedJobCreate, list[JobLocationCreate]]:
    employer = clean_text(job.get("company_name"), MAX_TITLE_CHARS)
    data = NormalizedJobCreate(
        job_source_id=source.id,
        source_job_id=required_str(job, "id"),
        source_url=required_str(job, "url"),
        canonical_url=str(job["url"]),
        employer_name=employer or source.display_name,
        title=clean_text(required_str(job, "title"), MAX_TITLE_CHARS)
        or "Untitled role",
        description_text=clean_text(
            job.get("description"), MAX_DESCRIPTION_CHARS
        ),
        source_updated_at=parse_iso_datetime(
            job.get("publication_date")
        ),
        source_attribution_text=source.attribution_text,
        source_attribution_url=source.attribution_url,
        content_hash=content_hash(job),
        normalization_version=NORMALIZATION_VERSION,
        remote_mode="remote",
    )
    return data, location_entries(
        job.get("candidate_required_location")
    )


def parse_arbeitnow(payload: bytes) -> list[dict[str, object]]:
    return _job_list(payload, "data")


def map_arbeitnow(
    source: JobSource,
    job: dict[str, object],
) -> tuple[NormalizedJobCreate, list[JobLocationCreate]]:
    employer = clean_text(job.get("company_name"), MAX_TITLE_CHARS)
    remote_mode = "remote" if job.get("remote") is True else None
    data = NormalizedJobCreate(
        job_source_id=source.id,
        source_job_id=required_str(job, "slug"),
        source_url=required_str(job, "url"),
        canonical_url=str(job["url"]),
        employer_name=employer or source.display_name,
        title=clean_text(required_str(job, "title"), MAX_TITLE_CHARS)
        or "Untitled role",
        description_text=clean_text(
            job.get("description"), MAX_DESCRIPTION_CHARS
        ),
        source_updated_at=parse_epoch(job.get("created_at")),
        source_attribution_text=source.attribution_text,
        source_attribution_url=source.attribution_url,
        content_hash=content_hash(job),
        normalization_version=NORMALIZATION_VERSION,
        **({"remote_mode": remote_mode} if remote_mode else {}),
    )
    return data, location_entries(job.get("location"))


def parse_adzuna(payload: bytes) -> list[dict[str, object]]:
    return _job_list(payload, "results")


def map_adzuna(
    source: JobSource,
    job: dict[str, object],
) -> tuple[NormalizedJobCreate, list[JobLocationCreate]]:
    company = job.get("company")
    employer = (
        clean_text(company.get("display_name"), MAX_TITLE_CHARS)
        if isinstance(company, dict)
        else None
    )
    location = job.get("location")
    location_text = (
        location.get("display_name")
        if isinstance(location, dict)
        else None
    )
    data = NormalizedJobCreate(
        job_source_id=source.id,
        source_job_id=required_str(job, "id"),
        source_url=required_str(job, "redirect_url"),
        canonical_url=str(job["redirect_url"]),
        employer_name=employer or source.display_name,
        title=clean_text(required_str(job, "title"), MAX_TITLE_CHARS)
        or "Untitled role",
        description_text=clean_text(
            job.get("description"), MAX_DESCRIPTION_CHARS
        ),
        source_updated_at=parse_iso_datetime(job.get("created")),
        source_attribution_text=source.attribution_text,
        source_attribution_url=source.attribution_url,
        content_hash=content_hash(job),
        normalization_version=NORMALIZATION_VERSION,
    )
    return data, location_entries(location_text)


def parse_reed(payload: bytes) -> list[dict[str, object]]:
    return _job_list(payload, "results")


def map_reed(
    source: JobSource,
    job: dict[str, object],
) -> tuple[NormalizedJobCreate, list[JobLocationCreate]]:
    employer = clean_text(job.get("employerName"), MAX_TITLE_CHARS)
    data = NormalizedJobCreate(
        job_source_id=source.id,
        source_job_id=required_str(job, "jobId"),
        source_url=required_str(job, "jobUrl"),
        canonical_url=str(job["jobUrl"]),
        employer_name=employer or source.display_name,
        title=clean_text(
            required_str(job, "jobTitle"), MAX_TITLE_CHARS
        )
        or "Untitled role",
        description_text=clean_text(
            job.get("jobDescription"), MAX_DESCRIPTION_CHARS
        ),
        source_updated_at=None,
        source_attribution_text=source.attribution_text,
        source_attribution_url=source.attribution_url,
        content_hash=content_hash(job),
        normalization_version=NORMALIZATION_VERSION,
    )
    return data, location_entries(job.get("locationName"))


# --- Provider specs ---------------------------------------------------------


@dataclass(frozen=True)
class ProviderSpec:
    provider_type: str
    base_url_re: re.Pattern[str]
    parse_jobs: Callable[[bytes], list[dict[str, object]]]
    map_job: Callable[
        [JobSource, dict[str, object]],
        tuple[NormalizedJobCreate, list[JobLocationCreate]],
    ]
    build_fetch_url: Callable[[JobSource, Settings], str]
    fetch_headers: Callable[[Settings], dict[str, str]] | None = None
    requires_keys: Callable[[Settings], str | None] | None = None


def _lever_fetch_url(source: JobSource, settings: Settings) -> str:
    return f"{source.base_url}?mode=json"


def _ashby_fetch_url(source: JobSource, settings: Settings) -> str:
    return f"{source.base_url}?includeCompensation=true"


def _plain_fetch_url(source: JobSource, settings: Settings) -> str:
    return str(source.base_url)


def _adzuna_missing_keys(settings: Settings) -> str | None:
    if settings.adzuna_app_id and settings.adzuna_app_key:
        return None
    return (
        "Adzuna is not configured on the server. Set "
        "CAREERPILOT_ADZUNA_APP_ID and CAREERPILOT_ADZUNA_APP_KEY "
        "(free keys from developer.adzuna.com)."
    )


def _adzuna_fetch_url(source: JobSource, settings: Settings) -> str:
    params = {
        "app_id": settings.adzuna_app_id or "",
        "app_key": settings.adzuna_app_key or "",
        "results_per_page": "50",
        "content-type": "application/json",
    }
    separator = "&" if "?" in str(source.base_url) else "?"
    return f"{source.base_url}{separator}{urlencode(params)}"


def _reed_missing_keys(settings: Settings) -> str | None:
    if settings.reed_api_key:
        return None
    return (
        "Reed is not configured on the server. Set "
        "CAREERPILOT_REED_API_KEY (free key from "
        "reed.co.uk/developers)."
    )


def _reed_headers(settings: Settings) -> dict[str, str]:
    import base64

    token = base64.b64encode(
        f"{settings.reed_api_key or ''}:".encode()
    ).decode()
    return {"Authorization": f"Basic {token}"}


PROVIDER_SPECS: dict[str, ProviderSpec] = {
    "lever": ProviderSpec(
        provider_type="lever",
        base_url_re=re.compile(
            r"^https://api\.lever\.co/v0/postings/"
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}$"
        ),
        parse_jobs=parse_lever,
        map_job=map_lever,
        build_fetch_url=_lever_fetch_url,
    ),
    "ashby": ProviderSpec(
        provider_type="ashby",
        base_url_re=re.compile(
            r"^https://api\.ashbyhq\.com/posting-api/job-board/"
            r"[A-Za-z0-9][A-Za-z0-9.%_-]{0,99}$"
        ),
        parse_jobs=parse_ashby,
        map_job=map_ashby,
        build_fetch_url=_ashby_fetch_url,
    ),
    "remotive": ProviderSpec(
        provider_type="remotive",
        base_url_re=re.compile(
            r"^https://remotive\.com/api/remote-jobs$"
        ),
        parse_jobs=parse_remotive,
        map_job=map_remotive,
        build_fetch_url=_plain_fetch_url,
    ),
    "arbeitnow": ProviderSpec(
        provider_type="arbeitnow",
        base_url_re=re.compile(
            r"^https://www\.arbeitnow\.com/api/job-board-api$"
        ),
        parse_jobs=parse_arbeitnow,
        map_job=map_arbeitnow,
        build_fetch_url=_plain_fetch_url,
    ),
    "adzuna": ProviderSpec(
        provider_type="adzuna",
        base_url_re=re.compile(
            r"^https://api\.adzuna\.com/v1/api/jobs/[a-z]{2}/search/1"
            r"(\?what=[A-Za-z0-9+%.,_-]{0,150})?$"
        ),
        parse_jobs=parse_adzuna,
        map_job=map_adzuna,
        build_fetch_url=_adzuna_fetch_url,
        requires_keys=_adzuna_missing_keys,
    ),
    "reed": ProviderSpec(
        provider_type="reed",
        base_url_re=re.compile(
            r"^https://www\.reed\.co\.uk/api/1\.0/search"
            r"(\?[A-Za-z0-9=+%.,&_-]{0,300})?$"
        ),
        parse_jobs=parse_reed,
        map_job=map_reed,
        build_fetch_url=_plain_fetch_url,
        fetch_headers=_reed_headers,
        requires_keys=_reed_missing_keys,
    ),
}


def get_provider_spec(provider_type: str) -> ProviderSpec:
    spec = PROVIDER_SPECS.get(provider_type)
    if spec is None:
        raise ProviderCatalogError(
            "Unknown or unsupported job source provider.",
            status_code=404,
        )
    return spec


# --- Connect ----------------------------------------------------------------


def _validated_token(value: str | None, label: str) -> str:
    token = (value or "").strip()
    if not BOARD_TOKEN_RE.fullmatch(token):
        raise ProviderCatalogError(
            f"Enter a valid {label} using letters, numbers, dots, "
            "hyphens, or underscores.",
        )
    return token


def _validated_query(value: str | None, label: str) -> str:
    text = (value or "").strip()
    if text and not QUERY_TEXT_RE.fullmatch(text):
        raise ProviderCatalogError(
            f"The {label} contains unsupported characters.",
        )
    return text


def build_connect_source(
    provider_type: str,
    *,
    board_token: str | None,
    display_name: str,
    country: str | None,
    search_query: str | None,
    settings: Settings,
) -> tuple[str, str]:
    """Return (source_key, base_url) for a connect request."""
    if provider_type == "lever":
        token = _validated_token(board_token, "Lever board name")
        return (
            f"lever:{token.lower()}",
            f"https://api.lever.co/v0/postings/{token}",
        )
    if provider_type == "ashby":
        token = _validated_token(board_token, "Ashby board name")
        return (
            f"ashby:{token.lower()}",
            "https://api.ashbyhq.com/posting-api/job-board/"
            f"{quote(token, safe='._-')}",
        )
    if provider_type == "remotive":
        return "remotive:global", "https://remotive.com/api/remote-jobs"
    if provider_type == "arbeitnow":
        return (
            "arbeitnow:global",
            "https://www.arbeitnow.com/api/job-board-api",
        )
    if provider_type == "adzuna":
        missing = _adzuna_missing_keys(settings)
        if missing:
            raise ProviderCatalogError(missing)
        cleaned_country = (country or "").strip().lower()
        if cleaned_country not in ADZUNA_COUNTRIES:
            raise ProviderCatalogError(
                "Enter a supported two-letter Adzuna country code "
                "(for example 'gb' or 'us').",
            )
        query = _validated_query(search_query, "search query")
        base = (
            "https://api.adzuna.com/v1/api/jobs/"
            f"{cleaned_country}/search/1"
        )
        if query:
            base = f"{base}?{urlencode({'what': query})}"
        key_suffix = quote(query.lower(), safe="") or "all"
        return f"adzuna:{cleaned_country}:{key_suffix}", base
    if provider_type == "reed":
        missing = _reed_missing_keys(settings)
        if missing:
            raise ProviderCatalogError(missing)
        query = _validated_query(search_query, "search keywords")
        location = _validated_query(country, "location")
        params: dict[str, str] = {"resultsToTake": "100"}
        if query:
            params["keywords"] = query
        if location:
            params["locationName"] = location
        base = f"https://www.reed.co.uk/api/1.0/search?{urlencode(params)}"
        key_suffix = quote(
            f"{query.lower()}:{location.lower()}", safe=":"
        )
        return f"reed:{key_suffix or 'all'}", base
    raise ProviderCatalogError(
        "Unknown or unsupported job source provider.",
        status_code=404,
    )


def connect_provider_source(
    provider_type: str,
    display_name: str,
    database: Session,
    *,
    board_token: str | None = None,
    country: str | None = None,
    search_query: str | None = None,
    settings: Settings | None = None,
) -> JobSource:
    """Connect one of the approved free providers as a job source.

    Mirrors ``connect_greenhouse_board``: only well-understood public
    endpoints are configured, and every compliance gate is set to the
    approved state for that pinned endpoint shape.
    """
    get_provider_spec(provider_type)
    trimmed_name = display_name.strip()
    if not trimmed_name:
        raise ProviderCatalogError(
            "Enter a display name for this job source.",
        )

    active_settings = settings or get_settings()
    source_key, base_url = build_connect_source(
        provider_type,
        board_token=board_token,
        display_name=trimmed_name,
        country=country,
        search_query=search_query,
        settings=active_settings,
    )

    now = current_utc_time()
    source = JobSource(
        source_key=source_key,
        display_name=trimmed_name,
        source_category=SOURCE_CATEGORY,
        provider_type=provider_type,
        base_url=base_url,
        enabled=True,
        allowlisted=True,
        access_mode=ACCESS_MODE,
        server_fetch_allowed=True,
        manual_review_required=False,
        terms_review_status=APPROVED_REVIEW_STATUS,
        terms_reviewed_at=now,
        robots_review_status=APPROVED_REVIEW_STATUS,
        robots_reviewed_at=now,
        commercial_use_review_status=APPROVED_REVIEW_STATUS,
        configured_retention_days=CONNECT_RETENTION_DAYS,
    )

    database.add(source)
    try:
        database.commit()
    except IntegrityError as exc:
        database.rollback()
        raise ProviderCatalogError(
            "That job source is already connected.",
            status_code=409,
        ) from exc

    database.refresh(source)
    return source


# --- Ingest -----------------------------------------------------------------


def validate_provider_source(
    source: JobSource,
    spec: ProviderSpec,
) -> None:
    """Enforce every compliance gate before any server fetch."""
    if source.provider_type != spec.provider_type:
        raise ProviderCatalogError(
            "Job source is not configured for this provider.",
        )
    if not source.enabled:
        raise ProviderCatalogError("Job source is not enabled.")
    if not source.allowlisted:
        raise ProviderCatalogError("Job source is not allowlisted.")
    if not source.server_fetch_allowed:
        raise ProviderCatalogError(
            "Server fetching is not allowed for this job source.",
        )
    if source.access_mode != ACCESS_MODE:
        raise ProviderCatalogError(
            "Job source access mode does not permit API fetching.",
        )
    review_statuses = {
        source.terms_review_status,
        source.robots_review_status,
        source.commercial_use_review_status,
    }
    if review_statuses != {APPROVED_REVIEW_STATUS}:
        raise ProviderCatalogError(
            "Job source policy review is not approved for "
            "configured use.",
        )
    if not source.base_url or not spec.base_url_re.fullmatch(
        source.base_url
    ):
        raise ProviderCatalogError(
            "Job source base URL is not an approved provider URL.",
        )


def fetch_provider_payload(
    source: JobSource,
    spec: ProviderSpec,
    http_client: httpx.Client,
    settings: Settings,
) -> bytes:
    fetch_url = spec.build_fetch_url(source, settings)
    headers = spec.fetch_headers(settings) if spec.fetch_headers else {}

    try:
        response = http_client.get(fetch_url, headers=headers)
    except httpx.HTTPError as exc:
        raise ProviderCatalogError(
            "Provider request failed before a response was received.",
        ) from exc

    if response.status_code != 200:
        raise ProviderCatalogError(
            f"Provider returned HTTP status {response.status_code}.",
        )

    content_type = response.headers.get("content-type", "")
    if "json" not in content_type.lower():
        raise ProviderCatalogError("Provider response was not JSON.")

    if len(response.content) > settings.max_source_snapshot_payload_bytes:
        raise ProviderCatalogError(
            "Provider payload exceeded the permitted size.",
        )

    return response.content


def _fail_run(
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


def ingest_job_source(
    source_id: int,
    database: Session,
    *,
    http_client: httpx.Client | None = None,
) -> IngestionRun:
    """Dispatch ingestion by provider: Greenhouse keeps its original
    adapter; every catalog provider uses the shared pipeline."""
    from app.services.provider_greenhouse import (
        ingest_greenhouse_source,
    )

    source = database.get(JobSource, source_id)
    if source is None:
        raise ProviderCatalogError(
            "Job source was not found.",
            status_code=404,
        )
    if source.provider_type == "greenhouse":
        return ingest_greenhouse_source(
            source_id,
            database,
            http_client=http_client,
        )
    return ingest_provider_source(
        source_id,
        database,
        http_client=http_client,
    )


def ingest_provider_source(
    source_id: int,
    database: Session,
    *,
    http_client: httpx.Client | None = None,
) -> IngestionRun:
    """Run one compliance-gated ingestion for a catalog provider."""
    source = database.get(JobSource, source_id)
    if source is None:
        raise ProviderCatalogError(
            "Job source was not found.",
            status_code=404,
        )

    spec = get_provider_spec(source.provider_type)
    validate_provider_source(source, spec)

    settings = get_settings()
    if spec.requires_keys is not None:
        missing = spec.requires_keys(settings)
        if missing:
            raise ProviderCatalogError(missing)

    try:
        run = create_ingestion_run(
            IngestionRunCreate(job_source_id=source.id),
            database,
        )
        run = start_ingestion_run(run.id, database)
    except IngestionServiceError as exc:
        raise ProviderCatalogError(
            exc.safe_message,
            status_code=exc.status_code,
        ) from exc

    client = http_client or build_http_client()
    owns_client = http_client is None

    try:
        payload = fetch_provider_payload(source, spec, client, settings)
    except ProviderCatalogError as exc:
        return _fail_run(run.id, exc.safe_message, database)
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
        return _fail_run(run.id, exc.safe_message, database)

    try:
        jobs = spec.parse_jobs(payload)
        entries = [spec.map_job(source, job) for job in jobs]
        discovered, updated = upsert_provider_jobs(
            source,
            entries,
            database,
        )
    except (ProviderCatalogError, JobNormalizationError) as exc:
        message = (
            exc.safe_message
            if isinstance(
                exc, (ProviderCatalogError, JobNormalizationError)
            )
            else "Provider ingestion failed."
        )
        return _fail_run(run.id, message, database)

    return complete_ingestion_run(
        run.id,
        IngestionRunCompletion(
            run_status="succeeded",
            jobs_discovered=discovered,
            jobs_updated=updated,
        ),
        database,
    )
