from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.document import Document


DETECTION_METHOD = "deterministic_section_detection_v1"
CONTACT_SCAN_CHAR_LIMIT = 900
CONTACT_SCAN_LINE_LIMIT = 12
HEADING_MAX_CHARACTERS = 90
HEADING_MAX_WORDS = 9

SECTION_ALIASES: dict[str, str] = {
    "contact": "contact",
    "contact information": "contact",
    "personal details": "contact",
    "personal information": "contact",
    "summary": "summary",
    "professional summary": "summary",
    "profile": "summary",
    "career profile": "summary",
    "objective": "summary",
    "career objective": "summary",
    "personal statement": "summary",
    "work experience": "work_experience",
    "professional experience": "work_experience",
    "experience": "work_experience",
    "employment history": "work_experience",
    "work history": "work_experience",
    "career history": "work_experience",
    "relevant experience": "work_experience",
    "education": "education",
    "academic background": "education",
    "education and qualifications": "education",
    "qualifications": "education",
    "skills": "skills",
    "technical skills": "skills",
    "core skills": "skills",
    "key skills": "skills",
    "competencies": "skills",
    "technologies": "skills",
    "technology stack": "skills",
    "projects": "projects",
    "project experience": "projects",
    "portfolio": "projects",
    "selected projects": "projects",
    "certifications": "certifications",
    "certificates": "certifications",
    "licenses": "certifications",
    "licences": "certifications",
    "certifications and licenses": "certifications",
    "awards": "awards",
    "honors": "awards",
    "honours": "awards",
    "awards and honors": "awards",
    "achievements": "awards",
    "publications": "publications",
    "research": "publications",
    "articles": "publications",
    "volunteering": "volunteering",
    "volunteer experience": "volunteering",
    "community involvement": "volunteering",
    "languages": "languages",
    "language skills": "languages",
    "interests": "interests",
    "hobbies": "interests",
    "interests and activities": "interests",
    "references": "references",
    "additional information": "additional",
    "additional": "additional",
    "other": "additional",
    "miscellaneous": "additional",
}

EMAIL_PATTERN = re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)"
)
URL_PATTERN = re.compile(
    r"\b(?:https?://|www\.|linkedin\.com|github\.com)[^\s]+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LineSpan:
    text: str
    start: int
    end: int
    next_start: int


@dataclass(frozen=True)
class HeadingMatch:
    line_index: int
    section_type: str
    title: str
    start: int
    end: int
    next_start: int
    confidence: float


@dataclass(frozen=True)
class DetectedSection:
    section_order: int
    section_type: str
    title: str | None
    start_char: int
    end_char: int
    content_text: str
    confidence: float
    detection_method: str


@dataclass(frozen=True)
class SectionDetectionResult:
    status: str
    sections: list[DetectedSection]
    section_detection_error: str | None
    section_detected_at: datetime
    section_count: int
    section_detection_method: str


class CVSectionDetectionError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.safe_message = message


def split_line_spans(text: str) -> list[LineSpan]:
    spans: list[LineSpan] = []
    position = 0

    for raw_line in text.splitlines(keepends=True):
        line_text = raw_line.rstrip("\r\n")
        start = position
        end = start + len(line_text)
        next_start = position + len(raw_line)
        spans.append(
            LineSpan(
                text=line_text,
                start=start,
                end=end,
                next_start=next_start,
            )
        )
        position = next_start

    if not spans and text:
        spans.append(
            LineSpan(
                text=text,
                start=0,
                end=len(text),
                next_start=len(text),
            )
        )

    return spans


def strip_heading_marker(line: str) -> tuple[str, bool]:
    stripped = line.strip()
    cleaned = re.sub(
        r"^(?:[-*]\s+|\d{1,2}[\.)]\s+|[A-Z][\.)]\s+|"
        r"[IVXLCM]{1,6}[\.)]\s+)",
        "",
        stripped,
        flags=re.IGNORECASE,
    )

    return cleaned.strip(), cleaned != stripped


def normalize_heading(line: str) -> str:
    cleaned, _ = strip_heading_marker(line)
    cleaned = cleaned.strip().strip(":")
    cleaned = cleaned.replace("&", " and ")
    cleaned = cleaned.replace("/", " ")
    cleaned = re.sub(r"[^A-Za-z0-9+ ]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.casefold().strip()


def has_contact_signal(line: str) -> bool:
    return bool(
        EMAIL_PATTERN.search(line)
        or PHONE_PATTERN.search(line)
        or URL_PATTERN.search(line)
    )


def is_all_caps_heading(line: str) -> bool:
    letters = [character for character in line if character.isalpha()]

    if len(letters) < 2:
        return False

    upper_letters = [
        character for character in letters if character.upper() == character
    ]

    return len(upper_letters) / len(letters) >= 0.8


def looks_like_unknown_heading(line: str, had_marker: bool) -> bool:
    stripped = line.strip().strip(":")

    if not stripped or len(stripped) > HEADING_MAX_CHARACTERS:
        return False

    if has_contact_signal(stripped):
        return False

    if any(separator in stripped for separator in [",", ";"]):
        return False

    if stripped.endswith("."):
        return False

    words = stripped.split()

    if not words or len(words) > HEADING_MAX_WORDS:
        return False

    return had_marker or is_all_caps_heading(stripped)


def clamp_confidence(value: float) -> float:
    return round(min(0.99, max(0.0, value)), 2)


def heading_match_for_line(
    line: LineSpan,
    line_index: int,
) -> HeadingMatch | None:
    raw_title, had_marker = strip_heading_marker(line.text)
    normalized = normalize_heading(raw_title)

    if not normalized:
        return None

    if normalized in SECTION_ALIASES:
        confidence = 0.86

        if raw_title.strip().endswith(":"):
            confidence += 0.03

        if had_marker:
            confidence += 0.03

        if is_all_caps_heading(raw_title):
            confidence += 0.04

        return HeadingMatch(
            line_index=line_index,
            section_type=SECTION_ALIASES[normalized],
            title=raw_title.strip().strip(":"),
            start=line.start,
            end=line.end,
            next_start=line.next_start,
            confidence=clamp_confidence(confidence),
        )

    if looks_like_unknown_heading(raw_title, had_marker):
        return HeadingMatch(
            line_index=line_index,
            section_type="additional",
            title=raw_title.strip().strip(":"),
            start=line.start,
            end=line.end,
            next_start=line.next_start,
            confidence=0.52,
        )

    return None


def detect_headings(lines: list[LineSpan]) -> list[HeadingMatch]:
    headings: list[HeadingMatch] = []
    seen_starts: set[int] = set()

    for line_index, line in enumerate(lines):
        match = heading_match_for_line(line, line_index)

        if match is None or match.start in seen_starts:
            continue

        headings.append(match)
        seen_starts.add(match.start)

    return headings


def trim_range(text: str, start: int, end: int) -> tuple[int, int, str]:
    start = max(0, min(start, len(text)))
    end = max(start, min(end, len(text)))

    while start < end and text[start].isspace():
        start += 1

    while end > start and text[end - 1].isspace():
        end -= 1

    return start, end, text[start:end]


def contact_confidence(contact_text: str) -> float:
    confidence = 0.74

    if EMAIL_PATTERN.search(contact_text):
        confidence += 0.08

    if PHONE_PATTERN.search(contact_text):
        confidence += 0.06

    if URL_PATTERN.search(contact_text):
        confidence += 0.05

    if "\n" in contact_text:
        confidence += 0.02

    return clamp_confidence(confidence)


def infer_contact_section(
    text: str,
    lines: list[LineSpan],
    first_heading_start: int | None,
) -> DetectedSection | None:
    scan_end = min(len(text), CONTACT_SCAN_CHAR_LIMIT)

    if first_heading_start is not None:
        scan_end = min(scan_end, first_heading_start)

    top_lines = [
        line for line in lines if line.start < scan_end
    ][:CONTACT_SCAN_LINE_LIMIT]
    non_empty_indices = [
        index
        for index, line in enumerate(top_lines)
        if line.text.strip()
    ]

    if not non_empty_indices:
        return None

    signal_indices = [
        index
        for index, line in enumerate(top_lines)
        if has_contact_signal(line.text)
    ]

    if not signal_indices:
        return None

    first_signal_index = signal_indices[0]
    last_signal_index = signal_indices[-1]
    start_candidates = [
        index
        for index in non_empty_indices
        if index >= max(0, first_signal_index - 2)
        and index <= first_signal_index
    ]
    start_line_index = start_candidates[0]
    end_line_index = last_signal_index

    for index in range(last_signal_index + 1, len(top_lines)):
        if top_lines[index].text.strip():
            end_line_index = index
            continue

        break

    start = top_lines[start_line_index].start
    end = top_lines[end_line_index].next_start
    start, end, content = trim_range(text, start, end)

    if not content:
        return None

    return DetectedSection(
        section_order=0,
        section_type="contact",
        title="Contact",
        start_char=start,
        end_char=end,
        content_text=content,
        confidence=contact_confidence(content),
        detection_method=DETECTION_METHOD,
    )


def content_confidence_adjustment(content: str) -> float:
    if not content:
        return -0.08

    if len(content) >= 40:
        return 0.04

    return 0.0


def make_section(
    text: str,
    heading: HeadingMatch,
    end: int,
) -> DetectedSection:
    start, trimmed_end, content = trim_range(text, heading.next_start, end)
    confidence = heading.confidence + content_confidence_adjustment(content)

    return DetectedSection(
        section_order=0,
        section_type=heading.section_type,
        title=heading.title,
        start_char=start,
        end_char=trimmed_end,
        content_text=content,
        confidence=clamp_confidence(confidence),
        detection_method=DETECTION_METHOD,
    )


def make_additional_section(
    text: str,
    start: int,
    end: int,
    *,
    title: str | None = "Additional",
) -> DetectedSection | None:
    start, end, content = trim_range(text, start, end)

    if not content:
        return None

    return DetectedSection(
        section_order=0,
        section_type="additional",
        title=title,
        start_char=start,
        end_char=end,
        content_text=content,
        confidence=0.35,
        detection_method=DETECTION_METHOD,
    )


def deduplicate_sections(
    sections: list[DetectedSection],
) -> list[DetectedSection]:
    deduplicated: list[DetectedSection] = []
    seen: set[tuple[str, int]] = set()

    for section in sorted(sections, key=lambda item: item.start_char):
        key = (section.section_type, section.start_char)

        if key in seen:
            continue

        deduplicated.append(section)
        seen.add(key)

    return [
        DetectedSection(
            section_order=index,
            section_type=section.section_type,
            title=section.title,
            start_char=section.start_char,
            end_char=section.end_char,
            content_text=section.content_text,
            confidence=section.confidence,
            detection_method=section.detection_method,
        )
        for index, section in enumerate(deduplicated)
    ]


def detect_sections_from_text(text: str) -> list[DetectedSection]:
    if not text or not text.strip():
        raise CVSectionDetectionError(
            "No extracted text is available for section detection."
        )

    lines = split_line_spans(text)
    headings = detect_headings(lines)
    first_heading_start = headings[0].start if headings else None
    has_explicit_contact = any(
        heading.section_type == "contact" for heading in headings
    )
    sections: list[DetectedSection] = []
    contact_section: DetectedSection | None = None

    if not has_explicit_contact:
        contact_section = infer_contact_section(
            text,
            lines,
            first_heading_start,
        )

        if contact_section is not None:
            sections.append(contact_section)

    if headings:
        preamble_end = headings[0].start
        preamble_start = contact_section.end_char if contact_section else 0
        preamble = make_additional_section(
            text,
            preamble_start,
            preamble_end,
            title="Preamble",
        )

        if preamble is not None:
            sections.append(preamble)

        for index, heading in enumerate(headings):
            next_start = (
                headings[index + 1].start
                if index + 1 < len(headings)
                else len(text)
            )
            sections.append(make_section(text, heading, next_start))
    else:
        additional_start = contact_section.end_char if contact_section else 0
        additional = make_additional_section(
            text,
            additional_start,
            len(text),
        )

        if additional is not None:
            sections.append(additional)

    sections = deduplicate_sections(sections)

    if not sections:
        raise CVSectionDetectionError("No CV sections could be detected.")

    return sections


def detect_document_sections(document: Document) -> SectionDetectionResult:
    if document.extraction_status != "completed":
        raise CVSectionDetectionError(
            "Only documents with completed text extraction can be sectioned."
        )

    if not document.extracted_text:
        raise CVSectionDetectionError(
            "No extracted text is available for section detection."
        )

    sections = detect_sections_from_text(document.extracted_text)

    return SectionDetectionResult(
        status="completed",
        sections=sections,
        section_detection_error=None,
        section_detected_at=datetime.now(timezone.utc),
        section_count=len(sections),
        section_detection_method=DETECTION_METHOD,
    )
