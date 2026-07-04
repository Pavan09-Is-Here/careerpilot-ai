"""Tests for the bulk 'verify all' profile action (user-initiated)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes.auth import login_rate_limiter
from app.models.education import Education
from app.models.skill import Skill
from tests.conftest import register_account


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    login_rate_limiter.reset()


def _seed_unverified(database: Session, profile_id: int) -> None:
    database.add(
        Education(
            candidate_profile_id=profile_id,
            institution="Example University",
            degree="BSc Computer Science",
            start_date=__import__("datetime").date(2019, 1, 1),
            is_current=False,
            verified=False,
        )
    )
    database.add(
        Skill(
            candidate_profile_id=profile_id,
            name="Python",
            verified=False,
        )
    )
    database.commit()


def test_verify_all_marks_own_records_verified(
    client: TestClient,
    db_session: Session,
) -> None:
    account = register_account(client, db_session)
    _seed_unverified(db_session, account.profile_id)

    response = client.post(
        "/api/profile/verify-all", headers=account.headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["verified"]["education"] == 1
    assert body["verified"]["skills"] == 1

    db_session.expire_all()
    assert all(
        edu.verified
        for edu in db_session.query(Education).all()
    )
    assert all(
        skill.verified
        for skill in db_session.query(Skill).all()
    )


def test_verify_all_requires_authentication(
    client: TestClient,
) -> None:
    assert client.post("/api/profile/verify-all").status_code == 401


def test_verify_all_does_not_touch_other_users(
    client: TestClient,
    db_session: Session,
) -> None:
    alice = register_account(
        client, db_session, username="alice", email="alice@example.com"
    )
    bob = register_account(
        client, db_session, username="bob", email="bob@example.com"
    )
    _seed_unverified(db_session, alice.profile_id)

    # Bob verifies his (empty) profile; Alice's records stay unverified.
    response = client.post(
        "/api/profile/verify-all", headers=bob.headers
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0

    db_session.expire_all()
    alice_edu = (
        db_session.query(Education)
        .filter(Education.candidate_profile_id == alice.profile_id)
        .all()
    )
    assert alice_edu and all(not e.verified for e in alice_edu)
