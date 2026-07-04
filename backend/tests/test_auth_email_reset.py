"""Email verification and password-reset flow tests (auth).

Only token hashes are stored, so tests capture the raw token by
monkeypatching the email-send helpers used by the auth routes to record
the token they are handed. No real email is ever sent — the send helpers
are replaced with in-memory recorders.
"""

import pytest
from fastapi.testclient import TestClient

import app.api.routes.auth as auth_routes
from app.api.routes.auth import login_rate_limiter


USERNAME = "test.user"
PASSWORD = "correct-horse-8"
EMAIL = "candidate@example.com"
NEW_PASSWORD = "new-battery-staple-9"


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    login_rate_limiter.reset()
    original_max = login_rate_limiter.max_attempts
    yield
    login_rate_limiter.reset()
    login_rate_limiter.max_attempts = original_max


@pytest.fixture
def captured(monkeypatch):
    """Capture raw tokens the routes would email, without sending."""
    box: dict[str, list[str]] = {"verify": [], "reset": []}

    def fake_verify(recipient, token, settings):  # noqa: ANN001
        box["verify"].append(token)
        return True

    def fake_reset(recipient, token, settings):  # noqa: ANN001
        box["reset"].append(token)
        return True

    monkeypatch.setattr(
        auth_routes, "send_verification_email", fake_verify
    )
    monkeypatch.setattr(
        auth_routes, "send_password_reset_email", fake_reset
    )
    return box


def register(
    client: TestClient,
    username: str = USERNAME,
    password: str = PASSWORD,
    email: str = EMAIL,
):
    return client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": password,
            "full_name": "Test Candidate",
            "email": email,
        },
    )


# --- Registration + verification -----------------------------------------


def test_register_creates_unverified_account(
    client: TestClient, captured
) -> None:
    created = register(client)
    assert created.status_code == 201
    token = created.json()["token"]

    session = client.get(
        "/api/auth/session",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert session["email_verified"] is False
    assert session["email"] == EMAIL
    # A verification email (token) was produced.
    assert len(captured["verify"]) == 1


def test_register_succeeds_without_smtp(client: TestClient) -> None:
    # With SMTP unconfigured (default test settings) the real send helper
    # is a graceful no-op; registration must still succeed.
    created = register(client)
    assert created.status_code == 201
    assert created.json()["token"]


def test_verify_email_flips_flag(client: TestClient, captured) -> None:
    register(client)
    raw_token = captured["verify"][0]

    resp = client.post(
        "/api/auth/verify-email", json={"token": raw_token}
    )
    assert resp.status_code == 200

    login = client.post(
        "/api/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
    ).json()
    session = client.get(
        "/api/auth/session",
        headers={"Authorization": f"Bearer {login['token']}"},
    ).json()
    assert session["email_verified"] is True


def test_verify_email_wrong_token_400(client: TestClient) -> None:
    register(client)
    resp = client.post(
        "/api/auth/verify-email", json={"token": "not-a-real-token"}
    )
    assert resp.status_code == 400


def test_verify_email_token_single_use(
    client: TestClient, captured
) -> None:
    register(client)
    raw_token = captured["verify"][0]
    assert (
        client.post(
            "/api/auth/verify-email", json={"token": raw_token}
        ).status_code
        == 200
    )
    # Reusing the now-cleared token fails.
    assert (
        client.post(
            "/api/auth/verify-email", json={"token": raw_token}
        ).status_code
        == 400
    )


def test_resend_verification(client: TestClient, captured) -> None:
    token = register(client).json()["token"]
    resp = client.post(
        "/api/auth/resend-verification",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    # A second verification token was produced (register + resend).
    assert len(captured["verify"]) == 2
    # The freshly issued token verifies the account.
    assert (
        client.post(
            "/api/auth/verify-email", json={"token": captured["verify"][1]}
        ).status_code
        == 200
    )


# --- Forgot / reset password ---------------------------------------------


def test_forgot_password_no_enumeration(
    client: TestClient, captured
) -> None:
    register(client)

    known = client.post(
        "/api/auth/forgot-password", json={"email": EMAIL}
    )
    unknown = client.post(
        "/api/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert known.status_code == 200
    assert unknown.status_code == 200
    # Identical generic message for both.
    assert known.json()["message"] == unknown.json()["message"]
    # A reset token is created only for the known email.
    assert len(captured["reset"]) == 1


def test_forgot_password_case_insensitive(
    client: TestClient, captured
) -> None:
    register(client, email="Candidate@Example.com")
    resp = client.post(
        "/api/auth/forgot-password",
        json={"email": "candidate@example.com"},
    )
    assert resp.status_code == 200
    assert len(captured["reset"]) == 1


def test_reset_password_changes_password_and_revokes(
    client: TestClient, captured
) -> None:
    old_token = register(client).json()["token"]
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    raw_reset = captured["reset"][0]

    resp = client.post(
        "/api/auth/reset-password",
        json={"token": raw_reset, "new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 200

    # Old password no longer works, new one does.
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

    # The pre-reset session was revoked.
    assert (
        client.get(
            "/api/auth/session",
            headers={"Authorization": f"Bearer {old_token}"},
        ).status_code
        == 401
    )


def test_reset_password_invalid_token_400(client: TestClient) -> None:
    register(client)
    resp = client.post(
        "/api/auth/reset-password",
        json={"token": "bogus-token", "new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 400


def test_reset_password_expired_token_400(
    client: TestClient, captured, monkeypatch
) -> None:
    from datetime import timedelta

    import app.services.auth as auth_service

    register(client)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    raw_reset = captured["reset"][0]

    # Fast-forward wall clock past the one-hour TTL.
    base = auth_service.current_utc_time()

    def later():
        return base + timedelta(hours=2)

    monkeypatch.setattr(auth_service, "current_utc_time", later)

    resp = client.post(
        "/api/auth/reset-password",
        json={"token": raw_reset, "new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 400


def test_reset_password_rejects_weak_password(
    client: TestClient, captured
) -> None:
    register(client)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    raw_reset = captured["reset"][0]
    resp = client.post(
        "/api/auth/reset-password",
        json={"token": raw_reset, "new_password": "short"},
    )
    # min_length=8 on the schema -> 422 validation error.
    assert resp.status_code == 422
