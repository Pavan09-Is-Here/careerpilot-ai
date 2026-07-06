"""Salary recommendation engine (Phase 7).

Conservative, deterministic, and local-data-only by explicit
decision: recommendations aggregate advertised compensation that
already exists in the local database — the job's own stated range
first, then exact-title comparables with the same currency and
period. No external market APIs, no currency conversion, no
invented numbers. When no advertised data exists the engine says
so instead of fabricating a range. The candidate's declared
minimum salary is never revealed in generated answers; it is only
used to warn when an advertised maximum falls below it.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.job import JobCompensation, NormalizedJob
from app.services.job_match import normalize_token


ALGORITHM_VERSION = "salary-local-1"
MIN_COMPARABLES_FOR_MEDIUM = 3


class SalaryServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SalaryRecommendation:
    job_id: int
    currency: str | None
    compensation_period: str | None
    minimum: Decimal | None
    maximum: Decimal | None
    midpoint: Decimal | None
    confidence: str
    basis: str
    comparable_job_count: int
    below_declared_minimum: bool
    factors: list[str] = field(default_factory=list)
    safe_answer: str = ""
    algorithm_version: str = ALGORITHM_VERSION


def bounded_range(
    compensations: list[JobCompensation],
) -> tuple[Decimal, Decimal] | None:
    minimums = [
        record.min_amount
        for record in compensations
        if record.min_amount is not None
    ]
    maximums = [
        record.max_amount
        for record in compensations
        if record.max_amount is not None
    ]
    if not minimums or not maximums:
        return None
    return (min(minimums), max(maximums))


def job_stated_compensations(
    job_id: int,
    database: Session,
) -> list[JobCompensation]:
    return list(
        database.scalars(
            select(JobCompensation).where(
                JobCompensation.job_id == job_id,
                JobCompensation.explicitly_supplied.is_(True),
            )
        ).all()
    )


def comparable_title(job: NormalizedJob) -> str:
    return normalize_token(job.normalized_title or job.title)


def find_comparable_compensations(
    job: NormalizedJob,
    database: Session,
) -> tuple[list[JobCompensation], int]:
    """Compensation records of other jobs with the identical
    normalized title. Exact match only — no fuzzy analogies."""
    title = comparable_title(job)
    others = [
        candidate
        for candidate in database.scalars(
            select(NormalizedJob).where(NormalizedJob.id != job.id)
        ).all()
        if comparable_title(candidate) == title
    ]

    compensations: list[JobCompensation] = []
    jobs_with_data = 0
    for other in others:
        records = job_stated_compensations(other.id, database)
        if records:
            jobs_with_data += 1
            compensations.extend(records)

    return compensations, jobs_with_data


def dominant_currency_period(
    compensations: list[JobCompensation],
) -> tuple[str | None, str | None]:
    counts: dict[tuple[str | None, str], int] = {}
    for record in compensations:
        key = (record.currency, record.compensation_period)
        counts[key] = counts.get(key, 0) + 1

    if not counts:
        return None, None

    (currency, period), _ = max(
        counts.items(),
        key=lambda item: (item[1], str(item[0])),
    )
    return currency, period


def filter_by_currency_period(
    compensations: list[JobCompensation],
    currency: str | None,
    period: str | None,
) -> list[JobCompensation]:
    return [
        record
        for record in compensations
        if record.currency == currency
        and record.compensation_period == period
    ]


def compute_midpoint(
    compensations: list[JobCompensation],
) -> Decimal | None:
    midpoints = [
        (record.min_amount + record.max_amount) / 2
        for record in compensations
        if record.min_amount is not None
        and record.max_amount is not None
    ]
    if not midpoints:
        return None
    return Decimal(median(midpoints)).quantize(Decimal("0.01"))


def check_below_declared_minimum(
    maximum: Decimal | None,
    currency: str | None,
    profile: CandidateProfile,
) -> bool:
    if (
        maximum is None
        or profile.minimum_salary is None
        or currency is None
        or currency != profile.salary_currency
    ):
        return False
    return maximum < Decimal(profile.minimum_salary)


def build_safe_answer(
    recommendation_basis: str,
    minimum: Decimal | None,
    maximum: Decimal | None,
    currency: str | None,
    period: str | None,
) -> str:
    """Deterministic template. Never reveals the candidate's own
    declared minimum salary and never invents numbers."""
    if (
        recommendation_basis == "advertised_range"
        and minimum is not None
        and maximum is not None
    ):
        return (
            "The advertised range for this role is "
            f"{minimum} to {maximum} {currency or ''} "
            f"({period or 'unspecified'}). My expectations are "
            "within the advertised range, depending on the full "
            "scope of the role and total compensation."
        ).replace("  ", " ")

    if (
        recommendation_basis == "comparable_jobs"
        and minimum is not None
        and maximum is not None
    ):
        return (
            "Comparable advertised roles I have on record range "
            f"from {minimum} to {maximum} {currency or ''} "
            f"({period or 'unspecified'}). My expectations are in "
            "line with advertised ranges for this kind of role, "
            "depending on scope and total compensation."
        ).replace("  ", " ")

    return (
        "I would like to understand the full scope of the role "
        "before discussing numbers. I am confident we can agree "
        "on compensation that reflects the advertised market for "
        "this position."
    )


def recommend_salary(
    job_id: int,
    database: Session,
    *,
    candidate_profile_id: int,
) -> SalaryRecommendation:
    job = database.get(NormalizedJob, job_id)
    if job is None:
        raise SalaryServiceError("Job was not found.", status_code=404)

    profile = database.get(CandidateProfile, candidate_profile_id)
    if profile is None:
        raise SalaryServiceError(
            "Candidate profile was not found.",
            status_code=404,
        )

    factors: list[str] = [
        f"Algorithm {ALGORITHM_VERSION}: deterministic aggregation "
        "of advertised compensation stored locally. No external "
        "market APIs, no currency conversion, no invented numbers.",
    ]

    own = job_stated_compensations(job.id, database)
    own_range = bounded_range(own)

    if own_range is not None:
        currency, period = dominant_currency_period(own)
        scoped = filter_by_currency_period(own, currency, period)
        scoped_range = bounded_range(scoped) or own_range
        minimum, maximum = scoped_range
        midpoint = compute_midpoint(scoped) or (
            (minimum + maximum) / 2
        ).quantize(Decimal("0.01"))
        basis = "advertised_range"
        confidence = "high"
        factors.append(
            "The posting itself advertises a compensation range; "
            "this is the strongest available evidence."
        )
        comparable_count = 0
    else:
        comparables, comparable_count = find_comparable_compensations(
            job,
            database,
        )
        currency, period = dominant_currency_period(comparables)
        scoped = filter_by_currency_period(
            comparables,
            currency,
            period,
        )
        scoped_range = bounded_range(scoped)

        if scoped_range is not None:
            minimum, maximum = scoped_range
            midpoint = compute_midpoint(scoped)
            basis = "comparable_jobs"
            confidence = (
                "medium"
                if comparable_count >= MIN_COMPARABLES_FOR_MEDIUM
                else "low"
            )
            factors.append(
                f"{comparable_count} stored job(s) with the "
                "identical normalized title advertise compensation "
                f"in {currency or 'unknown currency'} "
                f"({period or 'unspecified'}); exact-title matches "
                "only, no fuzzy analogies."
            )
        else:
            minimum = None
            maximum = None
            midpoint = None
            basis = "insufficient_data"
            confidence = "low"
            factors.append(
                "Neither this posting nor any stored job with the "
                "identical title advertises compensation. No range "
                "is recommended rather than inventing one."
            )

    below_minimum = check_below_declared_minimum(
        maximum,
        currency,
        profile,
    )
    if below_minimum:
        factors.append(
            "Warning: the advertised maximum is below your declared "
            "minimum salary. This is flagged for your review only "
            "and is never disclosed in generated answers."
        )

    if job.seniority != "unspecified":
        factors.append(
            f"Posting seniority as stated by the source: "
            f"{job.seniority}."
        )

    safe_answer = build_safe_answer(
        basis,
        minimum,
        maximum,
        currency,
        period,
    )

    return SalaryRecommendation(
        job_id=job.id,
        currency=currency,
        compensation_period=period,
        minimum=minimum,
        maximum=maximum,
        midpoint=midpoint,
        confidence=confidence,
        basis=basis,
        comparable_job_count=comparable_count,
        below_declared_minimum=below_minimum,
        factors=factors,
        safe_answer=safe_answer,
    )
