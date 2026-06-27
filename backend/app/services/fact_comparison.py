from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from hashlib import sha256

from app.models.candidate_profile import CandidateProfile
from app.models.certification import Certification
from app.models.cv_section import CVSection
from app.models.document import Document
from app.models.education import Education
from app.models.experience import Experience
from app.models.project import Project
from app.models.skill import Skill


COMPARISON_VERSION = "deterministic_fact_comparison_v1"
CV_EVIDENCE_LIMIT = 500
VERIFIED_EVIDENCE_LIMIT = 500
NORMALIZED_VALUE_LIMIT = 600
EXPLANATION_LIMIT = 500

EMAIL_PATTERN = re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)"
)
URL_PATTERN = re.compile(
    r"\b(?:https?://|www\.|linkedin\.com|github\.com)[^\s,;]+",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
CURRENT_DATE_WORDS = {"present", "current", "now"}
ORG_SUFFIXES = {"ltd", "limited", "inc", "llc"}
MONTH_PATTERN = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
    r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|"
    r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
DATE_YEAR_COMPONENT = rf"(?:{MONTH_PATTERN}\s+)?(?:19|20)\d{{2}}"
CURRENT_DATE_COMPONENT = r"(?:present|current|now)"
DATE_COMPONENT = rf"(?:{DATE_YEAR_COMPONENT}|{CURRENT_DATE_COMPONENT})"
DATE_RANGE_PATTERN = re.compile(
    rf"\b{DATE_COMPONENT}\b\s*(?:-|to|through|until)\s*"
    rf"\b{DATE_COMPONENT}\b",
    re.IGNORECASE,
)
LABELLED_DATE_PATTERN = re.compile(
    r"^\s*(?:dates?|period|start(?: date)?|end(?: date)?)\s*:",
    re.IGNORECASE,
)
START_DATE_LABEL_PATTERN = re.compile(
    r"^\s*start(?: date)?\s*:",
    re.IGNORECASE,
)
END_DATE_LABEL_PATTERN = re.compile(
    r"^\s*end(?: date)?\s*:",
    re.IGNORECASE,
)

ENTITY_ORDER = {
    "candidate_profile": 0,
    "education": 1,
    "work_experience": 2,
    "project": 3,
    "skill": 4,
    "certification": 5,
}
FINDING_ORDER = {
    "confirmed": 0,
    "possible_mismatch": 1,
    "date_conflict": 2,
    "organisation_conflict": 3,
    "skill_conflict": 4,
    "manual_review": 5,
    "missing_verified_fact": 6,
    "unverified_claim": 7,
}


@dataclass(frozen=True)
class FindingDraft:
    document_section_id: int | None
    entity_type: str
    verified_entity_id: int | None
    field_name: str | None
    finding_type: str
    cv_value: str | None
    verified_value: str | None
    normalized_cv_value: str | None
    normalized_verified_value: str | None
    confidence: float
    severity: str
    explanation: str
    requires_manual_review: bool


@dataclass(frozen=True)
class ComparisonFinding:
    document_section_id: int | None
    sort_order: int
    entity_type: str
    verified_entity_id: int | None
    field_name: str | None
    finding_type: str
    cv_value: str | None
    verified_value: str | None
    normalized_cv_value: str | None
    normalized_verified_value: str | None
    confidence: float
    severity: str
    explanation: str
    requires_manual_review: bool
    dedupe_key: str


@dataclass(frozen=True)
class ComparisonResult:
    status: str
    findings: list[ComparisonFinding]
    total_findings: int
    confirmed_count: int
    mismatch_count: int
    missing_verified_count: int
    unverified_claim_count: int
    manual_review_count: int
    comparison_version: str


@dataclass(frozen=True)
class DateEvidence:
    text: str
    years: set[str]
    has_current_marker: bool
    is_ambiguous: bool


class FactComparisonError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.safe_message = message


def bounded(
    value: str | None,
    limit: int,
) -> str | None:
    if value is None:
        return None

    cleaned = re.sub(r"\s+", " ", value).strip()

    if len(cleaned) <= limit:
        return cleaned

    return f"{cleaned[: limit - 3]}..."


def normalize_unicode(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    return (
        value.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u00a0", " ")
    )


def normalize_text_value(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = normalize_unicode(value).casefold()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9+#]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return bounded(normalized, NORMALIZED_VALUE_LIMIT)


def normalize_url(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = normalize_unicode(value).casefold().strip()
    normalized = re.sub(r"^https?://", "", normalized)
    normalized = re.sub(r"^www\.", "", normalized)
    normalized = normalized.split("#", 1)[0].split("?", 1)[0]
    normalized = normalized.rstrip("/")

    return bounded(normalized, NORMALIZED_VALUE_LIMIT)


def normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None

    digits = re.sub(r"\D+", "", value)

    if digits.startswith("00"):
        digits = digits[2:]

    return bounded(digits, NORMALIZED_VALUE_LIMIT)


def normalize_organisation(value: str | None) -> str | None:
    normalized = normalize_text_value(value)

    if normalized is None:
        return None

    parts = normalized.split()

    while parts and parts[-1] in ORG_SUFFIXES:
        parts.pop()

    return bounded(" ".join(parts), NORMALIZED_VALUE_LIMIT)


def normalize_skill(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = normalize_unicode(value).casefold()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9+#]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return bounded(normalized, NORMALIZED_VALUE_LIMIT)


def normalize_descriptive_evidence(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = normalize_unicode(value)
    cleaned = re.sub(r"^\s*[-*\u2022]\s*", "", cleaned).strip()

    return normalize_text_value(cleaned)


def descriptive_line_matches(
    line: str,
    verified_values: list[str],
) -> bool:
    normalized_line = normalize_descriptive_evidence(line)

    if not normalized_line:
        return False

    return normalized_line in {
        normalized
        for value in verified_values
        if (normalized := normalize_descriptive_evidence(value))
    }


def collect_verified_work_descriptions(
    records: list[Experience],
) -> list[str]:
    values: list[str] = []

    for record in records:
        for value in [
            record.description,
            *record.responsibilities,
            *record.achievements,
        ]:
            if value:
                values.append(value)

    return values


def collect_verified_project_descriptions(
    records: list[Project],
) -> list[str]:
    values: list[str] = []

    for record in records:
        for value in [
            record.description,
            *record.features,
            *record.achievements,
        ]:
            if value:
                values.append(value)

    return values


def phrase_contains(
    normalized_haystack: str | None,
    normalized_needle: str | None,
) -> bool:
    if not normalized_haystack or not normalized_needle:
        return False

    return f" {normalized_needle} " in f" {normalized_haystack} "


def phone_matches(
    cv_value: str | None,
    verified_value: str | None,
) -> bool:
    cv_normalized = normalize_phone(cv_value)
    verified_normalized = normalize_phone(verified_value)

    if not cv_normalized or not verified_normalized:
        return False

    if cv_normalized == verified_normalized:
        return True

    return (
        len(cv_normalized) >= 7
        and len(verified_normalized) >= 7
        and (
            cv_normalized.endswith(verified_normalized)
            or verified_normalized.endswith(cv_normalized)
        )
    )


def section_text(
    sections: list[CVSection],
    section_types: set[str],
) -> str:
    return "\n".join(
        section.content_text
        for section in sections
        if section.section_type in section_types
    )


def sections_by_type(
    sections: list[CVSection],
    section_types: set[str],
) -> list[CVSection]:
    return [
        section
        for section in sections
        if section.section_type in section_types
    ]


def all_text(sections: list[CVSection]) -> str:
    return "\n".join(section.content_text for section in sections)


def line_candidates(section: CVSection) -> list[str]:
    candidates: list[str] = []

    for line in section.content_text.splitlines():
        cleaned = line.strip()
        cleaned = re.sub(r"^[-*\u2022]\s*", "", cleaned).strip()

        if cleaned:
            candidates.append(cleaned)

    return candidates


def find_evidence(
    sections: list[CVSection],
    value: str | None,
    normalizer: object,
) -> tuple[CVSection | None, str | None, str | None]:
    if value is None:
        return None, None, None

    normalize = normalizer  # Keeps call sites readable with typed callables.
    normalized_value = normalize(value)  # type: ignore[operator]

    if not normalized_value:
        return None, None, normalized_value

    for section in sections:
        for line in line_candidates(section):
            normalized_line = normalize(line)  # type: ignore[operator]

            if phrase_contains(normalized_line, normalized_value):
                return section, bounded(line, CV_EVIDENCE_LIMIT), (
                    normalized_line
                )

        normalized_section = normalize(section.content_text)  # type: ignore[operator]

        if phrase_contains(normalized_section, normalized_value):
            return section, bounded(value, CV_EVIDENCE_LIMIT), (
                normalized_value
            )

    return None, None, normalized_value


def find_url_evidence(
    sections: list[CVSection],
    value: str | None,
) -> tuple[CVSection | None, str | None, str | None]:
    normalized_value = normalize_url(value)

    if not normalized_value:
        return None, None, normalized_value

    for section in sections:
        for match in URL_PATTERN.finditer(section.content_text):
            cv_value = match.group(0).rstrip(").]")
            normalized_cv = normalize_url(cv_value)

            if normalized_cv == normalized_value:
                return section, bounded(cv_value, CV_EVIDENCE_LIMIT), (
                    normalized_cv
                )

    return None, None, normalized_value


def find_phone_evidence(
    sections: list[CVSection],
    value: str | None,
) -> tuple[CVSection | None, str | None, str | None]:
    normalized_value = normalize_phone(value)

    if not normalized_value:
        return None, None, normalized_value

    for section in sections:
        for match in PHONE_PATTERN.finditer(section.content_text):
            cv_value = match.group(0)

            if phone_matches(cv_value, value):
                return section, bounded(cv_value, CV_EVIDENCE_LIMIT), (
                    normalize_phone(cv_value)
                )

    return None, None, normalized_value


def add_confirmed_or_missing(
    findings: list[FindingDraft],
    *,
    sections: list[CVSection],
    entity_type: str,
    verified_entity_id: int | None,
    field_name: str,
    verified_value: str | None,
    normalizer: object = normalize_text_value,
    explanation_subject: str,
) -> bool:
    if verified_value is None:
        return False

    if normalizer == normalize_url:
        section, cv_value, normalized_cv = find_url_evidence(
            sections,
            verified_value,
        )
        normalized_verified = normalize_url(verified_value)
    elif normalizer == normalize_phone:
        section, cv_value, normalized_cv = find_phone_evidence(
            sections,
            verified_value,
        )
        normalized_verified = normalize_phone(verified_value)
    else:
        section, cv_value, normalized_cv = find_evidence(
            sections,
            verified_value,
            normalizer,
        )
        normalized_verified = normalizer(verified_value)  # type: ignore[operator]

    if cv_value is not None:
        findings.append(
            make_draft(
                document_section_id=section.id if section else None,
                entity_type=entity_type,
                verified_entity_id=verified_entity_id,
                field_name=field_name,
                finding_type="confirmed",
                cv_value=cv_value,
                verified_value=verified_value,
                normalized_cv_value=normalized_cv,
                normalized_verified_value=normalized_verified,
                confidence=0.96,
                severity="info",
                explanation=(
                    f"{explanation_subject} matched the verified vault value."
                ),
                requires_manual_review=False,
            )
        )
        return True

    findings.append(
        make_draft(
            document_section_id=None,
            entity_type=entity_type,
            verified_entity_id=verified_entity_id,
            field_name=field_name,
            finding_type="missing_verified_fact",
            cv_value=None,
            verified_value=verified_value,
            normalized_cv_value=None,
            normalized_verified_value=normalized_verified,
            confidence=0.82,
            severity="info",
            explanation=(
                f"{explanation_subject} is verified in the vault but was not "
                "deterministically found in the CV. It may be intentionally "
                "omitted."
            ),
            requires_manual_review=False,
        )
    )
    return False


def make_draft(
    *,
    document_section_id: int | None,
    entity_type: str,
    verified_entity_id: int | None,
    field_name: str | None,
    finding_type: str,
    cv_value: str | None,
    verified_value: str | None,
    normalized_cv_value: str | None,
    normalized_verified_value: str | None,
    confidence: float,
    severity: str,
    explanation: str,
    requires_manual_review: bool,
) -> FindingDraft:
    return FindingDraft(
        document_section_id=document_section_id,
        entity_type=entity_type,
        verified_entity_id=verified_entity_id,
        field_name=field_name,
        finding_type=finding_type,
        cv_value=bounded(cv_value, CV_EVIDENCE_LIMIT),
        verified_value=bounded(verified_value, VERIFIED_EVIDENCE_LIMIT),
        normalized_cv_value=bounded(
            normalized_cv_value,
            NORMALIZED_VALUE_LIMIT,
        ),
        normalized_verified_value=bounded(
            normalized_verified_value,
            NORMALIZED_VALUE_LIMIT,
        ),
        confidence=round(min(1.0, max(0.0, confidence)), 2),
        severity=severity,
        explanation=bounded(explanation, EXPLANATION_LIMIT) or "",
        requires_manual_review=requires_manual_review,
    )


def context_for_record(
    sections: list[CVSection],
    anchors: list[str | None],
    normalizer: object = normalize_text_value,
) -> tuple[CVSection | None, str]:
    normalized_anchors = [
        normalizer(anchor)  # type: ignore[operator]
        for anchor in anchors
        if anchor
    ]
    normalized_anchors = [
        anchor for anchor in normalized_anchors if anchor
    ]

    for section in sections:
        lines = line_candidates(section)

        for index, line in enumerate(lines):
            normalized_line = normalizer(line)  # type: ignore[operator]

            if any(
                phrase_contains(normalized_line, anchor)
                for anchor in normalized_anchors
            ):
                start = max(0, index - 1)
                end = min(len(lines), index + 3)
                return section, "\n".join(lines[start:end])

    return (sections[0], sections[0].content_text) if sections else (None, "")


def safe_date_range_text(line: str) -> str | None:
    normalized_line = normalize_unicode(line)
    match = DATE_RANGE_PATTERN.search(normalized_line)

    return bounded(match.group(0), CV_EVIDENCE_LIMIT) if match else None


def labelled_date_text(line: str) -> str | None:
    normalized_line = normalize_unicode(line)

    if not LABELLED_DATE_PATTERN.search(normalized_line):
        return None

    if not YEAR_PATTERN.search(normalized_line) and not any(
        f" {word} " in f" {normalize_text_value(normalized_line) or ''} "
        for word in CURRENT_DATE_WORDS
    ):
        return None

    return bounded(normalized_line, CV_EVIDENCE_LIMIT)


def build_date_evidence(text: str, *, is_ambiguous: bool) -> DateEvidence:
    normalized_text = normalize_text_value(text) or ""

    return DateEvidence(
        text=text,
        years=set(YEAR_PATTERN.findall(text)),
        has_current_marker=any(
            f" {word} " in f" {normalized_text} "
            for word in CURRENT_DATE_WORDS
        ),
        is_ambiguous=is_ambiguous,
    )


def extract_date_evidence_from_line(line: str) -> DateEvidence | None:
    range_text = safe_date_range_text(line)

    if range_text is not None:
        return build_date_evidence(range_text, is_ambiguous=False)

    label_text = labelled_date_text(line)

    if label_text is not None:
        return build_date_evidence(label_text, is_ambiguous=True)

    return None


def date_evidence_from_context(context: str) -> list[DateEvidence]:
    evidence: list[DateEvidence] = []
    labelled_start: str | None = None
    labelled_end: str | None = None

    for line in context.splitlines():
        cleaned = line.strip()

        if not cleaned:
            continue

        if START_DATE_LABEL_PATTERN.search(cleaned):
            labelled_start = cleaned
        elif END_DATE_LABEL_PATTERN.search(cleaned):
            labelled_end = cleaned

        line_evidence = extract_date_evidence_from_line(cleaned)

        if line_evidence is not None:
            evidence.append(line_evidence)

    if labelled_start is not None and labelled_end is not None:
        evidence.insert(
            0,
            build_date_evidence(
                f"{labelled_start} - {labelled_end}",
                is_ambiguous=False,
            ),
        )

    return evidence


def is_date_like_line(line: str) -> bool:
    return extract_date_evidence_from_line(line) is not None


def date_evidence_matches(
    evidence: DateEvidence,
    *,
    start_date: date | None,
    end_date: date | None,
    is_current: bool,
) -> bool:
    expected_start = str(start_date.year) if start_date is not None else None
    expected_end = str(end_date.year) if end_date is not None else None
    start_matches = expected_start is None or expected_start in evidence.years

    if is_current:
        end_matches = evidence.has_current_marker
    elif expected_end is not None:
        end_matches = (
            expected_end in evidence.years and not evidence.has_current_marker
        )
    else:
        end_matches = not evidence.has_current_marker

    return start_matches and end_matches


def date_evidence_status(
    *,
    start_date: date | None,
    end_date: date | None,
    is_current: bool,
    context: str,
) -> tuple[str, str | None, float]:
    if start_date is None and end_date is None and not is_current:
        return "missing", None, 0.0

    evidences = date_evidence_from_context(context)
    clear_evidences = [
        evidence for evidence in evidences if not evidence.is_ambiguous
    ]
    ambiguous_evidences = [
        evidence for evidence in evidences if evidence.is_ambiguous
    ]

    for evidence in clear_evidences:
        if date_evidence_matches(
            evidence,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
        ):
            return "confirmed", evidence.text, 0.91

    if clear_evidences:
        return "conflict", clear_evidences[0].text, 0.78

    if ambiguous_evidences:
        return "manual_review", ambiguous_evidences[0].text, 0.62

    return "missing", None, 0.72


def verified_date_value(
    start_date: date | None,
    end_date: date | None,
    is_current: bool,
) -> str:
    start_value = start_date.isoformat() if start_date is not None else ""
    end_value = "present" if is_current else (
        end_date.isoformat() if end_date is not None else ""
    )

    return " - ".join(part for part in [start_value, end_value] if part)


def add_date_finding(
    findings: list[FindingDraft],
    *,
    section: CVSection | None,
    entity_type: str,
    verified_entity_id: int,
    start_date: date | None,
    end_date: date | None,
    is_current: bool,
    context: str,
    explanation_subject: str,
) -> None:
    status, cv_value, confidence = date_evidence_status(
        start_date=start_date,
        end_date=end_date,
        is_current=is_current,
        context=context,
    )
    verified_value = verified_date_value(
        start_date,
        end_date,
        is_current,
    )

    if not verified_value:
        return

    if status == "confirmed":
        findings.append(
            make_draft(
                document_section_id=section.id if section else None,
                entity_type=entity_type,
                verified_entity_id=verified_entity_id,
                field_name="dates",
                finding_type="confirmed",
                cv_value=cv_value,
                verified_value=verified_value,
                normalized_cv_value=normalize_text_value(cv_value),
                normalized_verified_value=normalize_text_value(
                    verified_value,
                ),
                confidence=confidence,
                severity="info",
                explanation=(
                    f"{explanation_subject} dates matched the verified "
                    "vault dates."
                ),
                requires_manual_review=False,
            )
        )
        return

    if status == "conflict":
        findings.append(
            make_draft(
                document_section_id=section.id if section else None,
                entity_type=entity_type,
                verified_entity_id=verified_entity_id,
                field_name="dates",
                finding_type="date_conflict",
                cv_value=cv_value,
                verified_value=verified_value,
                normalized_cv_value=normalize_text_value(cv_value),
                normalized_verified_value=normalize_text_value(
                    verified_value,
                ),
                confidence=confidence,
                severity="warning",
                explanation=(
                    f"{explanation_subject} contains date evidence that does "
                    "not match the verified vault dates."
                ),
                requires_manual_review=True,
            )
        )
        return

    if status == "manual_review":
        findings.append(
            make_draft(
                document_section_id=section.id if section else None,
                entity_type=entity_type,
                verified_entity_id=verified_entity_id,
                field_name="dates",
                finding_type="manual_review",
                cv_value=cv_value,
                verified_value=verified_value,
                normalized_cv_value=normalize_text_value(cv_value),
                normalized_verified_value=normalize_text_value(
                    verified_value,
                ),
                confidence=confidence,
                severity="review",
                explanation=(
                    f"{explanation_subject} contains date-like evidence, but "
                    "it is not a complete deterministic date range."
                ),
                requires_manual_review=True,
            )
        )
        return

    findings.append(
        make_draft(
            document_section_id=None,
            entity_type=entity_type,
            verified_entity_id=verified_entity_id,
            field_name="dates",
            finding_type="missing_verified_fact",
            cv_value=None,
            verified_value=verified_value,
            normalized_cv_value=None,
            normalized_verified_value=normalize_text_value(verified_value),
            confidence=confidence,
            severity="info",
            explanation=(
                f"{explanation_subject} dates are verified in the vault but "
                "were not deterministically found in the CV."
            ),
            requires_manual_review=False,
        )
    )


def compare_profile(
    findings: list[FindingDraft],
    *,
    profile: CandidateProfile | None,
    sections: list[CVSection],
) -> None:
    if profile is None or not profile.facts_verified:
        return

    profile_sections = sections_by_type(
        sections,
        {"contact", "summary", "additional"},
    ) or sections
    contact_sections = sections_by_type(sections, {"contact"}) or sections

    name_matched = add_confirmed_or_missing(
        findings,
        sections=profile_sections,
        entity_type="candidate_profile",
        verified_entity_id=profile.id,
        field_name="full_name",
        verified_value=profile.full_name,
        explanation_subject="Candidate name",
    )

    if not name_matched:
        candidate_name = first_contact_name_candidate(contact_sections)

        if candidate_name is not None:
            findings.append(
                make_draft(
                    document_section_id=contact_sections[0].id,
                    entity_type="candidate_profile",
                    verified_entity_id=profile.id,
                    field_name="full_name",
                    finding_type="possible_mismatch",
                    cv_value=candidate_name,
                    verified_value=profile.full_name,
                    normalized_cv_value=normalize_text_value(candidate_name),
                    normalized_verified_value=normalize_text_value(
                        profile.full_name,
                    ),
                    confidence=0.68,
                    severity="review",
                    explanation=(
                        "The contact section contains a different "
                        "name-like value. This requires manual review."
                    ),
                    requires_manual_review=True,
                )
            )

    add_confirmed_or_missing(
        findings,
        sections=profile_sections,
        entity_type="candidate_profile",
        verified_entity_id=profile.id,
        field_name="professional_title",
        verified_value=profile.professional_title,
        explanation_subject="Professional title",
    )
    compare_profile_contact_field(
        findings,
        sections=contact_sections,
        profile=profile,
        field_name="email",
        verified_value=profile.email,
        pattern=EMAIL_PATTERN,
        normalizer=normalize_text_value,
    )
    compare_profile_contact_field(
        findings,
        sections=contact_sections,
        profile=profile,
        field_name="phone",
        verified_value=profile.phone,
        pattern=PHONE_PATTERN,
        normalizer=normalize_phone,
    )
    add_confirmed_or_missing(
        findings,
        sections=contact_sections,
        entity_type="candidate_profile",
        verified_entity_id=profile.id,
        field_name="location",
        verified_value=profile.location,
        explanation_subject="Location",
    )

    for field_name, value in [
        ("linkedin_url", profile.linkedin_url),
        ("github_url", profile.github_url),
        ("portfolio_url", profile.portfolio_url),
    ]:
        add_confirmed_or_missing(
            findings,
            sections=contact_sections,
            entity_type="candidate_profile",
            verified_entity_id=profile.id,
            field_name=field_name,
            verified_value=value,
            normalizer=normalize_url,
            explanation_subject=field_name.replace("_", " ").title(),
        )


def first_contact_name_candidate(
    sections: list[CVSection],
) -> str | None:
    if not sections:
        return None

    for line in line_candidates(sections[0]):
        if EMAIL_PATTERN.search(line) or PHONE_PATTERN.search(line):
            continue

        if URL_PATTERN.search(line):
            continue

        if len(line) <= 100 and len(line.split()) <= 6:
            return line

    return None


def compare_profile_contact_field(
    findings: list[FindingDraft],
    *,
    sections: list[CVSection],
    profile: CandidateProfile,
    field_name: str,
    verified_value: str | None,
    pattern: re.Pattern[str],
    normalizer: object,
) -> None:
    matched = add_confirmed_or_missing(
        findings,
        sections=sections,
        entity_type="candidate_profile",
        verified_entity_id=profile.id,
        field_name=field_name,
        verified_value=verified_value,
        normalizer=normalizer,
        explanation_subject=field_name.title(),
    )

    if matched or verified_value is None:
        return

    for section in sections:
        match = pattern.search(section.content_text)

        if match is None:
            continue

        cv_value = match.group(0)
        normalized_cv = normalizer(cv_value)  # type: ignore[operator]
        normalized_verified = normalizer(verified_value)  # type: ignore[operator]

        if normalized_cv == normalized_verified:
            continue

        findings.append(
            make_draft(
                document_section_id=section.id,
                entity_type="candidate_profile",
                verified_entity_id=profile.id,
                field_name=field_name,
                finding_type="possible_mismatch",
                cv_value=cv_value,
                verified_value=verified_value,
                normalized_cv_value=normalized_cv,
                normalized_verified_value=normalized_verified,
                confidence=0.79,
                severity="review",
                explanation=(
                    f"The CV contains a {field_name} value that differs "
                    "from the verified vault value."
                ),
                requires_manual_review=True,
            )
        )
        return


def compare_education(
    findings: list[FindingDraft],
    *,
    education_records: list[Education],
    sections: list[CVSection],
) -> None:
    education_sections = sections_by_type(sections, {"education"})
    verified_records = [record for record in education_records if record.verified]

    for record in verified_records:
        add_confirmed_or_missing(
            findings,
            sections=education_sections,
            entity_type="education",
            verified_entity_id=record.id,
            field_name="institution",
            verified_value=record.institution,
            normalizer=normalize_organisation,
            explanation_subject="Education institution",
        )
        add_confirmed_or_missing(
            findings,
            sections=education_sections,
            entity_type="education",
            verified_entity_id=record.id,
            field_name="degree",
            verified_value=record.degree,
            explanation_subject="Education degree",
        )
        add_confirmed_or_missing(
            findings,
            sections=education_sections,
            entity_type="education",
            verified_entity_id=record.id,
            field_name="field_of_study",
            verified_value=record.field_of_study,
            explanation_subject="Education field of study",
        )
        add_confirmed_or_missing(
            findings,
            sections=education_sections,
            entity_type="education",
            verified_entity_id=record.id,
            field_name="grade",
            verified_value=record.grade,
            explanation_subject="Education grade",
        )

        section, context = context_for_record(
            education_sections,
            [record.institution, record.degree],
            normalize_organisation,
        )
        add_date_finding(
            findings,
            section=section,
            entity_type="education",
            verified_entity_id=record.id,
            start_date=record.start_date,
            end_date=record.end_date,
            is_current=record.is_current,
            context=context,
            explanation_subject="Education record",
        )

    add_unverified_education_claims(
        findings,
        education_sections,
        verified_records,
    )


def compare_experience(
    findings: list[FindingDraft],
    *,
    experience_records: list[Experience],
    sections: list[CVSection],
) -> None:
    experience_sections = sections_by_type(sections, {"work_experience"})
    verified_records = [
        record for record in experience_records if record.verified
    ]

    for record in verified_records:
        company_matched = add_confirmed_or_missing(
            findings,
            sections=experience_sections,
            entity_type="work_experience",
            verified_entity_id=record.id,
            field_name="company",
            verified_value=record.company,
            normalizer=normalize_organisation,
            explanation_subject="Work experience company",
        )
        section, context = context_for_record(
            experience_sections,
            [record.company, record.job_title],
            normalize_organisation,
        )

        if not company_matched and record.job_title:
            maybe_org = first_unmatched_org_line(
                experience_sections,
                [record.company],
            )

            if maybe_org is not None:
                findings.append(
                    make_draft(
                        document_section_id=section.id if section else None,
                        entity_type="work_experience",
                        verified_entity_id=record.id,
                        field_name="company",
                        finding_type="organisation_conflict",
                        cv_value=maybe_org,
                        verified_value=record.company,
                        normalized_cv_value=normalize_organisation(
                            maybe_org,
                        ),
                        normalized_verified_value=normalize_organisation(
                            record.company,
                        ),
                        confidence=0.7,
                        severity="review",
                        explanation=(
                            "A work-experience organisation-like value did "
                            "not match the verified company."
                        ),
                        requires_manual_review=True,
                    )
                )

        add_confirmed_or_missing(
            findings,
            sections=[section] if section else experience_sections,
            entity_type="work_experience",
            verified_entity_id=record.id,
            field_name="job_title",
            verified_value=record.job_title,
            explanation_subject="Work experience job title",
        )
        add_confirmed_or_missing(
            findings,
            sections=[section] if section else experience_sections,
            entity_type="work_experience",
            verified_entity_id=record.id,
            field_name="employment_type",
            verified_value=record.employment_type,
            explanation_subject="Employment type",
        )
        add_confirmed_or_missing(
            findings,
            sections=[section] if section else experience_sections,
            entity_type="work_experience",
            verified_entity_id=record.id,
            field_name="location",
            verified_value=record.location,
            explanation_subject="Work experience location",
        )
        add_date_finding(
            findings,
            section=section,
            entity_type="work_experience",
            verified_entity_id=record.id,
            start_date=record.start_date,
            end_date=record.end_date,
            is_current=record.is_current,
            context=context,
            explanation_subject="Work experience record",
        )

    add_unverified_work_claims(
        findings,
        experience_sections,
        verified_records,
    )


def compare_projects(
    findings: list[FindingDraft],
    *,
    project_records: list[Project],
    sections: list[CVSection],
) -> None:
    project_sections = sections_by_type(sections, {"projects"})
    verified_records = [record for record in project_records if record.verified]

    for record in verified_records:
        add_confirmed_or_missing(
            findings,
            sections=project_sections,
            entity_type="project",
            verified_entity_id=record.id,
            field_name="name",
            verified_value=record.name,
            explanation_subject="Project name",
        )
        section, context = context_for_record(
            project_sections,
            [record.name, record.project_url, record.github_url],
        )
        scoped_sections = [section] if section else project_sections
        add_confirmed_or_missing(
            findings,
            sections=scoped_sections,
            entity_type="project",
            verified_entity_id=record.id,
            field_name="role",
            verified_value=record.role,
            explanation_subject="Project role",
        )
        add_confirmed_or_missing(
            findings,
            sections=scoped_sections,
            entity_type="project",
            verified_entity_id=record.id,
            field_name="project_type",
            verified_value=record.project_type,
            explanation_subject="Project type",
        )
        add_confirmed_or_missing(
            findings,
            sections=scoped_sections,
            entity_type="project",
            verified_entity_id=record.id,
            field_name="project_url",
            verified_value=record.project_url,
            normalizer=normalize_url,
            explanation_subject="Project URL",
        )
        add_confirmed_or_missing(
            findings,
            sections=scoped_sections,
            entity_type="project",
            verified_entity_id=record.id,
            field_name="github_url",
            verified_value=record.github_url,
            normalizer=normalize_url,
            explanation_subject="Project GitHub URL",
        )

        for technology in record.technologies:
            add_confirmed_or_missing(
                findings,
                sections=scoped_sections,
                entity_type="project",
                verified_entity_id=record.id,
                field_name="technologies",
                verified_value=technology,
                normalizer=normalize_skill,
                explanation_subject="Project technology",
            )

        add_date_finding(
            findings,
            section=section,
            entity_type="project",
            verified_entity_id=record.id,
            start_date=record.start_date,
            end_date=record.end_date,
            is_current=record.is_current,
            context=context,
            explanation_subject="Project record",
        )

    add_unverified_project_claims(
        findings,
        project_sections,
        verified_records,
    )


def compare_skills(
    findings: list[FindingDraft],
    *,
    skill_records: list[Skill],
    sections: list[CVSection],
) -> None:
    skill_sections = sections_by_type(sections, {"skills"})
    document_normalized = normalize_skill(all_text(sections))
    verified_records = [record for record in skill_records if record.verified]
    verified_by_normalized = {
        normalize_skill(record.name): record
        for record in verified_records
        if normalize_skill(record.name)
    }
    skill_claims = extract_skill_claims(skill_sections)
    claim_by_normalized = {
        claim_normalized: (claim, section)
        for claim, section, claim_normalized in skill_claims
    }

    for normalized_name, record in verified_by_normalized.items():
        claim = claim_by_normalized.get(normalized_name)

        if claim is not None:
            cv_value, section = claim
            findings.append(
                make_draft(
                    document_section_id=section.id,
                    entity_type="skill",
                    verified_entity_id=record.id,
                    field_name="name",
                    finding_type="confirmed",
                    cv_value=cv_value,
                    verified_value=record.name,
                    normalized_cv_value=normalized_name,
                    normalized_verified_value=normalized_name,
                    confidence=0.97,
                    severity="info",
                    explanation=(
                        "CV skill matched the verified vault skill name."
                    ),
                    requires_manual_review=False,
                )
            )
            continue

        if phrase_contains(document_normalized, normalized_name):
            findings.append(
                make_draft(
                    document_section_id=None,
                    entity_type="skill",
                    verified_entity_id=record.id,
                    field_name="name",
                    finding_type="confirmed",
                    cv_value=record.name,
                    verified_value=record.name,
                    normalized_cv_value=normalized_name,
                    normalized_verified_value=normalized_name,
                    confidence=0.88,
                    severity="info",
                    explanation=(
                        "Verified skill was found elsewhere in the CV text."
                    ),
                    requires_manual_review=False,
                )
            )
            continue

        findings.append(
            make_draft(
                document_section_id=None,
                entity_type="skill",
                verified_entity_id=record.id,
                field_name="name",
                finding_type="missing_verified_fact",
                cv_value=None,
                verified_value=record.name,
                normalized_cv_value=None,
                normalized_verified_value=normalized_name,
                confidence=0.84,
                severity="info",
                explanation=(
                    "Verified skill was not deterministically found in the "
                    "CV. It may be intentionally omitted."
                ),
                requires_manual_review=False,
            )
        )

    add_unverified_skill_claims(
        findings,
        skill_claims,
        verified_by_normalized,
    )


def compare_certifications(
    findings: list[FindingDraft],
    *,
    certification_records: list[Certification],
    sections: list[CVSection],
) -> None:
    certification_sections = sections_by_type(sections, {"certifications"})
    verified_records = [
        record for record in certification_records if record.verified
    ]

    for record in verified_records:
        add_confirmed_or_missing(
            findings,
            sections=certification_sections,
            entity_type="certification",
            verified_entity_id=record.id,
            field_name="name",
            verified_value=record.name,
            explanation_subject="Certification name",
        )
        section, context = context_for_record(
            certification_sections,
            [record.name, record.issuing_organization],
        )
        scoped_sections = [section] if section else certification_sections
        add_confirmed_or_missing(
            findings,
            sections=scoped_sections,
            entity_type="certification",
            verified_entity_id=record.id,
            field_name="issuing_organization",
            verified_value=record.issuing_organization,
            normalizer=normalize_organisation,
            explanation_subject="Certification issuer",
        )
        add_confirmed_or_missing(
            findings,
            sections=scoped_sections,
            entity_type="certification",
            verified_entity_id=record.id,
            field_name="credential_id",
            verified_value=record.credential_id,
            explanation_subject="Credential ID",
        )
        add_confirmed_or_missing(
            findings,
            sections=scoped_sections,
            entity_type="certification",
            verified_entity_id=record.id,
            field_name="credential_url",
            verified_value=record.credential_url,
            normalizer=normalize_url,
            explanation_subject="Credential URL",
        )
        add_date_finding(
            findings,
            section=section,
            entity_type="certification",
            verified_entity_id=record.id,
            start_date=record.issue_date,
            end_date=record.expiry_date,
            is_current=record.does_not_expire,
            context=context,
            explanation_subject="Certification record",
        )

    add_unverified_certification_claims(
        findings,
        certification_sections,
        verified_records,
    )


def first_unmatched_org_line(
    sections: list[CVSection],
    verified_orgs: list[str],
) -> str | None:
    normalized_verified = {
        normalize_organisation(org)
        for org in verified_orgs
        if normalize_organisation(org)
    }

    for section in sections:
        for line in line_candidates(section):
            normalized_line = normalize_organisation(line)

            if not normalized_line:
                continue

            if any(
                phrase_contains(normalized_line, org)
                for org in normalized_verified
            ):
                continue

            if " - " in line or " at " in line.casefold():
                return line

    return None


def add_unverified_education_claims(
    findings: list[FindingDraft],
    sections: list[CVSection],
    verified_records: list[Education],
) -> None:
    verified_values = [
        item
        for record in verified_records
        for item in [record.institution, record.degree, record.field_of_study]
        if item
    ]
    normalized_verified = [
        normalize_organisation(item) or normalize_text_value(item)
        for item in verified_values
    ]

    for section in sections:
        for line in line_candidates(section):
            normalized_line = normalize_text_value(line)

            if not normalized_line:
                continue

            if any(
                phrase_contains(normalized_line, verified)
                for verified in normalized_verified
                if verified
            ):
                continue

            if re.search(
                r"\b(university|college|school|institute|bsc|msc|"
                r"bachelor|master|phd)\b",
                normalized_line,
            ):
                findings.append(
                    make_unverified_claim(
                        section,
                        "education",
                        "education_claim",
                        line,
                        "Education text was not matched to a verified "
                        "education record.",
                    )
                )


def add_unverified_work_claims(
    findings: list[FindingDraft],
    sections: list[CVSection],
    verified_records: list[Experience],
) -> None:
    normalized_companies = [
        normalize_organisation(record.company)
        for record in verified_records
        if normalize_organisation(record.company)
    ]
    verified_descriptions = collect_verified_work_descriptions(
        verified_records,
    )

    for section in sections:
        for line in line_candidates(section):
            if is_date_like_line(line) or descriptive_line_matches(
                line,
                verified_descriptions,
            ):
                continue

            normalized_line = normalize_organisation(line)

            if not normalized_line:
                continue

            if any(
                phrase_contains(normalized_line, company)
                for company in normalized_companies
                if company
            ):
                continue

            looks_like_role_line = (
                " - " in line
                or " at " in line.casefold()
                or bool(YEAR_PATTERN.search(line))
            )

            if looks_like_role_line:
                findings.append(
                    make_unverified_claim(
                        section,
                        "work_experience",
                        "company",
                        line,
                        "Work-experience text was not matched to a "
                        "verified work record.",
                    )
                )


def add_unverified_project_claims(
    findings: list[FindingDraft],
    sections: list[CVSection],
    verified_records: list[Project],
) -> None:
    normalized_values = [
        normalize_text_value(item)
        for record in verified_records
        for item in [
            record.name,
            record.role,
            record.project_type,
            record.project_url,
            record.github_url,
            *record.technologies,
        ]
        if item and normalize_text_value(item)
    ]
    verified_descriptions = collect_verified_project_descriptions(
        verified_records,
    )

    for section in sections:
        for line in line_candidates(section):
            if line.startswith(("-", "*")):
                continue

            if is_date_like_line(line) or descriptive_line_matches(
                line,
                verified_descriptions,
            ):
                continue

            normalized_line = normalize_text_value(line)

            if not normalized_line:
                continue

            if any(
                phrase_contains(normalized_line, value)
                for value in normalized_values
                if value
            ):
                continue

            if len(line.split()) <= 10:
                findings.append(
                    make_unverified_claim(
                        section,
                        "project",
                        "name",
                        line,
                        "Project text was not matched to a verified "
                        "project record.",
                    )
                )


def add_unverified_skill_claims(
    findings: list[FindingDraft],
    skill_claims: list[tuple[str, CVSection, str]],
    verified_by_normalized: dict[str | None, Skill],
) -> None:
    verified_names = {
        normalized
        for normalized in verified_by_normalized
        if normalized
    }

    for claim, section, normalized_claim in skill_claims:
        if normalized_claim in verified_names:
            continue

        ambiguous_name = next(
            (
                verified_name
                for verified_name in verified_names
                if phrase_contains(normalized_claim, verified_name)
                or phrase_contains(verified_name, normalized_claim)
            ),
            None,
        )

        if ambiguous_name is not None:
            findings.append(
                make_draft(
                    document_section_id=section.id,
                    entity_type="skill",
                    verified_entity_id=verified_by_normalized[
                        ambiguous_name
                    ].id,
                    field_name="name",
                    finding_type="manual_review",
                    cv_value=claim,
                    verified_value=verified_by_normalized[
                        ambiguous_name
                    ].name,
                    normalized_cv_value=normalized_claim,
                    normalized_verified_value=ambiguous_name,
                    confidence=0.58,
                    severity="review",
                    explanation=(
                        "The CV skill partially overlaps a verified skill. "
                        "The deterministic matcher will not treat this as a "
                        "confirmed fact."
                    ),
                    requires_manual_review=True,
                )
            )
            continue

        findings.append(
            make_unverified_claim(
                section,
                "skill",
                "name",
                claim,
                "CV skill was not matched to a verified vault skill.",
            )
        )


def add_unverified_certification_claims(
    findings: list[FindingDraft],
    sections: list[CVSection],
    verified_records: list[Certification],
) -> None:
    normalized_values = [
        normalize_text_value(item)
        for record in verified_records
        for item in [
            record.name,
            record.issuing_organization,
            record.credential_id,
            record.credential_url,
        ]
        if item and normalize_text_value(item)
    ]

    for section in sections:
        for line in line_candidates(section):
            if is_date_like_line(line):
                continue

            normalized_line = normalize_text_value(line)

            if not normalized_line:
                continue

            if any(
                phrase_contains(normalized_line, value)
                for value in normalized_values
                if value
            ):
                continue

            if len(line.split()) <= 12:
                findings.append(
                    make_unverified_claim(
                        section,
                        "certification",
                        "name",
                        line,
                        "Certification text was not matched to a verified "
                        "certification record.",
                    )
                )


def make_unverified_claim(
    section: CVSection,
    entity_type: str,
    field_name: str,
    claim: str,
    explanation: str,
) -> FindingDraft:
    return make_draft(
        document_section_id=section.id,
        entity_type=entity_type,
        verified_entity_id=None,
        field_name=field_name,
        finding_type="unverified_claim",
        cv_value=claim,
        verified_value=None,
        normalized_cv_value=normalize_text_value(claim),
        normalized_verified_value=None,
        confidence=0.73,
        severity="review",
        explanation=(
            f"{explanation} This is not labelled false or fraudulent."
        ),
        requires_manual_review=True,
    )


def extract_skill_claims(
    sections: list[CVSection],
) -> list[tuple[str, CVSection, str]]:
    claims: list[tuple[str, CVSection, str]] = []
    seen: set[str] = set()

    for section in sections:
        for line in line_candidates(section):
            line = re.sub(r"^[A-Za-z ]{2,30}:\s*", "", line)
            pieces = re.split(r"[,;|/]", line)

            for piece in pieces:
                cleaned = piece.strip(" -\t")

                if not cleaned:
                    continue

                if len(cleaned) > 80 or len(cleaned.split()) > 5:
                    continue

                normalized = normalize_skill(cleaned)

                if not normalized or normalized in seen:
                    continue

                seen.add(normalized)
                claims.append((cleaned, section, normalized))

    return claims


def finding_dedupe_key(finding: FindingDraft) -> str:
    raw_key = "\x1f".join(
        [
            finding.entity_type,
            str(finding.verified_entity_id or ""),
            finding.field_name or "",
            finding.finding_type,
            str(finding.document_section_id or ""),
            finding.normalized_cv_value or "",
            finding.normalized_verified_value or "",
        ]
    )

    return sha256(raw_key.encode()).hexdigest()


def finding_sort_key(finding: FindingDraft) -> tuple[object, ...]:
    return (
        ENTITY_ORDER.get(finding.entity_type, 99),
        finding.verified_entity_id or 0,
        FINDING_ORDER.get(finding.finding_type, 99),
        finding.field_name or "",
        finding.document_section_id or 0,
        finding.normalized_cv_value or "",
        finding.normalized_verified_value or "",
    )


def prepare_findings(
    drafts: list[FindingDraft],
) -> list[ComparisonFinding]:
    unique: dict[str, FindingDraft] = {}

    for draft in drafts:
        dedupe_key = finding_dedupe_key(draft)
        unique.setdefault(dedupe_key, draft)

    findings: list[ComparisonFinding] = []

    for sort_order, (dedupe_key, draft) in enumerate(
        sorted(
            unique.items(),
            key=lambda item: finding_sort_key(item[1]),
        )
    ):
        findings.append(
            ComparisonFinding(
                document_section_id=draft.document_section_id,
                sort_order=sort_order,
                entity_type=draft.entity_type,
                verified_entity_id=draft.verified_entity_id,
                field_name=draft.field_name,
                finding_type=draft.finding_type,
                cv_value=draft.cv_value,
                verified_value=draft.verified_value,
                normalized_cv_value=draft.normalized_cv_value,
                normalized_verified_value=draft.normalized_verified_value,
                confidence=draft.confidence,
                severity=draft.severity,
                explanation=draft.explanation,
                requires_manual_review=draft.requires_manual_review,
                dedupe_key=dedupe_key,
            )
        )

    return findings


def build_result(findings: list[ComparisonFinding]) -> ComparisonResult:
    mismatch_types = {
        "possible_mismatch",
        "date_conflict",
        "organisation_conflict",
        "skill_conflict",
    }

    return ComparisonResult(
        status="completed",
        findings=findings,
        total_findings=len(findings),
        confirmed_count=sum(
            1 for finding in findings if finding.finding_type == "confirmed"
        ),
        mismatch_count=sum(
            1
            for finding in findings
            if finding.finding_type in mismatch_types
        ),
        missing_verified_count=sum(
            1
            for finding in findings
            if finding.finding_type == "missing_verified_fact"
        ),
        unverified_claim_count=sum(
            1
            for finding in findings
            if finding.finding_type == "unverified_claim"
        ),
        manual_review_count=sum(
            1
            for finding in findings
            if finding.requires_manual_review
        ),
        comparison_version=COMPARISON_VERSION,
    )


def compare_document_to_verified_facts(
    *,
    document: Document,
    sections: list[CVSection],
    profile: CandidateProfile | None,
    education_records: list[Education],
    experience_records: list[Experience],
    project_records: list[Project],
    skill_records: list[Skill],
    certification_records: list[Certification],
) -> ComparisonResult:
    if document.upload_status != "validated":
        raise FactComparisonError(
            "Only validated documents can be compared to verified facts."
        )

    if document.extraction_status != "completed" or not document.extracted_text:
        raise FactComparisonError(
            "Only documents with completed text extraction can be compared."
        )

    if document.section_detection_status != "completed":
        raise FactComparisonError(
            "Only documents with completed section detection can be compared."
        )

    if not sections:
        raise FactComparisonError(
            "Detected CV sections are required before fact comparison."
        )

    drafts: list[FindingDraft] = []

    compare_profile(drafts, profile=profile, sections=sections)
    compare_education(
        drafts,
        education_records=education_records,
        sections=sections,
    )
    compare_experience(
        drafts,
        experience_records=experience_records,
        sections=sections,
    )
    compare_projects(
        drafts,
        project_records=project_records,
        sections=sections,
    )
    compare_skills(
        drafts,
        skill_records=skill_records,
        sections=sections,
    )
    compare_certifications(
        drafts,
        certification_records=certification_records,
        sections=sections,
    )

    return build_result(prepare_findings(drafts))
