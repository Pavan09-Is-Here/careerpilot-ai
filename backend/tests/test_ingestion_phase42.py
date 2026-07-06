from datetime import timedelta
from hashlib import sha256
from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.models.ingestion import IngestionRun, SourceSnapshot
from app.models.job import JobSource, NormalizedJob
from app.schemas.ingestion import (
    IngestionRunCompletion,
    IngestionRunCreate,
    SourceSnapshotCreate,
)
from app.schemas.job import JobSourceCreate, NormalizedJobCreate
from app.services.ingestion import (
    IngestionServiceError,
    cleanup_expired_source_snapshots,
    complete_ingestion_run,
    create_ingestion_run,
    current_utc_time,
    record_source_snapshot,
    start_ingestion_run,
)
from app.services.job import create_job_source, create_normalized_job


from app.api.routes.auth import login_rate_limiter


@pytest.fixture(autouse=True)
def _reset_auth_rate_limiter() -> None:
    login_rate_limiter.reset()



PHASE41_HEAD = "b8c9d0e1f2a3"
PHASE42_HEAD = "c9d0e1f2a3b4"


def content_hash(seed: str | None = None) -> str:
    return sha256((seed or uuid4().hex).encode()).hexdigest()


def enabled_source(database: Session, **overrides: object) -> JobSource:
    payload: dict[str, object] = {
        "source_key": f"source-{uuid4().hex[:12]}",
        "display_name": f"Synthetic Source {uuid4().hex[:8]}",
        "source_category": "provider_api",
        "provider_type": "none",
        "allowlisted": True,
        "enabled": True,
        "manual_review_required": True,
        "terms_review_status": "approved_for_configured_use",
        "robots_review_status": "approved_for_configured_use",
        "commercial_use_review_status": "approved_for_configured_use",
    }
    payload.update(overrides)
    return create_job_source(JobSourceCreate(**payload), database)


def disabled_source(database: Session) -> JobSource:
    return create_job_source(
        JobSourceCreate(
            source_key=f"source-{uuid4().hex[:12]}",
            display_name=f"Disabled Source {uuid4().hex[:8]}",
            source_category="provider_api",
        ),
        database,
    )


def make_run(
    database: Session,
    *,
    source: JobSource | None = None,
) -> IngestionRun:
    active_source = source or enabled_source(database)
    return create_ingestion_run(
        IngestionRunCreate(job_source_id=active_source.id),
        database,
    )


def make_running_run(
    database: Session,
    *,
    source: JobSource | None = None,
) -> IngestionRun:
    run = make_run(database, source=source)
    return start_ingestion_run(run.id, database)


def snapshot_payload(
    run: IngestionRun,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "ingestion_run_id": run.id,
        "content_hash": content_hash(),
        "payload_size_bytes": 2048,
        "payload_media_type": "application/json",
    }
    payload.update(overrides)
    return payload


def make_snapshot(
    database: Session,
    run: IngestionRun | None = None,
    **overrides: object,
) -> SourceSnapshot:
    active_run = run or make_running_run(database)
    return record_source_snapshot(
        SourceSnapshotCreate(**snapshot_payload(active_run, **overrides)),
        database,
    )


def make_job(database: Session, source: JobSource) -> NormalizedJob:
    return create_normalized_job(
        NormalizedJobCreate(
            job_source_id=source.id,
            source_job_id=f"job-{uuid4().hex[:16]}",
            source_url=f"https://jobs.example.com/{uuid4().hex}",
            employer_name="Example Robotics",
            title="Platform Engineer",
            content_hash=content_hash(),
            normalization_version="phase4.2-test",
        ),
        database,
    )


def test_run_creation_defaults(db_session: Session) -> None:
    run = make_run(db_session)

    assert run.run_status == "pending"
    assert run.started_at is None
    assert run.finished_at is None
    assert run.failure_summary is None
    assert run.jobs_discovered == 0
    assert run.jobs_updated == 0
    assert run.snapshots_recorded == 0


def test_run_requires_existing_source(db_session: Session) -> None:
    with pytest.raises(IngestionServiceError) as error:
        create_ingestion_run(
            IngestionRunCreate(job_source_id=987654),
            db_session,
        )

    assert "not found" in error.value.safe_message


def test_run_requires_enabled_source(db_session: Session) -> None:
    source = disabled_source(db_session)

    with pytest.raises(IngestionServiceError) as error:
        create_ingestion_run(
            IngestionRunCreate(job_source_id=source.id),
            db_session,
        )

    assert "enabled" in error.value.safe_message


def test_run_start_sets_started_at(db_session: Session) -> None:
    run = make_running_run(db_session)

    assert run.run_status == "running"
    assert run.started_at is not None
    assert run.finished_at is None


def test_run_success_completion(db_session: Session) -> None:
    run = make_running_run(db_session)
    completed = complete_ingestion_run(
        run.id,
        IngestionRunCompletion(
            run_status="succeeded",
            jobs_discovered=5,
            jobs_updated=2,
        ),
        db_session,
    )

    assert completed.run_status == "succeeded"
    assert completed.finished_at is not None
    assert completed.jobs_discovered == 5
    assert completed.jobs_updated == 2
    assert completed.failure_summary is None


def test_failed_run_requires_failure_summary(db_session: Session) -> None:
    run = make_running_run(db_session)

    with pytest.raises(IngestionServiceError) as error:
        complete_ingestion_run(
            run.id,
            IngestionRunCompletion(run_status="failed"),
            db_session,
        )

    assert "failure summary" in error.value.safe_message


def test_succeeded_run_rejects_failure_summary(db_session: Session) -> None:
    run = make_running_run(db_session)

    with pytest.raises(IngestionServiceError):
        complete_ingestion_run(
            run.id,
            IngestionRunCompletion(
                run_status="succeeded",
                failure_summary="should not be here",
            ),
            db_session,
        )


def test_failure_summary_rejects_control_characters(
    db_session: Session,
) -> None:
    run = make_running_run(db_session)

    with pytest.raises(IngestionServiceError):
        complete_ingestion_run(
            run.id,
            IngestionRunCompletion(
                run_status="failed",
                failure_summary="bad\x00summary",
            ),
            db_session,
        )


@pytest.mark.parametrize(
    ("initial_status", "next_call"),
    [
        ("succeeded", "start"),
        ("succeeded", "complete"),
        ("failed", "start"),
        ("cancelled", "complete"),
    ],
)
def test_terminal_runs_reject_further_transitions(
    db_session: Session,
    initial_status: str,
    next_call: str,
) -> None:
    run = make_running_run(db_session)
    completion = IngestionRunCompletion(
        run_status=initial_status,  # type: ignore[arg-type]
        failure_summary=(
            "Synthetic failure." if initial_status == "failed" else None
        ),
    )
    complete_ingestion_run(run.id, completion, db_session)

    with pytest.raises(IngestionServiceError):
        if next_call == "start":
            start_ingestion_run(run.id, db_session)
        else:
            complete_ingestion_run(
                run.id,
                IngestionRunCompletion(run_status="cancelled"),
                db_session,
            )


def test_pending_run_can_be_cancelled(db_session: Session) -> None:
    run = make_run(db_session)
    cancelled = complete_ingestion_run(
        run.id,
        IngestionRunCompletion(run_status="cancelled"),
        db_session,
    )

    assert cancelled.run_status == "cancelled"
    assert cancelled.finished_at is not None


def test_completion_counters_are_bounded() -> None:
    with pytest.raises(ValidationError):
        IngestionRunCompletion(
            run_status="succeeded",
            jobs_discovered=1_000_001,
        )

    with pytest.raises(ValidationError):
        IngestionRunCompletion(
            run_status="succeeded",
            jobs_updated=-1,
        )


def test_snapshot_counter_increments_per_snapshot(
    db_session: Session,
) -> None:
    run = make_running_run(db_session)
    make_snapshot(db_session, run)
    make_snapshot(db_session, run)

    db_session.refresh(run)
    assert run.snapshots_recorded == 2


def test_snapshot_requires_running_run(db_session: Session) -> None:
    run = make_run(db_session)

    with pytest.raises(IngestionServiceError) as error:
        record_source_snapshot(
            SourceSnapshotCreate(**snapshot_payload(run)),
            db_session,
        )

    assert "running" in error.value.safe_message


def test_snapshot_defaults_and_counter(db_session: Session) -> None:
    run = make_running_run(db_session)
    snapshot = make_snapshot(db_session, run)

    db_session.refresh(run)
    assert snapshot.ingestion_run_id == run.id
    assert snapshot.job_source_id == run.job_source_id
    assert snapshot.fetched_at is not None
    assert snapshot.expires_at > snapshot.fetched_at
    assert run.snapshots_recorded == 1


def test_snapshot_expiry_uses_source_retention(
    db_session: Session,
) -> None:
    source = enabled_source(db_session, configured_retention_days=7)
    run = make_running_run(db_session, source=source)
    snapshot = make_snapshot(db_session, run)

    delta = snapshot.expires_at - snapshot.fetched_at
    assert delta == timedelta(days=7)


def test_snapshot_rejects_expiry_before_fetch(db_session: Session) -> None:
    run = make_running_run(db_session)
    now = current_utc_time()

    with pytest.raises(IngestionServiceError):
        make_snapshot(
            db_session,
            run,
            fetched_at=now,
            expires_at=now - timedelta(hours=1),
        )


def test_snapshot_rejects_expiry_beyond_max_retention(
    db_session: Session,
) -> None:
    run = make_running_run(db_session)
    now = current_utc_time()

    with pytest.raises(IngestionServiceError):
        make_snapshot(
            db_session,
            run,
            fetched_at=now,
            expires_at=now + timedelta(days=400),
        )


def test_snapshot_rejects_invalid_content_hash(db_session: Session) -> None:
    run = make_running_run(db_session)

    with pytest.raises(IngestionServiceError):
        make_snapshot(db_session, run, content_hash="A" * 64)


def test_snapshot_rejects_oversized_payload(db_session: Session) -> None:
    run = make_running_run(db_session)

    with pytest.raises(IngestionServiceError):
        make_snapshot(
            db_session,
            run,
            payload_size_bytes=200 * 1024 * 1024,
        )


@pytest.mark.parametrize(
    "media_type",
    ["not-a-media-type", "TEXT/HTML", "a/b/c", "application/"],
)
def test_snapshot_rejects_invalid_media_type(
    db_session: Session,
    media_type: str,
) -> None:
    run = make_running_run(db_session)

    with pytest.raises(IngestionServiceError):
        make_snapshot(db_session, run, payload_media_type=media_type)


@pytest.mark.parametrize(
    "reference",
    ["../escape", "/etc/passwd", "a b", "dir/inner", ".hidden"],
)
def test_snapshot_rejects_unsafe_storage_reference(
    db_session: Session,
    reference: str,
) -> None:
    run = make_running_run(db_session)

    with pytest.raises(IngestionServiceError):
        make_snapshot(db_session, run, storage_reference=reference)


def test_retention_cleanup_deletes_only_expired_snapshots(
    db_session: Session,
) -> None:
    run = make_running_run(db_session)
    now = current_utc_time()
    expired = make_snapshot(
        db_session,
        run,
        fetched_at=now - timedelta(days=10),
        expires_at=now - timedelta(days=1),
    )
    live = make_snapshot(
        db_session,
        run,
        fetched_at=now,
        expires_at=now + timedelta(days=10),
    )

    deleted = cleanup_expired_source_snapshots(db_session, now=now)

    assert deleted == 1
    remaining = list(db_session.scalars(select(SourceSnapshot.id)).all())
    assert remaining == [live.id]
    assert db_session.get(SourceSnapshot, expired.id) is None


def test_retention_cleanup_preserves_job_provenance(
    db_session: Session,
) -> None:
    source = enabled_source(db_session)
    run = make_running_run(db_session, source=source)
    job = make_job(db_session, source)
    now = current_utc_time()
    make_snapshot(
        db_session,
        run,
        fetched_at=now - timedelta(days=10),
        expires_at=now - timedelta(days=1),
    )

    deleted = cleanup_expired_source_snapshots(db_session, now=now)

    assert deleted == 1
    assert db_session.get(NormalizedJob, job.id) is not None
    assert db_session.get(IngestionRun, run.id) is not None
    assert db_session.get(JobSource, source.id) is not None


def test_retention_cleanup_with_no_expired_snapshots(
    db_session: Session,
) -> None:
    run = make_running_run(db_session)
    make_snapshot(db_session, run)

    deleted = cleanup_expired_source_snapshots(db_session)

    assert deleted == 0


def test_list_runs_endpoint(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    source = enabled_source(db_session)
    first = make_run(db_session, source=source)
    second = make_run(db_session, source=source)

    response = auth_client.get("/api/ingestion-runs")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    returned_ids = {item["id"] for item in body["items"]}
    assert returned_ids == {first.id, second.id}


def test_list_runs_filters_by_source_and_status(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    source_a = enabled_source(db_session)
    source_b = enabled_source(db_session)
    run_a = make_running_run(db_session, source=source_a)
    make_run(db_session, source=source_b)

    response = auth_client.get(
        "/api/ingestion-runs",
        params={"source": source_a.id, "run_status": "running"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == run_a.id


def test_list_runs_rejects_invalid_status(auth_client: TestClient) -> None:
    response = auth_client.get(
        "/api/ingestion-runs",
        params={"run_status": "exploded"},
    )

    assert response.status_code == 422


def test_get_run_detail_and_404(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    run = make_run(db_session)

    found = auth_client.get(f"/api/ingestion-runs/{run.id}")
    missing = auth_client.get("/api/ingestion-runs/987654")

    assert found.status_code == 200
    assert found.json()["id"] == run.id
    assert missing.status_code == 404


def test_run_snapshots_endpoint_and_404(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    run = make_running_run(db_session)
    snapshot = make_snapshot(db_session, run)

    found = auth_client.get(f"/api/ingestion-runs/{run.id}/snapshots")
    missing = auth_client.get("/api/ingestion-runs/987654/snapshots")

    assert found.status_code == 200
    body = found.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == snapshot.id
    assert missing.status_code == 404


def test_snapshot_responses_never_expose_payload_or_storage(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    run = make_running_run(db_session)
    make_snapshot(
        db_session,
        run,
        storage_reference=f"snapshot-{uuid4().hex}",
    )

    response = auth_client.get(f"/api/ingestion-runs/{run.id}/snapshots")

    assert response.status_code == 200
    item = response.json()["items"][0]
    forbidden_fragments = ("storage", "payload_body", "raw", "path")
    for key in item:
        for fragment in forbidden_fragments:
            assert fragment not in key.lower()
    assert "storage_reference" not in item


def test_run_pagination_bounds(auth_client: TestClient) -> None:
    too_large = auth_client.get(
        "/api/ingestion-runs",
        params={"page_size": 1000},
    )
    zero_page = auth_client.get(
        "/api/ingestion-runs",
        params={"page": 0},
    )

    assert too_large.status_code == 422
    assert zero_page.status_code == 422


def test_ingestion_tables_have_no_credential_columns() -> None:
    from app.models.ingestion import IngestionRun as RunModel
    from app.models.ingestion import SourceSnapshot as SnapshotModel

    forbidden_fragments = ("secret", "token", "credential", "api_key")
    for model in (RunModel, SnapshotModel):
        for column in model.__table__.columns:
            for fragment in forbidden_fragments:
                assert fragment not in column.name.lower()


def test_phase42_migration_upgrade_downgrade_reupgrade(
    tmp_path: Path,
) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    migration_db = tmp_path / "phase42-migration.db"

    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{migration_db}")

    command.upgrade(config, PHASE42_HEAD)
    engine = create_engine(f"sqlite:///{migration_db}")
    tables = set(inspect(engine).get_table_names())
    assert "ingestion_runs" in tables
    assert "source_snapshots" in tables
    engine.dispose()

    command.downgrade(config, PHASE41_HEAD)
    engine = create_engine(f"sqlite:///{migration_db}")
    tables = set(inspect(engine).get_table_names())
    assert "ingestion_runs" not in tables
    assert "source_snapshots" not in tables
    assert "normalized_jobs" in tables
    engine.dispose()

    command.upgrade(config, PHASE42_HEAD)
    engine = create_engine(f"sqlite:///{migration_db}")
    tables = set(inspect(engine).get_table_names())
    assert "ingestion_runs" in tables
    assert "source_snapshots" in tables
    engine.dispose()


def test_phase42_downgrade_preserves_job_rows(tmp_path: Path) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    migration_db = tmp_path / "phase42-data-preservation.db"

    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{migration_db}")
    command.upgrade(config, PHASE42_HEAD)

    connection = sqlite3.connect(migration_db)
    connection.execute(
        """
        INSERT INTO job_sources (
            source_key, display_name, source_category, provider_type,
            enabled, allowlisted, access_mode, attribution_required,
            terms_review_status, robots_review_status,
            manual_review_required, commercial_use_review_status,
            server_fetch_allowed, configured_retention_days,
            created_at, updated_at
        ) VALUES (
            'preserve-source', 'Preserve Source', 'provider_api', 'none',
            0, 0, 'metadata_only', 0,
            'not_reviewed', 'not_reviewed',
            1, 'not_reviewed',
            0, 30,
            '2026-07-02 00:00:00', '2026-07-02 00:00:00'
        )
        """
    )
    connection.commit()
    connection.close()

    command.downgrade(config, PHASE41_HEAD)
    command.upgrade(config, PHASE42_HEAD)

    connection = sqlite3.connect(migration_db)
    row_count = connection.execute(
        "SELECT COUNT(*) FROM job_sources"
    ).fetchone()[0]
    connection.close()
    assert row_count == 1
