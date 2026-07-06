from decimal import Decimal
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.job import NormalizedJob
from app.schemas.job import (
    JobCompensationCreate,
    JobSourceCreate,
    NormalizedJobCreate,
)
from app.services.job import create_job_source, create_normalized_job
from app.services.salary import (
    ALGORITHM_VERSION,
    SalaryServiceError,
    recommend_salary,
)


def content_hash(seed: str | None = None) -> str:
    return sha256((seed or uuid4().hex).encode()).hexdigest()


def make_profile(
    database: Session,
    **overrides: object,
) -> CandidateProfile:
    values: dict[str, object] = {
        "full_name": "Test Candidate",
        "email": "candidate@example.com",
        "requires_sponsorship": False,
        "willing_to_relocate": False,
        "preferred_work_modes": [],
        "target_roles": [],
        "preferred_locations": [],
        "salary_currency": "GBP",
        "minimum_match_score": 50,
        "auto_apply_enabled": False,
        "facts_verified": True,
    }
    values.update(overrides)
    profile = CandidateProfile(**values)
    database.add(profile)
    database.commit()
    return profile


def compensation(
    minimum: str | None,
    maximum: str | None,
    currency: str = "GBP",
    period: str = "yearly",
) -> JobCompensationCreate:
    return JobCompensationCreate(
        min_amount=Decimal(minimum) if minimum else None,
        max_amount=Decimal(maximum) if maximum else None,
        currency=currency,
        compensation_period=period,
        source_text=f"{minimum}-{maximum} {currency}",
    )


def make_job(
    database: Session,
    *,
    title: str = "Platform Engineer",
    compensations: list[JobCompensationCreate] | None = None,
    **overrides: object,
) -> NormalizedJob:
    source = create_job_source(
        JobSourceCreate(
            source_key=f"source-{uuid4().hex[:12]}",
            display_name="Example Robotics",
            source_category="provider_api",
        ),
        database,
    )
    payload: dict[str, object] = {
        "job_source_id": source.id,
        "source_job_id": f"job-{uuid4().hex[:16]}",
        "source_url": f"https://jobs.example.com/{uuid4().hex}",
        "employer_name": "Example Robotics",
        "title": title,
        "normalized_title": title.casefold(),
        "content_hash": content_hash(),
        "normalization_version": "phase7-test",
    }
    payload.update(overrides)
    return create_normalized_job(
        NormalizedJobCreate(**payload),
        database,
        compensations=compensations or [],
    )


def test_requires_job_and_profile(db_session: Session) -> None:
    with pytest.raises(SalaryServiceError) as missing_job:
        recommend_salary(987654, db_session, candidate_profile_id=1)
    assert missing_job.value.status_code == 404

    job = make_job(db_session)
    with pytest.raises(SalaryServiceError) as missing_profile:
        recommend_salary(job.id, db_session, candidate_profile_id=1)
    assert missing_profile.value.status_code == 404


def test_advertised_range_gives_high_confidence(
    db_session: Session,
) -> None:
    make_profile(db_session)
    job = make_job(
        db_session,
        compensations=[compensation("70000", "90000")],
    )

    result = recommend_salary(job.id, db_session, candidate_profile_id=1)

    assert result.basis == "advertised_range"
    assert result.confidence == "high"
    assert result.minimum == Decimal("70000")
    assert result.maximum == Decimal("90000")
    assert result.midpoint == Decimal("80000.00")
    assert result.currency == "GBP"
    assert result.algorithm_version == ALGORITHM_VERSION
    assert "70000" in result.safe_answer
    assert "90000" in result.safe_answer


def test_comparables_give_medium_confidence_with_three_jobs(
    db_session: Session,
) -> None:
    make_profile(db_session)
    for minimum, maximum in (
        ("60000", "80000"),
        ("65000", "85000"),
        ("70000", "90000"),
    ):
        make_job(
            db_session,
            compensations=[compensation(minimum, maximum)],
        )
    target = make_job(db_session)

    result = recommend_salary(target.id, db_session, candidate_profile_id=1)

    assert result.basis == "comparable_jobs"
    assert result.confidence == "medium"
    assert result.comparable_job_count == 3
    assert result.minimum == Decimal("60000")
    assert result.maximum == Decimal("90000")


def test_few_comparables_give_low_confidence(
    db_session: Session,
) -> None:
    make_profile(db_session)
    make_job(
        db_session,
        compensations=[compensation("60000", "80000")],
    )
    target = make_job(db_session)

    result = recommend_salary(target.id, db_session, candidate_profile_id=1)

    assert result.basis == "comparable_jobs"
    assert result.confidence == "low"
    assert result.comparable_job_count == 1


def test_different_titles_are_not_comparable(
    db_session: Session,
) -> None:
    make_profile(db_session)
    make_job(
        db_session,
        title="Data Scientist",
        compensations=[compensation("100000", "120000")],
    )
    target = make_job(db_session, title="Platform Engineer")

    result = recommend_salary(target.id, db_session, candidate_profile_id=1)

    assert result.basis == "insufficient_data"
    assert result.minimum is None


def test_no_data_recommends_nothing_instead_of_inventing(
    db_session: Session,
) -> None:
    make_profile(db_session)
    job = make_job(db_session)

    result = recommend_salary(job.id, db_session, candidate_profile_id=1)

    assert result.basis == "insufficient_data"
    assert result.confidence == "low"
    assert result.minimum is None
    assert result.maximum is None
    assert result.midpoint is None
    assert not any(char.isdigit() for char in result.safe_answer)


def test_currency_groups_are_not_mixed(db_session: Session) -> None:
    make_profile(db_session)
    for currency in ("GBP", "GBP", "USD"):
        make_job(
            db_session,
            compensations=[
                compensation("60000", "80000", currency=currency)
            ],
        )
    target = make_job(db_session)

    result = recommend_salary(target.id, db_session, candidate_profile_id=1)

    assert result.currency == "GBP"
    assert result.minimum == Decimal("60000")
    assert result.maximum == Decimal("80000")


def test_below_declared_minimum_is_flagged_not_disclosed(
    db_session: Session,
) -> None:
    make_profile(
        db_session,
        minimum_salary=100000,
        salary_currency="GBP",
    )
    job = make_job(
        db_session,
        compensations=[compensation("60000", "80000")],
    )

    result = recommend_salary(job.id, db_session, candidate_profile_id=1)

    assert result.below_declared_minimum is True
    assert "100000" not in result.safe_answer
    assert any("declared minimum" in factor for factor in result.factors)


def test_minimum_in_other_currency_is_not_compared(
    db_session: Session,
) -> None:
    make_profile(
        db_session,
        minimum_salary=100000,
        salary_currency="USD",
    )
    job = make_job(
        db_session,
        compensations=[compensation("60000", "80000", currency="GBP")],
    )

    result = recommend_salary(job.id, db_session, candidate_profile_id=1)

    assert result.below_declared_minimum is False


def test_endpoint_shape_and_404(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    job = make_job(
        db_session,
        compensations=[compensation("70000", "90000")],
    )

    response = auth_client.post(
        "/api/salary-recommendation",
        json={"job_id": job.id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] == "high"
    assert body["basis"] == "advertised_range"
    assert body["safe_answer"]
    assert isinstance(body["factors"], list)

    missing = auth_client.post(
        "/api/salary-recommendation",
        json={"job_id": 987654},
    )
    assert missing.status_code == 404

    invalid = auth_client.post(
        "/api/salary-recommendation",
        json={"job_id": 0},
    )
    assert invalid.status_code == 422
