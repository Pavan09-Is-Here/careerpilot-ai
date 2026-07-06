from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects import sqlite

from app.core.database import Base
from app.models.application import Application  # noqa: F401
from app.models.application_answer import ApplicationAnswer  # noqa: F401
from app.models.application_package import ApplicationPackage  # noqa: F401
from app.models.application_run import ApplicationRun  # noqa: F401
from app.models.auth import AuthSession  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.candidate_profile import CandidateProfile  # noqa: F401
from app.models.certification import Certification  # noqa: F401
from app.models.cv_section import CVSection  # noqa: F401
from app.models.cv_version import CVVersion  # noqa: F401
from app.models.cv_version_artifact import CVVersionArtifact  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.education import Education  # noqa: F401
from app.models.experience import Experience  # noqa: F401
from app.models.fact_comparison import FactComparisonFinding  # noqa: F401
from app.models.fact_comparison import FactComparisonRun  # noqa: F401
from app.models.ingestion import IngestionRun  # noqa: F401
from app.models.ingestion import SourceSnapshot  # noqa: F401
from app.models.job import JobCompensation  # noqa: F401
from app.models.job import JobDuplicate  # noqa: F401
from app.models.job import JobLocation  # noqa: F401
from app.models.job import JobSkillRequirement  # noqa: F401
from app.models.job import JobSource  # noqa: F401
from app.models.job import NormalizedJob  # noqa: F401
from app.models.job_match import JobMatch  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.job_tailored_cv import JobTailoredCV  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.saved_job import SavedJob  # noqa: F401
from app.models.skill import Skill  # noqa: F401
from app.models.worker import AuditLogEntry  # noqa: F401
from app.models.worker import WorkerRun  # noqa: F401


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
    "cv_versions",
    "cv_version_artifacts",
    "job_sources",
    "normalized_jobs",
    "job_locations",
    "job_compensations",
    "job_skill_requirements",
    "ingestion_runs",
    "source_snapshots",
    "job_duplicates",
    "saved_jobs",
    "job_matches",
    "job_tailored_cvs",
    "application_answers",
    "application_packages",
    "application_runs",
    "applications",
    "worker_runs",
    "audit_log_entries",
    "users",
    "auth_sessions",
    "notifications",
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
    "cv_versions": {
        ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
        ("source_document_id", "documents", "id", "SET NULL"),
        ("parent_version_id", "cv_versions", "id", "RESTRICT"),
    },
    "cv_version_artifacts": {
        ("cv_version_id", "cv_versions", "id", "CASCADE"),
    },
    "normalized_jobs": {
        ("job_source_id", "job_sources", "id", "RESTRICT"),
    },
    "job_locations": {
        ("job_id", "normalized_jobs", "id", "CASCADE"),
    },
    "job_compensations": {
        ("job_id", "normalized_jobs", "id", "CASCADE"),
    },
    "job_skill_requirements": {
        ("job_id", "normalized_jobs", "id", "CASCADE"),
    },
    "ingestion_runs": {
        ("job_source_id", "job_sources", "id", "RESTRICT"),
    },
    "source_snapshots": {
        ("ingestion_run_id", "ingestion_runs", "id", "CASCADE"),
        ("job_source_id", "job_sources", "id", "RESTRICT"),
    },
    "job_duplicates": {
        ("job_id", "normalized_jobs", "id", "CASCADE"),
        ("duplicate_of_job_id", "normalized_jobs", "id", "CASCADE"),
    },
    "saved_jobs": {
        ("job_id", "normalized_jobs", "id", "RESTRICT"),
        ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
    },
    "job_matches": {
        ("job_id", "normalized_jobs", "id", "CASCADE"),
        (
            "candidate_profile_id",
            "candidate_profiles",
            "id",
            "CASCADE",
        ),
    },
    "job_tailored_cvs": {
        ("job_id", "normalized_jobs", "id", "RESTRICT"),
        ("cv_version_id", "cv_versions", "id", "CASCADE"),
        ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
    },
    "application_answers": {
        ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
    },
    "application_packages": {
        ("job_id", "normalized_jobs", "id", "CASCADE"),
        ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
    },
    "application_runs": {
        ("job_id", "normalized_jobs", "id", "CASCADE"),
        ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
        (
            "application_package_id",
            "application_packages",
            "id",
            "SET NULL",
        ),
    },
    "applications": {
        ("job_id", "normalized_jobs", "id", "CASCADE"),
        ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
        ("cv_id", "cv_versions", "id", "SET NULL"),
    },
    "audit_log_entries": {
        ("worker_run_id", "worker_runs", "id", "CASCADE"),
    },
    "notifications": {
        ("related_job_id", "normalized_jobs", "id", "SET NULL"),
        ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
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
    "cv_versions": {
        "ix_cv_versions_candidate_profile_id",
        "ix_cv_versions_source_document_id",
        "ix_cv_versions_parent_version_id",
        "ix_cv_versions_version_type",
        "ix_cv_versions_status",
        "ix_cv_versions_is_primary",
        "ix_cv_versions_candidate_type",
        "uq_cv_versions_generation_key",
        "uq_cv_versions_primary_per_type",
    },
    "cv_version_artifacts": {
        "ix_cv_version_artifacts_cv_version_id",
        "ix_cv_version_artifacts_artifact_type",
    },
    "job_sources": {
        "ix_job_sources_display_name",
        "ix_job_sources_source_category",
        "ix_job_sources_access_mode",
        "ix_job_sources_enabled",
        "ix_job_sources_allowlisted",
        "ix_job_sources_server_fetch_allowed",
    },
    "normalized_jobs": {
        "ix_normalized_jobs_job_source_id",
        "ix_normalized_jobs_lifecycle_status",
        "ix_normalized_jobs_employer_name",
        "ix_normalized_jobs_employment_type",
        "ix_normalized_jobs_remote_mode",
        "ix_normalized_jobs_source_lifecycle",
        "ix_normalized_jobs_last_seen",
    },
    "job_locations": {
        "ix_job_locations_job_id",
        "ix_job_locations_job_order",
    },
    "job_compensations": {
        "ix_job_compensations_job_id",
        "ix_job_compensations_job_order",
    },
    "job_skill_requirements": {
        "ix_job_skill_requirements_job_id",
        "ix_job_skill_requirements_job_order",
        "ix_job_skill_requirements_requirement_type",
        "ix_job_skill_requirements_normalized_skill_key",
    },
    "ingestion_runs": {
        "ix_ingestion_runs_job_source_id",
        "ix_ingestion_runs_run_status",
        "ix_ingestion_runs_source_created",
    },
    "source_snapshots": {
        "ix_source_snapshots_ingestion_run_id",
        "ix_source_snapshots_job_source_id",
        "ix_source_snapshots_content_hash",
        "ix_source_snapshots_expires_at",
        "ix_source_snapshots_run_fetched",
    },
    "job_duplicates": {
        "ix_job_duplicates_job_id",
        "ix_job_duplicates_duplicate_of_job_id",
    },
    "saved_jobs": {
        "ix_saved_jobs_job_id",
        "ix_saved_jobs_review_status",
        "ix_saved_jobs_candidate_profile_id",
    },
    "job_matches": {
        "ix_job_matches_job_id",
        "ix_job_matches_candidate_profile_id",
        "ix_job_matches_eligibility_status",
    },
    "job_tailored_cvs": {
        "ix_job_tailored_cvs_job_id",
        "ix_job_tailored_cvs_cv_version_id",
        "ix_job_tailored_cvs_candidate_profile_id",
    },
    "application_answers": {
        "ix_application_answers_candidate_profile_id",
        "ix_application_answers_category",
        "ix_application_answers_candidate_category",
    },
    "application_packages": {
        "ix_application_packages_job_id",
        "ix_application_packages_candidate_profile_id",
        "ix_application_packages_readiness_status",
    },
    "application_runs": {
        "ix_application_runs_job_id",
        "ix_application_runs_candidate_profile_id",
        "ix_application_runs_application_package_id",
        "ix_application_runs_status",
    },
    "applications": {
        "ix_applications_job_id",
        "ix_applications_candidate_profile_id",
        "ix_applications_cv_id",
        "ix_applications_status",
    },
    "worker_runs": {
        "ix_worker_runs_worker_name",
        "ix_worker_runs_status",
        "ix_worker_runs_run_date",
    },
    "audit_log_entries": {
        "ix_audit_log_entries_worker_run_id",
        "ix_audit_log_entries_worker_name",
        "ix_audit_log_entries_level",
        "ix_audit_log_entries_created_at",
    },
    "auth_sessions": {
        "ix_auth_sessions_token_hash",
        "ix_auth_sessions_expires_at",
    },
    "notifications": {
        "ix_notifications_category",
        "ix_notifications_status",
        "ix_notifications_related_job_id",
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

    assert script.get_heads() == ["a5b6c7d8e9f0"]

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
