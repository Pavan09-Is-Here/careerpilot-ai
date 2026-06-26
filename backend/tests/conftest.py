from collections.abc import Callable, Generator
from sqlite3 import Connection as SQLiteConnection

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app


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
