"""Phase 8 — Verified Application Answer Vault tests."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.application_answer import ApplicationAnswer
from app.models.candidate_profile import CandidateProfile
from app.schemas.application_answer import (
    ApplicationAnswerCreate,
    ApplicationAnswerUpdate,
)
from app.services.application_answer import (
    ApplicationAnswerServiceError,
    create_application_answer,
    evaluate_requires_manual_confirmation,
    update_application_answer,
)


def seed_profile(database: Session) -> CandidateProfile:
    profile = CandidateProfile(
        full_name="Test Candidate",
        email="candidate@example.com",
        requires_sponsorship=False,
        willing_to_relocate=False,
        preferred_work_modes=[],
        target_roles=[],
        preferred_locations=[],
        salary_currency="GBP",
        minimum_match_score=50,
        auto_apply_enabled=False,
        facts_verified=True,
    )
    database.add(profile)
    database.commit()
    return profile


def answer_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "category": "availability",
        "question_label": "When can you start?",
        "answer_text": "Available to start immediately.",
        "verified": True,
        "manually_confirmed": False,
        "notes": None,
    }
    payload.update(overrides)
    return payload


# --- Sensitivity detection (deterministic, no external services) ---


def test_sensitive_category_flags_confirmation() -> None:
    assert evaluate_requires_manual_confirmation(
        "work_authorization",
        "Are you authorized to work in the US?",
        "US citizen with unrestricted work authorization.",
    )
    assert evaluate_requires_manual_confirmation(
        "sponsorship",
        "Do you require sponsorship?",
        "Does not require sponsorship.",
    )


def test_sensitive_keyword_flags_confirmation() -> None:
    assert evaluate_requires_manual_confirmation(
        "other",
        "Have you ever been convicted of a felony?",
        "No.",
    )
    assert evaluate_requires_manual_confirmation(
        "other",
        "Voluntary demographic survey",
        "Prefer not to say.",
    )


def test_non_sensitive_answer_not_flagged() -> None:
    assert not evaluate_requires_manual_confirmation(
        "availability",
        "When can you start?",
        "Available to start immediately.",
    )
    assert not evaluate_requires_manual_confirmation(
        "notice_period",
        "What is your notice period?",
        "Two weeks' notice.",
    )


# --- Create ---


def test_create_requires_profile(client: TestClient) -> None:
    response = client.post(
        "/api/application-answers",
        json=answer_payload(),
    )
    assert response.status_code == 400


def test_create_non_sensitive_answer(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)

    response = client.post(
        "/api/application-answers",
        json=answer_payload(),
    )
    assert response.status_code == 201

    body = response.json()
    assert body["category"] == "availability"
    assert body["answer_text"] == "Available to start immediately."
    assert body["verified"] is True
    assert body["requires_manual_confirmation"] is False
    assert body["candidate_profile_id"] == 1
    assert "id" in body


def test_create_sensitive_requires_confirmation_before_verified(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)

    response = client.post(
        "/api/application-answers",
        json=answer_payload(
            category="sponsorship",
            question_label="Do you require visa sponsorship?",
            answer_text="Does not require sponsorship.",
            verified=True,
            manually_confirmed=False,
        ),
    )
    assert response.status_code == 400
    assert "manually confirmed" in response.json()["detail"].lower()


def test_create_sensitive_with_confirmation_succeeds(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)

    response = client.post(
        "/api/application-answers",
        json=answer_payload(
            category="sponsorship",
            question_label="Do you require visa sponsorship?",
            answer_text="Does not require sponsorship.",
            verified=True,
            manually_confirmed=True,
        ),
    )
    assert response.status_code == 201

    body = response.json()
    assert body["requires_manual_confirmation"] is True
    assert body["manually_confirmed"] is True
    assert body["verified"] is True


def test_create_sensitive_unverified_allowed_without_confirmation(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)

    response = client.post(
        "/api/application-answers",
        json=answer_payload(
            category="work_authorization",
            question_label="Work authorization status",
            answer_text="US citizen.",
            verified=False,
            manually_confirmed=False,
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["requires_manual_confirmation"] is True
    assert body["verified"] is False


def test_create_rejects_invalid_category(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)

    response = client.post(
        "/api/application-answers",
        json=answer_payload(category="not_a_category"),
    )
    assert response.status_code == 422


def test_create_rejects_empty_answer(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)

    response = client.post(
        "/api/application-answers",
        json=answer_payload(answer_text="   "),
    )
    assert response.status_code == 422


def test_create_duplicate_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)

    first = client.post(
        "/api/application-answers",
        json=answer_payload(),
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/application-answers",
        json=answer_payload(
            answer_text="Available in two weeks.",
        ),
    )
    assert duplicate.status_code == 409


# --- List and retrieval by question type ---


def test_list_and_filter_by_category(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)

    client.post(
        "/api/application-answers",
        json=answer_payload(),
    )
    client.post(
        "/api/application-answers",
        json=answer_payload(
            category="relocation",
            question_label="Are you willing to relocate?",
            answer_text="Willing to relocate to the Bay Area.",
        ),
    )

    all_answers = client.get("/api/application-answers")
    assert all_answers.status_code == 200
    assert len(all_answers.json()) == 2

    filtered = client.get(
        "/api/application-answers",
        params={"category": "relocation"},
    )
    assert filtered.status_code == 200
    filtered_body = filtered.json()
    assert len(filtered_body) == 1
    assert filtered_body[0]["category"] == "relocation"


def test_get_missing_answer_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)

    response = client.get("/api/application-answers/999")
    assert response.status_code == 404


# --- Update ---


def test_update_recomputes_sensitivity(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)

    created = client.post(
        "/api/application-answers",
        json=answer_payload(),
    ).json()
    answer_id = created["id"]

    # Change to a sensitive category and attempt to verify without
    # confirmation -> rejected.
    blocked = client.put(
        f"/api/application-answers/{answer_id}",
        json=answer_payload(
            category="work_authorization",
            question_label="Work authorization status",
            answer_text="US citizen.",
            verified=True,
            manually_confirmed=False,
        ),
    )
    assert blocked.status_code == 400

    # Confirm and verify -> succeeds and flag persists.
    confirmed = client.put(
        f"/api/application-answers/{answer_id}",
        json=answer_payload(
            category="work_authorization",
            question_label="Work authorization status",
            answer_text="US citizen.",
            verified=True,
            manually_confirmed=True,
        ),
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["requires_manual_confirmation"] is True


def test_update_missing_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)

    response = client.put(
        "/api/application-answers/999",
        json=answer_payload(),
    )
    assert response.status_code == 404


# --- Delete ---


def test_delete_answer(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)

    created = client.post(
        "/api/application-answers",
        json=answer_payload(),
    ).json()
    answer_id = created["id"]

    deleted = client.delete(f"/api/application-answers/{answer_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/api/application-answers/{answer_id}")
    assert missing.status_code == 404

    remaining = client.get("/api/application-answers")
    assert remaining.json() == []


def test_delete_missing_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)

    response = client.delete("/api/application-answers/999")
    assert response.status_code == 404


# --- Service-level guards ---


def test_service_rejects_verified_sensitive_without_confirmation(
    db_session: Session,
) -> None:
    seed_profile(db_session)

    try:
        create_application_answer(
            ApplicationAnswerCreate(
                category="sponsorship",
                question_label="Do you require sponsorship?",
                answer_text="Requires H1-B sponsorship.",
                verified=True,
                manually_confirmed=False,
            ),
            db_session,
        )
    except ApplicationAnswerServiceError as exc:
        assert exc.status_code == 400
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ApplicationAnswerServiceError")


def test_service_update_persists_fields(
    db_session: Session,
) -> None:
    seed_profile(db_session)

    answer = create_application_answer(
        ApplicationAnswerCreate(
            category="company_interest",
            question_label="Why are you interested?",
            answer_text="Interested in the platform team.",
            verified=False,
            manually_confirmed=False,
        ),
        db_session,
    )

    updated = update_application_answer(
        answer.id,
        ApplicationAnswerUpdate(
            category="company_interest",
            question_label="Why are you interested?",
            answer_text="Interested in the ML platform team.",
            verified=True,
            manually_confirmed=False,
        ),
        db_session,
    )

    assert isinstance(updated, ApplicationAnswer)
    assert updated.answer_text == "Interested in the ML platform team."
    assert updated.verified is True
    assert updated.requires_manual_confirmation is False
