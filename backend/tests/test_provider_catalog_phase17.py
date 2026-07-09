"""Phase 17 — free provider catalog tests.

Six free sources share one compliance-gated pipeline: Lever, Ashby,
Remotive, Arbeitnow (keyless) and Adzuna, Reed (environment keys).
These tests connect each provider, ingest mocked payloads, verify the
normalized jobs, and prove the safety properties: compliance gates
block fetching, key-gated providers stay inert without keys, and no
secrets are stored on the source row.
"""

import json
from typing import Callable

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes.auth import login_rate_limiter
from app.models.job import JobSource, NormalizedJob
from app.services import provider_catalog
from app.services.provider_catalog import (
    ProviderCatalogError,
    connect_provider_source,
    ingest_job_source,
    ingest_provider_source,
)
from tests.conftest import Account, register_account


@pytest.fixture(autouse=True)
def _reset_auth_rate_limiter() -> None:
    login_rate_limiter.reset()


@pytest.fixture
def account(client: TestClient, db_session: Session) -> Account:
    return register_account(client, db_session)


def json_response(payload: object) -> httpx.Response:
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


def payload_client(payload: object) -> httpx.Client:
    return mock_client(lambda request: json_response(payload))


def job_titles(database: Session) -> set[str]:
    return {job.title for job in database.query(NormalizedJob).all()}


# --- Connect ----------------------------------------------------------------


def test_connect_lever_and_ashby_boards(db_session: Session) -> None:
    lever = connect_provider_source(
        "lever",
        "Example Lever Co",
        db_session,
        board_token="exampleco",
    )
    assert lever.source_key == "lever:exampleco"
    assert lever.base_url == (
        "https://api.lever.co/v0/postings/exampleco"
    )
    assert lever.enabled and lever.allowlisted
    assert lever.server_fetch_allowed
    assert lever.terms_review_status == "approved_for_configured_use"

    ashby = connect_provider_source(
        "ashby",
        "Example Ashby Co",
        db_session,
        board_token="ExampleCo",
    )
    assert ashby.source_key == "ashby:exampleco"
    assert ashby.base_url == (
        "https://api.ashbyhq.com/posting-api/job-board/ExampleCo"
    )


def test_connect_rejects_bad_board_token(db_session: Session) -> None:
    with pytest.raises(ProviderCatalogError):
        connect_provider_source(
            "lever",
            "Bad",
            db_session,
            board_token="../etc/passwd",
        )


def test_connect_duplicate_source_conflicts(
    db_session: Session,
) -> None:
    connect_provider_source(
        "remotive", "Remotive", db_session
    )
    with pytest.raises(ProviderCatalogError) as excinfo:
        connect_provider_source(
            "remotive", "Remotive again", db_session
        )
    assert excinfo.value.status_code == 409


def test_connect_adzuna_requires_keys_and_valid_country(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CAREERPILOT_ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("CAREERPILOT_ADZUNA_APP_KEY", raising=False)
    with pytest.raises(ProviderCatalogError) as excinfo:
        connect_provider_source(
            "adzuna",
            "Adzuna UK",
            db_session,
            country="gb",
        )
    assert "not configured" in excinfo.value.safe_message

    monkeypatch.setenv("CAREERPILOT_ADZUNA_APP_ID", "test-id")
    monkeypatch.setenv("CAREERPILOT_ADZUNA_APP_KEY", "test-key")
    with pytest.raises(ProviderCatalogError):
        connect_provider_source(
            "adzuna",
            "Adzuna Mars",
            db_session,
            country="zz",
        )

    source = connect_provider_source(
        "adzuna",
        "Adzuna UK Engineering",
        db_session,
        country="gb",
        search_query="platform engineer",
    )
    assert source.source_key.startswith("adzuna:gb:")
    # Keys must never be stored on the source row.
    assert "test-id" not in (source.base_url or "")
    assert "test-key" not in (source.base_url or "")


def test_connect_reed_requires_key(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CAREERPILOT_REED_API_KEY", raising=False)
    with pytest.raises(ProviderCatalogError) as excinfo:
        connect_provider_source(
            "reed",
            "Reed London",
            db_session,
            search_query="platform engineer",
            country="London",
        )
    assert "not configured" in excinfo.value.safe_message

    monkeypatch.setenv("CAREERPILOT_REED_API_KEY", "reed-test-key")
    source = connect_provider_source(
        "reed",
        "Reed London",
        db_session,
        search_query="platform engineer",
        country="London",
    )
    assert source.base_url is not None
    assert source.base_url.startswith(
        "https://www.reed.co.uk/api/1.0/search?"
    )
    assert "reed-test-key" not in source.base_url


# --- Ingest: keyless providers ----------------------------------------------


def test_ingest_lever_jobs(db_session: Session) -> None:
    source = connect_provider_source(
        "lever",
        "Example Lever Co",
        db_session,
        board_token="exampleco",
    )
    payload = [
        {
            "id": "abc-123",
            "text": "Platform Engineer",
            "hostedUrl": "https://jobs.lever.co/exampleco/abc-123",
            "createdAt": 1767225600000,
            "descriptionPlain": "Build reliable platforms.",
            "categories": {"location": "London, UK"},
        }
    ]
    run = ingest_provider_source(
        source.id,
        db_session,
        http_client=payload_client(payload),
    )
    assert run.run_status == "succeeded"
    assert run.jobs_discovered == 1
    assert "Platform Engineer" in job_titles(db_session)

    job = db_session.query(NormalizedJob).one()
    assert job.employer_name == "Example Lever Co"
    assert job.source_url == (
        "https://jobs.lever.co/exampleco/abc-123"
    )


def test_ingest_ashby_jobs_marks_remote(db_session: Session) -> None:
    source = connect_provider_source(
        "ashby",
        "Example Ashby Co",
        db_session,
        board_token="exampleco",
    )
    payload = {
        "jobs": [
            {
                "id": "a1",
                "title": "Backend Engineer",
                "jobUrl": "https://jobs.ashbyhq.com/exampleco/a1",
                "descriptionPlain": "APIs.",
                "isRemote": True,
                "location": "United Kingdom",
                "publishedAt": "2026-07-01T00:00:00Z",
            }
        ]
    }
    run = ingest_provider_source(
        source.id,
        db_session,
        http_client=payload_client(payload),
    )
    assert run.run_status == "succeeded"
    job = db_session.query(NormalizedJob).one()
    assert job.remote_mode == "remote"


def test_ingest_remotive_uses_per_job_employer(
    db_session: Session,
) -> None:
    source = connect_provider_source(
        "remotive", "Remotive", db_session
    )
    payload = {
        "jobs": [
            {
                "id": 991,
                "url": "https://remotive.com/jobs/991",
                "title": "Remote Data Engineer",
                "company_name": "Acme Analytics",
                "candidate_required_location": "Europe",
                "publication_date": "2026-07-01T08:00:00",
                "description": "<p>Pipelines.</p>",
            }
        ]
    }
    run = ingest_provider_source(
        source.id,
        db_session,
        http_client=payload_client(payload),
    )
    assert run.run_status == "succeeded"
    job = db_session.query(NormalizedJob).one()
    assert job.employer_name == "Acme Analytics"
    assert job.remote_mode == "remote"
    assert job.description_text == "Pipelines."


def test_ingest_arbeitnow_jobs(db_session: Session) -> None:
    source = connect_provider_source(
        "arbeitnow", "Arbeitnow", db_session
    )
    payload = {
        "data": [
            {
                "slug": "backend-engineer-berlin-1",
                "company_name": "Beispiel GmbH",
                "title": "Backend Engineer",
                "description": "<p>Go and Python.</p>",
                "remote": True,
                "url": (
                    "https://www.arbeitnow.com/jobs/companies/"
                    "beispiel/backend-engineer-berlin-1"
                ),
                "location": "Berlin",
                "created_at": 1767225600,
            }
        ]
    }
    run = ingest_provider_source(
        source.id,
        db_session,
        http_client=payload_client(payload),
    )
    assert run.run_status == "succeeded"
    job = db_session.query(NormalizedJob).one()
    assert job.employer_name == "Beispiel GmbH"
    assert job.remote_mode == "remote"


# --- Ingest: key-gated providers ---------------------------------------------


def test_ingest_adzuna_sends_keys_only_at_fetch_time(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAREERPILOT_ADZUNA_APP_ID", "test-id")
    monkeypatch.setenv("CAREERPILOT_ADZUNA_APP_KEY", "test-key")
    source = connect_provider_source(
        "adzuna",
        "Adzuna UK",
        db_session,
        country="gb",
        search_query="engineer",
    )

    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["app_id"] = request.url.params.get("app_id", "")
        seen["app_key"] = request.url.params.get("app_key", "")
        return json_response(
            {
                "results": [
                    {
                        "id": 777,
                        "title": "Site Reliability Engineer",
                        "redirect_url": (
                            "https://www.adzuna.co.uk/jobs/777"
                        ),
                        "description": "Keep things up.",
                        "company": {"display_name": "Uptime Ltd"},
                        "location": {"display_name": "London, UK"},
                        "created": "2026-07-01T00:00:00Z",
                    }
                ]
            }
        )

    run = ingest_provider_source(
        source.id,
        db_session,
        http_client=mock_client(handler),
    )
    assert run.run_status == "succeeded"
    assert seen == {"app_id": "test-id", "app_key": "test-key"}
    job = db_session.query(NormalizedJob).one()
    assert job.employer_name == "Uptime Ltd"


def test_ingest_reed_uses_basic_auth_header(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAREERPILOT_REED_API_KEY", "reed-test-key")
    source = connect_provider_source(
        "reed",
        "Reed London",
        db_session,
        search_query="engineer",
        country="London",
    )

    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get(
            "authorization", ""
        )
        return json_response(
            {
                "results": [
                    {
                        "jobId": 555,
                        "employerName": "Thames Tech",
                        "jobTitle": "Platform Engineer",
                        "locationName": "London",
                        "jobDescription": "Ship platforms.",
                        "jobUrl": (
                            "https://www.reed.co.uk/jobs/555"
                        ),
                    }
                ]
            }
        )

    run = ingest_provider_source(
        source.id,
        db_session,
        http_client=mock_client(handler),
    )
    assert run.run_status == "succeeded"
    assert seen["authorization"].startswith("Basic ")
    job = db_session.query(NormalizedJob).one()
    assert job.employer_name == "Thames Tech"


def test_ingest_key_gated_provider_without_keys_fails_clearly(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAREERPILOT_ADZUNA_APP_ID", "test-id")
    monkeypatch.setenv("CAREERPILOT_ADZUNA_APP_KEY", "test-key")
    source = connect_provider_source(
        "adzuna",
        "Adzuna UK",
        db_session,
        country="gb",
    )
    monkeypatch.delenv("CAREERPILOT_ADZUNA_APP_ID")
    monkeypatch.delenv("CAREERPILOT_ADZUNA_APP_KEY")

    with pytest.raises(ProviderCatalogError) as excinfo:
        ingest_provider_source(
            source.id,
            db_session,
            http_client=payload_client({"results": []}),
        )
    assert "not configured" in excinfo.value.safe_message


# --- Safety gates -------------------------------------------------------------


def test_disabled_source_never_fetches(db_session: Session) -> None:
    source = connect_provider_source(
        "lever",
        "Example Lever Co",
        db_session,
        board_token="exampleco",
    )
    source.enabled = False
    db_session.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Fetch must never happen.")

    with pytest.raises(ProviderCatalogError):
        ingest_provider_source(
            source.id,
            db_session,
            http_client=mock_client(handler),
        )


def test_tampered_base_url_never_fetches(db_session: Session) -> None:
    source = connect_provider_source(
        "remotive", "Remotive", db_session
    )
    source.base_url = "https://evil.example.com/api/remote-jobs"
    db_session.commit()

    with pytest.raises(ProviderCatalogError):
        ingest_provider_source(
            source.id,
            db_session,
            http_client=payload_client({"jobs": []}),
        )


def test_dispatch_routes_greenhouse_to_original_adapter(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.provider_greenhouse import (
        connect_greenhouse_board,
    )

    source = connect_greenhouse_board(
        "exampleco", "Example Co", db_session
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "boards-api.greenhouse.io"
        return json_response({"jobs": []})

    run = ingest_job_source(
        source.id,
        db_session,
        http_client=mock_client(handler),
    )
    assert run.run_status == "succeeded"


# --- API roundtrip -------------------------------------------------------------


def test_connect_and_ingest_via_api(
    client: TestClient,
    db_session: Session,
    account: Account,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connected = client.post(
        "/api/job-sources/connect",
        json={
            "provider_type": "lever",
            "display_name": "Example Lever Co",
            "board_token": "exampleco",
        },
        headers=account.headers,
    )
    assert connected.status_code == 201, connected.text
    source_id = connected.json()["id"]

    monkeypatch.setattr(
        provider_catalog,
        "build_http_client",
        lambda: payload_client(
            [
                {
                    "id": "abc-1",
                    "text": "Platform Engineer",
                    "hostedUrl": (
                        "https://jobs.lever.co/exampleco/abc-1"
                    ),
                }
            ]
        ),
    )
    ingested = client.post(
        f"/api/job-sources/{source_id}/ingest",
        headers=account.headers,
    )
    assert ingested.status_code == 201, ingested.text
    assert ingested.json()["run_status"] == "succeeded"
    assert ingested.json()["jobs_discovered"] == 1

    # Anonymous connect is rejected.
    anonymous = client.post(
        "/api/job-sources/connect",
        json={
            "provider_type": "remotive",
            "display_name": "Remotive",
        },
    )
    assert anonymous.status_code == 401

    # Unknown provider types are rejected by schema validation.
    invalid = client.post(
        "/api/job-sources/connect",
        json={
            "provider_type": "indeed",
            "display_name": "Nope",
        },
        headers=account.headers,
    )
    assert invalid.status_code == 422