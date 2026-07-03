from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.models.job import JobSource, NormalizedJob
from app.models.saved_job import SavedJob
from app.schemas.job import JobSourceCreate, NormalizedJobCreate
from app.schemas.saved_job import SavedJobCreate, SavedJobUpdate
from app.services.job import create_job_source, create_normalized_job
from app.services.saved_job import (
    SavedJobServiceError,
    create_saved_job,
    update_saved_job,
)

from tests.conftest import Account


PHASE44_HEAD = "d0e1f2a3b4c5"
PHASE45_HEAD = "e1f2a3b4c5d6"


@pytest.fixture(autouse=True)
def _reset_login_rate_limiter() -> None:
    # Registration reuses the login rate limiter; reset it so repeated
    # account registration across tests does not trip the 429 guard.
    from app.api.routes.auth import login_rate_limiter

    login_rate_limiter.reset()


def make_source(database: Session) -> JobSource:
    return create_job_source(
        JobSourceCreate(
            source_key=f"source-{uuid4().hex[:12]}",
            display_name=f"Synthetic Source {uuid4().hex[:8]}",
            source_category="provider_api",
        ),
        database,
    )


def make_job(
    database: Session,
    source: JobSource | None = None,
    **overrides: object,
) -> NormalizedJob:
    active_source = source or make_source(database)
    payload: dict[str, object] = {
        "job_source_id": active_source.id,
        "source_job_id": f"job-{uuid4().hex[:16]}",
        "source_url": f"https://jobs.example.com/{uuid4().hex}",
        "employer_name": "Example Robotics",
        "title": "Platform Engineer",
        "content_hash": sha256(uuid4().hex.encode()).hexdigest(),
        "normalization_version": "phase4.5-test",
    }
    payload.update(overrides)
    return create_normalized_job(
        NormalizedJobCreate(**payload),
        database,
    )


def save(
    database: Session,
    job: NormalizedJob,
    candidate_profile_id: int,
    notes: str | None = None,
) -> dict[str, object]:
    return create_saved_job(
        SavedJobCreate(job_id=job.id, notes=notes),
        database,
        candidate_profile_id=candidate_profile_id,
    )


def test_save_job_defaults(db_session: Session, account: Account) -> None:
    job = make_job(db_session)
    payload = save(
        db_session, job, account.profile_id, notes="Looks promising."
    )

    assert payload["review_status"] == "saved"
    assert payload["notes"] == "Looks promising."
    assert payload["job_id"] == job.id
    embedded = payload["job"]
    assert isinstance(embedded, dict)
    assert embedded["title"] == "Platform Engineer"


def test_save_unknown_job_404(db_session: Session, account: Account) -> None:
    with pytest.raises(SavedJobServiceError) as error:
        create_saved_job(
            SavedJobCreate(job_id=987654),
            db_session,
            candidate_profile_id=account.profile_id,
        )

    assert error.value.status_code == 404


def test_duplicate_save_conflict(
    db_session: Session, account: Account
) -> None:
    job = make_job(db_session)
    save(db_session, job, account.profile_id)

    with pytest.raises(SavedJobServiceError) as error:
        save(db_session, job, account.profile_id)

    assert error.value.status_code == 409


def test_notes_reject_control_characters(
    db_session: Session, account: Account
) -> None:
    job = make_job(db_session)

    with pytest.raises(SavedJobServiceError):
        save(db_session, job, account.profile_id, notes="bad\x00note")


@pytest.mark.parametrize(
    ("path", "expected_allowed"),
    [
        (["shortlisted"], True),
        (["shortlisted", "dismissed"], True),
        (["dismissed", "saved"], True),
        (["archived", "saved"], False),
        (["archived", "shortlisted"], False),
    ],
)
def test_review_transition_paths(
    db_session: Session,
    account: Account,
    path: list[str],
    expected_allowed: bool,
) -> None:
    job = make_job(db_session)
    payload = save(db_session, job, account.profile_id)
    saved_id = payload["id"]
    assert isinstance(saved_id, int)

    if expected_allowed:
        for status in path:
            update_saved_job(
                saved_id,
                SavedJobUpdate(review_status=status),  # type: ignore[arg-type]
                db_session,
                candidate_profile_id=account.profile_id,
            )
        return

    update_saved_job(
        saved_id,
        SavedJobUpdate(review_status=path[0]),  # type: ignore[arg-type]
        db_session,
        candidate_profile_id=account.profile_id,
    )
    with pytest.raises(SavedJobServiceError):
        update_saved_job(
            saved_id,
            SavedJobUpdate(review_status=path[1]),  # type: ignore[arg-type]
            db_session,
            candidate_profile_id=account.profile_id,
        )


def test_stale_and_expired_jobs_remain_saveable_and_inspectable(
    db_session: Session,
    account: Account,
) -> None:
    for status in ("possibly_stale", "expired", "removed", "unavailable"):
        job = make_job(db_session)
        job.lifecycle_status = status
        db_session.commit()

        payload = save(db_session, job, account.profile_id)
        embedded = payload["job"]
        assert isinstance(embedded, dict)
        assert embedded["lifecycle_status"] == status


def test_saved_job_blocks_job_deletion(
    db_session: Session, account: Account
) -> None:
    """RESTRICT FK: saved jobs preserve their underlying job rows."""
    job = make_job(db_session)
    save(db_session, job, account.profile_id)

    db_session.delete(job)
    with pytest.raises(Exception):
        db_session.commit()
    db_session.rollback()

    assert db_session.get(NormalizedJob, job.id) is not None


def test_saved_jobs_endpoints_full_workflow(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    job = make_job(db_session)

    unauthenticated = client.post(
        "/api/saved-jobs",
        json={"job_id": job.id},
    )
    assert unauthenticated.status_code == 401

    created = client.post(
        "/api/saved-jobs",
        json={"job_id": job.id, "notes": "Interesting role."},
        headers=account.headers,
    )
    assert created.status_code == 201
    saved_id = created.json()["id"]

    duplicate = client.post(
        "/api/saved-jobs",
        json={"job_id": job.id},
        headers=account.headers,
    )
    assert duplicate.status_code == 409

    listed = client.get("/api/saved-jobs", headers=account.headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    detail = client.get(
        f"/api/saved-jobs/{saved_id}", headers=account.headers
    )
    assert detail.status_code == 200
    assert detail.json()["job"]["id"] == job.id

    updated = client.patch(
        f"/api/saved-jobs/{saved_id}",
        json={"review_status": "shortlisted", "notes": "Top pick."},
        headers=account.headers,
    )
    assert updated.status_code == 200
    assert updated.json()["review_status"] == "shortlisted"
    assert updated.json()["notes"] == "Top pick."

    filtered = client.get(
        "/api/saved-jobs",
        params={"review_status": "shortlisted"},
        headers=account.headers,
    )
    assert filtered.json()["total"] == 1

    missing = client.get(
        "/api/saved-jobs/987654", headers=account.headers
    )
    assert missing.status_code == 404

    invalid_status = client.patch(
        f"/api/saved-jobs/{saved_id}",
        json={"review_status": "exploded"},
        headers=account.headers,
    )
    assert invalid_status.status_code == 422


def test_no_delete_endpoint_for_saved_jobs(
    client: TestClient, account: Account
) -> None:
    response = client.delete(
        "/api/saved-jobs/1", headers=account.headers
    )

    assert response.status_code == 405


def test_saved_job_responses_have_no_internal_fields(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    job = make_job(db_session)
    created = client.post(
        "/api/saved-jobs",
        json={"job_id": job.id},
        headers=account.headers,
    )

    body = created.json()
    forbidden_fragments = ("secret", "token", "credential", "storage")
    for key in body:
        for fragment in forbidden_fragments:
            assert fragment not in key.lower()


def test_saved_job_table_persists_after_maintenance(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    job = make_job(db_session)
    save(db_session, job, account.profile_id)

    response = client.post("/api/jobs/maintenance")

    assert response.status_code == 200
    assert db_session.scalar(select(SavedJob)) is not None


def test_phase45_migration_upgrade_downgrade_reupgrade(
    tmp_path: Path,
) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    migration_db = tmp_path / "phase45-migration.db"

    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{migration_db}")

    command.upgrade(config, PHASE45_HEAD)
    engine = create_engine(f"sqlite:///{migration_db}")
    assert "saved_jobs" in set(inspect(engine).get_table_names())
    engine.dispose()

    command.downgrade(config, PHASE44_HEAD)
    engine = create_engine(f"sqlite:///{migration_db}")
    tables = set(inspect(engine).get_table_names())
    assert "saved_jobs" not in tables
    assert "normalized_jobs" in tables
    engine.dispose()

    command.upgrade(config, PHASE45_HEAD)
    engine = create_engine(f"sqlite:///{migration_db}")
    assert "saved_jobs" in set(inspect(engine).get_table_names())
    engine.dispose()
