"""Deterministic extraction of candidate details from an uploaded CV.

Turns an already-extracted CV (text + detected sections) into a
profile suggestion. Everything produced here is a *suggestion*, never
a verified fact: the truthfulness rules require that CV-derived data
be reviewed and confirmed by the candidate. Nothing is invented — a
field is only suggested when it is found in the CV text, with a
bounded evidence snippet.

Sensitivity: private/personal fields (phone number, location) and any
structured history that would require inventing dates (education,
work experience, projects, certifications) are flagged for manual
review and are never auto-applied. Safe, high-confidence fields (name,
email, professional title/summary, profile links) and the skills list
can be applied — always as unverified data.

No AI, OCR, embeddings, network, or external services are used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.certification import Certification
from app.models.document import Document
from app.models.education import Education
from app.models.experience import Experience
from app.models.project import Project
from app.models.skill import Skill
from app.services.document_section_detection import (
    EMAIL_PATTERN,
    PHONE_PATTERN,
    URL_PATTERN,
    CVSectionDetectionError,
    detect_sections_from_text,
    has_contact_signal,
)


EXTRACTION_VERSION = "cv-profile-extraction-2"
EVIDENCE_LIMIT = 300
SUMMARY_LIMIT = 2000
MANUAL_CONTENT_LIMIT = 2000
MAX_NAME_WORDS = 6
MAX_SKILLS = 100

TITLE_KEYWORDS = (
    "engineer",
    "developer",
    "manager",
    "designer",
    "analyst",
    "scientist",
    "consultant",
    "architect",
    "administrator",
    "specialist",
    "lead",
    "director",
    "officer",
    "coordinator",
    "intern",
)

SKILL_SPLIT_PATTERN = re.compile(r"[,;|•\t]| - |•")

# Structured-parsing limits and vocabulary --------------------------------
MAX_STRUCTURED_ENTRIES = 40
DESCRIPTION_LIMIT = 2000
ENTRY_TEXT_LIMIT = 4000

_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_PRESENT_WORDS = ("present", "current", "now", "ongoing", "till date", "to date")

# "Jun 2020", "June 2020", "2020"
_MONTH_YEAR = re.compile(
    r"(?P<month>[A-Za-z]{3,9})[.,]?\s+(?P<year>(?:19|20)\d{2})",
    re.IGNORECASE,
)
_YEAR = re.compile(r"(?<!\d)(?P<year>(?:19|20)\d{2})(?!\d)")
_PRESENT = re.compile(
    r"\b(present|current|now|ongoing|till\s+date|to\s+date)\b",
    re.IGNORECASE,
)
_RANGE_SEP = re.compile(r"\s*(?:–|—|-|to|until|through)\s*", re.IGNORECASE)

# Degree keywords used to recognise an education line.
_DEGREE_KEYWORDS = (
    "bachelor",
    "master",
    "doctor",
    "phd",
    "ph.d",
    "bsc",
    "b.sc",
    "b.s",
    "b.a",
    "ba ",
    "msc",
    "m.sc",
    "m.s",
    "m.a",
    "mba",
    "beng",
    "b.eng",
    "meng",
    "m.eng",
    "btech",
    "b.tech",
    "mtech",
    "m.tech",
    "bs ",
    "ms ",
    "diploma",
    "associate",
    "hnd",
    "higher national",
    "degree",
    "a-level",
    "a level",
    "gcse",
    "foundation",
    "certificate of",
    "postgraduate",
    "undergraduate",
)

_GRADE = re.compile(
    r"(?:gpa|cgpa|grade|classification)\s*[:\-]?\s*"
    r"([0-9]\.[0-9]{1,2}(?:\s*/\s*[0-9]\.?[0-9]?)?|"
    r"first(?:\s+class)?(?:\s+honou?rs)?|"
    r"second(?:\s+class)?(?:\s+honou?rs)?|"
    r"distinction|merit|pass|[0-9]{1,3}%)",
    re.IGNORECASE,
)

_FIELD_OF_STUDY = re.compile(
    r"\bin\s+([A-Z][A-Za-z&/,\- ]{2,60})",
)

# Certification issuer connectors: "AWS Certified ... - Amazon", "issued by X".
_ISSUED_BY = re.compile(r"issued\s+by\s+(.+)$", re.IGNORECASE)

# Common issuing organisations for reliable "name by/– org" splits.
_KNOWN_ISSUERS = (
    "amazon web services",
    "amazon",
    "aws",
    "microsoft",
    "google",
    "google cloud",
    "oracle",
    "cisco",
    "comptia",
    "hashicorp",
    "kubernetes",
    "cncf",
    "linux foundation",
    "red hat",
    "ibm",
    "salesforce",
    "pmi",
    "scrum alliance",
    "coursera",
    "udemy",
    "edx",
    "meta",
    "isc2",
    "(isc)2",
)


class CVProfileExtractionError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


@dataclass
class SuggestedField:
    field: str
    value: str
    evidence: str
    sensitive: bool
    auto_fill: bool
    note: str = ""


@dataclass
class SuggestedSkill:
    name: str
    evidence: str


@dataclass
class ManualSuggestion:
    category: str
    content: str
    reason: str


@dataclass
class SuggestedEducation:
    institution: str
    degree: str
    start_date: str
    end_date: str | None
    is_current: bool
    field_of_study: str | None
    grade: str | None
    description: str
    evidence: str


@dataclass
class SuggestedExperience:
    company: str
    job_title: str
    start_date: str
    end_date: str | None
    is_current: bool
    location: str | None
    description: str
    responsibilities: list[str]
    evidence: str


@dataclass
class SuggestedProject:
    name: str
    description: str
    technologies: list[str]
    features: list[str]
    project_url: str | None
    github_url: str | None
    evidence: str


@dataclass
class SuggestedCertification:
    name: str
    issuing_organization: str
    issue_date: str
    credential_id: str | None
    description: str
    evidence: str


@dataclass
class ProfileSuggestion:
    document_id: int
    extraction_version: str
    verified: bool
    fields: list[SuggestedField] = field(default_factory=list)
    skills: list[SuggestedSkill] = field(default_factory=list)
    education: list[SuggestedEducation] = field(default_factory=list)
    experience: list[SuggestedExperience] = field(default_factory=list)
    projects: list[SuggestedProject] = field(default_factory=list)
    certifications: list[SuggestedCertification] = field(
        default_factory=list
    )
    manual_review: list[ManualSuggestion] = field(default_factory=list)


def _bounded(text: str, limit: int = EVIDENCE_LIMIT) -> str:
    collapsed = " ".join(text.split())
    return collapsed[:limit]


def require_extracted_document(
    document: Document,
) -> str:
    if document.extraction_status != "completed" or not (
        document.extracted_text
    ):
        raise CVProfileExtractionError(
            "Extract the document text before pulling candidate "
            "details from it.",
        )
    return document.extracted_text


def _sections_by_type(text: str) -> dict[str, str]:
    try:
        sections = detect_sections_from_text(text)
    except CVSectionDetectionError:
        return {}

    by_type: dict[str, str] = {}
    for section in sections:
        if not section.content_text:
            continue
        existing = by_type.get(section.section_type)
        by_type[section.section_type] = (
            f"{existing}\n{section.content_text}"
            if existing
            else section.content_text
        )
    return by_type


def _first_url(text: str, needle: str) -> str | None:
    for match in URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(".,);")
        if needle in url.lower():
            return url
    return None


def _other_url(text: str) -> str | None:
    for match in URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(".,);")
        lowered = url.lower()
        if "linkedin.com" in lowered or "github.com" in lowered:
            continue
        return url
    return None


def _looks_like_name(line: str) -> bool:
    stripped = line.strip()
    if not stripped or has_contact_signal(stripped):
        return False
    if any(ch.isdigit() for ch in stripped):
        return False
    if any(sep in stripped for sep in (",", ":", "@", "/")):
        return False
    words = stripped.split()
    if not (1 < len(words) <= MAX_NAME_WORDS):
        return False
    alpha = [w for w in words if w.replace("-", "").replace(".", "").isalpha()]
    if len(alpha) < len(words):
        return False
    # Name lines are typically Title Case or ALL CAPS, not lowercase.
    return all(w[0].isupper() for w in words if w)


def _extract_name(text: str) -> tuple[str | None, str]:
    for raw in text.splitlines()[:8]:
        if _looks_like_name(raw):
            return raw.strip(), _bounded(raw)
    return None, ""


def _extract_title(text: str, name: str | None) -> tuple[str | None, str]:
    lines = [line.strip() for line in text.splitlines()[:10]]
    for line in lines:
        if not line or (name and line == name):
            continue
        if has_contact_signal(line):
            continue
        lowered = line.casefold()
        if any(keyword in lowered for keyword in TITLE_KEYWORDS):
            if len(line) <= 120 and "." not in line.rstrip("."):
                return line, _bounded(line)
    return None, ""


def _extract_location(contact_text: str) -> tuple[str | None, str]:
    for raw in contact_text.splitlines():
        line = raw.strip().strip("|").strip()
        if not line or has_contact_signal(line):
            continue
        if any(ch.isdigit() for ch in line):
            continue
        # A short comma-separated place like "London, UK".
        if "," in line and len(line) <= 80 and len(line.split()) <= 8:
            return line, _bounded(line)
    return None, ""


def _clean_skills(section_text: str) -> list[SuggestedSkill]:
    tokens: list[str] = []
    for raw_line in section_text.splitlines():
        line = re.sub(r"^[\s\-*•]+", "", raw_line).strip()
        if not line:
            continue
        for part in SKILL_SPLIT_PATTERN.split(line):
            token = part.strip().strip(".").strip()
            if token:
                tokens.append(token)

    seen: set[str] = set()
    skills: list[SuggestedSkill] = []
    for token in tokens:
        if not (1 <= len(token) <= 60):
            continue
        if len(token.split()) > 6:
            continue
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        skills.append(SuggestedSkill(name=token, evidence=_bounded(token)))
        if len(skills) >= MAX_SKILLS:
            break
    return skills


# --- Structured section parsing (deterministic, no invention) -------------


def _split_entries(section_text: str) -> list[str]:
    """Split a section into entries on blank-line boundaries.

    A blank line separates entries. Consecutive bullet lines with no
    blank line between them stay in the same entry (they describe one
    record), so we do not fragment a single job/education block.
    """
    entries: list[str] = []
    current: list[str] = []
    for raw_line in section_text.splitlines():
        if raw_line.strip():
            current.append(raw_line.rstrip())
        elif current:
            entries.append("\n".join(current))
            current = []
    if current:
        entries.append("\n".join(current))
    return [entry for entry in entries if entry.strip()]


def _is_bullet(line: str) -> bool:
    return bool(re.match(r"^\s*[\-*•▪·]\s+", line))


def _strip_bullet(line: str) -> str:
    return re.sub(r"^\s*[\-*•▪·]\s+", "", line).strip()


def _is_present(text: str) -> bool:
    return bool(_PRESENT.search(text))


def _year_to_start(year: int) -> str:
    return date(year, 1, 1).isoformat()


def _year_to_end(year: int) -> str:
    return date(year, 12, 31).isoformat()


def _parse_single_date(token: str, *, is_end: bool) -> str | None:
    """Parse one date token into ISO text, or None if no year is found.

    Month + year -> first of that month. Year only -> Jan 1 (start) or
    Dec 31 (end). Never guesses a year that is not present in the text.
    """
    month_year = _MONTH_YEAR.search(token)
    if month_year:
        month = _MONTHS.get(month_year.group("month").lower())
        year = int(month_year.group("year"))
        if month:
            return date(year, month, 1).isoformat()
        return _year_to_end(year) if is_end else _year_to_start(year)
    year_match = _YEAR.search(token)
    if year_match:
        year = int(year_match.group("year"))
        return _year_to_end(year) if is_end else _year_to_start(year)
    return None


@dataclass
class _DateSpan:
    start_date: str | None
    end_date: str | None
    is_current: bool


def _parse_date_span(text: str) -> _DateSpan:
    """Extract a start/end span from free text without inventing dates.

    Handles "2019 - 2023", "Jun 2020 - Present", and single years. When
    only one year is present it is treated as the start.
    """
    is_current = _is_present(text)

    # Prefer an explicit range near date tokens: find the segment that
    # contains at least one year and a separator.
    range_match = re.search(
        r"("
        r"(?:[A-Za-z]{3,9}[.,]?\s+)?(?:19|20)\d{2}"
        r")"
        r"\s*(?:–|—|-|to|until|through)\s*"
        r"("
        r"(?:[A-Za-z]{3,9}[.,]?\s+)?(?:19|20)\d{2}"
        r"|present|current|now|ongoing|till\s+date|to\s+date"
        r")",
        text,
        re.IGNORECASE,
    )
    if range_match:
        start = _parse_single_date(range_match.group(1), is_end=False)
        end_token = range_match.group(2)
        if _is_present(end_token):
            return _DateSpan(start_date=start, end_date=None, is_current=True)
        end = _parse_single_date(end_token, is_end=True)
        return _DateSpan(
            start_date=start,
            end_date=end,
            is_current=is_current and end is None,
        )

    # No explicit range: take the first year as the start date.
    start = _parse_single_date(text, is_end=False)
    if start is None:
        return _DateSpan(start_date=None, end_date=None, is_current=is_current)
    return _DateSpan(
        start_date=start,
        end_date=None,
        is_current=is_current,
    )


def _entry_lines(entry: str) -> tuple[list[str], list[str]]:
    """Split an entry into header lines and bullet/detail lines."""
    header: list[str] = []
    details: list[str] = []
    for line in entry.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _is_bullet(line):
            details.append(_strip_bullet(line))
        elif details:
            # Once bullets have begun, treat remaining lines as details.
            details.append(stripped)
        else:
            header.append(stripped)
    return header, details


def _split_header_parts(line: str) -> list[str]:
    """Split a header line on common separators, dropping date parenthesis."""
    without_dates = re.sub(r"\([^)]*\)", "", line)
    parts = re.split(r"\s*[|]\s*|\s+[–—-]\s+|\s*,\s*|\s+at\s+", without_dates)
    return [part.strip() for part in parts if part.strip()]


def _looks_like_degree(text: str) -> bool:
    lowered = f" {text.lower()} "
    return any(keyword in lowered for keyword in _DEGREE_KEYWORDS)


def _parse_education_entry(entry: str) -> SuggestedEducation | None:
    header, details = _entry_lines(entry)
    header_text = " ".join(header)
    span = _parse_date_span(entry)
    if span.start_date is None:
        return None

    degree: str | None = None
    institution: str | None = None
    for line in header:
        parts = _split_header_parts(line)
        for part in parts:
            if degree is None and _looks_like_degree(part):
                degree = part
            elif institution is None and (
                "universit" in part.lower()
                or "college" in part.lower()
                or "institute" in part.lower()
                or "school" in part.lower()
                or "academy" in part.lower()
            ):
                institution = part
    # Fall back: if exactly two parts on the degree line and one looks
    # like a degree, the other is the institution.
    if degree is not None and institution is None:
        for line in header:
            parts = _split_header_parts(line)
            remaining = [p for p in parts if p != degree]
            if len(remaining) == 1:
                institution = remaining[0]
                break

    if not degree or not institution:
        return None

    grade_match = _GRADE.search(header_text)
    grade = grade_match.group(1).strip() if grade_match else None

    field_of_study: str | None = None
    field_match = _FIELD_OF_STUDY.search(degree)
    if field_match:
        candidate_field = field_match.group(1).strip(" ,")
        if candidate_field:
            field_of_study = candidate_field

    return SuggestedEducation(
        institution=institution[:250],
        degree=degree[:250],
        start_date=span.start_date,
        end_date=span.end_date,
        is_current=span.is_current,
        field_of_study=field_of_study[:250] if field_of_study else None,
        grade=grade[:100] if grade else None,
        description=_join_details(details),
        evidence=_bounded(entry),
    )


def _join_details(details: list[str], limit: int = DESCRIPTION_LIMIT) -> str:
    text = "\n".join(details).strip()
    return text[:limit]


def _parse_experience_entry(entry: str) -> SuggestedExperience | None:
    header, details = _entry_lines(entry)
    span = _parse_date_span(entry)
    if span.start_date is None:
        return None
    if not header:
        return None

    # The first header line carries company + title (+ dates removed).
    first_line = header[0]
    parts = _split_header_parts(first_line)
    if len(parts) < 2:
        # Company on one line, title on next, or vice versa.
        if len(header) >= 2:
            parts = [
                _split_header_parts(header[0])[0]
                if _split_header_parts(header[0])
                else header[0],
                _split_header_parts(header[1])[0]
                if _split_header_parts(header[1])
                else header[1],
            ]
        else:
            return None

    title_idx = next(
        (
            index
            for index, part in enumerate(parts)
            if any(kw in part.lower() for kw in TITLE_KEYWORDS)
        ),
        None,
    )
    if title_idx is None:
        return None
    job_title = parts[title_idx]
    other = [p for i, p in enumerate(parts) if i != title_idx]
    if not other:
        return None
    company = other[0]

    body_lines: list[str] = []
    body_lines.extend(details)
    for extra in header[1:]:
        if extra and extra not in (company, job_title):
            body_lines.append(extra)

    return SuggestedExperience(
        company=company[:250],
        job_title=job_title[:250],
        start_date=span.start_date,
        end_date=span.end_date,
        is_current=span.is_current,
        location=None,
        description=_join_details(body_lines),
        responsibilities=[d for d in details if d][:20],
        evidence=_bounded(entry),
    )


def _parse_project_entry(entry: str) -> SuggestedProject | None:
    header, details = _entry_lines(entry)
    if not header:
        return None

    name_line = header[0]
    parts = _split_header_parts(name_line)
    name = parts[0] if parts else name_line.strip()
    name = re.sub(r"\([^)]*\)", "", name).strip(" .:-")
    if not name or len(name) > 250:
        return None

    description_parts: list[str] = []
    # Remaining header text after the name becomes description context.
    if len(parts) > 1:
        description_parts.append(", ".join(parts[1:]))
    description_parts.extend(header[1:])
    description_parts.extend(details)
    description = _join_details(description_parts)
    if not description.strip():
        return None

    technologies: list[str] = []
    tech_match = re.search(
        r"(?:technologies|tech\s*stack|stack|built\s+with|tools)\s*[:\-]\s*(.+)",
        entry,
        re.IGNORECASE,
    )
    if tech_match:
        for token in SKILL_SPLIT_PATTERN.split(tech_match.group(1)):
            cleaned = token.strip().strip(".").strip()
            if cleaned and len(cleaned) <= 60:
                technologies.append(cleaned)

    project_url = _first_url(entry, "http") if "http" in entry else None
    github_url = _first_url(entry, "github.com")

    return SuggestedProject(
        name=name[:250],
        description=description,
        technologies=technologies[:30],
        features=[],
        project_url=(
            project_url
            if project_url and "github.com" not in project_url.lower()
            else None
        ),
        github_url=github_url,
        evidence=_bounded(entry),
    )


def _parse_certification_entry(entry: str) -> SuggestedCertification | None:
    header, details = _entry_lines(entry)
    if not header:
        return None
    span = _parse_date_span(entry)
    if span.start_date is None:
        return None

    first_line = header[0]
    name: str | None = None
    organization: str | None = None

    issued_by = _ISSUED_BY.search(entry)
    without_dates = re.sub(r"\([^)]*\)", "", first_line).strip()

    if issued_by:
        organization = re.sub(
            r"\([^)]*\)", "", issued_by.group(1)
        ).strip(" .,")
        name = re.split(
            r"\s*[–—-]\s*|\s*\bissued\b", without_dates, flags=re.IGNORECASE
        )[0].strip(" .,")
    else:
        parts = re.split(r"\s+[–—|]\s+|\s+-\s+", without_dates)
        parts = [p.strip(" .,") for p in parts if p.strip()]
        if len(parts) >= 2:
            name = parts[0]
            organization = parts[-1]
        elif len(parts) == 1:
            # Try to recognise a known issuer embedded in the name.
            lowered = parts[0].lower()
            for issuer in _KNOWN_ISSUERS:
                if issuer in lowered:
                    organization = issuer.upper() if len(issuer) <= 4 else (
                        issuer.title()
                    )
                    name = parts[0]
                    break

    if not name or not organization:
        return None
    if len(name) > 250 or len(organization) > 250:
        return None

    return SuggestedCertification(
        name=name[:250],
        issuing_organization=organization[:250],
        issue_date=span.start_date,
        credential_id=None,
        description=_join_details(details),
        evidence=_bounded(entry),
    )


def _parse_structured_sections(
    suggestion: ProfileSuggestion,
    sections: dict[str, str],
) -> None:
    """Fill structured lists; unparseable entries go to manual_review."""
    parsers = (
        ("education", _parse_education_entry, suggestion.education),
        ("work_experience", _parse_experience_entry, suggestion.experience),
        ("projects", _parse_project_entry, suggestion.projects),
        (
            "certifications",
            _parse_certification_entry,
            suggestion.certifications,
        ),
    )
    manual_labels = {
        "work_experience": "work_experience",
        "education": "education",
        "projects": "projects",
        "certifications": "certifications",
    }

    for section_type, parser, target in parsers:
        content = sections.get(section_type)
        if not content or not content.strip():
            continue
        unparsed: list[str] = []
        for entry in _split_entries(content):
            if len(target) >= MAX_STRUCTURED_ENTRIES:
                unparsed.append(entry)
                continue
            parsed = parser(entry)
            if parsed is None:
                unparsed.append(entry)
            else:
                target.append(parsed)
        if unparsed:
            suggestion.manual_review.append(
                ManualSuggestion(
                    category=manual_labels[section_type],
                    content="\n\n".join(unparsed).strip()[
                        :MANUAL_CONTENT_LIMIT
                    ],
                    reason=(
                        "Required fields (e.g. dates, titles, "
                        "institution/organisation) were not clearly "
                        "present, so these entries were left for manual "
                        "review rather than guessed."
                    ),
                )
            )


def build_profile_suggestion(
    document: Document,
) -> ProfileSuggestion:
    text = require_extracted_document(document)
    sections = _sections_by_type(text)

    contact_text = sections.get("contact", "") or text[:600]
    header_text = text[:1200]

    suggestion = ProfileSuggestion(
        document_id=document.id,
        extraction_version=EXTRACTION_VERSION,
        verified=False,
    )

    # --- Non-sensitive profile fields (auto-fillable, unverified) ---
    name, name_evidence = _extract_name(header_text)
    if name:
        suggestion.fields.append(
            SuggestedField(
                field="full_name",
                value=name,
                evidence=name_evidence,
                sensitive=False,
                auto_fill=True,
            )
        )

    email_match = EMAIL_PATTERN.search(contact_text) or EMAIL_PATTERN.search(
        text
    )
    if email_match:
        email = email_match.group(0)
        suggestion.fields.append(
            SuggestedField(
                field="email",
                value=email,
                evidence=_bounded(email),
                sensitive=False,
                auto_fill=True,
            )
        )

    title, title_evidence = _extract_title(header_text, name)
    if title:
        suggestion.fields.append(
            SuggestedField(
                field="professional_title",
                value=title,
                evidence=title_evidence,
                sensitive=False,
                auto_fill=True,
            )
        )

    summary_text = sections.get("summary")
    if summary_text and summary_text.strip():
        suggestion.fields.append(
            SuggestedField(
                field="professional_summary",
                value=summary_text.strip()[:SUMMARY_LIMIT],
                evidence=_bounded(summary_text),
                sensitive=False,
                auto_fill=True,
            )
        )

    for field_name, needle in (
        ("linkedin_url", "linkedin.com"),
        ("github_url", "github.com"),
    ):
        url = _first_url(text, needle)
        if url:
            suggestion.fields.append(
                SuggestedField(
                    field=field_name,
                    value=url if url.startswith("http") else f"https://{url}",
                    evidence=_bounded(url),
                    sensitive=False,
                    auto_fill=True,
                )
            )

    portfolio = _other_url(text)
    if portfolio:
        suggestion.fields.append(
            SuggestedField(
                field="portfolio_url",
                value=(
                    portfolio
                    if portfolio.startswith("http")
                    else f"https://{portfolio}"
                ),
                evidence=_bounded(portfolio),
                sensitive=False,
                auto_fill=True,
            )
        )

    # --- Sensitive/personal fields (manual review only) ---
    phone_match = PHONE_PATTERN.search(contact_text) or PHONE_PATTERN.search(
        header_text
    )
    if phone_match:
        phone = phone_match.group(0).strip()
        suggestion.fields.append(
            SuggestedField(
                field="phone",
                value=phone,
                evidence=_bounded(phone),
                sensitive=True,
                auto_fill=False,
                note="Personal contact detail — confirm manually.",
            )
        )

    location, location_evidence = _extract_location(contact_text)
    if location:
        suggestion.fields.append(
            SuggestedField(
                field="location",
                value=location,
                evidence=location_evidence,
                sensitive=True,
                auto_fill=False,
                note="Personal location — confirm manually.",
            )
        )

    # --- Skills (auto-fillable, unverified) ---
    skills_text = sections.get("skills")
    if skills_text:
        suggestion.skills = _clean_skills(skills_text)

    # --- Structured history: real parsing, manual review as fallback ---
    # Education, work experience, projects, and certifications are parsed
    # into structured draft records. An entry is only turned into a draft
    # when its required fields are clearly present in the text; otherwise
    # it stays in manual_review so nothing (dates, titles, employers,
    # institutions, organisations) is ever guessed.
    _parse_structured_sections(suggestion, sections)

    return suggestion


# --- Apply ----------------------------------------------------------------


AUTO_PROFILE_FIELDS = (
    "full_name",
    "email",
    "professional_title",
    "professional_summary",
    "linkedin_url",
    "github_url",
    "portfolio_url",
)
SENSITIVE_PROFILE_FIELDS = ("phone", "location")
REQUIRED_PROFILE_FIELDS = ("full_name", "email")


def _existing_skill_names(
    database: Session,
    candidate_profile_id: int,
) -> set[str]:
    names = database.scalars(
        select(Skill.name).where(
            Skill.candidate_profile_id == candidate_profile_id
        )
    ).all()
    return {name.casefold() for name in names}


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _existing_keys(
    database: Session,
    model: object,
    columns: tuple[object, ...],
    candidate_profile_id: int,
) -> set[tuple[str, ...]]:
    rows = database.execute(
        select(*columns).where(
            model.candidate_profile_id == candidate_profile_id
        )
    ).all()
    return {
        tuple((value or "").casefold().strip() for value in row) for row in rows
    }


def _apply_education(
    database: Session,
    candidate_profile_id: int,
    entries: list[SuggestedEducation],
) -> list[str]:
    existing = _existing_keys(
        database,
        Education,
        (Education.institution, Education.degree),
        candidate_profile_id,
    )
    added: list[str] = []
    for entry in entries:
        start = _parse_iso_date(entry.start_date)
        if start is None:
            continue
        key = (entry.institution.casefold().strip(), entry.degree.casefold().strip())
        if key in existing:
            continue
        existing.add(key)
        database.add(
            Education(
                candidate_profile_id=candidate_profile_id,
                institution=entry.institution,
                degree=entry.degree,
                field_of_study=entry.field_of_study,
                start_date=start,
                end_date=_parse_iso_date(entry.end_date),
                grade=entry.grade,
                description=entry.description or None,
                is_current=entry.is_current,
                verified=False,
            )
        )
        added.append(f"{entry.degree} — {entry.institution}")
    return added


def _apply_experience(
    database: Session,
    candidate_profile_id: int,
    entries: list[SuggestedExperience],
) -> list[str]:
    existing = _existing_keys(
        database,
        Experience,
        (Experience.company, Experience.job_title),
        candidate_profile_id,
    )
    added: list[str] = []
    for entry in entries:
        start = _parse_iso_date(entry.start_date)
        if start is None:
            continue
        key = (
            entry.company.casefold().strip(),
            entry.job_title.casefold().strip(),
        )
        if key in existing:
            continue
        existing.add(key)
        database.add(
            Experience(
                candidate_profile_id=candidate_profile_id,
                company=entry.company,
                job_title=entry.job_title,
                location=entry.location,
                start_date=start,
                end_date=_parse_iso_date(entry.end_date),
                is_current=entry.is_current,
                description=entry.description or None,
                responsibilities=entry.responsibilities,
                achievements=[],
                technologies=[],
                verified=False,
            )
        )
        added.append(f"{entry.job_title} — {entry.company}")
    return added


def _apply_projects(
    database: Session,
    candidate_profile_id: int,
    entries: list[SuggestedProject],
) -> list[str]:
    existing = _existing_keys(
        database,
        Project,
        (Project.name,),
        candidate_profile_id,
    )
    added: list[str] = []
    for entry in entries:
        if not entry.description.strip():
            continue
        key = (entry.name.casefold().strip(),)
        if key in existing:
            continue
        existing.add(key)
        database.add(
            Project(
                candidate_profile_id=candidate_profile_id,
                name=entry.name,
                description=entry.description,
                project_url=entry.project_url,
                github_url=entry.github_url,
                technologies=entry.technologies,
                features=entry.features,
                achievements=[],
                verified=False,
            )
        )
        added.append(entry.name)
    return added


def _apply_certifications(
    database: Session,
    candidate_profile_id: int,
    entries: list[SuggestedCertification],
) -> list[str]:
    existing = _existing_keys(
        database,
        Certification,
        (Certification.name, Certification.issuing_organization),
        candidate_profile_id,
    )
    added: list[str] = []
    for entry in entries:
        issue = _parse_iso_date(entry.issue_date)
        if issue is None:
            continue
        key = (
            entry.name.casefold().strip(),
            entry.issuing_organization.casefold().strip(),
        )
        if key in existing:
            continue
        existing.add(key)
        database.add(
            Certification(
                candidate_profile_id=candidate_profile_id,
                name=entry.name,
                issuing_organization=entry.issuing_organization,
                credential_id=entry.credential_id,
                issue_date=issue,
                description=entry.description or None,
                skills=[],
                verified=False,
            )
        )
        added.append(f"{entry.name} — {entry.issuing_organization}")
    return added


def apply_profile_suggestion(
    document: Document,
    database: Session,
    candidate_profile_id: int,
    *,
    apply_profile: bool = True,
    apply_skills: bool = True,
    apply_education: bool = True,
    apply_experience: bool = True,
    apply_projects: bool = True,
    apply_certifications: bool = True,
    include_sensitive: bool = False,
    overwrite: bool = False,
) -> dict[str, object]:
    suggestion = build_profile_suggestion(document)

    fields_by_name = {item.field: item for item in suggestion.fields}
    applied_fields: list[str] = []
    skipped_fields: list[str] = []

    profile = database.get(CandidateProfile, candidate_profile_id)
    if profile is None:
        raise CVProfileExtractionError(
            "No candidate profile exists for this account.",
            status_code=404,
        )

    if apply_profile:
        candidate_fields = list(AUTO_PROFILE_FIELDS)
        if include_sensitive:
            candidate_fields += list(SENSITIVE_PROFILE_FIELDS)

        for field_name in candidate_fields:
            item = fields_by_name.get(field_name)
            if item is None:
                continue
            if field_name in applied_fields:
                continue
            current = getattr(profile, field_name, None)
            if current and not overwrite:
                skipped_fields.append(field_name)
                continue
            setattr(profile, field_name, item.value)
            applied_fields.append(field_name)

        # Applied data comes from the CV and is unverified until the
        # candidate confirms it.
        if applied_fields:
            profile.facts_verified = False

    added_skills: list[str] = []
    if apply_skills and suggestion.skills:
        existing = _existing_skill_names(database, candidate_profile_id)
        for skill in suggestion.skills:
            key = skill.name.casefold()
            if key in existing:
                continue
            existing.add(key)
            database.add(
                Skill(
                    candidate_profile_id=candidate_profile_id,
                    name=skill.name,
                    verified=False,
                )
            )
            added_skills.append(skill.name)

    added_education: list[str] = []
    if apply_education and suggestion.education:
        added_education = _apply_education(
            database, candidate_profile_id, suggestion.education
        )

    added_experience: list[str] = []
    if apply_experience and suggestion.experience:
        added_experience = _apply_experience(
            database, candidate_profile_id, suggestion.experience
        )

    added_projects: list[str] = []
    if apply_projects and suggestion.projects:
        added_projects = _apply_projects(
            database, candidate_profile_id, suggestion.projects
        )

    added_certifications: list[str] = []
    if apply_certifications and suggestion.certifications:
        added_certifications = _apply_certifications(
            database, candidate_profile_id, suggestion.certifications
        )

    # Any structured draft created from the CV is unverified, so the
    # profile's verified state must reflect that new unverified data.
    if (
        added_education
        or added_experience
        or added_projects
        or added_certifications
    ):
        profile.facts_verified = False

    database.commit()

    return {
        "document_id": document.id,
        "verified": False,
        "applied_fields": applied_fields,
        "skipped_existing_fields": skipped_fields,
        "added_skills": added_skills,
        "added_education": added_education,
        "added_experience": added_experience,
        "added_projects": added_projects,
        "added_certifications": added_certifications,
        "manual_review": [
            {"category": m.category, "reason": m.reason}
            for m in suggestion.manual_review
        ]
        + [
            {"field": item.field, "reason": item.note or "Manual review."}
            for item in suggestion.fields
            if item.sensitive and not include_sensitive
        ],
    }
