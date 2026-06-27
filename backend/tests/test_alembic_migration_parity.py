from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects import sqlite

from app.core.database import Base
from app.models.candidate_profile import CandidateProfile  # noqa: F401
from app.models.certification import Certification  # noqa: F401
from app.models.cv_section import CVSection  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.education import Education  # noqa: F401
from app.models.experience import Experience  # noqa: F401
from app.models.fact_comparison import FactComparisonFinding  # noqa: F401
from app.models.fact_comparison import FactComparisonRun  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.skill import Skill  # noqa: F401


EXPECTED_APPLICATION_TABLES = {
    "candidate_profiles",
    "education",
    "work_experiences",
    "projects",
    "skills",
    "certifications",
    "documents",
    "cv_sections",
    "fact_comparison_runs",
    "fact_comparison_findings",
}

EXPECTED_FOREIGN_KEYS = {
    "education": {
        ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
    },
    "work_experiences": {
        ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
    },
    "projects": {
        ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
    },
    "skills": {
        ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
    },
    "certifications": {
        ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
    },
    "documents": {
        ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
    },
    "cv_sections": {
        ("document_id", "documents", "id", "CASCADE"),
    },
    "fact_comparison_runs": {
        ("document_id", "documents", "id", "CASCADE"),
    },
    "fact_comparison_findings": {
        (
            "comparison_run_id",
            "fact_comparison_runs",
            "id",
            "CASCADE",
        ),
        ("document_section_id", "cv_sections", "id", "SET NULL"),
    },
}

EXPECTED_INDEXES = {
    "education": {"ix_education_candidate_profile_id"},
    "work_experiences": {"ix_work_experiences_candidate_profile_id"},
    "projects": {"ix_projects_candidate_profile_id"},
    "skills": {"ix_skills_candidate_profile_id", "ix_skills_name"},
    "certifications": {"ix_certifications_candidate_profile_id"},
    "documents": {"ix_documents_candidate_profile_id"},
    "cv_sections": {"ix_cv_sections_document_id"},
    "fact_comparison_runs": {
        "ix_fact_comparison_runs_document_id",
        "ix_fact_comparison_runs_is_latest_successful",
        "ix_fact_comparison_runs_status",
    },
    "fact_comparison_findings": {
        "ix_fact_comparison_findings_comparison_run_id",
        "ix_fact_comparison_findings_document_section_id",
        "ix_fact_comparison_findings_entity_type",
        "ix_fact_comparison_findings_finding_type",
    },
}


def assert_outside_repository(path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]

    try:
        path.resolve().relative_to(repository_root)
    except ValueError:
        return

    raise AssertionError(
        f"Migration parity database must be outside the repository: {path}"
    )


def sqlite_type(column_type: object) -> str:
    return column_type.compile(dialect=sqlite.dialect())


def test_alembic_head_matches_sqlalchemy_metadata(
    tmp_path: Path,
) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    migration_db = tmp_path / "alembic-metadata-parity.db"
    assert_outside_repository(migration_db)

    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{migration_db}")
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["e5f6a7b8c9d0"]

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{migration_db}")

    try:
        inspector = inspect(engine)
        actual_tables = set(inspector.get_table_names())
        metadata_tables = set(Base.metadata.tables)

        assert EXPECTED_APPLICATION_TABLES.issubset(actual_tables)
        assert metadata_tables == EXPECTED_APPLICATION_TABLES
        assert metadata_tables.issubset(actual_tables)

        for table_name in sorted(metadata_tables):
            metadata_table = Base.metadata.tables[table_name]
            actual_columns = {
                column["name"]: column
                for column in inspector.get_columns(table_name)
            }

            assert set(actual_columns) == set(metadata_table.columns.keys())

            for column in metadata_table.columns:
                reflected_column = actual_columns[column.name]
                assert reflected_column["nullable"] == column.nullable
                assert sqlite_type(reflected_column["type"]) == sqlite_type(
                    column.type
                )

            primary_key = inspector.get_pk_constraint(table_name)
            assert set(primary_key["constrained_columns"]) == {
                column.name
                for column in metadata_table.primary_key.columns
            }

        for table_name, expected_foreign_keys in EXPECTED_FOREIGN_KEYS.items():
            actual_foreign_keys = {
                (
                    foreign_key["constrained_columns"][0],
                    foreign_key["referred_table"],
                    foreign_key["referred_columns"][0],
                    foreign_key.get("options", {}).get("ondelete"),
                )
                for foreign_key in inspector.get_foreign_keys(table_name)
            }
            assert expected_foreign_keys.issubset(actual_foreign_keys)

        for table_name, expected_indexes in EXPECTED_INDEXES.items():
            actual_indexes = {
                index["name"]
                for index in inspector.get_indexes(table_name)
            }
            assert expected_indexes.issubset(actual_indexes)
    finally:
        engine.dispose()
