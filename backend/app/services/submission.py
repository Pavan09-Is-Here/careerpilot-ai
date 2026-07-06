"""Source-permitted application submission adapters (Phase 16).

An adapter submits a prepared, candidate-confirmed application through
a channel the job source explicitly permits (for example a provider's
official application API configured with valid credentials). Adapters
NEVER drive a browser against a site's application form, never bypass
CAPTCHA, bot detection, rate limits, or terms of service, and never
run without the candidate's explicit recorded consent for that job.

Most sources do not offer a candidate-side submission API. For those,
``attempt_submission`` reports ``unsupported`` and the application run
pauses at the ``submission_confirmation`` gate exactly like the
manual-assist flow — the candidate submits themselves and records the
confirmation number. Nothing is fabricated: adapters transmit only the
verified fill plan and package contents.

The registry is intentionally simple: tests (and future providers)
register a driver per ``JobSource.provider_type``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from sqlalchemy.orm import Session

from app.models.application_package import ApplicationPackage
from app.models.job import JobSource, NormalizedJob


SUBMISSION_STATUSES = ("submitted", "unsupported", "failed")


@dataclass(frozen=True)
class SubmissionResult:
    """Outcome of one submission attempt.

    ``status`` is one of ``SUBMISSION_STATUSES``. ``method`` names the
    adapter used (recorded on the run as ``submission_method``).
    ``detail`` is a safe, human-readable explanation — it must never
    contain secrets, absolute paths, or fabricated claims.
    """

    status: str
    method: str
    confirmation_number: str | None = None
    detail: str = ""


class SubmissionDriver(Protocol):
    def __call__(
        self,
        job: NormalizedJob,
        package: ApplicationPackage,
        fill_plan: list[dict[str, object]],
        database: Session,
    ) -> SubmissionResult: ...


# provider_type -> driver. Empty by default: no currently supported
# source offers a candidate-side submission API. Tests and future
# provider integrations register drivers here.
_DRIVERS: dict[str, SubmissionDriver] = {}


def register_submission_driver(
    provider_type: str,
    driver: SubmissionDriver,
) -> Callable[[], None]:
    """Register a driver for a provider type.

    Returns an unregister callback so tests can clean up.
    """
    _DRIVERS[provider_type] = driver

    def unregister() -> None:
        if _DRIVERS.get(provider_type) is driver:
            del _DRIVERS[provider_type]

    return unregister


def driver_for_source(source: JobSource | None) -> SubmissionDriver | None:
    if source is None:
        return None
    return _DRIVERS.get(source.provider_type)


def attempt_submission(
    job: NormalizedJob,
    package: ApplicationPackage,
    fill_plan: list[dict[str, object]],
    database: Session,
) -> SubmissionResult:
    """Attempt to submit through a source-permitted channel.

    Returns ``unsupported`` when the job's source has no registered
    driver; the caller must fall back to candidate-performed
    submission. Driver failures are contained and reported as
    ``failed`` — never raised — so a submission problem can never
    corrupt the run state.
    """
    source = database.get(JobSource, job.job_source_id)
    driver = driver_for_source(source)
    if driver is None:
        return SubmissionResult(
            status="unsupported",
            method="none",
            detail=(
                "This job's source does not offer a permitted "
                "automatic submission channel. Submit the prepared "
                "application yourself, then record the confirmation "
                "number."
            ),
        )

    try:
        result = driver(job, package, fill_plan, database)
    except Exception:  # noqa: BLE001 - contained, reported as failed
        return SubmissionResult(
            status="failed",
            method="unknown",
            detail=(
                "The submission channel reported an error. No "
                "submission was recorded; submit manually or retry."
            ),
        )

    if result.status not in SUBMISSION_STATUSES:
        return SubmissionResult(
            status="failed",
            method=result.method,
            detail="The submission channel returned an invalid status.",
        )
    return result
