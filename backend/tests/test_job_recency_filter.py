"""Tests for the recency filters on GET /api/jobs (latest / last 24h)."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.job import NormalizedJob
from app.schemas.job import JobSourceCreate, NormalizedJobCreate
from app.services.job import (
    create_job_source,
    create_normalized_job,
    list_normalized_jobs,
)


from app.api.routes.auth import login_rate_limiter


@pytest.fixture(autouse=True)
def _reset_auth_rate_limiter() -> None:
    login_rate_limiter.reset()


NOW = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)


def content_hash(seed: str | None = None) -> str:
    return sha256((seed or uuid4().hex).encode()).hexdigest()


def make_job(
    database: Session,
    *,
    title: str,
    posted_at: datetime | None,
    last_seen_at: datetime,
) -> NormalizedJob:
    source = create_job_source(
        JobSourceCreate(
            source_key=f"source-{uuid4().hex[:12]}",
            display_name="Example Robotics",
            source_category="provider_api",
        ),
        database,
    )
    job = create_normalized_job(
        NormalizedJobCreate(
            job_source_id=source.id,
            source_job_id=f"job-{uuid4().hex[:16]}",
            source_url=f"https://jobs.example.com/{uuid4().hex}",
            employer_name="Example Robotics",
            title=title,
            content_hash=content_hash(),
            normalization_version="recency-test",
        ),
        database,
    )
    job.posted_at = posted_at
    job.last_seen_at = last_seen_at
    database.add(job)
    database.commit()
    database.refresh(job)
    return job


def test_posted_within_hours_filters_by_posted_at(
    db_session: Session,
) -> None:
    make_job(
        db_session,
        title="Fresh Role",
        posted_at=NOW - timedelta(hours=2),
        last_seen_at=NOW,
    )
    make_job(
        db_session,
        title="Old Role",
        posted_at=NOW - timedelta(hours=48),
        last_seen_at=NOW,
    )
    make_job(
        db_session,
        title="No Posted Date",
        posted_at=None,
        last_seen_at=NOW,
    )

    result = list_normalized_jobs(
        db_session,
        posted_within_hours=24,
        now=NOW,
    )
    titles = {item["title"] for item in result["items"]}
    assert titles == {"Fresh Role"}
    assert result["total"] == 1


def test_updated_within_hours_filters_by_last_seen(
    db_session: Session,
) -> None:
    make_job(
        db_session,
        title="Seen Recently",
        posted_at=None,
        last_seen_at=NOW - timedelta(hours=3),
    )
    make_job(
        db_session,
        title="Seen Long Ago",
        posted_at=None,
        last_seen_at=NOW - timedelta(hours=72),
    )

    result = list_normalized_jobs(
        db_session,
        updated_within_hours=24,
        now=NOW,
    )
    titles = {item["title"] for item in result["items"]}
    assert titles == {"Seen Recently"}


def test_no_recency_filter_returns_all(db_session: Session) -> None:
    make_job(
        db_session,
        title="A",
        posted_at=NOW - timedelta(hours=100),
        last_seen_at=NOW - timedelta(hours=100),
    )
    make_job(
        db_session,
        title="B",
        posted_at=NOW,
        last_seen_at=NOW,
    )
    result = list_normalized_jobs(db_session, now=NOW)
    assert result["total"] == 2


def test_recency_filter_via_api(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    now = datetime.now(timezone.utc)
    make_job(
        db_session,
        title="API Fresh",
        posted_at=now - timedelta(hours=1),
        last_seen_at=now,
    )
    make_job(
        db_session,
        title="API Stale",
        posted_at=now - timedelta(hours=100),
        last_seen_at=now,
    )

    response = auth_client.get("/api/jobs", params={"posted_within_hours": 24})
    assert response.status_code == 200
    titles = {item["title"] for item in response.json()["items"]}
    assert titles == {"API Fresh"}


def test_api_rejects_invalid_hours(auth_client: TestClient) -> None:
    assert (
        auth_client.get("/api/jobs", params={"posted_within_hours": 0})
    ).status_code == 422
    assert (
        auth_client.get("/api/jobs", params={"updated_within_hours": 99999})
    ).status_code == 422
