"""Data privacy controls (Phase 13): GDPR export and erasure.

Export returns the candidate's own data, sanitized of internal storage
references (no absolute paths, no server-side stored filenames). Erasure
("right to be forgotten") removes all candidate-owned records on an
explicit, confirmed, authenticated request and revokes all sessions.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.application_answer import ApplicationAnswer
from app.models.application_package import ApplicationPackage
from app.models.application_run import ApplicationRun
from app.models.candidate_profile import CandidateProfile
from app.models.certification import Certification
from app.models.cv_version import CVVersion
from app.models.document import Document
from app.models.education import Education
from app.models.experience import Experience
from app.models.job_match import JobMatch
from app.models.project import Project
from app.models.skill import Skill
from app.services.auth import revoke_all_sessions


CANDIDATE_PROFILE_ID = 1

# Internal columns that must never leave the system in an export.
SENSITIVE_COLUMNS = {
    "storage_path",
    "stored_filename",
    "extraction_error",
}


class PrivacyServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def _serialize_value(value: object) -> object:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _row_to_dict(row: object) -> dict[str, object]:
    columns = row.__table__.columns  # type: ignore[attr-defined]
    result: dict[str, object] = {}
    for column in columns:
        if column.name in SENSITIVE_COLUMNS:
            continue
        result[column.name] = _serialize_value(
            getattr(row, column.name)
        )
    return result


def _rows(model: type, database: Session) -> list[dict[str, object]]:
    items = list(
        database.scalars(
            select(model).where(
                model.candidate_profile_id == CANDIDATE_PROFILE_ID
            )
        ).all()
    )
    return [_row_to_dict(item) for item in items]


def export_candidate_data(database: Session) -> dict[str, object]:
    profile = database.get(CandidateProfile, CANDIDATE_PROFILE_ID)
    if profile is None:
        raise PrivacyServiceError(
            "No candidate profile exists to export.",
            status_code=404,
        )

    return {
        "exported_at": datetime.now().astimezone().isoformat(),
        "candidate_profile": _row_to_dict(profile),
        "education": _rows(Education, database),
        "experience": _rows(Experience, database),
        "projects": _rows(Project, database),
        "skills": _rows(Skill, database),
        "certifications": _rows(Certification, database),
        "documents": _rows(Document, database),
        "cv_versions": _rows(CVVersion, database),
        "application_answers": _rows(ApplicationAnswer, database),
        "application_packages": _rows(ApplicationPackage, database),
        "applications": _rows(Application, database),
    }


def _count(model: type, database: Session) -> int:
    return int(
        database.scalar(
            select(func.count())
            .select_from(model)
            .where(
                model.candidate_profile_id == CANDIDATE_PROFILE_ID
            )
        )
        or 0
    )


def delete_candidate_data(
    database: Session,
    *,
    confirm: bool,
) -> dict[str, object]:
    if not confirm:
        raise PrivacyServiceError(
            "Deletion must be explicitly confirmed. This permanently "
            "erases all candidate data and cannot be undone.",
        )

    profile = database.get(CandidateProfile, CANDIDATE_PROFILE_ID)
    if profile is None:
        raise PrivacyServiceError(
            "No candidate profile exists to delete.",
            status_code=404,
        )

    summary = {
        "education": _count(Education, database),
        "experience": _count(Experience, database),
        "projects": _count(Project, database),
        "skills": _count(Skill, database),
        "certifications": _count(Certification, database),
        "documents": _count(Document, database),
        "cv_versions": _count(CVVersion, database),
        "application_answers": _count(ApplicationAnswer, database),
        "application_packages": _count(ApplicationPackage, database),
        "applications": _count(Application, database),
        "job_matches": _count(JobMatch, database),
        "application_runs": _count(ApplicationRun, database),
    }

    where = lambda model: model.candidate_profile_id == CANDIDATE_PROFILE_ID

    # Delete references first, then owned records, in FK-safe order.
    database.execute(delete(ApplicationRun).where(where(ApplicationRun)))
    database.execute(delete(Application).where(where(Application)))
    database.execute(delete(JobMatch).where(where(JobMatch)))
    database.execute(
        delete(ApplicationPackage).where(where(ApplicationPackage))
    )
    database.execute(
        delete(ApplicationAnswer).where(where(ApplicationAnswer))
    )

    # Break the self-referential parent link before deleting CV
    # versions so the RESTRICT constraint cannot block erasure.
    database.execute(
        update(CVVersion)
        .where(where(CVVersion))
        .values(parent_version_id=None)
    )
    database.execute(delete(CVVersion).where(where(CVVersion)))

    database.execute(delete(Document).where(where(Document)))
    database.execute(delete(Certification).where(where(Certification)))
    database.execute(delete(Skill).where(where(Skill)))
    database.execute(delete(Project).where(where(Project)))
    database.execute(delete(Experience).where(where(Experience)))
    database.execute(delete(Education).where(where(Education)))
    database.delete(profile)
    database.commit()

    revoked = revoke_all_sessions(database)

    return {
        "deleted": summary,
        "profile_deleted": True,
        "sessions_revoked": revoked,
    }
