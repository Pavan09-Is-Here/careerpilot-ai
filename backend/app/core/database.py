from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATABASE_FILE = BACKEND_DIR / "careerpilot.db"
DEFAULT_SQLITE_URL = f"sqlite:///{DATABASE_FILE.as_posix()}"


def resolve_database_url(settings: Settings | None = None) -> str:
    """The configured database URL, defaulting to local SQLite.

    Set CAREERPILOT_DATABASE_URL to a PostgreSQL URL in production.
    """
    settings = settings or Settings()
    return settings.database_url or DEFAULT_SQLITE_URL


DATABASE_URL = resolve_database_url()


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models."""

    pass


def _is_sqlite(url: str) -> bool:
    return make_url(url).get_backend_name() == "sqlite"


def create_configured_engine(url: str) -> Engine:
    """Create an engine with dialect-appropriate options.

    SQLite needs check_same_thread disabled for FastAPI's threadpool
    and requires the foreign-key pragma to enforce constraints;
    PostgreSQL enforces foreign keys natively and needs neither.
    """
    if _is_sqlite(url):
        new_engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(new_engine, "connect")
        def _enable_sqlite_foreign_keys(
            database_connection: object,
            _connection_record: object,
        ) -> None:
            cursor = database_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
            finally:
                cursor.close()

        return new_engine

    # PostgreSQL (and other server databases): pre-ping for resilience
    # against dropped connections behind poolers/load balancers.
    return create_engine(url, pool_pre_ping=True)


engine = create_configured_engine(DATABASE_URL)

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
