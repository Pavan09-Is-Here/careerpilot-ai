from hashlib import sha256
from pathlib import Path
import sqlite3
from typing import Any
import urllib.request
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.models.job import JobSkillRequirement, JobSource, NormalizedJob
from app.schemas.job import (
    JobCompensationCreate,
    JobLocationCreate,
    JobSkillRequirementCreate,
    JobSourceCreate,
    NormalizedJobCreate,
)
from app.services.job import (
    JobServiceError,
    build_job_source,
    create_job_source,
    create_normalized_job,
    validate_job_lifecycle_transition,
)


PHASE37_HEAD = "a7b8c9d0e1f2"
PHASE41_HEAD = "b8c9d0e1f2a3"
CHAIN_HEAD = "d2e3f4a5b6c7"


def content_hash(seed: str | None = None) -> str:
    return sha256((seed or uuid4().hex).encode()).hexdigest()


def source_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_key": f"source-{uuid4().hex[:12]}",
        "display_name": f"Synthetic Source {uuid4().hex[:8]}",
        "source_category": "provider_api",
        "provider_type": "none",
    }
    payload.update(overrides)
    return payload


def make_source(
    database: Session,
    **overrides: object,
) -> JobSource:
    return create_job_source(
        JobSourceCreate(**source_payload(**overrides)),
        database,
    )


def approved_source_payload(**overrides: object) -> dict[str, object]:
    payload = source_payload(
        allowlisted=True,
        enabled=True,
        manual_review_required=True,
        terms_review_status="approved_for_configured_use",
        robots_review_status="approved_for_configured_use",
        commercial_use_review_status="approved_for_configured_use",
    )
    payload.update(overrides)
    return payload


def job_payload(
    source: JobSource,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "job_source_id": source.id,
        "source_job_id": f"job-{uuid4().hex[:16]}",
        "source_url": f"https://jobs.example.com/{uuid4().hex}",
        "canonical_url": f"https://careers.example.com/{uuid4().hex}",
        "employer_name": "Example Robotics",
        "employer_external_id": None,
        "title": "Platform Engineer",
        "normalized_title": "platform engineer",
        "description_text": "Synthetic role description.",
        "responsibilities_text": "Build reliable internal services.",
        "required_qualifications_text": "Experience with backend systems.",
        "preferred_qualifications_text": "Experience with observability.",
        "remote_mode": "unspecified",
        "employment_type": "unspecified",
        "seniority": "unspecified",
        "source_sponsorship_visa_text": "Source wording only.",
        "source_attribution_text": "Synthetic attribution.",
        "source_license_reference": "Synthetic licence reference.",
        "content_hash": content_hash(),
        "normalization_version": "phase4.1-test",
    }
    payload.update(overrides)
    return payload


def make_job(
    database: Session,
    *,
    source: JobSource | None = None,
    locations: list[JobLocationCreate] | None = None,
    compensations: list[JobCompensationCreate] | None = None,
    skill_requirements: list[JobSkillRequirementCreate] | None = None,
    **overrides: object,
) -> NormalizedJob:
    active_source = source or make_source(database)
    return create_normalized_job(
        NormalizedJobCreate(**job_payload(active_source, **overrides)),
        database,
        locations=locations or [],
        compensations=compensations or [],
        skill_requirements=skill_requirements or [],
    )


def real_database_fingerprint() -> tuple[str, int, int, str]:
    database_path = Path(__file__).resolve().parents[1] / "careerpilot.db"
    stat_result = database_path.stat()
    with database_path.open("rb") as file_obj:
        digest = sha256(file_obj.read()).hexdigest()

    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    try:
        revision = connection.execute(
            "select version_num from alembic_version"
        ).fetchone()[0]
    finally:
        connection.close()

    return (
        digest,
        stat_result.st_size,
        stat_result.st_mtime_ns,
        str(revision),
    )


def assert_no_sensitive_job_fields(payload: dict[str, Any]) -> None:
    forbidden_fragments = {
        "credential",
        "secret",
        "token",
        "api_key",
        "password",
        "internal_notes",
        "storage_path",
        "raw_payload",
    }

    for key in payload:
        assert not any(fragment in key for fragment in forbidden_fragments)


def test_job_source_defaults_are_disabled_unapproved_and_metadata_only() -> None:
    source = build_job_source(
        JobSourceCreate(**source_payload(source_key="synthetic-source"))
    )

    assert source.enabled is False
    assert source.allowlisted is False
    assert source.server_fetch_allowed is False
    assert source.configured_retention_days == 30
    assert source.terms_review_status == "not_reviewed"
    assert source.robots_review_status == "not_reviewed"
    assert source.commercial_use_review_status == "not_reviewed"
    assert source.access_mode == "metadata_only"


def test_invalid_source_retention_is_rejected() -> None:
    with pytest.raises(ValidationError):
        JobSourceCreate(**source_payload(configured_retention_days=366))


def test_source_cannot_enable_without_allowlist() -> None:
    with pytest.raises(JobServiceError) as exc_info:
        build_job_source(
            JobSourceCreate(
                **approved_source_payload(
                    source_key="not-allowlisted",
                    allowlisted=False,
                )
            )
        )

    assert "allowlisted" in exc_info.value.safe_message


def test_manual_review_source_cannot_enable_before_approval() -> None:
    with pytest.raises(JobServiceError) as exc_info:
        build_job_source(
            JobSourceCreate(
                **source_payload(
                    source_key="review-unresolved",
                    enabled=True,
                    allowlisted=True,
                    manual_review_required=True,
                    terms_review_status="review_required",
                )
            )
        )

    assert "Manual review" in exc_info.value.safe_message


def test_attribution_required_source_cannot_enable_without_attribution() -> None:
    with pytest.raises(JobServiceError) as exc_info:
        build_job_source(
            JobSourceCreate(
                **approved_source_payload(
                    source_key="missing-attribution",
                    attribution_required=True,
                )
            )
        )

    assert "Attribution information" in exc_info.value.safe_message


def test_metadata_only_url_source_cannot_enable_server_fetching() -> None:
    with pytest.raises(JobServiceError) as exc_info:
        build_job_source(
            JobSourceCreate(
                **source_payload(
                    source_key="metadata-url",
                    source_category="user_supplied_url",
                    access_mode="metadata_only",
                    server_fetch_allowed=True,
                )
            )
        )

    assert "cannot allow server fetching" in exc_info.value.safe_message


def test_source_enums_validate() -> None:
    with pytest.raises(ValidationError):
        JobSourceCreate(**source_payload(access_mode="scrape_anything"))


def test_source_creation_rejects_credentials() -> None:
    payload = source_payload(api_key="not-a-real-key")

    with pytest.raises(ValidationError):
        JobSourceCreate(**payload)


def test_documentation_url_does_not_infer_approval() -> None:
    source = build_job_source(
        JobSourceCreate(
            **source_payload(
                source_key="docs-only",
                base_url="https://docs.example.com/jobs",
            )
        )
    )

    assert source.enabled is False
    assert source.allowlisted is False
    assert source.terms_review_status == "not_reviewed"


def test_compliance_statuses_are_operational_not_legal_guarantees(
    client: TestClient,
    db_session: Session,
) -> None:
    source = make_source(
        db_session,
        **approved_source_payload(source_key="operational-status"),
    )

    response = client.get(f"/api/job-sources/{source.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["terms_review_status"] == "approved_for_configured_use"
    assert "compliant" not in payload
    assert "legal_compliance" not in payload


def test_source_list_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    make_source(db_session, display_name="Beta Source")
    first = make_source(db_session, display_name="Alpha Source")
    make_source(db_session, display_name="Gamma Source")

    response = client.get("/api/job-sources?page=1&page_size=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["page"] == 1
    assert payload["page_size"] == 1
    assert payload["items"][0]["id"] == first.id


def test_source_detail_404(client: TestClient) -> None:
    response = client.get("/api/job-sources/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job source was not found."


def test_job_requires_source(db_session: Session) -> None:
    with pytest.raises(JobServiceError) as exc_info:
        create_normalized_job(
            NormalizedJobCreate(
                **{
                    **job_payload(
                        JobSource(id=999999, source_key="missing"),
                    ),
                    "job_source_id": 999999,
                }
            ),
            db_session,
        )

    assert exc_info.value.safe_message == "Job source was not found."


def test_source_scoped_source_job_id_uniqueness(
    db_session: Session,
) -> None:
    source = make_source(db_session)
    source_job_id = "same-source-id"
    make_job(db_session, source=source, source_job_id=source_job_id)

    with pytest.raises(JobServiceError) as exc_info:
        make_job(db_session, source=source, source_job_id=source_job_id)

    assert exc_info.value.status_code == 409


def test_same_source_job_id_may_exist_under_different_sources(
    db_session: Session,
) -> None:
    source_job_id = "shared-provider-id"
    first = make_job(
        db_session,
        source=make_source(db_session),
        source_job_id=source_job_id,
    )
    second = make_job(
        db_session,
        source=make_source(db_session),
        source_job_id=source_job_id,
    )

    assert first.source_job_id == second.source_job_id
    assert first.job_source_id != second.job_source_id


def test_default_job_lifecycle_does_not_claim_active(
    db_session: Session,
) -> None:
    job = make_job(db_session)

    assert job.lifecycle_status == "discovered"


def test_job_lifecycle_transition_validation() -> None:
    validate_job_lifecycle_transition("discovered", "active")

    with pytest.raises(JobServiceError):
        validate_job_lifecycle_transition("unavailable", "active")


def test_job_list_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    first = make_job(db_session, title="First Job")
    make_job(db_session, title="Second Job")

    response = client.get("/api/jobs?page=1&page_size=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["items"][0]["id"] != first.id
    assert len(payload["items"]) == 1


def test_job_list_filtering_by_source(
    client: TestClient,
    db_session: Session,
) -> None:
    selected_source = make_source(db_session)
    selected = make_job(db_session, source=selected_source)
    make_job(db_session, source=make_source(db_session))

    response = client.get(f"/api/jobs?source={selected_source.id}")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [selected.id]


def test_job_list_filtering_by_lifecycle(
    client: TestClient,
    db_session: Session,
) -> None:
    active = make_job(db_session, lifecycle_status="active")
    make_job(db_session, lifecycle_status="expired")

    response = client.get("/api/jobs?lifecycle_status=active")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [active.id]


def test_job_list_filtering_by_employer(
    client: TestClient,
    db_session: Session,
) -> None:
    selected = make_job(db_session, employer_name="Unicode Labs")
    make_job(db_session, employer_name="Other Employer")

    response = client.get("/api/jobs?employer=unicode%20labs")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [selected.id]


def test_job_list_filtering_by_employment_type(
    client: TestClient,
    db_session: Session,
) -> None:
    selected = make_job(db_session, employment_type="full_time")
    make_job(db_session, employment_type="contract")

    response = client.get("/api/jobs?employment_type=full_time")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [selected.id]


def test_job_list_filtering_by_remote_mode(
    client: TestClient,
    db_session: Session,
) -> None:
    selected = make_job(db_session, remote_mode="remote")
    make_job(db_session, remote_mode="hybrid")

    response = client.get("/api/jobs?remote_mode=remote")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [selected.id]


def test_job_detail_404(client: TestClient) -> None:
    response = client.get("/api/jobs/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job was not found."


def test_list_response_excludes_full_oversized_description(
    client: TestClient,
    db_session: Session,
) -> None:
    long_description = "A" * 1000
    job = make_job(db_session, description_text=long_description)

    response = client.get("/api/jobs")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["id"] == job.id
    assert "description_text" not in item
    assert len(item["description_excerpt"]) <= 240


def test_detail_response_returns_bounded_safe_text(
    client: TestClient,
    db_session: Session,
) -> None:
    description = "Detailed synthetic description " * 20
    job = make_job(db_session, description_text=description)

    response = client.get(f"/api/jobs/{job.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["description_text"] == description
    assert len(payload["description_text"]) <= 20000


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:text/plain,hello",
        "file:///tmp/job",
        "not a url",
    ],
)
def test_invalid_url_schemes_rejected(
    db_session: Session,
    url: str,
) -> None:
    source = make_source(db_session)

    with pytest.raises((JobServiceError, ValidationError)):
        create_normalized_job(
            NormalizedJobCreate(**job_payload(source, source_url=url)),
            db_session,
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/jobs/1",
        "http://localhost/jobs/1",
        "http://10.0.0.5/jobs/1",
        "http://172.16.0.1/jobs/1",
        "http://192.168.1.10/jobs/1",
        "http://[::1]/jobs/1",
    ],
)
def test_private_and_loopback_url_validation(
    db_session: Session,
    url: str,
) -> None:
    source = make_source(db_session)

    with pytest.raises(JobServiceError):
        create_normalized_job(
            NormalizedJobCreate(**job_payload(source, source_url=url)),
            db_session,
        )


def test_no_server_side_url_request_occurs(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = make_source(db_session)

    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("URL fetching must not occur in Phase 4.1")

    monkeypatch.setattr(urllib.request, "urlopen", fail_if_called)
    job = make_job(
        db_session,
        source=source,
        source_url="https://example.com/jobs/no-fetch",
    )

    assert job.source_url == "https://example.com/jobs/no-fetch"


def test_unicode_job_text_is_preserved(
    client: TestClient,
    db_session: Session,
) -> None:
    job = make_job(
        db_session,
        employer_name="Łódź AI 株式会社",
        title="Développeur Plateforme",
        description_text="Build tooling for São Paulo, Kraków, and 東京.",
    )

    response = client.get(f"/api/jobs/{job.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["employer_name"] == "Łódź AI 株式会社"
    assert payload["title"] == "Développeur Plateforme"
    assert "東京" in payload["description_text"]


@pytest.mark.parametrize("bad_text", ["Bad\x00Title", "Bad\x01Title"])
def test_null_byte_and_control_character_rejection(
    db_session: Session,
    bad_text: str,
) -> None:
    source = make_source(db_session)

    with pytest.raises(JobServiceError):
        create_normalized_job(
            NormalizedJobCreate(**job_payload(source, title=bad_text)),
            db_session,
        )


def test_description_size_limit() -> None:
    source = JobSource(id=1, source_key="source")

    with pytest.raises(ValidationError):
        NormalizedJobCreate(
            **job_payload(source, description_text="x" * 20001)
        )


def test_compensation_min_max_validation(
    db_session: Session,
) -> None:
    source = make_source(db_session)

    with pytest.raises(JobServiceError):
        create_normalized_job(
            NormalizedJobCreate(**job_payload(source)),
            db_session,
            compensations=[
                JobCompensationCreate(
                    min_amount="150000.00",
                    max_amount="100000.00",
                    currency="GBP",
                    compensation_period="yearly",
                )
            ],
        )


def test_currency_validation(
    db_session: Session,
) -> None:
    source = make_source(db_session)

    with pytest.raises(JobServiceError):
        create_normalized_job(
            NormalizedJobCreate(**job_payload(source)),
            db_session,
            compensations=[
                JobCompensationCreate(
                    min_amount="100000.00",
                    currency="usd",
                    compensation_period="yearly",
                )
            ],
        )


def test_no_currency_conversion(
    client: TestClient,
    db_session: Session,
) -> None:
    job = make_job(
        db_session,
        compensations=[
            JobCompensationCreate(
                min_amount="100000.00",
                max_amount="120000.00",
                currency="USD",
                compensation_period="yearly",
                source_text="USD 100,000-120,000 per year",
            )
        ],
    )

    response = client.get(f"/api/jobs/{job.id}")

    assert response.status_code == 200
    compensation = response.json()["compensations"][0]
    assert compensation["currency"] == "USD"
    assert compensation["min_amount"] == "100000.00"
    assert compensation["max_amount"] == "120000.00"


def test_duplicate_skill_requirement_prevention(
    db_session: Session,
) -> None:
    source = make_source(db_session)
    skill = JobSkillRequirementCreate(
        skill_text="Python",
        requirement_type="required",
    )

    with pytest.raises(JobServiceError):
        create_normalized_job(
            NormalizedJobCreate(**job_payload(source)),
            db_session,
            skill_requirements=[skill, skill],
        )


def test_skill_stable_ordering(
    client: TestClient,
    db_session: Session,
) -> None:
    job = make_job(
        db_session,
        skill_requirements=[
            JobSkillRequirementCreate(
                sort_order=2,
                skill_text="Observability",
                requirement_type="preferred",
            ),
            JobSkillRequirementCreate(
                sort_order=1,
                skill_text="Python",
                requirement_type="required",
            ),
        ],
    )

    response = client.get(f"/api/jobs/{job.id}")

    assert response.status_code == 200
    assert [
        item["skill_text"]
        for item in response.json()["skill_requirements"]
    ] == ["Python", "Observability"]


def test_no_ai_or_inferred_skills_from_description(
    client: TestClient,
    db_session: Session,
) -> None:
    job = make_job(
        db_session,
        description_text="This source text mentions Python and Kubernetes.",
    )

    response = client.get(f"/api/jobs/{job.id}")

    assert response.status_code == 200
    assert response.json()["skill_requirements"] == []


def test_skill_records_must_be_source_provided(
    db_session: Session,
) -> None:
    source = make_source(db_session)

    with pytest.raises(JobServiceError):
        create_normalized_job(
            NormalizedJobCreate(**job_payload(source)),
            db_session,
            skill_requirements=[
                JobSkillRequirementCreate(
                    skill_text="Inferred Skill",
                    requirement_type="mentioned",
                    source_provided=False,
                )
            ],
        )


def test_provenance_fields_are_required() -> None:
    payload = job_payload(JobSource(id=1, source_key="source"))
    for key in [
        "job_source_id",
        "source_job_id",
        "source_url",
        "content_hash",
        "normalization_version",
    ]:
        invalid_payload = dict(payload)
        invalid_payload.pop(key)
        with pytest.raises(ValidationError):
            NormalizedJobCreate(**invalid_payload)


def test_content_hash_format_validation(
    db_session: Session,
) -> None:
    source = make_source(db_session)

    with pytest.raises(JobServiceError):
        create_normalized_job(
            NormalizedJobCreate(
                **job_payload(source, content_hash="g" * 64)
            ),
            db_session,
        )


def test_normalization_version_validation(
    db_session: Session,
) -> None:
    source = make_source(db_session)

    with pytest.raises(JobServiceError):
        create_normalized_job(
            NormalizedJobCreate(
                **job_payload(source, normalization_version="bad version")
            ),
            db_session,
        )


def test_location_preserves_source_fields_without_geocoding(
    client: TestClient,
    db_session: Session,
) -> None:
    job = make_job(
        db_session,
        locations=[
            JobLocationCreate(
                raw_location_text="London, UK",
                city="London",
                sort_order=0,
            )
        ],
    )

    response = client.get(f"/api/jobs/{job.id}")

    assert response.status_code == 200
    location = response.json()["locations"][0]
    assert location["raw_location_text"] == "London, UK"
    assert location["city"] == "London"
    assert location["country"] is None


def test_api_responses_do_not_expose_internal_notes_secrets_or_paths(
    client: TestClient,
    db_session: Session,
) -> None:
    source = make_source(db_session)
    job = make_job(db_session, source=source)

    source_response = client.get(f"/api/job-sources/{source.id}")
    job_response = client.get(f"/api/jobs/{job.id}")

    assert source_response.status_code == 200
    assert job_response.status_code == 200
    assert_no_sensitive_job_fields(source_response.json())
    assert_no_sensitive_job_fields(job_response.json())


def test_job_tables_have_no_credential_columns() -> None:
    table_columns = {
        column.name
        for table in (
            JobSource.__table__,
            NormalizedJob.__table__,
            JobSkillRequirement.__table__,
        )
        for column in table.columns
    }

    assert "credential" not in table_columns
    assert "api_key" not in table_columns
    assert "token" not in table_columns
    assert "secret" not in table_columns


def test_phase41_migration_upgrade_downgrade_reupgrade(
    tmp_path: Path,
) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    migration_db = tmp_path / "phase41-migration-validation.db"
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{migration_db}")
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == [CHAIN_HEAD]
    assert script.get_revision(PHASE41_HEAD).down_revision == PHASE37_HEAD

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{migration_db}")

    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {
            "job_sources",
            "normalized_jobs",
            "job_locations",
            "job_compensations",
            "job_skill_requirements",
        }.issubset(tables)
        assert "cv_versions" in tables

        source_indexes = {
            index["name"]
            for index in inspector.get_indexes("job_sources")
        }
        job_indexes = {
            index["name"]
            for index in inspector.get_indexes("normalized_jobs")
        }
        assert "ix_job_sources_enabled" in source_indexes
        assert "ix_normalized_jobs_source_lifecycle" in job_indexes

        command.downgrade(config, PHASE37_HEAD)
        downgraded_tables = set(inspect(engine).get_table_names())
        assert "job_sources" not in downgraded_tables
        assert "normalized_jobs" not in downgraded_tables
        assert "cv_version_artifacts" in downgraded_tables

        command.upgrade(config, "head")
        reupgraded_tables = set(inspect(engine).get_table_names())
        assert "job_sources" in reupgraded_tables
        assert "normalized_jobs" in reupgraded_tables
    finally:
        engine.dispose()


def test_exactly_one_alembic_head() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == [CHAIN_HEAD]


def test_real_database_remains_unchanged_by_temp_migration(
    tmp_path: Path,
) -> None:
    before = real_database_fingerprint()
    backend_dir = Path(__file__).resolve().parents[1]
    migration_db = tmp_path / "real-db-safety-validation.db"
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{migration_db}")

    command.upgrade(config, "head")
    command.downgrade(config, PHASE37_HEAD)
    command.upgrade(config, "head")

    assert real_database_fingerprint() == before
