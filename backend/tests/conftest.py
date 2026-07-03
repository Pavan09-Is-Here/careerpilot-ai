from collections.abc import Callable, Generator
from dataclasses import dataclass
from sqlite3 import Connection as SQLiteConnection

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app


DEFAULT_USERNAME = "test.user"
DEFAULT_PASSWORD = "correct-horse-8"
DEFAULT_FULL_NAME = "Test Candidate"
DEFAULT_EMAIL = "candidate@example.com"


@dataclass
class Account:
    """Registered account handle for authenticated test requests."""

    username: str
    token: str
    profile_id: int
    headers: dict[str, str]


@pytest.fixture
def test_engine() -> Generator[Engine, None, None]:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def enable_test_foreign_keys(
        database_connection: SQLiteConnection,
        _connection_record: object,
    ) -> None:
        cursor = database_connection.cursor()

        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    Base.metadata.create_all(bind=test_engine)

    try:
        yield test_engine
    finally:
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session_factory(
    test_engine: Engine,
) -> Callable[[], Session]:
    testing_session_local = sessionmaker(
        bind=test_engine,
        class_=Session,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    return testing_session_local


@pytest.fixture
def db_session(
    db_session_factory: Callable[[], Session],
) -> Generator[Session, None, None]:
    database = db_session_factory()

    try:
        yield database
    finally:
        database.close()


@pytest.fixture
def client(
    db_session_factory: Callable[[], Session],
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        database = db_session_factory()

        try:
            yield database
        finally:
            database.close()

    app.dependency_overrides[get_db] = override_get_db

    test_client = TestClient(app)

    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.clear()


def register_account(
    client: TestClient,
    db_session: Session,
    username: str = DEFAULT_USERNAME,
    password: str = DEFAULT_PASSWORD,
    full_name: str = DEFAULT_FULL_NAME,
    email: str = DEFAULT_EMAIL,
) -> Account:
    """Register an account and return its token + owned profile id.

    Registration also creates the caller's candidate profile. The profile
    id is read back from the database rather than hardcoded.
    """
    from app.models.candidate_profile import CandidateProfile
    from app.models.user import User

    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": password,
            "full_name": full_name,
            "email": email,
        },
    )

    assert response.status_code == 201, response.text
    token = response.json()["token"]

    db_session.expire_all()
    user = (
        db_session.query(User)
        .filter(User.username == username.lower())
        .one()
    )
    profile = (
        db_session.query(CandidateProfile)
        .filter(CandidateProfile.user_id == user.id)
        .one()
    )

    return Account(
        username=username,
        token=token,
        profile_id=profile.id,
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.fixture
def account(
    client: TestClient,
    db_session: Session,
) -> Account:
    """Register a default account and return its auth handle."""
    return register_account(client, db_session)


@pytest.fixture
def auth_client(
    client: TestClient,
    account: Account,
) -> TestClient:
    """A TestClient pre-configured with the default account's token.

    The plain ``client`` fixture stays unauthenticated for auth tests.
    """
    client.headers.update(account.headers)
    return client
