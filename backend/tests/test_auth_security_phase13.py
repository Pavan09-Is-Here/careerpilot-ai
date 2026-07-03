"""Authentication, privacy and security tests (accounts, Phase 15)."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes.auth import login_rate_limiter
from app.models.candidate_profile import CandidateProfile
from app.models.education import Education
from app.models.document import Document


USERNAME = "test.user"
PASSWORD = "correct-horse-8"
NEW_PASSWORD = "new-battery-staple-9"


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    login_rate_limiter.reset()
    original_max = login_rate_limiter.max_attempts
    yield
    login_rate_limiter.reset()
    login_rate_limiter.max_attempts = original_max


def register(
    client: TestClient,
    username: str = USERNAME,
    password: str = PASSWORD,
    full_name: str = "Test Candidate",
    email: str = "candidate@example.com",
):
    return client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": password,
            "full_name": full_name,
            "email": email,
        },
    )


def auth_headers(client: TestClient) -> dict[str, str]:
    token = register(client).json()["token"]
    return {"Authorization": f"Bearer {token}"}


# --- Registration / login / session ---------------------------------------


def test_status_register_and_login_flow(client: TestClient) -> None:
    assert client.get("/api/auth/status").json()["configured"] is False

    created = register(client)
    assert created.status_code == 201
    body = created.json()
    assert body["token"]
    assert body["username"] == USERNAME
    assert client.get("/api/auth/status").json()["configured"] is True

    # Duplicate username is rejected (case-insensitive).
    assert register(client, username="Test.User").status_code == 409

    # Wrong username and wrong password both fail with 401.
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "nobody", "password": PASSWORD},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"username": USERNAME, "password": "wrong-pass-1"},
        ).status_code
        == 401
    )

    ok = client.post(
        "/api/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
    )
    assert ok.status_code == 200
    assert ok.json()["token_type"] == "bearer"
    assert ok.json()["username"] == USERNAME


def test_register_rejects_short_password(client: TestClient) -> None:
    assert register(client, password="short").status_code == 422


def test_register_rejects_bad_username(client: TestClient) -> None:
    # Illegal characters are rejected by the service (400).
    assert register(client, username="ab!").status_code == 400


def test_second_account_is_isolated_profile(client: TestClient) -> None:
    first = register(
        client, username="alice", email="alice@example.com"
    )
    second = register(
        client, username="bob", email="bob@example.com"
    )
    assert first.status_code == 201
    assert second.status_code == 201

    alice_headers = {"Authorization": f"Bearer {first.json()['token']}"}
    bob_headers = {"Authorization": f"Bearer {second.json()['token']}"}

    assert (
        client.get("/api/auth/session", headers=alice_headers).json()[
            "username"
        ]
        == "alice"
    )
    assert (
        client.get("/api/auth/session", headers=bob_headers).json()[
            "username"
        ]
        == "bob"
    )


def test_session_requires_valid_bearer_token(client: TestClient) -> None:
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
    assert client.get("/api/auth/session", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/session", headers=headers).status_code == 401


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

    assert client.get("/api/auth/session", headers=headers).status_code == 401
    assert (
        client.post(
            "/api/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"username": USERNAME, "password": NEW_PASSWORD},
        ).status_code
        == 200
    )


# --- Rate limiting --------------------------------------------------------


def test_login_rate_limited(client: TestClient) -> None:
    register(client)
    login_rate_limiter.reset()
    login_rate_limiter.max_attempts = 3

    statuses = [
        client.post(
            "/api/auth/login",
            json={"username": USERNAME, "password": "wrong-pass-1"},
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
    headers = auth_headers(client)
    profile = db_session.query(CandidateProfile).one()
    db_session.add(
        Document(
            candidate_profile_id=profile.id,
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

    export = client.get("/api/privacy/export", headers=headers)
    assert export.status_code == 200
    body = export.json()
    assert body["candidate_profile"]["full_name"] == "Test Candidate"
    assert len(body["documents"]) == 1
    document = body["documents"][0]
    assert "storage_path" not in document
    assert "stored_filename" not in document
    assert document["original_filename"] == "cv.pdf"


# --- Privacy: deletion ----------------------------------------------------


def test_delete_requires_confirm(client: TestClient) -> None:
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
    headers = auth_headers(client)
    profile = db_session.query(CandidateProfile).one()
    profile_id = profile.id
    db_session.add(
        Education(
            candidate_profile_id=profile_id,
            institution="Example University",
            degree="BSc",
            start_date=datetime(2015, 9, 1).date(),
            end_date=datetime(2018, 6, 30).date(),
            is_current=False,
            verified=True,
        )
    )
    db_session.commit()

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
    assert db_session.get(CandidateProfile, profile_id) is None
    assert db_session.query(Education).count() == 0
    assert client.get("/api/auth/session", headers=headers).status_code == 401


# --- Service-level password hashing ---------------------------------------


def test_password_is_not_stored_in_plaintext(db_session: Session) -> None:
    from app.api.deps import get_settings
    from app.services.auth import create_account, verify_password

    user, _profile = create_account(
        USERNAME,
        PASSWORD,
        "Test Candidate",
        "candidate@example.com",
        db_session,
        get_settings(),
    )
    assert PASSWORD not in user.password_hash
    assert user.algorithm == "pbkdf2_sha256"
    assert user.iterations >= 100_000
    assert verify_password(user, PASSWORD) is True
    assert verify_password(user, "wrong-pass-1") is False
