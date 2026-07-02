"""Phase 13 — Authentication, Privacy, and Security tests."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes.auth import login_rate_limiter
from app.models.candidate_profile import CandidateProfile
from app.models.education import Education
from app.models.document import Document


PASSWORD = "correct-horse-8"
NEW_PASSWORD = "new-battery-staple-9"


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    login_rate_limiter.reset()
    original_max = login_rate_limiter.max_attempts
    yield
    login_rate_limiter.reset()
    login_rate_limiter.max_attempts = original_max


def make_profile(database: Session) -> CandidateProfile:
    profile = CandidateProfile(
        full_name="Test Candidate",
        email="candidate@example.com",
        requires_sponsorship=False,
        willing_to_relocate=False,
        preferred_work_modes=[],
        target_roles=[],
        preferred_locations=[],
        salary_currency="GBP",
        minimum_match_score=50,
        auto_apply_enabled=False,
        facts_verified=True,
    )
    database.add(profile)
    database.commit()
    return profile


def auth_headers(client: TestClient) -> dict[str, str]:
    client.post("/api/auth/setup", json={"password": PASSWORD})
    token = client.post(
        "/api/auth/login", json={"password": PASSWORD}
    ).json()["token"]
    return {"Authorization": f"Bearer {token}"}


# --- Setup / login / session ----------------------------------------------


def test_status_setup_and_login_flow(client: TestClient) -> None:
    status = client.get("/api/auth/status")
    assert status.json()["configured"] is False

    setup = client.post("/api/auth/setup", json={"password": PASSWORD})
    assert setup.status_code == 201
    assert client.get("/api/auth/status").json()["configured"] is True

    # Setup again is rejected.
    assert (
        client.post("/api/auth/setup", json={"password": PASSWORD})
    ).status_code == 409

    assert (
        client.post("/api/auth/login", json={"password": "wrong-pass-1"})
    ).status_code == 401

    ok = client.post("/api/auth/login", json={"password": PASSWORD})
    assert ok.status_code == 200
    body = ok.json()
    assert body["token_type"] == "bearer"
    assert body["token"]


def test_setup_rejects_short_password(client: TestClient) -> None:
    response = client.post("/api/auth/setup", json={"password": "short"})
    assert response.status_code == 422


def test_session_requires_valid_bearer_token(
    client: TestClient,
) -> None:
    headers = auth_headers(client)

    assert client.get("/api/auth/session").status_code == 401
    assert (
        client.get(
            "/api/auth/session",
            headers={"Authorization": "Bearer not-a-real-token"},
        ).status_code
        == 401
    )

    ok = client.get("/api/auth/session", headers=headers)
    assert ok.status_code == 200
    assert ok.json()["authenticated"] is True


def test_logout_revokes_session(client: TestClient) -> None:
    headers = auth_headers(client)
    assert client.get("/api/auth/session", headers=headers).status_code == (
        200
    )

    assert client.post("/api/auth/logout", headers=headers).status_code == (
        200
    )
    # Token no longer works.
    assert client.get("/api/auth/session", headers=headers).status_code == (
        401
    )


def test_change_password_revokes_sessions(client: TestClient) -> None:
    headers = auth_headers(client)

    wrong = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "wrong-pass-1",
            "new_password": NEW_PASSWORD,
        },
        headers=headers,
    )
    assert wrong.status_code == 401

    changed = client.post(
        "/api/auth/change-password",
        json={
            "current_password": PASSWORD,
            "new_password": NEW_PASSWORD,
        },
        headers=headers,
    )
    assert changed.status_code == 200

    # Old session invalidated; old password rejected; new one works.
    assert client.get("/api/auth/session", headers=headers).status_code == (
        401
    )
    assert (
        client.post("/api/auth/login", json={"password": PASSWORD})
    ).status_code == 401
    assert (
        client.post("/api/auth/login", json={"password": NEW_PASSWORD})
    ).status_code == 200


# --- Rate limiting --------------------------------------------------------


def test_login_rate_limited(client: TestClient) -> None:
    client.post("/api/auth/setup", json={"password": PASSWORD})
    login_rate_limiter.max_attempts = 3

    statuses = [
        client.post(
            "/api/auth/login", json={"password": "wrong-pass-1"}
        ).status_code
        for _ in range(4)
    ]
    assert statuses[:3] == [401, 401, 401]
    assert statuses[3] == 429


# --- Security headers -----------------------------------------------------


def test_security_headers_present(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Content-Security-Policy" in response.headers
    assert "Strict-Transport-Security" in response.headers


# --- Privacy: export ------------------------------------------------------


def test_export_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/privacy/export").status_code == 401


def test_export_returns_sanitized_data(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    db_session.add(
        Document(
            candidate_profile_id=1,
            original_filename="cv.pdf",
            stored_filename="secret-stored-name.pdf",
            file_extension=".pdf",
            media_type="application/pdf",
            size_bytes=100,
            sha256_hash="a" * 64,
            document_type="original_cv",
            upload_status="validated",
            is_primary=True,
        )
    )
    db_session.commit()

    headers = auth_headers(client)
    export = client.get("/api/privacy/export", headers=headers)
    assert export.status_code == 200
    body = export.json()
    assert body["candidate_profile"]["full_name"] == "Test Candidate"
    assert "documents" in body
    assert len(body["documents"]) == 1
    document = body["documents"][0]
    assert "storage_path" not in document
    assert "stored_filename" not in document
    assert document["original_filename"] == "cv.pdf"


# --- Privacy: deletion ----------------------------------------------------


def test_delete_requires_confirm(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    headers = auth_headers(client)

    unconfirmed = client.post(
        "/api/privacy/delete",
        json={"confirm": False},
        headers=headers,
    )
    assert unconfirmed.status_code == 400


def test_delete_erases_candidate_data(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    db_session.add(
        Education(
            candidate_profile_id=profile.id,
            institution="Example University",
            degree="BSc",
            start_date=datetime(2015, 9, 1).date(),
            end_date=datetime(2018, 6, 30).date(),
            is_current=False,
            verified=True,
        )
    )
    db_session.commit()

    headers = auth_headers(client)
    deleted = client.post(
        "/api/privacy/delete",
        json={"confirm": True},
        headers=headers,
    )
    assert deleted.status_code == 200
    body = deleted.json()
    assert body["profile_deleted"] is True
    assert body["deleted"]["education"] == 1

    db_session.expire_all()
    assert db_session.get(CandidateProfile, 1) is None
    assert db_session.query(Education).count() == 0
    # Deletion revoked sessions, so the token no longer authenticates.
    assert client.get("/api/auth/session", headers=headers).status_code == (
        401
    )


# --- Service-level password hashing ---------------------------------------


def test_password_is_not_stored_in_plaintext(db_session: Session) -> None:
    from app.api.deps import get_settings
    from app.models.auth import AuthCredential
    from app.services.auth import set_password, verify_password

    set_password(PASSWORD, db_session, get_settings())
    credential = db_session.get(AuthCredential, 1)
    assert credential is not None
    assert PASSWORD not in credential.password_hash
    assert credential.algorithm == "pbkdf2_sha256"
    assert credential.iterations >= 100_000
    assert verify_password(PASSWORD, db_session) is True
    assert verify_password("wrong-pass-1", db_session) is False
