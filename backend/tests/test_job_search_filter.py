"""Job discovery title search filter."""

from hashlib import sha256

from sqlalchemy.orm import Session

from app.schemas.job import JobSourceCreate, NormalizedJobCreate
from app.services.job import (
    create_job_source,
    create_normalized_job,
    list_normalized_jobs,
)


def _make_job(database: Session, source_id: int, title: str, key: str) -> None:
    create_normalized_job(
        NormalizedJobCreate(
            job_source_id=source_id,
            source_job_id=key,
            source_url=f"https://jobs.example.com/{key}",
            employer_name="Example",
            title=title,
            content_hash=sha256(key.encode()).hexdigest(),
            normalization_version="test",
        ),
        database,
    )


def test_search_filters_by_title(db_session: Session) -> None:
    source = create_job_source(
        JobSourceCreate(
            source_key="src-1",
            display_name="Example",
            source_category="provider_api",
        ),
        db_session,
    )
    _make_job(db_session, source.id, "Software Engineering Intern", "a")
    _make_job(db_session, source.id, "Senior Platform Engineer", "b")
    _make_job(db_session, source.id, "Data Scientist", "c")

    # Case-insensitive title match.
    result = list_normalized_jobs(db_session, search="intern")
    titles = [item["title"] for item in result["items"]]
    assert titles == ["Software Engineering Intern"]

    # A broader term matches multiple.
    engineer = list_normalized_jobs(db_session, search="engineer")
    assert result["total"] == 1
    assert engineer["total"] == 2

    # Empty/whitespace search returns everything.
    everything = list_normalized_jobs(db_session, search="   ")
    assert everything["total"] == 3
