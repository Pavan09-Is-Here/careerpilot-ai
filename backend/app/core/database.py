from collections.abc import Generator
from pathlib import Path
from sqlite3 import Connection as SQLiteConnection

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATABASE_FILE = BACKEND_DIR / "careerpilot.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE.as_posix()}"


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models."""

    pass


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(
    database_connection: SQLiteConnection,
    _connection_record: object,
) -> None:
    """Ensure SQLite enforces declared foreign key constraints."""

    cursor = database_connection.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Create one database session for each API request."""

    database = SessionLocal()

    try:
        yield database
    finally:
        database.close()
