import json
from typing import Callable
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ingestion import SourceSnapshot
from app.models.job import (
    JobCompensation,
    JobLocation,
    JobSkillRequirement,
    JobSource,
    NormalizedJob,
)
from app.schemas.job import JobSourceCreate
from app.services.job import create_job_source
from app.services.provider_greenhouse import (
    GreenhouseAdapterError,
    ingest_greenhouse_source,
    strip_html_to_text,
    validate_greenhouse_source,
)


from app.api.routes.auth import login_rate_limiter


@pytest.fixture(autouse=True)
def _reset_auth_rate_limiter() -> None:
    login_rate_limiter.reset()


BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/exampleco"


def greenhouse_source(
    database: Session,
    **overrides: object,
) -> JobSource:
    payload: dict[str, object] = {
        "source_key": f"greenhouse-{uuid4().hex[:12]}",
        "display_name": "Example Robotics",
        "source_category": "provider_api",
        "provider_type": "greenhouse",
        "base_url": BOARD_URL,
        "enabled": True,
        "allowlisted": True,
        "access_mode": "api",
        "server_fetch_allowed": True,
        "manual_review_required": True,
        "terms_review_status": "approved_for_configured_use",
        "robots_review_status": "approved_for_configured_use",
        "commercial_use_review_status": "approved_for_configured_use",
    }
    payload.update(overrides)
    return create_job_source(JobSourceCreate(**payload), database)


def greenhouse_job(**overrides: object) -> dict[str, object]:
    job: dict[str, object] = {
        "id": 4000123,
        "absolute_url": (
            "https://boards.greenhouse.io/exampleco/jobs/4000123"
        ),
        "title": "Platform Engineer",
        "content": "&lt;p&gt;Build reliable services.&lt;/p&gt;",
        "updated_at": "2026-06-30T12:00:00+00:00",
        "location": {"name": "London, United Kingdom"},
    }
    job.update(overrides)
    return job


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


def jobs_client(*jobs: dict[str, object]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "boards-api.greenhouse.io"
        assert request.url.path == "/v1/boards/exampleco/jobs"
        assert request.url.params["content"] == "true"
        return json_response({"jobs": list(jobs)})

    return mock_client(handler)


@pytest.mark.parametrize(
    "overrides",
    [
        {"provider_type": "lever"},
        {"enabled": False},
        {"enabled": False, "allowlisted": False},
        {"server_fetch_allowed": False, "access_mode": "api"},
        {"server_fetch_allowed": False, "access_mode": "manual_import"},
        {"base_url": "https://boards.example.com/v1/boards/exampleco"},
        {"base_url": None},
    ],
)
def test_gating_rejects_non_compliant_sources(
    db_session: Session,
    overrides: dict[str, object],
) -> None:
    source = greenhouse_source(db_session, **overrides)

    with pytest.raises(GreenhouseAdapterError):
        validate_greenhouse_source(source)


def test_gating_rejects_unapproved_reviews(db_session: Session) -> None:
    source = greenhouse_source(db_session)
    source.commercial_use_review_status = "review_required"

    with pytest.raises(GreenhouseAdapterError) as error:
        validate_greenhouse_source(source)

    assert "review" in error.value.safe_message


def test_ingest_unknown_source_raises_404(db_session: Session) -> None:
    with pytest.raises(GreenhouseAdapterError) as error:
        ingest_greenhouse_source(987654, db_session)

    assert error.value.status_code == 404


def test_no_fetch_occurs_for_non_compliant_source(
    db_session: Session,
) -> None:
    source = greenhouse_source(db_session, server_fetch_allowed=False)

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("No request should be sent.")

    with pytest.raises(GreenhouseAdapterError):
        ingest_greenhouse_source(
            source.id,
            db_session,
            http_client=mock_client(handler),
        )


def test_successful_ingest_creates_jobs_and_snapshot(
    db_session: Session,
) -> None:
    source = greenhouse_source(
        db_session,
        attribution_required=True,
        attribution_text="Data provided by Example Robotics.",
    )
    run = ingest_greenhouse_source(
        source.id,
        db_session,
        http_client=jobs_client(greenhouse_job()),
    )

    assert run.run_status == "succeeded"
    assert run.jobs_discovered == 1
    assert run.jobs_updated == 0
    assert run.snapshots_recorded == 1
    assert run.failure_summary is None

    job = db_session.scalar(select(NormalizedJob))
    assert job is not None
    assert job.job_source_id == source.id
    assert job.source_job_id == "4000123"
    assert job.title == "Platform Engineer"
    assert job.employer_name == "Example Robotics"
    assert job.description_text == "Build reliable services."
    assert "<" not in (job.description_text or "")
    assert job.source_attribution_text == (
        "Data provided by Example Robotics."
    )
    assert job.normalization_version == "greenhouse-adapter-1"
    assert job.lifecycle_status == "discovered"

    location = db_session.scalar(select(JobLocation))
    assert location is not None
    assert location.raw_location_text == "London, United Kingdom"
    assert location.source_provided is True

    snapshot = db_session.scalar(select(SourceSnapshot))
    assert snapshot is not None
    assert snapshot.job_source_id == source.id
    assert snapshot.payload_media_type == "application/json"
    assert snapshot.payload_size_bytes > 0


def test_reingest_touches_existing_jobs_without_duplicates(
    db_session: Session,
) -> None:
    source = greenhouse_source(db_session)
    first = ingest_greenhouse_source(
        source.id,
        db_session,
        http_client=jobs_client(greenhouse_job()),
    )
    second = ingest_greenhouse_source(
        source.id,
        db_session,
        http_client=jobs_client(greenhouse_job()),
    )

    assert first.jobs_discovered == 1
    assert second.jobs_discovered == 0
    assert second.jobs_updated == 1

    job_ids = list(db_session.scalars(select(NormalizedJob.id)).all())
    assert len(job_ids) == 1


def test_no_compensation_or_skills_are_invented(
    db_session: Session,
) -> None:
    source = greenhouse_source(db_session)
    ingest_greenhouse_source(
        source.id,
        db_session,
        http_client=jobs_client(
            greenhouse_job(
                content=(
                    "&lt;p&gt;Requires Python. Salary $200,000."
                    "&lt;/p&gt;"
                ),
            )
        ),
    )

    assert db_session.scalar(select(JobCompensation)) is None
    assert db_session.scalar(select(JobSkillRequirement)) is None


def test_http_error_fails_run_with_safe_summary(
    db_session: Session,
) -> None:
    source = greenhouse_source(db_session)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    run = ingest_greenhouse_source(
        source.id,
        db_session,
        http_client=mock_client(handler),
    )

    assert run.run_status == "failed"
    assert run.failure_summary == "Provider returned HTTP status 500."
    assert db_session.scalar(select(NormalizedJob)) is None


def test_redirect_is_not_followed_and_fails_run(
    db_session: Session,
) -> None:
    source = greenhouse_source(db_session)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"location": "https://evil.example.com/jobs"},
        )

    run = ingest_greenhouse_source(
        source.id,
        db_session,
        http_client=mock_client(handler),
    )

    assert run.run_status == "failed"
    assert run.failure_summary == "Provider returned HTTP status 302."


def test_failed_parse_still_preserves_fetch_snapshot_audit(
    db_session: Session,
) -> None:
    """Snapshots are fetch-audit records and survive parse failures."""
    source = greenhouse_source(db_session)
    run = ingest_greenhouse_source(
        source.id,
        db_session,
        http_client=jobs_client({"id": 1, "title": ""}),
    )

    assert run.run_status == "failed"
    snapshot = db_session.scalar(select(SourceSnapshot))
    assert snapshot is not None
    assert snapshot.ingestion_run_id == run.id


def test_non_json_response_fails_run(db_session: Session) -> None:
    source = greenhouse_source(db_session)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"<html></html>",
            headers={"content-type": "text/html"},
        )

    run = ingest_greenhouse_source(
        source.id,
        db_session,
        http_client=mock_client(handler),
    )

    assert run.run_status == "failed"
    assert run.failure_summary == "Provider response was not JSON."


def test_invalid_json_fails_run(db_session: Session) -> None:
    source = greenhouse_source(db_session)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"{not-json",
            headers={"content-type": "application/json"},
        )

    run = ingest_greenhouse_source(
        source.id,
        db_session,
        http_client=mock_client(handler),
    )

    assert run.run_status == "failed"
    assert run.failure_summary == "Provider payload was not valid JSON."


def test_oversized_payload_fails_run(db_session: Session) -> None:
    source = greenhouse_source(db_session)
    oversized = json.dumps(
        {"jobs": [], "padding": "x" * (11 * 1024 * 1024)}
    ).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=oversized,
            headers={"content-type": "application/json"},
        )

    run = ingest_greenhouse_source(
        source.id,
        db_session,
        http_client=mock_client(handler),
    )

    assert run.run_status == "failed"
    assert run.failure_summary == (
        "Provider payload exceeded the permitted size."
    )
    assert db_session.scalar(select(SourceSnapshot)) is None


def test_incomplete_job_entry_fails_run_without_partial_writes(
    db_session: Session,
) -> None:
    source = greenhouse_source(db_session)
    run = ingest_greenhouse_source(
        source.id,
        db_session,
        http_client=jobs_client(
            greenhouse_job(),
            {"id": 999, "title": ""},
        ),
    )

    assert run.run_status == "failed"
    assert run.failure_summary == (
        "Provider job entry was missing required fields."
    )
    assert db_session.scalar(select(NormalizedJob)) is None


def test_failure_summaries_never_contain_urls_or_paths(
    db_session: Session,
) -> None:
    source = greenhouse_source(db_session)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom /internal/path")

    run = ingest_greenhouse_source(
        source.id,
        db_session,
        http_client=mock_client(handler),
    )

    assert run.run_status == "failed"
    assert run.failure_summary is not None
    assert "http" not in run.failure_summary.lower()
    assert "/" not in run.failure_summary
    assert "boom" not in run.failure_summary


def test_html_stripping_is_deterministic() -> None:
    assert strip_html_to_text(
        "&lt;p&gt;Hello &amp;amp; welcome&lt;/p&gt;"
    ) == "Hello &amp; welcome"
    assert strip_html_to_text("<b>Bold</b> move") == "Bold move"


def test_ingest_endpoint_success(
    auth_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = greenhouse_source(db_session)
    monkeypatch.setattr(
        "app.services.provider_greenhouse.build_http_client",
        lambda: jobs_client(greenhouse_job()),
    )

    response = auth_client.post(f"/api/job-sources/{source.id}/ingest")

    assert response.status_code == 201
    body = response.json()
    assert body["run_status"] == "succeeded"
    assert body["jobs_discovered"] == 1
    assert body["snapshots_recorded"] == 1
    forbidden_fragments = ("storage", "payload_body", "secret", "token")
    for key in body:
        for fragment in forbidden_fragments:
            assert fragment not in key.lower()


def test_ingest_endpoint_rejects_non_compliant_source(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    source = greenhouse_source(db_session, server_fetch_allowed=False)

    response = auth_client.post(f"/api/job-sources/{source.id}/ingest")

    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]


def test_ingest_endpoint_unknown_source_404(auth_client: TestClient) -> None:
    response = auth_client.post("/api/job-sources/987654/ingest")

    assert response.status_code == 404
