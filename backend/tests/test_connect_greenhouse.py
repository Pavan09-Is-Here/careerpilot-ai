"""Connect-a-company-board (public Greenhouse) tests.

Covers the authenticated connect endpoint, board-token validation, the
duplicate/unauthenticated guards, and an end-to-end ingest run using a
stubbed HTTP fetch (mirroring test_provider_greenhouse_phase43.py).
"""

import json
from typing import Callable

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.auth import login_rate_limiter
from app.models.job import JobSource
from tests.conftest import Account, register_account


@pytest.fixture(autouse=True)
def _reset_auth_rate_limiter() -> None:
    login_rate_limiter.reset()


@pytest.fixture
def account(client: TestClient, db_session: Session) -> Account:
    return register_account(client, db_session)


def json_response(payload: dict[str, object]) -> httpx.Response:
    return httpx.Response(
        200,
        content=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
    )


def mock_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
    )


def jobs_client(token: str, *jobs: dict[str, object]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "boards-api.greenhouse.io"
        assert request.url.path == f"/v1/boards/{token}/jobs"
        assert request.url.params["content"] == "true"
        return json_response({"jobs": list(jobs)})

    return mock_client(handler)


def greenhouse_job(**overrides: object) -> dict[str, object]:
    job: dict[str, object] = {
        "id": 5500001,
        "absolute_url": (
            "https://boards.greenhouse.io/exampleco/jobs/5500001"
        ),
        "title": "Backend Engineer",
        "content": "&lt;p&gt;Build APIs.&lt;/p&gt;",
        "updated_at": "2026-06-30T09:00:00+00:00",
        "location": {"name": "Remote, United Kingdom"},
    }
    job.update(overrides)
    return job


def test_connect_creates_source_with_approved_flags(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    response = client.post(
        "/api/job-sources/greenhouse",
        json={"board_token": "exampleco", "display_name": "Example Co"},
        headers=account.headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_key"] == "greenhouse:exampleco"
    assert body["display_name"] == "Example Co"
    assert body["source_category"] == "provider_api"
    assert body["provider_type"] == "greenhouse"
    assert body["access_mode"] == "api"
    assert body["base_url"] == (
        "https://boards-api.greenhouse.io/v1/boards/exampleco"
    )
    assert body["enabled"] is True
    assert body["allowlisted"] is True
    assert body["server_fetch_allowed"] is True
    assert body["manual_review_required"] is False
    assert body["terms_review_status"] == "approved_for_configured_use"
    assert body["robots_review_status"] == "approved_for_configured_use"
    assert (
        body["commercial_use_review_status"]
        == "approved_for_configured_use"
    )

    db_session.expire_all()
    source = db_session.scalar(
        select(JobSource).where(
            JobSource.source_key == "greenhouse:exampleco"
        )
    )
    assert source is not None
    assert source.enabled is True
    assert source.allowlisted is True
    assert source.server_fetch_allowed is True
    assert source.manual_review_required is False
    assert source.access_mode == "api"
    assert source.terms_review_status == "approved_for_configured_use"
    assert source.robots_review_status == "approved_for_configured_use"
    assert (
        source.commercial_use_review_status
        == "approved_for_configured_use"
    )


@pytest.mark.parametrize(
    "board_token",
    ["ExampleCo", "example co", "", "  ", "bad!token"],
)
def test_connect_rejects_invalid_tokens(
    client: TestClient,
    account: Account,
    board_token: str,
) -> None:
    response = client.post(
        "/api/job-sources/greenhouse",
        json={"board_token": board_token, "display_name": "Example Co"},
        headers=account.headers,
    )

    assert response.status_code in (400, 422)


def test_connect_duplicate_returns_409(
    client: TestClient,
    account: Account,
) -> None:
    payload = {"board_token": "dupco", "display_name": "Dup Co"}
    first = client.post(
        "/api/job-sources/greenhouse",
        json=payload,
        headers=account.headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/api/job-sources/greenhouse",
        json=payload,
        headers=account.headers,
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "That board is already connected."


def test_connect_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/job-sources/greenhouse",
        json={"board_token": "exampleco", "display_name": "Example Co"},
    )

    assert response.status_code == 401


def test_connect_then_ingest_creates_visible_jobs(
    client: TestClient,
    account: Account,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connect = client.post(
        "/api/job-sources/greenhouse",
        json={"board_token": "exampleco", "display_name": "Example Co"},
        headers=account.headers,
    )
    assert connect.status_code == 201
    source_id = connect.json()["id"]

    monkeypatch.setattr(
        "app.services.provider_greenhouse.build_http_client",
        lambda: jobs_client(
            "exampleco",
            greenhouse_job(),
            greenhouse_job(
                id=5500002,
                absolute_url=(
                    "https://boards.greenhouse.io/exampleco/jobs/5500002"
                ),
                title="Frontend Engineer",
            ),
        ),
    )

    ingest = client.post(f"/api/job-sources/{source_id}/ingest")
    assert ingest.status_code == 201
    run = ingest.json()
    assert run["run_status"] == "succeeded"
    assert run["jobs_discovered"] == 2

    jobs = client.get(f"/api/jobs?source={source_id}")
    assert jobs.status_code == 200
    body = jobs.json()
    assert body["total"] == 2
    titles = {item["title"] for item in body["items"]}
    assert titles == {"Backend Engineer", "Frontend Engineer"}
    assert all(
        item["employer_name"] == "Example Co" for item in body["items"]
    )
