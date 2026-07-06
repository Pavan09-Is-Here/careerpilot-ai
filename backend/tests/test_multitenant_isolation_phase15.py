"""Phase 15B — cross-user (multi-tenant) data isolation tests.

Every personal endpoint is now scoped to the authenticated caller's own
candidate profile. These tests register two independent accounts (alice and
bob) and prove that:

* their candidate profiles are distinct;
* a resource created by alice never appears in bob's list endpoints;
* bob cannot read, update or delete alice's resources (404, not 200);
* unauthenticated requests to personal endpoints return 401.

All resources are created through the real HTTP API (TestClient), mirroring
how the phase-specific tests exercise the same endpoints. Prerequisite
catalog rows (a normalized job) are inserted via ``db_session`` exactly as the
other suites do.
"""

from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes.auth import login_rate_limiter
from app.models.job import NormalizedJob
from app.schemas.job import JobSourceCreate, NormalizedJobCreate
from app.services.job import create_job_source, create_normalized_job
from tests.conftest import Account, register_account


@pytest.fixture(autouse=True)
def _reset_auth_rate_limiter() -> None:
    """Registration reuses the login rate limiter; keep it clean per test."""
    login_rate_limiter.reset()


@pytest.fixture
def alice(client: TestClient, db_session: Session) -> Account:
    return register_account(
        client,
        db_session,
        username="alice",
        email="alice@example.com",
        full_name="Alice Candidate",
    )


@pytest.fixture
def bob(client: TestClient, db_session: Session) -> Account:
    return register_account(
        client,
        db_session,
        username="bob",
        email="bob@example.com",
        full_name="Bob Candidate",
    )


def make_job(database: Session) -> NormalizedJob:
    source = create_job_source(
        JobSourceCreate(
            source_key=f"source-{uuid4().hex[:12]}",
            display_name="Example Robotics",
            source_category="provider_api",
        ),
        database,
    )
    return create_normalized_job(
        NormalizedJobCreate(
            job_source_id=source.id,
            source_job_id=f"job-{uuid4().hex[:16]}",
            source_url=f"https://jobs.example.com/{uuid4().hex}",
            employer_name="Example Robotics",
            title="Platform Engineer",
            content_hash=sha256(uuid4().hex.encode()).hexdigest(),
            normalization_version="phase15-isolation",
        ),
        database,
    )


# --- Profiles are distinct -------------------------------------------------


def test_registered_profiles_are_distinct(
    alice: Account,
    bob: Account,
) -> None:
    assert alice.profile_id != bob.profile_id


# --- Skills isolation ------------------------------------------------------


def test_skill_is_not_visible_to_other_user(
    client: TestClient,
    alice: Account,
    bob: Account,
) -> None:
    created = client.post(
        "/api/skills",
        json={"name": "Python", "proficiency": "Advanced"},
        headers=alice.headers,
    )
    assert created.status_code == 201
    skill_id = created.json()["id"]
    assert created.json()["candidate_profile_id"] == alice.profile_id

    # Bob's list must not contain alice's skill.
    bob_list = client.get("/api/skills", headers=bob.headers)
    assert bob_list.status_code == 200
    assert all(item["id"] != skill_id for item in bob_list.json())

    # Alice can see her own.
    alice_list = client.get("/api/skills", headers=alice.headers)
    assert any(item["id"] == skill_id for item in alice_list.json())

    # Bob cannot read, update or delete alice's skill -> 404.
    assert (
        client.put(
            f"/api/skills/{skill_id}",
            json={"name": "Rust", "proficiency": "Advanced"},
            headers=bob.headers,
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/skills/{skill_id}",
            headers=bob.headers,
        ).status_code
        == 404
    )

    # Alice's skill survived bob's attempts.
    assert (
        client.get("/api/skills", headers=alice.headers).json()[0]["id"]
        == skill_id
    )

    # Unauthenticated access is rejected.
    assert client.get("/api/skills").status_code == 401
    assert (
        client.post(
            "/api/skills",
            json={"name": "Go", "proficiency": "Advanced"},
        ).status_code
        == 401
    )


# --- Saved-job isolation ---------------------------------------------------


def test_saved_job_is_not_visible_to_other_user(
    client: TestClient,
    db_session: Session,
    alice: Account,
    bob: Account,
) -> None:
    job = make_job(db_session)

    created = client.post(
        "/api/saved-jobs",
        json={"job_id": job.id, "notes": "Interesting role."},
        headers=alice.headers,
    )
    assert created.status_code == 201
    saved_id = created.json()["id"]

    bob_list = client.get("/api/saved-jobs", headers=bob.headers)
    assert bob_list.status_code == 200
    assert bob_list.json()["total"] == 0
    assert bob_list.json()["items"] == []

    alice_list = client.get("/api/saved-jobs", headers=alice.headers)
    assert any(
        item["id"] == saved_id for item in alice_list.json()["items"]
    )

    # Bob fetching / mutating alice's saved job -> 404.
    assert (
        client.get(
            f"/api/saved-jobs/{saved_id}", headers=bob.headers
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/saved-jobs/{saved_id}",
            json={"review_status": "shortlisted"},
            headers=bob.headers,
        ).status_code
        == 404
    )

    # Alice's saved job is untouched.
    assert (
        client.get(
            f"/api/saved-jobs/{saved_id}", headers=alice.headers
        ).status_code
        == 200
    )

    # Unauthenticated -> 401.
    assert client.get("/api/saved-jobs").status_code == 401
    assert (
        client.post(
            "/api/saved-jobs", json={"job_id": job.id}
        ).status_code
        == 401
    )


# --- Application-answer isolation ------------------------------------------


def test_application_answer_is_not_visible_to_other_user(
    client: TestClient,
    alice: Account,
    bob: Account,
) -> None:
    payload = {
        "category": "availability",
        "question_label": "When can you start?",
        "answer_text": "Available to start immediately.",
        "verified": True,
        "manually_confirmed": False,
        "notes": None,
    }
    created = client.post(
        "/api/application-answers",
        json=payload,
        headers=alice.headers,
    )
    assert created.status_code == 201
    answer_id = created.json()["id"]
    assert created.json()["candidate_profile_id"] == alice.profile_id

    bob_list = client.get("/api/application-answers", headers=bob.headers)
    assert bob_list.status_code == 200
    assert bob_list.json() == []

    # Bob reading / mutating alice's answer -> 404.
    assert (
        client.get(
            f"/api/application-answers/{answer_id}", headers=bob.headers
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/application-answers/{answer_id}",
            json=payload,
            headers=bob.headers,
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/application-answers/{answer_id}", headers=bob.headers
        ).status_code
        == 404
    )

    # Alice still owns it.
    assert (
        client.get(
            f"/api/application-answers/{answer_id}", headers=alice.headers
        ).status_code
        == 200
    )

    # Unauthenticated -> 401.
    assert client.get("/api/application-answers").status_code == 401
    assert (
        client.post("/api/application-answers", json=payload).status_code
        == 401
    )


# --- Application (tracking) isolation --------------------------------------


def test_application_is_not_visible_to_other_user(
    client: TestClient,
    db_session: Session,
    alice: Account,
    bob: Account,
) -> None:
    job = make_job(db_session)

    tracked = client.post(
        f"/api/jobs/{job.id}/track",
        headers=alice.headers,
    )
    assert tracked.status_code in (200, 201)
    application_id = tracked.json()["id"]

    # Bob's application list must not contain alice's application.
    bob_list = client.get("/api/applications", headers=bob.headers)
    assert bob_list.status_code == 200
    assert all(
        item["id"] != application_id for item in bob_list.json()
    )

    alice_list = client.get("/api/applications", headers=alice.headers)
    assert any(item["id"] == application_id for item in alice_list.json())

    # Bob reading / updating alice's application -> 404.
    assert (
        client.get(
            f"/api/applications/{application_id}", headers=bob.headers
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/applications/{application_id}",
            json={"status": "ready_to_apply"},
            headers=bob.headers,
        ).status_code
        == 404
    )

    # Alice still owns it.
    assert (
        client.get(
            f"/api/applications/{application_id}", headers=alice.headers
        ).status_code
        == 200
    )

    # Unauthenticated -> 401.
    assert client.get("/api/applications").status_code == 401
    assert (
        client.post(f"/api/jobs/{job.id}/track").status_code == 401
    )


def test_both_users_can_track_the_same_job(
    client: TestClient,
    db_session: Session,
    alice: Account,
    bob: Account,
) -> None:
    """Applications are unique per (job, profile), not per job:
    two accounts may each apply to the same posting, and tracking by
    one must never return (or block) the other's record."""
    job = make_job(db_session)

    alice_tracked = client.post(
        f"/api/jobs/{job.id}/track",
        headers=alice.headers,
    )
    assert alice_tracked.status_code in (200, 201)
    alice_id = alice_tracked.json()["id"]

    bob_tracked = client.post(
        f"/api/jobs/{job.id}/track",
        headers=bob.headers,
    )
    assert bob_tracked.status_code in (200, 201)
    bob_id = bob_tracked.json()["id"]

    assert alice_id != bob_id

    # Re-tracking is idempotent per profile.
    assert (
        client.post(
            f"/api/jobs/{job.id}/track", headers=alice.headers
        ).json()["id"]
        == alice_id
    )

    alice_items = client.get(
        "/api/applications", headers=alice.headers
    ).json()
    bob_items = client.get(
        "/api/applications", headers=bob.headers
    ).json()
    assert [item["id"] for item in alice_items] == [alice_id]
    assert [item["id"] for item in bob_items] == [bob_id]


# --- Privacy export/delete isolation ---------------------------------------


def test_privacy_export_and_delete_are_scoped_to_caller(
    client: TestClient,
    alice: Account,
    bob: Account,
) -> None:
    # Alice adds a skill; Bob adds a differently-named skill.
    client.post(
        "/api/skills",
        json={"name": "AliceSecretSkill", "proficiency": "Advanced"},
        headers=alice.headers,
    )
    client.post(
        "/api/skills",
        json={"name": "BobOwnSkill", "proficiency": "Advanced"},
        headers=bob.headers,
    )

    # Bob's export must contain only Bob's data, never Alice's.
    bob_export = client.get("/api/privacy/export", headers=bob.headers)
    assert bob_export.status_code == 200
    body = bob_export.json()
    assert body["candidate_profile"]["full_name"] == "Bob Candidate"
    skill_names = {s["name"] for s in body["skills"]}
    assert "BobOwnSkill" in skill_names
    assert "AliceSecretSkill" not in skill_names

    # Bob deleting his own data must NOT erase Alice's.
    deleted = client.post(
        "/api/privacy/delete",
        json={"confirm": True},
        headers=bob.headers,
    )
    assert deleted.status_code == 200

    # Bob's session is revoked; Alice is unaffected and keeps her skill.
    assert client.get("/api/skills", headers=bob.headers).status_code == 401
    alice_skills = client.get("/api/skills", headers=alice.headers)
    assert alice_skills.status_code == 200
    assert any(
        s["name"] == "AliceSecretSkill" for s in alice_skills.json()
    )

    # Unauthenticated privacy access -> 401.
    assert client.get("/api/privacy/export").status_code == 401
