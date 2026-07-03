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

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.document import Document
from app.models.skill import Skill
from app.services.document_section_detection import (
    EMAIL_PATTERN,
    PHONE_PATTERN,
    URL_PATTERN,
    CVSectionDetectionError,
    detect_sections_from_text,
    has_contact_signal,
)


EXTRACTION_VERSION = "cv-profile-extraction-1"
EVIDENCE_LIMIT = 300
SUMMARY_LIMIT = 2000
MANUAL_CONTENT_LIMIT = 2000
MAX_NAME_WORDS = 6
MAX_SKILLS = 100

# Sections whose structured records require dates we must not invent;
# surfaced as manual-review suggestions instead of being auto-applied.
MANUAL_SECTION_LABELS = {
    "work_experience": "work_experience",
    "education": "education",
    "projects": "projects",
    "certifications": "certifications",
}

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
class ProfileSuggestion:
    document_id: int
    extraction_version: str
    verified: bool
    fields: list[SuggestedField] = field(default_factory=list)
    skills: list[SuggestedSkill] = field(default_factory=list)
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

    # --- Structured history: manual review (no invented dates) ---
    for section_type, label in MANUAL_SECTION_LABELS.items():
        content = sections.get(section_type)
        if content and content.strip():
            suggestion.manual_review.append(
                ManualSuggestion(
                    category=label,
                    content=content.strip()[:MANUAL_CONTENT_LIMIT],
                    reason=(
                        "Dated records must be reviewed and entered "
                        "manually so no dates or titles are guessed."
                    ),
                )
            )

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


def apply_profile_suggestion(
    document: Document,
    database: Session,
    candidate_profile_id: int,
    *,
    apply_profile: bool = True,
    apply_skills: bool = True,
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

    database.commit()

    return {
        "document_id": document.id,
        "verified": False,
        "applied_fields": applied_fields,
        "skipped_existing_fields": skipped_fields,
        "added_skills": added_skills,
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
