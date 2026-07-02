from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.models.job import (
    JobDuplicate,
    JobLocation,
    JobSource,
    NormalizedJob,
)
from app.schemas.job import (
    JobLocationCreate,
    JobSourceCreate,
    NormalizedJobCreate,
)
from app.services.job import create_job_source
from app.services.job_normalization import (
    current_utc_time,
    detect_job_duplicates,
    evaluate_job_freshness,
    run_job_maintenance,
    upsert_provider_jobs,
)


PHASE42_HEAD = "c9d0e1f2a3b4"
PHASE44_HEAD = "d0e1f2a3b4c5"


def content_hash(seed: str | None = None) -> str:
    return sha256((seed or uuid4().hex).encode()).hexdigest()


def make_source(database: Session, **overrides: object) -> JobSource:
    payload: dict[str, object] = {
        "source_key": f"source-{uuid4().hex[:12]}",
        "display_name": f"Synthetic Source {uuid4().hex[:8]}",
        "source_category": "provider_api",
        "provider_type": "greenhouse",
    }
    payload.update(overrides)
    return create_job_source(JobSourceCreate(**payload), database)


def job_create(
    source: JobSource,
    **overrides: object,
) -> NormalizedJobCreate:
    payload: dict[str, object] = {
        "job_source_id": source.id,
        "source_job_id": f"job-{uuid4().hex[:16]}",
        "source_url": f"https://jobs.example.com/{uuid4().hex}",
        "employer_name": "Example Robotics",
        "title": "Platform Engineer",
        "content_hash": content_hash(),
        "normalization_version": "phase4.4-test",
    }
    payload.update(overrides)
    return NormalizedJobCreate(**payload)


def upsert_one(
    database: Session,
    source: JobSource,
    data: NormalizedJobCreate,
    locations: list[JobLocationCreate] | None = None,
) -> NormalizedJob:
    upsert_provider_jobs(
        source,
        [(data, locations or [])],
        database,
    )
    job = database.scalar(
        select(NormalizedJob).where(
            NormalizedJob.job_source_id == source.id,
            NormalizedJob.source_job_id == data.source_job_id,
        )
    )
    assert job is not None
    return job


def test_upsert_creates_then_touches_without_content_change(
    db_session: Session,
) -> None:
    source = make_source(db_session)
    data = job_create(source)

    job = upsert_one(db_session, source, data)
    original_hash = job.content_hash
    original_description = job.description_text

    discovered, updated = upsert_provider_jobs(
        source,
        [(data, [])],
        db_session,
    )

    assert (discovered, updated) == (0, 1)
    db_session.refresh(job)
    assert job.content_hash == original_hash
    assert job.description_text == original_description


def test_content_change_refreshes_provider_fields(
    db_session: Session,
) -> None:
    source = make_source(db_session)
    data = job_create(
        source,
        description_text="Original description.",
    )
    job = upsert_one(
        db_session,
        source,
        data,
        [JobLocationCreate(raw_location_text="London")],
    )

    changed = job_create(
        source,
        source_job_id=data.source_job_id,
        source_url=data.source_url,
        title="Senior Platform Engineer",
        description_text="Updated description.",
        content_hash=content_hash("changed"),
    )
    discovered, updated = upsert_provider_jobs(
        source,
        [(changed, [JobLocationCreate(raw_location_text="Berlin")])],
        db_session,
    )

    assert (discovered, updated) == (0, 1)
    db_session.refresh(job)
    assert job.title == "Senior Platform Engineer"
    assert job.description_text == "Updated description."
    assert job.content_hash == content_hash("changed")

    locations = list(
        db_session.scalars(
            select(JobLocation).where(JobLocation.job_id == job.id)
        ).all()
    )
    assert [item.raw_location_text for item in locations] == ["Berlin"]


def test_reseen_job_is_promoted_to_active(db_session: Session) -> None:
    source = make_source(db_session)
    data = job_create(source)
    job = upsert_one(db_session, source, data)
    assert job.lifecycle_status == "discovered"

    upsert_provider_jobs(source, [(data, [])], db_session)

    db_session.refresh(job)
    assert job.lifecycle_status == "active"


def test_expired_job_is_reactivated_when_reseen(
    db_session: Session,
) -> None:
    source = make_source(db_session)
    data = job_create(source)
    job = upsert_one(db_session, source, data)
    job.lifecycle_status = "expired"
    db_session.commit()

    upsert_provider_jobs(source, [(data, [])], db_session)

    db_session.refresh(job)
    assert job.lifecycle_status == "active"


def test_freshness_marks_expired_jobs(db_session: Session) -> None:
    source = make_source(db_session)
    now = current_utc_time()
    job = upsert_one(
        db_session,
        source,
        job_create(source, expires_at=now - timedelta(days=1)),
    )

    results = evaluate_job_freshness(db_session, now=now)

    assert results["jobs_marked_expired"] == 1
    db_session.refresh(job)
    assert job.lifecycle_status == "expired"


def test_freshness_marks_stale_jobs(db_session: Session) -> None:
    source = make_source(db_session)
    now = current_utc_time()
    job = upsert_one(
        db_session,
        source,
        job_create(source, last_seen_at=now - timedelta(days=30)),
    )

    results = evaluate_job_freshness(db_session, now=now)

    assert results["jobs_marked_possibly_stale"] == 1
    db_session.refresh(job)
    assert job.lifecycle_status == "possibly_stale"


def test_freshness_leaves_fresh_jobs_untouched(
    db_session: Session,
) -> None:
    source = make_source(db_session)
    job = upsert_one(db_session, source, job_create(source))

    results = evaluate_job_freshness(db_session)

    assert results == {
        "jobs_marked_expired": 0,
        "jobs_marked_possibly_stale": 0,
    }
    db_session.refresh(job)
    assert job.lifecycle_status == "discovered"


def test_freshness_never_deletes_jobs(db_session: Session) -> None:
    source = make_source(db_session)
    now = current_utc_time()
    upsert_one(
        db_session,
        source,
        job_create(source, expires_at=now - timedelta(days=5)),
    )
    upsert_one(
        db_session,
        source,
        job_create(source, last_seen_at=now - timedelta(days=60)),
    )

    evaluate_job_freshness(db_session, now=now)

    remaining = list(db_session.scalars(select(NormalizedJob.id)).all())
    assert len(remaining) == 2


def test_cross_source_duplicates_by_canonical_url(
    db_session: Session,
) -> None:
    source_a = make_source(db_session)
    source_b = make_source(db_session)
    shared_url = "https://careers.example.com/shared-role"
    first = upsert_one(
        db_session,
        source_a,
        job_create(source_a, canonical_url=shared_url),
    )
    second = upsert_one(
        db_session,
        source_b,
        job_create(source_b, canonical_url=shared_url),
    )

    results = detect_job_duplicates(db_session)

    assert results["duplicate_links_created"] == 1
    link = db_session.scalar(select(JobDuplicate))
    assert link is not None
    assert link.job_id == second.id
    assert link.duplicate_of_job_id == first.id
    assert link.detection_method == "canonical_url"


def test_duplicates_by_content_hash(db_session: Session) -> None:
    source_a = make_source(db_session)
    source_b = make_source(db_session)
    shared_hash = content_hash("identical-content")
    upsert_one(
        db_session,
        source_a,
        job_create(source_a, content_hash=shared_hash),
    )
    upsert_one(
        db_session,
        source_b,
        job_create(source_b, content_hash=shared_hash),
    )

    results = detect_job_duplicates(db_session)

    assert results["duplicate_links_created"] == 1
    link = db_session.scalar(select(JobDuplicate))
    assert link is not None
    assert link.detection_method == "content_hash"


def test_duplicate_detection_is_idempotent(db_session: Session) -> None:
    source_a = make_source(db_session)
    source_b = make_source(db_session)
    shared_url = "https://careers.example.com/idempotent-role"
    upsert_one(
        db_session,
        source_a,
        job_create(source_a, canonical_url=shared_url),
    )
    upsert_one(
        db_session,
        source_b,
        job_create(source_b, canonical_url=shared_url),
    )

    first_pass = detect_job_duplicates(db_session)
    second_pass = detect_job_duplicates(db_session)

    assert first_pass["duplicate_links_created"] == 1
    assert second_pass["duplicate_links_created"] == 0
    links = list(db_session.scalars(select(JobDuplicate.id)).all())
    assert len(links) == 1


def test_no_fuzzy_duplicate_detection(db_session: Session) -> None:
    """Similar titles alone must never create duplicate links."""
    source = make_source(db_session)
    upsert_one(
        db_session,
        source,
        job_create(source, title="Platform Engineer"),
    )
    upsert_one(
        db_session,
        source,
        job_create(source, title="Platform Engineer II"),
    )

    results = detect_job_duplicates(db_session)

    assert results["duplicate_links_created"] == 0
    assert db_session.scalar(select(JobDuplicate)) is None


def test_duplicate_detection_never_deletes_jobs(
    db_session: Session,
) -> None:
    source_a = make_source(db_session)
    source_b = make_source(db_session)
    shared_url = "https://careers.example.com/preserved-role"
    upsert_one(
        db_session,
        source_a,
        job_create(source_a, canonical_url=shared_url),
    )
    upsert_one(
        db_session,
        source_b,
        job_create(source_b, canonical_url=shared_url),
    )

    detect_job_duplicates(db_session)

    jobs = list(db_session.scalars(select(NormalizedJob.id)).all())
    assert len(jobs) == 2


def test_run_job_maintenance_combines_results(
    db_session: Session,
) -> None:
    source = make_source(db_session)
    now = current_utc_time()
    upsert_one(
        db_session,
        source,
        job_create(source, expires_at=now - timedelta(days=1)),
    )

    results = run_job_maintenance(db_session, now=now)

    assert results["jobs_marked_expired"] == 1
    assert results["jobs_marked_possibly_stale"] == 0
    assert results["duplicate_links_created"] == 0


def test_maintenance_endpoint(
    client: TestClient,
    db_session: Session,
) -> None:
    source = make_source(db_session)
    upsert_one(db_session, source, job_create(source))

    response = client.post("/api/jobs/maintenance")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "jobs_marked_expired",
        "jobs_marked_possibly_stale",
        "duplicate_links_created",
    }


def test_job_duplicates_endpoint_and_404(
    client: TestClient,
    db_session: Session,
) -> None:
    source_a = make_source(db_session)
    source_b = make_source(db_session)
    shared_url = "https://careers.example.com/endpoint-role"
    first = upsert_one(
        db_session,
        source_a,
        job_create(source_a, canonical_url=shared_url),
    )
    second = upsert_one(
        db_session,
        source_b,
        job_create(source_b, canonical_url=shared_url),
    )
    detect_job_duplicates(db_session)

    for job_id in (first.id, second.id):
        response = client.get(f"/api/jobs/{job_id}/duplicates")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["detection_method"] == "canonical_url"

    missing = client.get("/api/jobs/987654/duplicates")
    assert missing.status_code == 404


def test_duplicate_rejects_self_link(db_session: Session) -> None:
    source = make_source(db_session)
    job = upsert_one(db_session, source, job_create(source))

    with pytest.raises(Exception):
        db_session.add(
            JobDuplicate(
                job_id=job.id,
                duplicate_of_job_id=job.id,
                detection_method="canonical_url",
            )
        )
        db_session.commit()
    db_session.rollback()


def test_phase44_migration_upgrade_downgrade_reupgrade(
    tmp_path: Path,
) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    migration_db = tmp_path / "phase44-migration.db"

    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{migration_db}")

    command.upgrade(config, PHASE44_HEAD)
    engine = create_engine(f"sqlite:///{migration_db}")
    assert "job_duplicates" in set(inspect(engine).get_table_names())
    engine.dispose()

    command.downgrade(config, PHASE42_HEAD)
    engine = create_engine(f"sqlite:///{migration_db}")
    tables = set(inspect(engine).get_table_names())
    assert "job_duplicates" not in tables
    assert "normalized_jobs" in tables
    engine.dispose()

    command.upgrade(config, PHASE44_HEAD)
    engine = create_engine(f"sqlite:///{migration_db}")
    assert "job_duplicates" in set(inspect(engine).get_table_names())
    engine.dispose()
