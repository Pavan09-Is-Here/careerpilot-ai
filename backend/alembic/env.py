from logging.config import fileConfig
from pathlib import Path
import sys

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.models.candidate_profile import CandidateProfile  # noqa: E402,F401

# When a database URL is configured in the environment
# (CAREERPILOT_DATABASE_URL, e.g. a PostgreSQL URL in production),
# use it. Otherwise keep whatever alembic.ini or the caller set (the
# local SQLite database, or an explicit URL passed by tests).
_configured_database_url = Settings().database_url
if _configured_database_url:
    config.set_main_option("sqlalchemy.url", _configured_database_url)
from app.models.certification import Certification  # noqa: E402,F401
from app.models.cv_section import CVSection  # noqa: E402,F401
from app.models.cv_version import CVVersion  # noqa: E402,F401
from app.models.cv_version_artifact import CVVersionArtifact  # noqa: E402,F401
from app.models.document import Document  # noqa: E402,F401
from app.models.education import Education  # noqa: E402,F401
from app.models.experience import Experience  # noqa: E402,F401
from app.models.fact_comparison import FactComparisonFinding  # noqa: E402,F401
from app.models.fact_comparison import FactComparisonRun  # noqa: E402,F401
from app.models.ingestion import IngestionRun  # noqa: E402,F401
from app.models.ingestion import SourceSnapshot  # noqa: E402,F401
from app.models.job import JobCompensation  # noqa: E402,F401
from app.models.job import JobDuplicate  # noqa: E402,F401
from app.models.job import JobLocation  # noqa: E402,F401
from app.models.job import JobSkillRequirement  # noqa: E402,F401
from app.models.job import JobSource  # noqa: E402,F401
from app.models.job import NormalizedJob  # noqa: E402,F401
from app.models.job_match import JobMatch  # noqa: E402,F401
from app.models.job_tailored_cv import JobTailoredCV  # noqa: E402,F401
from app.models.project import Project  # noqa: E402,F401
from app.models.saved_job import SavedJob  # noqa: E402,F401
from app.models.skill import Skill  # noqa: E402,F401

# target_metadata should include all model metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        from app.core.database import DATABASE_URL

        url = DATABASE_URL

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    if not connectable.url:
        from app.core.database import DATABASE_URL

        connectable = engine_from_config(
            {"sqlalchemy.url": DATABASE_URL},
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
