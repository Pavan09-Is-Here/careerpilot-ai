"""Verified application answer vault (Phase 8).

Stores reusable, verified answers to recurring job-application
questions (work authorization, sponsorship, availability, salary,
relocation, and so on). The vault never fabricates candidate
information. Sensitive questions -- legal declarations, demographic
or equal-opportunity monitoring, health, criminal history, and
background-check consent -- are flagged and cannot be marked verified
until the candidate has explicitly confirmed them.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.application_answer import ApplicationAnswer
from app.models.candidate_profile import CandidateProfile
from app.schemas.application_answer import (
    ApplicationAnswerCreate,
    ApplicationAnswerUpdate,
)


# Categories that are legal declarations by nature and always require
# explicit manual confirmation before an answer may be verified.
SENSITIVE_CATEGORIES: frozenset[str] = frozenset(
    {
        "work_authorization",
        "sponsorship",
    }
)


# Keyword signals that indicate a sensitive or legally protected topic
# regardless of the chosen category. Matched case-insensitively against
# the question label and answer text.
SENSITIVE_KEYWORDS: tuple[str, ...] = (
    "sponsorship",
    "visa",
    "work authorization",
    "work authorisation",
    "citizenship",
    "immigration",
    "green card",
    "background check",
    "criminal",
    "felony",
    "conviction",
    "arrest",
    "disability",
    "disabled",
    "veteran",
    "gender",
    "race",
    "ethnicity",
    "ethnic",
    "national origin",
    "religion",
    "sexual orientation",
    "marital status",
    "pregnan",
    "health condition",
    "medical condition",
    "date of birth",
    "social security",
    "equal opportunity",
    "eeo",
    "demographic",
    "diversity monitoring",
)


class ApplicationAnswerServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def evaluate_requires_manual_confirmation(
    category: str,
    question_label: str,
    answer_text: str,
) -> bool:
    """Return True when an answer touches a sensitive/legal topic.

    Sensitivity is derived deterministically from the category and from
    keyword signals in the question and answer. No external services,
    inference, or candidate-fact mutation are involved.
    """

    if category in SENSITIVE_CATEGORIES:
        return True

    haystack = f"{question_label}\n{answer_text}".lower()

    return any(keyword in haystack for keyword in SENSITIVE_KEYWORDS)


def guard_verified_state(
    *,
    verified: bool,
    manually_confirmed: bool,
    requires_manual_confirmation: bool,
) -> None:
    """Enforce that sensitive answers are confirmed before verification.

    A sensitive answer must not be promoted to verified until the
    candidate has explicitly confirmed it. This keeps legal and
    sensitive declarations under deliberate human control.
    """

    if (
        verified
        and requires_manual_confirmation
        and not manually_confirmed
    ):
        raise ApplicationAnswerServiceError(
            "This answer covers a sensitive or legal question and must "
            "be manually confirmed before it can be marked verified.",
        )


def ensure_candidate_profile(
    database: Session,
    candidate_profile_id: int,
) -> None:
    profile = database.get(CandidateProfile, candidate_profile_id)

    if profile is None:
        raise ApplicationAnswerServiceError(
            "Create the candidate profile before adding "
            "application answers.",
        )


def get_answer_or_404(
    answer_id: int,
    database: Session,
    candidate_profile_id: int,
) -> ApplicationAnswer:
    answer = database.get(ApplicationAnswer, answer_id)

    if (
        answer is None
        or answer.candidate_profile_id != candidate_profile_id
    ):
        raise ApplicationAnswerServiceError(
            "Application answer was not found.",
            status_code=404,
        )

    return answer


def create_application_answer(
    data: ApplicationAnswerCreate,
    database: Session,
    candidate_profile_id: int,
) -> ApplicationAnswer:
    ensure_candidate_profile(database, candidate_profile_id)

    requires_confirmation = evaluate_requires_manual_confirmation(
        data.category,
        data.question_label,
        data.answer_text,
    )
    guard_verified_state(
        verified=data.verified,
        manually_confirmed=data.manually_confirmed,
        requires_manual_confirmation=requires_confirmation,
    )

    now = current_utc_time()
    answer = ApplicationAnswer(
        candidate_profile_id=candidate_profile_id,
        category=data.category,
        question_label=data.question_label,
        answer_text=data.answer_text,
        verified=data.verified,
        manually_confirmed=data.manually_confirmed,
        requires_manual_confirmation=requires_confirmation,
        notes=data.notes,
        created_at=now,
        updated_at=now,
    )
    database.add(answer)

    try:
        database.commit()
        database.refresh(answer)
    except IntegrityError as exc:
        database.rollback()
        raise ApplicationAnswerServiceError(
            "An answer for this category and question already exists.",
            status_code=409,
        ) from exc

    return answer


def update_application_answer(
    answer_id: int,
    data: ApplicationAnswerUpdate,
    database: Session,
    candidate_profile_id: int,
) -> ApplicationAnswer:
    answer = get_answer_or_404(answer_id, database, candidate_profile_id)

    requires_confirmation = evaluate_requires_manual_confirmation(
        data.category,
        data.question_label,
        data.answer_text,
    )
    guard_verified_state(
        verified=data.verified,
        manually_confirmed=data.manually_confirmed,
        requires_manual_confirmation=requires_confirmation,
    )

    answer.category = data.category
    answer.question_label = data.question_label
    answer.answer_text = data.answer_text
    answer.verified = data.verified
    answer.manually_confirmed = data.manually_confirmed
    answer.requires_manual_confirmation = requires_confirmation
    answer.notes = data.notes
    answer.updated_at = current_utc_time()

    try:
        database.commit()
        database.refresh(answer)
    except IntegrityError as exc:
        database.rollback()
        raise ApplicationAnswerServiceError(
            "An answer for this category and question already exists.",
            status_code=409,
        ) from exc

    return answer


def list_application_answers(
    database: Session,
    candidate_profile_id: int,
    *,
    category: str | None = None,
) -> list[ApplicationAnswer]:
    statement = select(ApplicationAnswer).where(
        ApplicationAnswer.candidate_profile_id == candidate_profile_id
    )

    if category is not None:
        statement = statement.where(
            ApplicationAnswer.category == category
        )

    statement = statement.order_by(
        ApplicationAnswer.category.asc(),
        ApplicationAnswer.updated_at.desc(),
        ApplicationAnswer.id.desc(),
    )

    return list(database.scalars(statement).all())


def delete_application_answer(
    answer_id: int,
    database: Session,
    candidate_profile_id: int,
) -> None:
    answer = get_answer_or_404(answer_id, database, candidate_profile_id)
    database.delete(answer)
    database.commit()
