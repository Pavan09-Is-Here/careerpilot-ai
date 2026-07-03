from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path
import re
import shutil
import subprocess
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.certification import Certification
from app.models.cv_version import CVVersion
from app.models.cv_version_artifact import CVVersionArtifact
from app.models.document import Document
from app.models.education import Education
from app.models.experience import Experience
from app.models.project import Project
from app.models.skill import Skill
from app.services import cv_version as cv_version_service
from app.services.document_extraction import (
    extract_docx_text,
    extract_pdf_text,
)
from app.services.document_storage import (
    validate_docx_file,
    validate_pdf_file,
)
from app.services.generated_cv_storage import resolve_generated_artifact_path
from app.services.verified_master_cv import (
    PDF_CJK_FONT_PACKAGE,
    PDF_CJK_FONT_RESOURCE,
    PDF_LATIN_FONT_PACKAGE,
    PDF_LATIN_FONT_RESOURCE,
    cjk_font_codepoints,
    latin_font_codepoints,
    packaged_font_path,
    pdf_font_for_character,
)
from tests.conftest import Account


PHASE36_HEAD = "f6a7b8c9d0e1"
PHASE37_HEAD = "a7b8c9d0e1f2"
CURRENT_HEAD = "d2e3f4a5b6c7"
UNICODE_SAMPLE = "José Núñez – Łukasz Żółć 李雷"
UNICODE_DETAIL = (
    f"{UNICODE_SAMPLE} • Candidate’s résumé – café naïve"
)
UNSUPPORTED_UNICODE = "Unsupported emoji 😀"


@pytest.fixture(autouse=True)
def reset_auth_rate_limiter() -> None:
    from app.api.routes.auth import login_rate_limiter

    login_rate_limiter.reset()
    yield
    login_rate_limiter.reset()


@pytest.fixture(autouse=True)
def clear_phase37_rows_after_test(db_session: Session) -> None:
    yield
    db_session.rollback()
    db_session.execute(text("PRAGMA foreign_keys=OFF"))
    for table_name in (
        "cv_version_artifacts",
        "cv_versions",
        "documents",
        "work_experiences",
        "education",
        "projects",
        "skills",
        "certifications",
        "candidate_profiles",
    ):
        db_session.execute(text(f"DELETE FROM {table_name}"))
    db_session.commit()
    db_session.execute(text("PRAGMA foreign_keys=ON"))


def configure_generated_storage(
    monkeypatch,
    tmp_path: Path,
) -> Path:
    storage_dir = tmp_path / "generated-cvs"
    monkeypatch.setenv(
        "CAREERPILOT_GENERATED_CV_STORAGE_DIR",
        str(storage_dir),
    )
    monkeypatch.setenv(
        "CAREERPILOT_MAX_GENERATED_CV_FILE_SIZE_BYTES",
        str(10 * 1024 * 1024),
    )
    return storage_dir


def make_profile(
    database: Session,
    account: Account,
    *,
    facts_verified: bool = True,
    full_name: str = "Pavan Test",
    professional_title: str = "Senior Backend Engineer",
    summary: str | None = (
        "Backend engineer focused on reliable APIs and data integrity."
    ),
) -> CandidateProfile:
    """Mutate the authenticated account's own profile into the test state.

    Registration already created the caller's profile, so we fetch and
    update it instead of inserting a second candidate profile.
    """
    profile = database.get(CandidateProfile, account.profile_id)
    assert profile is not None
    profile.full_name = full_name
    profile.email = "pavan@example.com"
    profile.phone = "+44 20 0000 0000"
    profile.location = "London"
    profile.professional_title = professional_title
    profile.professional_summary = summary
    profile.linkedin_url = "https://linkedin.example/pavan"
    profile.github_url = "https://github.example/pavan"
    profile.portfolio_url = "https://portfolio.example/pavan"
    profile.work_authorization = "Do not include"
    profile.requires_sponsorship = False
    profile.willing_to_relocate = True
    profile.preferred_work_modes = ["Remote"]
    profile.target_roles = ["Backend Engineer"]
    profile.preferred_locations = ["London"]
    profile.minimum_salary = 120000
    profile.salary_currency = "GBP"
    profile.minimum_match_score = 85
    profile.auto_apply_enabled = False
    profile.facts_verified = facts_verified
    database.commit()
    database.refresh(profile)
    return profile


def make_document(database: Session) -> Document:
    token = uuid4().hex
    document = Document(
        candidate_profile_id=1,
        original_filename="source-cv.pdf",
        stored_filename=f"{token}.pdf",
        file_extension=".pdf",
        media_type="application/pdf",
        size_bytes=42,
        sha256_hash=sha256(token.encode()).hexdigest(),
        document_type="original_cv",
        upload_status="validated",
        is_primary=False,
        extraction_status="completed",
        extracted_text="Uploaded CV text must not be copied.",
        extraction_error=None,
        extracted_at=datetime.now(timezone.utc),
        page_count=1,
        extracted_character_count=35,
        section_detection_status="completed",
        section_detection_error=None,
        section_detected_at=datetime.now(timezone.utc),
        section_count=0,
        section_detection_method="test",
    )
    database.add(document)
    database.commit()
    database.refresh(document)
    return document


def make_version(
    database: Session,
    *,
    version_type: str,
    status: str = "ready",
    parent_version_id: int | None = None,
    source_document_id: int | None = None,
) -> CVVersion:
    now = datetime.now(timezone.utc)
    version = CVVersion(
        candidate_profile_id=1,
        source_document_id=source_document_id,
        parent_version_id=parent_version_id,
        version_type=version_type,
        status=status,
        display_name=f"{version_type} {uuid4().hex[:8]}",
        description=None,
        job_reference=None,
        is_primary=False,
        storage_path=None,
        mime_type=None,
        file_size=None,
        sha256=None,
        generation_key=None,
        generation_version=None,
        source_summary=None,
        generated_at=None,
        created_at=now,
        updated_at=now,
        archived_at=now if status == "archived" else None,
    )
    database.add(version)
    database.commit()
    database.refresh(version)
    return version


def make_parent_chain(database: Session) -> CVVersion:
    document = make_document(database)
    original = make_version(
        database,
        version_type="original",
        source_document_id=document.id,
    )
    return make_version(
        database,
        version_type="parsed",
        parent_version_id=original.id,
    )


def add_verified_facts(
    database: Session,
    *,
    long_cv: bool = False,
    unicode_suffix: str | None = None,
) -> None:
    suffix = f" {unicode_suffix}" if unicode_suffix else ""

    database.add_all(
        [
            Experience(
                candidate_profile_id=1,
                company="Verified Labs",
                job_title="Senior Backend Engineer",
                employment_type="Full-time",
                location="London",
                start_date=date(2022, 1, 1),
                end_date=None,
                is_current=True,
                description="Maintained the hiring platform API.",
                responsibilities=[
                    "Built deterministic services for candidate records.",
                    (
                        "Protected 2024 audit evidence without changing "
                        f"facts.{suffix}"
                    ),
                ],
                achievements=[
                    "Reduced reconciliation time by 30%.",
                    "Duplicate bullet",
                    "Duplicate bullet",
                ],
                technologies=["Python", "FastAPI"],
                verified=True,
            ),
            Experience(
                candidate_profile_id=1,
                company="Older Co",
                job_title="Software Engineer",
                employment_type=None,
                location="Bristol",
                start_date=date(2019, 5, 1),
                end_date=date(2021, 12, 1),
                is_current=False,
                description=None,
                responsibilities=["Supported legacy data services."],
                achievements=[],
                technologies=["SQL"],
                verified=True,
            ),
            Experience(
                candidate_profile_id=1,
                company="Unverified Employer",
                job_title="Principal Inventor",
                employment_type=None,
                location=None,
                start_date=date(2024, 1, 1),
                end_date=None,
                is_current=True,
                description="This must never appear.",
                responsibilities=["Invented unsupported work."],
                achievements=["Invented unsupported achievement."],
                technologies=["ImaginaryDB"],
                verified=False,
            ),
            Education(
                candidate_profile_id=1,
                institution="Verified University",
                degree="MSc",
                field_of_study="Computer Science",
                start_date=date(2017, 9, 1),
                end_date=date(2018, 9, 1),
                grade="Distinction",
                location="Bath",
                description="Studied distributed systems.",
                is_current=False,
                verified=True,
            ),
            Project(
                candidate_profile_id=1,
                name="Truthful CV Builder",
                role="Lead Developer",
                project_type="Personal",
                description="Generated CVs only from verified facts.",
                start_date=date(2024, 2, 1),
                end_date=None,
                is_current=True,
                project_url="https://projects.example/truthful-cv",
                github_url="https://github.example/truthful-cv",
                technologies=["Python", "SQLAlchemy"],
                features=["Created DOCX and PDF artifacts."],
                achievements=["Kept unverified claims out of output."],
                verified=True,
            ),
            Project(
                candidate_profile_id=1,
                name="Unverified Moonshot",
                role="Inventor",
                project_type="Secret",
                description="Unverified project content.",
                start_date=None,
                end_date=None,
                is_current=False,
                project_url=None,
                github_url=None,
                technologies=["UnverifiedTech"],
                features=["Unsupported feature"],
                achievements=["Unsupported achievement"],
                verified=False,
            ),
            Skill(
                candidate_profile_id=1,
                name="Python",
                category="Programming",
                proficiency="Advanced",
                years_experience=12.0,
                evidence="Verified records",
                is_primary=True,
                verified=True,
            ),
            Skill(
                candidate_profile_id=1,
                name="python",
                category="Programming",
                proficiency="Advanced",
                years_experience=99.0,
                evidence="Duplicate casing",
                is_primary=False,
                verified=True,
            ),
            Skill(
                candidate_profile_id=1,
                name="Unverified Skill",
                category="Magic",
                proficiency="Expert",
                years_experience=99.0,
                evidence=None,
                is_primary=False,
                verified=False,
            ),
            Certification(
                candidate_profile_id=1,
                name="Verified Cloud Certification",
                issuing_organization="Cloud Org",
                credential_id="CERT-123",
                credential_url="https://certs.example/cert-123",
                issue_date=date(2021, 6, 1),
                expiry_date=date(2026, 6, 1),
                does_not_expire=False,
                description="Validated cloud architecture knowledge.",
                skills=["Cloud", "Architecture"],
                verified=True,
            ),
        ]
    )

    if long_cv:
        long_responsibilities = [
            (
                f"Delivered verified long-form responsibility {number}."
                f"{suffix}"
            )
            for number in range(1, 170)
        ]
        database.add(
            Experience(
                candidate_profile_id=1,
                company="Pagination Co",
                job_title="Platform Engineer",
                employment_type=None,
                location="Remote",
                start_date=date(2023, 1, 1),
                end_date=None,
                is_current=True,
                description=None,
                responsibilities=long_responsibilities,
                achievements=[],
                technologies=["Python"],
                verified=True,
            )
        )

    database.commit()


def generated_artifacts(
    database: Session,
    version_id: int,
) -> list[CVVersionArtifact]:
    return list(
        database.scalars(
            select(CVVersionArtifact)
            .where(CVVersionArtifact.cv_version_id == version_id)
            .order_by(CVVersionArtifact.artifact_type.asc())
        ).all()
    )


def artifact_path(artifact: CVVersionArtifact) -> Path:
    return resolve_generated_artifact_path(artifact.storage_path)


def mark_version_draft(
    database: Session,
    version_id: int,
) -> CVVersion:
    version = database.get(CVVersion, version_id)
    assert version is not None
    version.status = "draft"
    version.is_primary = False
    database.commit()
    database.refresh(version)
    return version


def extracted_generated_texts(
    artifacts: list[CVVersionArtifact],
) -> tuple[str, str]:
    by_type = {artifact.artifact_type: artifact for artifact in artifacts}
    docx_path = artifact_path(by_type["docx"])
    pdf_path = artifact_path(by_type["pdf"])

    validate_docx_file(docx_path)
    validate_pdf_file(pdf_path)

    docx = extract_docx_text(docx_path, 200_000)
    pdf = extract_pdf_text(pdf_path, 200_000)

    assert docx.status == "completed"
    assert pdf.status == "completed"
    assert docx.extracted_text is not None
    assert pdf.extracted_text is not None

    return docx.extracted_text, pdf.extracted_text


def assert_no_private_artifact_fields(payload: dict[str, object]) -> None:
    assert "storage_path" not in payload
    assert "absolute_path" not in payload
    assert "content" not in payload


def assert_no_font_binary_is_tracked() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked_fonts = [
        path
        for path in result.stdout.splitlines()
        if path.lower().endswith((".ttf", ".otf", ".ttc"))
    ]

    assert tracked_fonts == []


def assert_ordered(text: str, ordered_values: list[str]) -> None:
    positions = [text.index(value) for value in ordered_values]
    assert positions == sorted(positions)


def pdf_font_summaries(pdf_path: Path) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    reader = PdfReader(str(pdf_path))

    for page in reader.pages:
        fonts = (page.get("/Resources") or {}).get("/Font", {})
        for resource_name, font_reference in fonts.items():
            font = font_reference.get_object()
            descriptor_reference = font.get("/FontDescriptor")
            embedded: list[str] = []
            if descriptor_reference is not None:
                descriptor = descriptor_reference.get_object()
                embedded = [
                    str(key)
                    for key in ("/FontFile", "/FontFile2", "/FontFile3")
                    if key in descriptor
                ]

            summaries.append(
                {
                    "resource": str(resource_name),
                    "base_font": str(font.get("/BaseFont")),
                    "subtype": str(font.get("/Subtype")),
                    "has_to_unicode": "/ToUnicode" in font,
                    "embedded": embedded,
                }
            )

    return summaries


def assert_pdf_uses_embedded_packaged_fonts(pdf_path: Path) -> None:
    summaries = pdf_font_summaries(pdf_path)
    assert len(summaries) >= 2
    assert all(summary["has_to_unicode"] is True for summary in summaries)
    assert all(summary["embedded"] for summary in summaries)
    assert all(summary["subtype"] == "/TrueType" for summary in summaries)
    base_fonts = {str(summary["base_font"]) for summary in summaries}
    assert any(
        "NotoSans-Regular" in base_font
        for base_font in base_fonts
    )
    assert any(
        "NotoSansSC" in base_font
        for base_font in base_fonts
    )
    assert all(
        "Helvetica" not in str(summary["base_font"])
        and "STSong" not in str(summary["base_font"])
        for summary in summaries
    )


def assert_packaged_font_coverage() -> None:
    latin_path = packaged_font_path(
        PDF_LATIN_FONT_PACKAGE,
        PDF_LATIN_FONT_RESOURCE,
    )
    cjk_path = packaged_font_path(
        PDF_CJK_FONT_PACKAGE,
        PDF_CJK_FONT_RESOURCE,
    )
    assert "site-packages/justmytype_western_core" in latin_path.as_posix()
    assert "site-packages/justmytype_intl_cjk" in cjk_path.as_posix()

    for character in UNICODE_DETAIL:
        if character.isspace():
            continue

        selected_font = pdf_font_for_character(character)
        if ord(character) in latin_font_codepoints():
            assert selected_font == "CareerPilotNotoSans"
        else:
            assert ord(character) in cjk_font_codepoints()
            assert selected_font == "CareerPilotNotoSansSC"


def assert_pdf_thumbnail_is_nonblank(pdf_path: Path, tmp_path: Path) -> None:
    qlmanage = shutil.which("qlmanage")
    if qlmanage is None:
        pytest.skip("Quick Look thumbnail renderer is not available.")

    result = subprocess.run(
        [
            qlmanage,
            "-t",
            "-s",
            "1200",
            "-o",
            str(tmp_path),
            str(pdf_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and "sandbox initialization failed" in (
        result.stderr
    ):
        pytest.skip("Quick Look thumbnail renderer is blocked by sandboxing.")

    assert result.returncode == 0
    thumbnail = tmp_path / f"{pdf_path.name}.png"
    assert thumbnail.exists()
    assert thumbnail.stat().st_size > 0


def long_marker_text(
    prefix: str,
    target_characters: int,
    *,
    include_unicode: bool = False,
    wide: bool = False,
) -> tuple[str, list[str]]:
    values: list[str] = []
    index = 1
    filler = "WWWWWWWWWWWW" if wide else "verified"

    while len(" ".join(values)) < target_characters:
        suffix = f" {UNICODE_DETAIL}" if include_unicode else ""
        values.append(f"{prefix}-{index:03d}-{filler}{suffix}")
        index += 1

    markers = [
        values[0].split()[0],
        values[len(values) // 2].split()[0],
        values[-1].split()[0],
    ]

    return " ".join(values), markers


def pdf_text_positions(pdf_path: Path) -> list[dict[str, object]]:
    positions: list[dict[str, object]] = []
    reader = PdfReader(str(pdf_path))

    for page_number, page in enumerate(reader.pages, start=1):
        def collect_text(
            text: str,
            _current_matrix: object,
            text_matrix: object,
            _font_dictionary: object,
            _font_size: object,
        ) -> None:
            cleaned = text.strip()
            if not cleaned:
                return

            assert isinstance(text_matrix, list)
            positions.append(
                {
                    "page": page_number,
                    "text": cleaned,
                    "x": float(text_matrix[4]),
                    "y": float(text_matrix[5]),
                }
            )

        page.extract_text(visitor_text=collect_text)

    return positions


def assert_pdf_geometry_is_inside_margins(pdf_path: Path) -> None:
    positions = pdf_text_positions(pdf_path)
    assert positions

    bottom_margin = 0.75 * 72
    assert all(float(position["y"]) >= bottom_margin for position in positions)

    pages = {int(position["page"]) for position in positions}
    for page_number in pages:
        y_values = sorted(
            {
                round(float(position["y"]), 1)
                for position in positions
                if position["page"] == page_number
            },
            reverse=True,
        )
        for previous, current in zip(y_values, y_values[1:]):
            assert previous - current >= 10


def assert_markers_are_continuous_once(
    text: str,
    markers: list[str],
) -> None:
    assert_ordered(text, markers)
    for marker in markers:
        assert text.count(marker) == 1


def marker_pages(
    pdf_path: Path,
    marker_prefix: str,
) -> set[int]:
    return {
        int(position["page"])
        for position in pdf_text_positions(pdf_path)
        if marker_prefix in str(position["text"])
    }


def assert_marker_indent_is_consistent(
    pdf_path: Path,
    marker_prefix: str,
    expected_x: float,
) -> None:
    matching_positions = [
        position
        for position in pdf_text_positions(pdf_path)
        if marker_prefix in str(position["text"])
    ]
    assert matching_positions
    assert any(int(position["page"]) > 1 for position in matching_positions)
    for position in matching_positions:
        assert abs(float(position["x"]) - expected_x) < 0.5


def pdf_page_font_summaries(
    pdf_path: Path,
) -> dict[int, list[dict[str, object]]]:
    reader = PdfReader(str(pdf_path))
    summaries: dict[int, list[dict[str, object]]] = {}

    for page_number, page in enumerate(reader.pages, start=1):
        page_summaries: list[dict[str, object]] = []
        fonts = (page.get("/Resources") or {}).get("/Font", {})
        for resource_name, font_reference in fonts.items():
            font = font_reference.get_object()
            descriptor_reference = font.get("/FontDescriptor")
            embedded: list[str] = []
            if descriptor_reference is not None:
                descriptor = descriptor_reference.get_object()
                embedded = [
                    str(key)
                    for key in ("/FontFile", "/FontFile2", "/FontFile3")
                    if key in descriptor
                ]

            page_summaries.append(
                {
                    "resource": str(resource_name),
                    "base_font": str(font.get("/BaseFont")),
                    "has_to_unicode": "/ToUnicode" in font,
                    "embedded": embedded,
                }
            )
        summaries[page_number] = page_summaries

    return summaries


def assert_later_page_uses_western_and_cjk_fonts(pdf_path: Path) -> None:
    page_summaries = pdf_page_font_summaries(pdf_path)
    later_pages = {
        page_number: summaries
        for page_number, summaries in page_summaries.items()
        if page_number > 1
    }
    assert later_pages
    assert any(
        any("NotoSans-Regular" in str(summary["base_font"]) for summary in summaries)
        and any("NotoSansSC" in str(summary["base_font"]) for summary in summaries)
        and all(summary["has_to_unicode"] for summary in summaries)
        and all(summary["embedded"] for summary in summaries)
        for summaries in later_pages.values()
    )


def test_generate_verified_master_cv_creates_safe_docx_and_pdf(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    storage_dir = configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session)

    response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={
            "display_name": "Verified Master CV",
            "idempotency_key": "phase37-main",
            "is_primary": True,
        },
        headers=account.headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["created"] is True
    assert payload["version"]["version_type"] == "verified_master"
    assert payload["version"]["status"] == "ready"
    assert payload["version"]["parent_version_id"] == parent.id
    assert payload["version"]["is_primary"] is True
    assert payload["version"]["generated_at"] is not None
    assert payload["version"]["source_summary"] == {
        "profile": 1,
        "education": 1,
        "work_experiences": 2,
        "projects": 1,
        "skills": 2,
        "certifications": 1,
    }

    artifact_payloads = payload["artifacts"]
    assert [item["artifact_type"] for item in artifact_payloads] == [
        "docx",
        "pdf",
    ]
    for artifact_payload in artifact_payloads:
        assert_no_private_artifact_fields(artifact_payload)
        assert artifact_payload["safe_filename"].startswith(
            "pavan_test-verified-master-cv-v"
        )

    artifacts = generated_artifacts(db_session, payload["version"]["id"])
    assert {artifact.artifact_type for artifact in artifacts} == {
        "docx",
        "pdf",
    }

    for artifact in artifacts:
        path = artifact_path(artifact)
        assert path.exists()
        assert path.parent.resolve() == storage_dir.resolve()
        assert re.fullmatch(
            r"[a-f0-9]{32}\.(docx|pdf)",
            artifact.storage_path,
        )
        assert artifact.file_size == path.stat().st_size
        assert artifact.sha256 == sha256(path.read_bytes()).hexdigest()
        assert artifact.safe_filename.endswith(f".{artifact.artifact_type}")

    docx_text, pdf_text = extracted_generated_texts(artifacts)
    expected_phrases = [
        "Contact",
        "Pavan Test",
        "Senior Backend Engineer",
        "Email: pavan@example.com",
        "Professional Summary",
        "Backend engineer focused on reliable APIs and data integrity.",
        "Work Experience",
        "Senior Backend Engineer, Verified Labs",
        "Jan 2022 - Present",
        "Protected 2024 audit evidence without changing facts.",
        "Reduced reconciliation time by 30%.",
        "Education",
        "MSc in Computer Science, Verified University",
        "Skills",
        "Programming: Python (Advanced)",
        "Projects",
        "Truthful CV Builder - Lead Developer",
        "Created DOCX and PDF artifacts.",
        "Certifications",
        "Verified Cloud Certification, Cloud Org",
        "Credential ID: CERT-123",
    ]
    for phrase in expected_phrases:
        assert phrase in docx_text
        assert phrase in pdf_text

    excluded_phrases = [
        "Unverified Employer",
        "Unverified Moonshot",
        "Unverified Skill",
        "Uploaded CV text must not be copied.",
        "Do not include",
        "120000",
        "Right to work",
        "99.0",
    ]
    combined_text = f"{docx_text}\n{pdf_text}"
    for phrase in excluded_phrases:
        assert phrase not in combined_text

    assert docx_text.index("Verified Labs") < docx_text.index("Older Co")
    assert pdf_text.index("Verified Labs") < pdf_text.index("Older Co")
    section_order = [
        "Contact",
        "Professional Summary",
        "Work Experience",
        "Education",
        "Skills",
        "Projects",
        "Certifications",
    ]
    assert_ordered(docx_text, section_order)
    assert_ordered(pdf_text, section_order)


def test_unicode_docx_and_pdf_round_trip_preserves_canonical_text(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(
        db_session,
        account,
        full_name="José Núñez",
        professional_title="Łukasz Żółć 李雷 Engineer",
        summary=UNICODE_DETAIL,
    )
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session, unicode_suffix=UNICODE_DETAIL)

    response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-unicode-main"},
        headers=account.headers,
    )

    assert response.status_code == 201
    artifacts = generated_artifacts(db_session, response.json()["version"]["id"])
    docx_text, pdf_text = extracted_generated_texts(artifacts)
    by_type = {artifact.artifact_type: artifact for artifact in artifacts}
    pdf_path = artifact_path(by_type["pdf"])

    expected_phrases = [
        UNICODE_SAMPLE,
        UNICODE_DETAIL,
        "Łukasz Żółć 李雷 Engineer",
        "Protected 2024 audit evidence without changing facts.",
    ]
    for phrase in expected_phrases:
        assert phrase in docx_text
        assert phrase in pdf_text

    assert UNICODE_DETAIL in docx_text
    assert UNICODE_DETAIL in pdf_text
    assert "\u25a0" not in pdf_text
    assert "\ufffd" not in pdf_text
    assert "?" not in pdf_text
    assert_packaged_font_coverage()
    assert_pdf_uses_embedded_packaged_fonts(pdf_path)
    assert_pdf_thumbnail_is_nonblank(pdf_path, tmp_path)
    assert_no_font_binary_is_tracked()


def test_empty_sections_are_omitted_without_changing_remaining_order(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account, summary=None)
    parent = make_parent_chain(db_session)
    db_session.add(
        Skill(
            candidate_profile_id=1,
            name="Python",
            category="Programming",
            proficiency="Advanced",
            years_experience=None,
            evidence=None,
            is_primary=True,
            verified=True,
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-empty-section-order"},
        headers=account.headers,
    )

    assert response.status_code == 201
    artifacts = generated_artifacts(db_session, response.json()["version"]["id"])
    docx_text, pdf_text = extracted_generated_texts(artifacts)

    for text_value in (docx_text, pdf_text):
        assert "Contact" in text_value
        assert "Skills" in text_value
        assert "Professional Summary" not in text_value
        assert "Work Experience" not in text_value
        assert "Education" not in text_value
        assert "Projects" not in text_value
        assert "Certifications" not in text_value
        assert_ordered(text_value, ["Contact", "Skills"])


def test_long_unicode_pdf_paginates_without_content_loss(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account, summary=UNICODE_DETAIL)
    parent = make_parent_chain(db_session)
    add_verified_facts(
        db_session,
        long_cv=True,
        unicode_suffix=UNICODE_SAMPLE,
    )

    response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-long-unicode"},
        headers=account.headers,
    )

    assert response.status_code == 201
    artifacts = generated_artifacts(db_session, response.json()["version"]["id"])
    by_type = {artifact.artifact_type: artifact for artifact in artifacts}
    assert by_type["pdf"].page_count is not None
    assert by_type["pdf"].page_count >= 2

    docx_text, pdf_text = extracted_generated_texts(artifacts)
    expected = (
        "Delivered verified long-form responsibility 169."
        f" {UNICODE_SAMPLE}"
    )
    assert expected in docx_text
    assert expected in pdf_text


def test_long_single_paragraph_fields_paginate_without_clipping(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    summary_text, summary_markers = long_marker_text(
        "SUMMARY",
        5_200,
        include_unicode=True,
        wide=True,
    )
    project_text, project_markers = long_marker_text(
        "PROJECT",
        5_500,
        wide=True,
    )
    make_profile(db_session, account, summary=summary_text)
    parent = make_parent_chain(db_session)
    db_session.add(
        Project(
            candidate_profile_id=1,
            name="Long Verified Project",
            role="Author",
            project_type="Synthetic",
            description=project_text,
            start_date=date(2024, 1, 1),
            end_date=None,
            is_current=True,
            project_url=None,
            github_url=None,
            technologies=[],
            features=[],
            achievements=[],
            verified=True,
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-long-single-paragraphs"},
        headers=account.headers,
    )

    assert response.status_code == 201
    artifacts = generated_artifacts(db_session, response.json()["version"]["id"])
    by_type = {artifact.artifact_type: artifact for artifact in artifacts}
    assert by_type["pdf"].page_count is not None
    assert by_type["pdf"].page_count >= 3

    pdf_path = artifact_path(by_type["pdf"])
    docx_text, pdf_text = extracted_generated_texts(artifacts)
    assert_pdf_geometry_is_inside_margins(pdf_path)
    assert_markers_are_continuous_once(docx_text, summary_markers)
    assert_markers_are_continuous_once(pdf_text, summary_markers)
    assert_markers_are_continuous_once(docx_text, project_markers)
    assert_markers_are_continuous_once(pdf_text, project_markers)
    assert_ordered(
        pdf_text,
        [
            "Contact",
            "Professional Summary",
            *summary_markers,
            "Projects",
            *project_markers,
        ],
    )
    assert len(marker_pages(pdf_path, "SUMMARY-")) >= 2
    assert len(marker_pages(pdf_path, "PROJECT-")) >= 2


def test_single_long_responsibility_bullet_paginates_with_indent(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    bullet_text, bullet_markers = long_marker_text(
        "BULLET",
        6_500,
        wide=True,
    )
    make_profile(db_session, account, summary=None)
    parent = make_parent_chain(db_session)
    db_session.add(
        Experience(
            candidate_profile_id=1,
            company="Verified Pagination Co",
            job_title="Pagination Engineer",
            employment_type=None,
            location="Remote",
            start_date=date(2024, 1, 1),
            end_date=None,
            is_current=True,
            description=None,
            responsibilities=[bullet_text],
            achievements=[],
            technologies=[],
            verified=True,
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-long-bullet"},
        headers=account.headers,
    )

    assert response.status_code == 201
    artifacts = generated_artifacts(db_session, response.json()["version"]["id"])
    by_type = {artifact.artifact_type: artifact for artifact in artifacts}
    assert by_type["pdf"].page_count is not None
    assert by_type["pdf"].page_count >= 2

    pdf_path = artifact_path(by_type["pdf"])
    docx_text, pdf_text = extracted_generated_texts(artifacts)
    assert_pdf_geometry_is_inside_margins(pdf_path)
    assert_markers_are_continuous_once(docx_text, bullet_markers)
    assert_markers_are_continuous_once(pdf_text, bullet_markers)
    assert_ordered(
        pdf_text,
        [
            "Contact",
            "Work Experience",
            "Pagination Engineer, Verified Pagination Co",
            *bullet_markers,
        ],
    )
    assert len(marker_pages(pdf_path, "BULLET-")) >= 2
    assert_marker_indent_is_consistent(
        pdf_path,
        "BULLET-",
        expected_x=(0.75 * 72) + 14,
    )


def test_mixed_unicode_text_survives_pdf_page_boundaries(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    unicode_text, unicode_markers = long_marker_text(
        "UNICODE",
        8_500,
        include_unicode=True,
        wide=True,
    )
    make_profile(db_session, account, summary=unicode_text)
    parent = make_parent_chain(db_session)

    response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-unicode-page-breaks"},
        headers=account.headers,
    )

    assert response.status_code == 201
    artifacts = generated_artifacts(db_session, response.json()["version"]["id"])
    by_type = {artifact.artifact_type: artifact for artifact in artifacts}
    assert by_type["pdf"].page_count is not None
    assert by_type["pdf"].page_count >= 2

    pdf_path = artifact_path(by_type["pdf"])
    docx_text, pdf_text = extracted_generated_texts(artifacts)
    reader = PdfReader(str(pdf_path))
    page_texts = [page.extract_text() or "" for page in reader.pages]

    assert_pdf_geometry_is_inside_margins(pdf_path)
    assert_markers_are_continuous_once(docx_text, unicode_markers)
    assert_markers_are_continuous_once(pdf_text, unicode_markers)
    assert UNICODE_DETAIL in docx_text
    assert UNICODE_DETAIL in pdf_text
    assert any(UNICODE_DETAIL in page_text for page_text in page_texts[1:])
    assert "\u25a0" not in pdf_text
    assert "\ufffd" not in pdf_text
    assert "?" not in pdf_text
    assert_later_page_uses_western_and_cjk_fonts(pdf_path)


def test_unsupported_unicode_fails_safely_without_ready_artifacts(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    storage_dir = configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account, summary=UNSUPPORTED_UNICODE)
    parent = make_parent_chain(db_session)

    response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-unsupported-unicode"},
        headers=account.headers,
    )

    assert response.status_code == 400
    assert "PDF renderer" in response.json()["detail"]
    failed_version = db_session.scalars(
        select(CVVersion).where(
            CVVersion.generation_key == "phase37-unsupported-unicode"
        )
    ).one()
    assert failed_version.status == "failed"
    assert failed_version.is_primary is False
    assert generated_artifacts(db_session, failed_version.id) == []
    assert not list(storage_dir.glob("*.docx"))
    assert not list(storage_dir.glob("*.pdf"))


def test_generated_artifact_metadata_and_downloads_are_safe(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session)

    generate_response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-download"},
        headers=account.headers,
    )
    version_id = generate_response.json()["version"]["id"]
    list_response = client.get(f"/api/cv-versions/{version_id}/artifacts", headers=account.headers)

    assert list_response.status_code == 200
    listed = list_response.json()
    assert [item["artifact_type"] for item in listed] == ["docx", "pdf"]
    for item in listed:
        assert_no_private_artifact_fields(item)
        metadata_response = client.get(f"/api/cv-artifacts/{item['id']}", headers=account.headers)
        assert metadata_response.status_code == 200
        assert_no_private_artifact_fields(metadata_response.json())

        download_response = client.get(
            f"/api/cv-artifacts/{item['id']}/download",
            headers=account.headers,
        )
        assert download_response.status_code == 200
        assert download_response.headers["content-type"].startswith(
            item["mime_type"]
        )
        assert item["safe_filename"] in (
            download_response.headers["content-disposition"]
        )
        assert download_response.content


def test_idempotency_key_prevents_uncontrolled_duplicates(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session)

    first = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-repeat"},
        headers=account.headers,
    )
    second = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-repeat"},
        headers=account.headers,
    )
    third = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-regenerate"},
        headers=account.headers,
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert second.json()["version"]["id"] == first.json()["version"]["id"]
    assert third.status_code == 201
    assert third.json()["version"]["id"] != first.json()["version"]["id"]

    versions = list(
        db_session.scalars(
            select(CVVersion).where(
                CVVersion.version_type == "verified_master"
            )
        ).all()
    )
    assert len(versions) == 2


def test_generic_verified_master_creation_and_ready_update_are_blocked(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)

    create_response = client.post(
        "/api/cv-versions",
        json={
            "version_type": "verified_master",
            "parent_version_id": parent.id,
            "status": "ready",
            "display_name": "Forged Verified Master",
        },
        headers=account.headers,
    )
    assert create_response.status_code == 400
    assert "generation workflow" in create_response.json()["detail"]

    artifactless = make_version(
        db_session,
        version_type="verified_master",
        status="draft",
        parent_version_id=parent.id,
    )
    update_response = client.patch(
        f"/api/cv-versions/{artifactless.id}",
        json={"status": "ready"},
        headers=account.headers,
    )
    assert update_response.status_code == 400
    assert "DOCX and PDF artifacts" in update_response.json()["detail"]

    primary_response = client.patch(
        f"/api/cv-versions/{artifactless.id}/primary",
        headers=account.headers,
    )
    assert primary_response.status_code == 400


def test_single_artifact_verified_master_cannot_be_marked_ready(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    version = make_version(
        db_session,
        version_type="verified_master",
        status="draft",
        parent_version_id=parent.id,
    )
    artifact = CVVersionArtifact(
        cv_version_id=version.id,
        artifact_type="docx",
        mime_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        safe_filename="single.docx",
        storage_path="single.docx",
        file_size=10,
        sha256=sha256(b"single").hexdigest(),
        page_count=None,
        renderer_version="test",
        content_version="test",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(artifact)
    db_session.commit()

    response = client.patch(
        f"/api/cv-versions/{version.id}",
        json={"status": "ready"},
        headers=account.headers,
    )

    assert response.status_code == 400
    assert "DOCX and PDF artifacts" in response.json()["detail"]


def test_valid_existing_artifacts_allow_ready_and_primary(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session)

    generate_response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-valid-ready"},
        headers=account.headers,
    )
    version_id = generate_response.json()["version"]["id"]
    mark_version_draft(db_session, version_id)

    ready_response = client.patch(
        f"/api/cv-versions/{version_id}",
        json={"status": "ready"},
        headers=account.headers,
    )
    primary_response = client.patch(f"/api/cv-versions/{version_id}/primary", headers=account.headers)

    assert ready_response.status_code == 200
    assert ready_response.json()["status"] == "ready"
    assert primary_response.status_code == 200
    assert primary_response.json()["is_primary"] is True


@pytest.mark.parametrize(
    ("artifact_type", "expected_message"),
    [
        ("docx", "DOCX and PDF artifacts"),
        ("pdf", "DOCX and PDF artifacts"),
    ],
)
def test_missing_required_artifact_blocks_ready_status(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
    artifact_type: str,
    expected_message: str,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session)

    generate_response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": f"phase37-missing-{artifact_type}"},
        headers=account.headers,
    )
    version_id = generate_response.json()["version"]["id"]
    mark_version_draft(db_session, version_id)
    artifact = next(
        item
        for item in generated_artifacts(db_session, version_id)
        if item.artifact_type == artifact_type
    )
    db_session.delete(artifact)
    db_session.commit()

    response = client.patch(
        f"/api/cv-versions/{version_id}",
        json={"status": "ready"},
        headers=account.headers,
    )

    assert response.status_code == 400
    assert expected_message in response.json()["detail"]


@pytest.mark.parametrize(
    "tamper_case",
    [
        "missing_file",
        "wrong_size",
        "wrong_sha256",
        "wrong_mime",
        "unsafe_path",
        "corrupt_docx",
        "corrupt_pdf",
    ],
)
def test_invalid_physical_artifacts_block_ready_status(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
    tamper_case: str,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session)

    generate_response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": f"phase37-tamper-{tamper_case}"},
        headers=account.headers,
    )
    version_id = generate_response.json()["version"]["id"]
    mark_version_draft(db_session, version_id)
    artifacts = generated_artifacts(db_session, version_id)
    by_type = {artifact.artifact_type: artifact for artifact in artifacts}
    target = by_type["pdf"]

    if tamper_case == "missing_file":
        artifact_path(target).unlink()
    elif tamper_case == "wrong_size":
        target.file_size += 1
    elif tamper_case == "wrong_sha256":
        target.sha256 = sha256(b"wrong").hexdigest()
    elif tamper_case == "wrong_mime":
        target.mime_type = "application/octet-stream"
    elif tamper_case == "unsafe_path":
        target.storage_path = "../escape.pdf"
    elif tamper_case == "corrupt_docx":
        target = by_type["docx"]
        path = artifact_path(target)
        path.write_bytes(b"not a docx")
        target.file_size = path.stat().st_size
        target.sha256 = sha256(path.read_bytes()).hexdigest()
    elif tamper_case == "corrupt_pdf":
        path = artifact_path(target)
        path.write_bytes(b"%PDF-1.4\n%%EOF")
        target.file_size = path.stat().st_size
        target.sha256 = sha256(path.read_bytes()).hexdigest()
    else:
        raise AssertionError(f"Unhandled tamper case: {tamper_case}")

    db_session.commit()

    response = client.patch(
        f"/api/cv-versions/{version_id}",
        json={"status": "ready"},
        headers=account.headers,
    )

    assert response.status_code == 400
    assert "missing or invalid" in response.json()["detail"]


def test_modified_artifact_blocks_primary_selection(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session)

    generate_response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-primary-tamper"},
        headers=account.headers,
    )
    version_id = generate_response.json()["version"]["id"]
    artifact = next(
        item
        for item in generated_artifacts(db_session, version_id)
        if item.artifact_type == "pdf"
    )
    artifact_path(artifact).unlink()

    response = client.patch(f"/api/cv-versions/{version_id}/primary", headers=account.headers)

    assert response.status_code == 400
    assert "missing or invalid" in response.json()["detail"]


def test_generation_rejects_missing_or_invalid_verified_inputs(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account, facts_verified=False)
    parent = make_parent_chain(db_session)

    unverified_profile_response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-unverified-profile"},
        headers=account.headers,
    )
    assert unverified_profile_response.status_code == 400
    assert "verified" in unverified_profile_response.json()["detail"]

    db_session.rollback()
    profile = db_session.get(CandidateProfile, account.profile_id)
    assert profile is not None
    profile.facts_verified = True
    profile.professional_summary = None
    db_session.commit()

    no_facts_response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-empty-vault"},
        headers=account.headers,
    )
    assert no_facts_response.status_code == 400
    assert "No eligible verified facts" in no_facts_response.json()["detail"]

    missing_parent_response = client.post(
        "/api/cv-versions/999999/generate-master",
        json={"idempotency_key": "phase37-missing-parent"},
        headers=account.headers,
    )
    assert missing_parent_response.status_code == 404

    original = make_version(db_session, version_type="original")
    invalid_type_response = client.post(
        f"/api/cv-versions/{original.id}/generate-master",
        json={"idempotency_key": "phase37-invalid-type"},
        headers=account.headers,
    )
    assert invalid_type_response.status_code == 400

    archived_parent = make_version(
        db_session,
        version_type="parsed",
        status="archived",
    )
    archived_response = client.post(
        f"/api/cv-versions/{archived_parent.id}/generate-master",
        json={"idempotency_key": "phase37-archived-parent"},
        headers=account.headers,
    )
    assert archived_response.status_code == 400
    assert "ready" in archived_response.json()["detail"]


def test_failure_during_pdf_generation_leaves_failed_version_without_files(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    storage_dir = configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session)

    from app.services import verified_master_cv as service

    def fail_pdf(*_args, **_kwargs) -> int | None:
        raise RuntimeError("synthetic pdf failure")

    monkeypatch.setattr(service, "render_pdf", fail_pdf)

    response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-pdf-failure"},
        headers=account.headers,
    )

    assert response.status_code == 500
    assert "Failed to generate" in response.json()["detail"]
    failed_version = db_session.scalars(
        select(CVVersion).where(
            CVVersion.generation_key == "phase37-pdf-failure"
        )
    ).one()
    assert failed_version.status == "failed"
    assert failed_version.is_primary is False
    assert generated_artifacts(db_session, failed_version.id) == []
    assert not list(storage_dir.glob("*.docx"))
    assert not list(storage_dir.glob("*.pdf"))

    primary_response = client.patch(
        f"/api/cv-versions/{failed_version.id}/primary",
        headers=account.headers,
    )
    assert primary_response.status_code == 400


def test_archive_preserves_artifacts_and_leaf_delete_removes_only_artifacts(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session)
    source_document_count = db_session.query(Document).count()

    generate_response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-lifecycle"},
        headers=account.headers,
    )
    version_id = generate_response.json()["version"]["id"]
    artifacts = generated_artifacts(db_session, version_id)
    artifact_paths = [artifact_path(artifact) for artifact in artifacts]

    archive_response = client.patch(f"/api/cv-versions/{version_id}/archive", headers=account.headers)
    assert archive_response.status_code == 200
    for path in artifact_paths:
        assert path.exists()

    delete_response = client.delete(f"/api/cv-versions/{version_id}", headers=account.headers)
    assert delete_response.status_code == 204
    for path in artifact_paths:
        assert not path.exists()

    assert db_session.query(Document).count() == source_document_count
    assert db_session.get(CVVersion, parent.id) is not None


def test_leaf_delete_database_failure_leaves_generated_artifacts_untouched(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session)

    generate_response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-delete-rollback"},
        headers=account.headers,
    )
    version_id = generate_response.json()["version"]["id"]
    artifacts = generated_artifacts(db_session, version_id)
    artifact_paths = [artifact_path(artifact) for artifact in artifacts]
    assert all(path.exists() for path in artifact_paths)

    def fail_commit() -> None:
        raise RuntimeError("synthetic database failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)

    with pytest.raises(cv_version_service.CVVersionServiceError) as exc:
        cv_version_service.delete_cv_version(version_id, db_session)

    assert exc.value.safe_message == "Failed to delete CV version."
    assert all(path.exists() for path in artifact_paths)
    db_session.expire_all()
    assert db_session.get(CVVersion, version_id) is not None
    assert len(generated_artifacts(db_session, version_id)) == 2


def test_post_commit_cleanup_failure_keeps_database_deletion_committed(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session)

    generate_response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-cleanup-failure"},
        headers=account.headers,
    )
    version_id = generate_response.json()["version"]["id"]
    db_session.rollback()
    artifacts = generated_artifacts(db_session, version_id)
    assert len(artifacts) == 2
    artifact_paths = {artifact_path(artifact) for artifact in artifacts}
    failing_storage_paths = {artifact.storage_path for artifact in artifacts}
    original_remove_generated_artifact = (
        cv_version_service.remove_generated_artifact
    )

    def fail_artifact_unlink(
        storage_path: str,
    ) -> None:
        if storage_path in failing_storage_paths:
            raise RuntimeError("synthetic cleanup failure")

        original_remove_generated_artifact(storage_path)

    monkeypatch.setattr(
        cv_version_service,
        "remove_generated_artifact",
        fail_artifact_unlink,
    )
    cleanup_warnings: list[str] = []

    def record_cleanup_warning(message: str) -> None:
        cleanup_warnings.append(message)

    monkeypatch.setattr(
        cv_version_service.logger,
        "warning",
        record_cleanup_warning,
    )

    cv_version_service.delete_cv_version(version_id, db_session)

    db_session.expire_all()
    assert db_session.get(CVVersion, version_id) is None
    assert generated_artifacts(db_session, version_id) == []
    assert all(path.exists() for path in artifact_paths)
    assert cleanup_warnings == [
        "Generated CV artifact cleanup failed after CV version deletion.",
        "Generated CV artifact cleanup failed after CV version deletion.",
    ]
    assert all(
        str(path) not in " ".join(cleanup_warnings)
        for path in artifact_paths
    )


def test_leaf_delete_cleanup_affects_only_deleted_version_artifacts(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session)

    first = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-delete-one"},
        headers=account.headers,
    )
    second = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-keep-other"},
        headers=account.headers,
    )
    first_id = first.json()["version"]["id"]
    second_id = second.json()["version"]["id"]
    first_paths = [
        artifact_path(artifact)
        for artifact in generated_artifacts(db_session, first_id)
    ]
    second_paths = [
        artifact_path(artifact)
        for artifact in generated_artifacts(db_session, second_id)
    ]

    response = client.delete(f"/api/cv-versions/{first_id}", headers=account.headers)

    assert response.status_code == 204
    assert all(not path.exists() for path in first_paths)
    assert all(path.exists() for path in second_paths)
    assert db_session.get(CVVersion, second_id) is not None


def test_delete_rejects_unsafe_generated_artifact_path_without_file_cleanup(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    storage_dir = configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    version = make_version(db_session, version_type="verified_master")
    outside_file = tmp_path / "outside.pdf"
    outside_file.write_bytes(b"%PDF-1.4\n%%EOF")
    artifact = CVVersionArtifact(
        cv_version_id=version.id,
        artifact_type="pdf",
        mime_type="application/pdf",
        safe_filename="safe.pdf",
        storage_path="../outside.pdf",
        file_size=outside_file.stat().st_size,
        sha256=sha256(outside_file.read_bytes()).hexdigest(),
        page_count=1,
        renderer_version="test",
        content_version="test",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(artifact)
    db_session.commit()

    response = client.delete(f"/api/cv-versions/{version.id}", headers=account.headers)

    assert response.status_code == 500
    assert outside_file.exists()
    assert db_session.get(CVVersion, version.id) is not None
    assert not any(storage_dir.glob("*.delete-pending*"))


def test_download_blocks_artifact_path_traversal(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    version = make_version(db_session, version_type="verified_master")
    artifact = CVVersionArtifact(
        cv_version_id=version.id,
        artifact_type="pdf",
        mime_type="application/pdf",
        safe_filename="safe.pdf",
        storage_path="../evil.pdf",
        file_size=10,
        sha256=sha256(b"fake").hexdigest(),
        page_count=1,
        renderer_version="test",
        content_version="test",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(artifact)
    db_session.commit()
    db_session.refresh(artifact)

    response = client.get(f"/api/cv-artifacts/{artifact.id}/download", headers=account.headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_long_verified_master_cv_paginates_without_content_loss(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session, long_cv=True)

    response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-long-cv"},
        headers=account.headers,
    )
    assert response.status_code == 201
    artifacts = generated_artifacts(db_session, response.json()["version"]["id"])
    by_type = {artifact.artifact_type: artifact for artifact in artifacts}
    assert by_type["pdf"].page_count is not None
    assert by_type["pdf"].page_count >= 2

    _, pdf_text = extracted_generated_texts(artifacts)
    assert "Delivered verified long-form responsibility 169." in pdf_text


def test_generation_does_not_modify_candidate_facts(
    client: TestClient,
    db_session: Session,
    account: Account,
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_generated_storage(monkeypatch, tmp_path)
    profile = make_profile(db_session, account)
    parent = make_parent_chain(db_session)
    add_verified_facts(db_session)
    before = {
        "profile_summary": profile.professional_summary,
        "experience_count": db_session.query(Experience).count(),
        "project_count": db_session.query(Project).count(),
        "skill_names": [
            skill.name
            for skill in db_session.scalars(
                select(Skill).order_by(Skill.id.asc())
            ).all()
        ],
    }

    response = client.post(
        f"/api/cv-versions/{parent.id}/generate-master",
        json={"idempotency_key": "phase37-readonly-facts"},
        headers=account.headers,
    )

    assert response.status_code == 201
    db_session.expire_all()
    persisted_profile = db_session.get(CandidateProfile, profile.id)
    assert persisted_profile is not None
    after = {
        "profile_summary": persisted_profile.professional_summary,
        "experience_count": db_session.query(Experience).count(),
        "project_count": db_session.query(Project).count(),
        "skill_names": [
            skill.name
            for skill in db_session.scalars(
                select(Skill).order_by(Skill.id.asc())
            ).all()
        ],
    }
    assert after == before


def assert_outside_repository(path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]

    try:
        path.resolve().relative_to(repository_root)
    except ValueError:
        return

    raise AssertionError(f"Temporary database is inside repository: {path}")


def test_verified_master_cv_migration_upgrade_downgrade_reupgrade(
    tmp_path: Path,
) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    migration_db = tmp_path / "verified-master-cv-migration.db"
    assert_outside_repository(migration_db)

    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{migration_db}")
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == [CURRENT_HEAD]
    assert script.get_revision(PHASE37_HEAD).down_revision == PHASE36_HEAD

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{migration_db}")

    try:
        inspector = inspect(engine)
        assert "cv_version_artifacts" in inspector.get_table_names()
        cv_version_columns = {
            column["name"]
            for column in inspector.get_columns("cv_versions")
        }
        assert {
            "generation_key",
            "generation_version",
            "source_summary",
            "generated_at",
        }.issubset(cv_version_columns)
        artifact_indexes = {
            index["name"]
            for index in inspector.get_indexes("cv_version_artifacts")
        }
        assert {
            "ix_cv_version_artifacts_cv_version_id",
            "ix_cv_version_artifacts_artifact_type",
        }.issubset(artifact_indexes)

        with engine.connect() as connection:
            upgraded_tables = {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT name FROM sqlite_master "
                        "WHERE type = 'table'"
                    )
                )
            }

        command.downgrade(config, PHASE36_HEAD)

        with engine.connect() as connection:
            downgraded_tables = {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT name FROM sqlite_master "
                        "WHERE type = 'table'"
                    )
                )
            }
        assert {
            "cv_version_artifacts",
        }.issubset(upgraded_tables - downgraded_tables)
        assert "cv_versions" in downgraded_tables
        downgraded_columns = {
            column["name"]
            for column in inspect(engine).get_columns("cv_versions")
        }
        assert "generation_key" not in downgraded_columns

        command.upgrade(config, "head")

        reupgraded_tables = set(inspect(engine).get_table_names())
        reupgraded_columns = {
            column["name"]
            for column in inspect(engine).get_columns("cv_versions")
        }
        assert "cv_version_artifacts" in reupgraded_tables
        assert "generation_key" in reupgraded_columns
    finally:
        engine.dispose()
