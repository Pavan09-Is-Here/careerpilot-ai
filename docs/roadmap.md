# CareerPilot AI Development Roadmap

**Version:** 0.9.10
**Last Updated:** 2026-07-02 (Phase 14 code-level groundwork committed)
**Status:** Actively in development — Phases 1–13 COMPLETED; Phase 14 (Production Database and Deployment) IN PROGRESS — code groundwork committed, infrastructure provisioning/deployment remaining

---

## Table of Contents

1. [Executive Overview](#executive-overview)
2. [Status Legend](#status-legend)
3. [Current Repository Architecture](#current-repository-architecture)
4. [Completed Functionality](#completed-functionality)
5. [Development Phases and Milestones](#development-phases-and-milestones)
6. [Dependency Map](#dependency-map)
7. [Risk Register](#risk-register)
8. [Validation Matrix](#validation-matrix)
9. [Standard Milestone Workflow](#standard-milestone-workflow)
10. [Current Project Position](#current-project-position)

---

## Executive Overview

### What is CareerPilot AI?

CareerPilot AI is a personal career automation platform designed to help verified job candidates safely prepare, tailor, and manage job applications. The system maintains a single-user verified candidate facts vault, ensures all CV claims are grounded in verified information, and assists with compliant job discovery, eligibility analysis, and application workflows.

### Intended Users

- Individual job candidates who require verified career records
- Professionals seeking safe, truthful CV management and application support
- Candidates in regulated industries where claim verification is critical

### Main Business and Technical Goals

**Business Goals:**
- Provide a trustworthy, verification-first platform for candidate self-presentation
- Ensure CVs reflect only verified, truthful candidate information
- Reduce application friction while maintaining claim accuracy
- Enable data-driven job matching and eligibility assessment
- Support safe, compliant job application workflows

**Technical Goals:**
- Build a secure, single-tenant candidate facts vault on SQLite (SQLite for development, PostgreSQL/Supabase for production)
- Implement reliable PDF/DOCX upload, validation, and text extraction
- Create deterministic CV section detection and mapping to verified facts
- Enable job discovery from compliant sources (APIs, permitted scraping)
- Support job eligibility analysis with explainable scoring
- Generate truthful, ATS-friendly CV versions from verified facts
- Provide browser-assisted application workflows with appropriate safety gates
- Audit and track all applications and outcomes

### Core Safety and Truthfulness Principles

1. **Never fabricate candidate information** — Every CV claim, statement, answer, or generated document must be grounded in verified candidate data
2. **Prevent unsupported claims** — Uncertain matches between CV text and verified facts are flagged for manual review, not silently accepted
3. **Explicit verification workflow** — Candidate facts must be entered directly; inferred data is treated as uncertain until verified
4. **Safe application automation** — The system pauses for CAPTCHA, MFA, assessments, legal declarations, and human judgment calls; it never bypasses security or ToS restrictions
5. **Audit and transparency** — All application actions, matches, and decisions are logged and reviewable
6. **No unsupported metrics** — Years of experience, salary claims, and project achievements must be sourced from verified records

### Current Overall Project Position

**Completed Phases:**
- Phase 1: Project Foundation ✓ (Backend, frontend, database, testing, health checks)
- Phase 2: Verified Candidate Facts Vault ✓ (Profile, education, experience, projects, skills, certifications)
- Phase 3.1: Secure PDF/DOCX Upload ✓ (Validation, hashing, deduplication, storage)
- Phase 3.2: Alembic Migration Foundation ✓ (Baseline migration, reversible schema versioning)
- Phase 3.3: PDF and DOCX Text Extraction ✓ (Embedded-text extraction, safe errors, metadata, migration validation)
- Phase 3.4: Deterministic CV Section Detection ✓ (Structured section storage, deterministic parser, API endpoints, migration validation)
- Phase 3.5: Verified Facts Comparison ✓ (Deterministic vault comparison, safe review findings, migration validation)
- Phase 3.6: CV Version Management ✓ (Version metadata, lineage, lifecycle, primary selection, migration validation)
- Phase 3.7: Verified Master CV Generation ✓ (Truthful DOCX/PDF generation, artifact validation, Unicode PDF rendering)
- Phase 3.8: Document Management Frontend ✓ (Document upload, review, extraction, comparison, CV-version, generation, artifact download workflows)

- Phase 4.1: Core Job and Job Source Foundation ✓ (Backend schema, source compliance policy, normalized job read APIs)
- Phase 4.2: Ingestion Runs and Source Snapshots ✓ (Run lifecycle tracking, bounded snapshot metadata, retention cleanup, read-only run APIs)
- Phase 4.3: First Approved Provider Adapter ✓ (Greenhouse Job Board API, keyless, compliance-gated fetch)
- Phase 4.4: Normalization, Deduplication, and Freshness ✓ (Content refresh, exact-signal duplicate links, lifecycle freshness)
- Phase 4.5: Saved Jobs and Review Workflow ✓ (Review statuses, archive-not-delete, provenance protection)
- Phase 4.6: Job Discovery Frontend ✓ (Job browsing, detail, saved-job review UI)

**Phase 3 CV Document System:** COMPLETED
**Phase 4 Job Discovery:** COMPLETED

**Not Started:**
- Phase 5–14: Analysis/matching/eligibility, CV tailoring, salary recommendations, application answers, application preparation, browser automation, tracking, background automation, authentication, production deployment

---

## Status Legend

| Status | Meaning | Criteria |
|--------|---------|----------|
| `COMPLETED` | Implemented, tested, validated, committed to Git | Implementation exists, tests pass, migrations validated, changes committed and reachable from Git history |
| `IN REVIEW` | Implementation complete, awaiting merge or commit | Code written and tested, pull request open or staging for commit; uncommitted code in working directory |
| `IN PROGRESS` | Active development | Branch exists, partial implementation, tests not yet passing |
| `BLOCKED` | Work blocked by unresolved dependency or external issue | Identified blocker documented; waiting on resolution |
| `NOT STARTED` | Not yet begun | No branch, no implementation |

---

## Current Repository Architecture

### Backend

**Runtime:** Python 3.14, FastAPI 0.114+  
**ORM:** SQLAlchemy 2 with typed models and `Mapped` columns  
**Migrations:** Alembic with reversible schema versioning  
**Validation:** Pydantic schemas with strong typing  
**Database:** SQLite (development); PostgreSQL or Supabase (planned for production)  
**Testing:** pytest with dependency injection via `conftest.py`  
**Server:** Uvicorn (via `fastapi dev` command)

**Directory Structure:**
```
backend/
├── app/
│   ├── main.py                    # FastAPI app, CORS, lifespan
│   ├── api/
│   │   ├── router.py              # Unified API router
│   │   └── routes/                # Feature-specific routers
│   │       ├── candidate_profile.py
│   │       ├── education.py
│   │       ├── experience.py
│   │       ├── project.py
│   │       ├── skill.py
│   │       ├── certification.py
│   │       ├── document.py        # Document upload, extraction, comparison, original-version adoption
│   │       ├── fact_comparison.py # Comparison run retrieval
│   │       ├── cv_version.py      # CV version metadata, lifecycle, master generation
│   │       ├── cv_artifact.py     # Generated CV artifact metadata and downloads
│   │       └── job.py             # Phase 4.1 read-only source/job APIs
│   ├── core/
│   │   ├── config.py              # Settings (document storage path, etc.)
│   │   └── database.py            # SQLAlchemy engine, session, Base
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── candidate_profile.py
│   │   ├── education.py
│   │   ├── experience.py
│   │   ├── project.py
│   │   ├── skill.py
│   │   ├── certification.py
│   │   ├── document.py
│   │   ├── cv_section.py          # Detected CV sections
│   │   ├── fact_comparison.py     # Comparison runs and findings
│   │   ├── cv_version.py          # CV version metadata and lineage
│   │   ├── cv_version_artifact.py # Generated DOCX/PDF artifact metadata
│   │   └── job.py                 # Job sources, normalized jobs, location, compensation, skills
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── candidate_profile.py
│   │   ├── education.py
│   │   ├── experience.py
│   │   ├── project.py
│   │   ├── skill.py
│   │   ├── certification.py
│   │   ├── document.py
│   │   ├── fact_comparison.py
│   │   ├── cv_version.py
│   │   └── job.py
│   ├── services/                  # Business logic
│   │   ├── document_storage.py    # File validation, safe storage
│   │   ├── document_extraction.py # PDF/DOCX text extraction
│   │   ├── document_section_detection.py # Deterministic section detection
│   │   ├── fact_comparison.py     # Deterministic verified-fact comparison
│   │   ├── cv_version.py          # CV version lifecycle rules
│   │   ├── generated_cv_storage.py # Safe generated artifact storage
│   │   ├── verified_master_cv.py  # Verified master CV generation
│   │   └── job.py                 # Phase 4.1 compliance, lifecycle, read/filter rules
├── alembic/
│   ├── env.py                     # Alembic configuration
│   ├── versions/                  # Versioned migrations
│   │   ├── 6a528be87510_baseline_current_schema.py
│   │   ├── b7a3c8d9e012_add_document_extraction_metadata.py (committed)
│   │   ├── d8e9f0a1b2c3_add_missing_facts_vault_tables.py (committed repair)
│   │   ├── c4e7d9a1b2c3_add_cv_section_detection.py (committed)
│   │   ├── e5f6a7b8c9d0_add_fact_comparison.py (committed)
│   │   ├── f6a7b8c9d0e1_add_cv_version_management.py (committed)
│   │   ├── a7b8c9d0e1f2_add_verified_master_cv_generation.py (committed)
│   │   ├── b8c9d0e1f2a3_add_phase_4_1_job_foundation.py (committed)
│   │   └── c9d0e1f2a3b4_add_phase_4_2_ingestion_runs.py (committed)
│   └── alembic.ini                # Migration settings
├── tests/
│   ├── conftest.py                # Fixtures, test database setup
│   ├── test_profile_resources.py  # Candidate facts vault tests
│   ├── test_documents.py          # Upload and document tests
│   ├── test_document_extraction.py # Text extraction tests
│   ├── test_document_section_detection.py # Section detection tests
│   ├── test_fact_comparison.py # Verified facts comparison tests
│   ├── test_cv_version.py      # CV version management tests
│   ├── test_verified_master_cv.py # Verified master CV generation tests
│   ├── test_jobs_phase41.py       # Phase 4.1 job source/job foundation tests
│   └── test_ingestion_phase42.py  # Phase 4.2 ingestion run/snapshot tests
├── .venv/                         # Virtual environment
├── pyproject.toml                 # Tool config (pytest, ruff, mypy)
├── requirements.txt               # Production dependencies
└── requirements-dev.txt           # Development dependencies
```

**Key Dependencies:**
- `fastapi` — REST API framework
- `sqlalchemy[asyncio]` — ORM with async support
- `pydantic` — Request/response validation
- `alembic` — Schema migrations
- `pypdf` — PDF embedded-text extraction
- `python-docx` — DOCX verified-master CV generation
- `reportlab` — Selectable-text PDF verified-master CV generation
- `justmytype`, `justmytype-western-core`, `justmytype-intl-cjk`, `fonttools` — Packaged embedded Noto font loading and glyph preflight for Unicode PDF generation
- `httpx` — HTTP client (test client)
- `pytest` — Testing framework

### Frontend

**Runtime:** Node.js 20+, Next.js 16 with App Router  
**Language:** TypeScript with strict type checking  
**Styling:** Tailwind CSS 4 with PostCSS  
**Testing:** Node test runner (no additional framework required)

**Directory Structure:**
```
frontend/
├── app/
│   ├── layout.tsx                 # Root layout
│   ├── page.tsx                   # Dashboard
│   ├── globals.css                # Tailwind setup
│   └── profile/
│       └── page.tsx               # Profile management page
├── components/
│   └── profile/
│       ├── CandidateProfileForm.tsx   # Profile editing
│       ├── EducationManager.tsx
│       ├── ExperienceManager.tsx
│       ├── ProjectManager.tsx
│       ├── SkillManager.tsx
│       └── CertificationManager.tsx
├── lib/
│   └── api.ts                     # API client functions
├── types/
│   ├── candidate.ts               # Candidate profile types
│   ├── education.ts
│   ├── experience.ts
│   ├── project.ts
│   ├── skill.ts
│   └── certification.ts
├── public/                        # Static assets
├── tests/                         # Component and integration tests
├── package.json                   # Dependencies, scripts
├── tsconfig.json                  # TypeScript configuration
├── next.config.ts                 # Next.js configuration
├── postcss.config.mjs             # PostCSS configuration
├── eslint.config.mjs              # ESLint rules
└── next-env.d.ts                  # Auto-generated Next.js types
```

**Key Dependencies:**
- `next` 16 — React framework with App Router
- `react` 19 — UI library
- `react-dom` 19 — DOM rendering
- `tailwindcss` 4 — Utility CSS
- `typescript` 5 — Type checking
- `eslint` 9 — Linting

### Environment Configuration

**Backend:**
- `backend/.venv/bin/activate` — Python environment activation
- `DOCUMENT_STORAGE_DIR` (env var) — Path to store uploaded files (configured in `app/core/config.py`)
- `.env` file (Git-ignored) — Local database path, secret keys, etc.

**Frontend:**
- `NEXT_PUBLIC_API_URL` (env var, default `http://127.0.0.1:8000`) — Backend API base URL

---

## Completed Functionality

### Phase 1 — Project Foundation ✓ `COMPLETED`

**Status:** COMPLETED (Committed)

**Implemented:**
- FastAPI backend with OpenAPI documentation
- Next.js 16 frontend with App Router and TypeScript
- SQLAlchemy 2 ORM with typed models
- SQLite development database
- CORS middleware (`http://localhost:3000`, `http://127.0.0.1:3000`)
- Health check endpoints (`GET /`, `GET /api/health`)
- Pydantic validation schemas
- pytest testing framework with fixtures
- Environment configuration via `Settings` class
- Git repository with meaningful commit history

**API Endpoints:**
- `GET /` — Root status
- `GET /api/health` — Service health

**Frontend Pages:**
- Dashboard at `/` — Overview and navigation
- Profile page at `/profile` — Facts vault management

**Validation:** ✓ Tests passing (41 total at start of Phase 3.3)  
**Security:** ✓ CORS configured, no secrets in source code

---

### Phase 2 — Verified Candidate Facts Vault ✓ `COMPLETED`

**Status:** COMPLETED (Committed — commit `87c3ae3`)

**Implemented Models and CRUD:**
- **Candidate Profile**: Full name, email, phone, location, professional title, summary, URLs, work authorization, relocation preference, salary expectations, auto-apply settings, verification flag
- **Education**: School/university, degree, field, dates, GPA, achievements
- **Work Experience**: Company, job title, dates, location, employment type, salary, achievements
- **Projects**: Title, description, technologies, URL, dates, achievement metrics
- **Skills**: Skill name, proficiency level, endorsements
- **Certifications**: Certification name, issuing organization, issue/expiry dates, credential ID, credential URL

**API Endpoints (all under `/api`):**
- `GET /profile` — Retrieve profile (GET http://127.0.0.1:8000/api/profile)
- `PUT /profile` — Update profile
- `POST /education`, `GET /education`, `PUT /education/{id}`, `DELETE /education/{id}`
- `POST /experience`, `GET /experience`, `PUT /experience/{id}`, `DELETE /experience/{id}`
- `POST /projects`, `GET /projects`, `PUT /projects/{id}`, `DELETE /projects/{id}`
- `POST /skills`, `GET /skills`, `PUT /skills/{id}`, `DELETE /skills/{id}`
- `POST /certifications`, `GET /certifications`, `PUT /certifications/{id}`, `DELETE /certifications/{id}`

**Frontend Components:**
- `CandidateProfileForm` — Edit profile fields with real-time validation
- `EducationManager` — Add, edit, delete education records
- `ExperienceManager` — Add, edit, delete work experience
- `ProjectManager` — Add, edit, delete projects
- `SkillManager` — Add, edit, delete skills
- `CertificationManager` — Add, edit, delete certifications

**Database Schema:**
- `candidate_profiles` table (id=1 by design, single user)
- `education` table with FK to candidate_profiles
- `experience` table with FK to candidate_profiles
- `projects` table with FK to candidate_profiles
- `skills` table with FK to candidate_profiles
- `certifications` table with FK to candidate_profiles
- All with `created_at` and `updated_at` timestamps

**Validation:** ✓ Comprehensive tests for all CRUD operations  
**Security:** ✓ All fields validated, no direct model exposure

---

### Phase 3.1 — Secure PDF and DOCX Upload ✓ `COMPLETED`

**Status:** COMPLETED (Committed — commit `d1fffe9`)

**Implemented Security:**
- **File Extension Validation** — Allowed: `.pdf`, `.docx`
- **Media Type Signature Validation**:
  - PDF: Must start with `%PDF` or `%PDF-1.x`
  - DOCX: Must be valid ZIP with `[Content_Types].xml` and `word/document.xml`
- **Size Limits** — Configurable max file size (default: 50 MB)
- **SHA-256 Hashing** — Computed for every upload; used for duplicate detection
- **Stored Filename Randomization** — Files stored as UUID.pdf or UUID.docx; originals preserved in metadata
- **Path Traversal Prevention** — `assert_within_storage_directory()` validates all paths
- **Duplicate Detection** — Unique constraint `(candidate_profile_id, sha256_hash)` prevents re-upload of identical files
- **Primary CV Management** — Only one original CV can be marked `is_primary`; switching primary unmarks previous
- **Safe Deletion** — Uploaded files removed from disk; soft deletion via database
- **Git Ignore** — Uploaded files stored outside `frontend/public/` (configurable)

**Document Model Fields:**
- `candidate_profile_id` — FK to candidate_profiles
- `original_filename` — Sanitized user-provided filename
- `stored_filename` — Random server-side filename
- `file_extension` — `.pdf` or `.docx`
- `media_type` — MIME type (application/pdf, application/vnd.openxmlformats...)
- `size_bytes` — File size
- `sha256_hash` — Content hash for deduplication
- `document_type` — "original_cv" or other types (extensible)
- `upload_status` — "validated" (current), later "pending_extraction", "extraction_failed"
- `is_primary` — Boolean for primary CV marker
- `created_at`, `updated_at` — Timestamps

**API Endpoints:**
- `POST /documents/upload` — Upload CV with form data (file, document_type, is_primary)
- `GET /documents` — List all candidate documents
- `GET /documents/{id}` — Retrieve single document metadata
- `PATCH /documents/{id}/primary` — Mark as primary original CV
- `DELETE /documents/{id}` — Delete document and remove file

**Tests:**
- `test_documents.py` — Upload validation, duplicate detection, primary CV switching, deletion
- Covers validation failures, edge cases, permission checks

**Validation:** ✓ All tests passing  
**Security:** ✓ All OWASP file-upload risks mitigated

---

### Phase 3.2 — Alembic Migration Foundation ✓ `COMPLETED`

**Status:** COMPLETED (Committed — commit `cc32c10`)

**Implemented:**
- **Alembic Setup**: `alembic init` completed, `env.py` configured
- **Baseline Migration** (`6a528be87510_baseline_current_schema.py`):
  - Original committed baseline creates the `documents` table
  - Committed forward repair migration `d8e9f0a1b2c3_add_missing_facts_vault_tables.py` creates the missing Facts Vault tables without rewriting committed migration history
  - Revisions properly configured; down_revision set to None (baseline)
- **Reversible Migrations**: All migrations include `upgrade()` and `downgrade()` functions
- **Migration Commands**:
  - `alembic heads` — Check current migration head (committed Phase 4.2 head is `c9d0e1f2a3b4`)
  - `alembic upgrade head` — Apply all pending migrations
  - `alembic downgrade -1` — Rollback one migration

**Validation Strategy:**
- Baseline migration tested against temporary SQLite database
- Schema creation verified with `alembic upgrade head`
- Downgrade path verified with `alembic downgrade base`
- Existing candidate data preserved across upgrade/downgrade
- Alembic is the authoritative schema mechanism for application databases; app startup must not rely on `Base.metadata.create_all()`
- Local setup requires running `alembic upgrade head` from `backend/` before starting the API against a new database

**Current Repaired Migration Chain:**
- `6a528be87510_baseline_current_schema` (committed baseline; creates `documents`)
- `b7a3c8d9e012_add_document_extraction_metadata` (Phase 3.3, committed and validated)
- `d8e9f0a1b2c3_add_missing_facts_vault_tables` (committed repair for Facts Vault tables)
- `c4e7d9a1b2c3_add_cv_section_detection` (Phase 3.4, committed and validated)
- `e5f6a7b8c9d0_add_fact_comparison` (Phase 3.5, committed and validated)
- `f6a7b8c9d0e1_add_cv_version_management` (Phase 3.6, committed, safely migrated, and validated)
- `a7b8c9d0e1f2_add_verified_master_cv_generation` (Phase 3.7, committed, safely migrated, and validated)
- `b8c9d0e1f2a3_add_phase_4_1_job_foundation` (Phase 4.1, committed, safely migrated, and validated)
- `c9d0e1f2a3b4_add_phase_4_2_ingestion_runs` (Phase 4.2, committed, safely migrated, and validated)

**Validation:** ✓ Baseline migration tested; reversible structure confirmed; `alembic heads` reports one working-tree head: `b8c9d0e1f2a3`
**Data Preservation:** ✓ No data loss on upgrade/downgrade

**Existing Database Adoption:** ✓ The local `backend/careerpilot.db` was safely adopted by stamping the verified repair revision `d8e9f0a1b2c3`, applying the Phase 3.4 migration `c4e7d9a1b2c3`, safely upgrading to the Phase 3.5 migration `e5f6a7b8c9d0`, safely upgrading to the Phase 3.6 migration `f6a7b8c9d0e1`, safely upgrading to the Phase 3.7 migration `a7b8c9d0e1f2`, and safely upgrading to the Phase 4.1 migration `b8c9d0e1f2a3`. Database integrity passed; `cv_sections`, `fact_comparison_runs`, `fact_comparison_findings`, `cv_versions`, and `cv_version_artifacts` exist.

---

### Phase 3.3 — PDF and DOCX Text Extraction (COMPLETED) ✅

**Status:** COMPLETED (Committed — commit `7b48890`)

**Implemented:**
- **PDF Text Extraction** (`extract_document_text()`):
  - Uses `pypdf.PdfReader` to extract embedded text
  - Handles encrypted PDFs safely
  - Handles malformed PDFs gracefully
  - Records page count and extracted character count
  - Returns `no_text` for textless or image-only PDFs
  - **OCR remains intentionally out of scope**

- **DOCX Text Extraction** (`extract_docx_text()`):
  - Validates DOCX structure and extracts paragraphs from `word/document.xml`
  - Handles malformed or incomplete DOCX files safely
  - Preserves paragraph boundaries in extracted plain text

- **Text Normalization** (`normalize_text()`):
  - Converts `\r\n` and `\r` to `\n`
  - Replaces tabs with spaces
  - Collapses repeated whitespace and blank lines
  - Returns clean, readable text

- **Extraction Status Tracking**:
  - `pending` — Document uploaded, not yet extracted
  - `processing` — Extraction in progress
  - `completed` — Text extracted successfully
  - `no_text` — No embedded text found
  - `failed` — Extraction failed with a safe error recorded

- **Metadata Captured**:
  - `extracted_text` — Full document text (available only in detail responses)
  - `extraction_error` — Safe error message for failed extractions
  - `extracted_at` — Timestamp of extraction attempt
  - `page_count` — Number of pages for PDF documents
  - `extracted_character_count` — Character count of extracted text

- **Safe Error Handling**:
  - Encrypted PDFs: recorded as unsupported
  - Malformed files: recorded as invalid or corrupted
  - Missing files: recorded as missing without exposing paths
  - Text size limit exceeded: recorded as configured-size violation

- **Re-extraction Support**:
  - Re-extract via `POST /api/documents/{document_id}/extract`
  - Previous errors are cleared on success
  - No OCR or external document service is used

**API Endpoint:**
- `POST /api/documents/{document_id}/extract` — Trigger text extraction for validated document

**Document Model Extension (Migration `b7a3c8d9e012`):**
```python
op.add_column("documents", sa.Column("extraction_status", sa.String(50), server_default="pending"))
op.add_column("documents", sa.Column("extracted_text", sa.Text(), nullable=True))
op.add_column("documents", sa.Column("extraction_error", sa.Text(), nullable=True))
op.add_column("documents", sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True))
op.add_column("documents", sa.Column("page_count", sa.Integer(), nullable=True))
op.add_column("documents", sa.Column("extracted_character_count", sa.Integer(), nullable=True))
```

**Tests** (`test_document_extraction.py`):
- ✓ PDF text extraction and DOCX text extraction
- ✓ PDF page count and DOCX paragraph preservation
- ✓ Character-count storage and status transitions
- ✓ Missing document, missing file, corrupt PDF, corrupt DOCX, encrypted PDF, and `no_text` cases
- ✓ Safe re-extraction, path traversal protection, list/detail response behavior, and extraction-size limit enforcement

**Validation:**
- ✓ 43 backend tests passed
- ✓ `python -m compileall app` passed
- ✓ Alembic has one head: `b7a3c8d9e012`
- ✓ Upgrade, downgrade, and re-upgrade validated using an isolated temporary SQLite database
- ✓ The real development database remained unchanged during the final validation

**Known Limitations:**
- ❌ OCR remains intentionally out of scope for scanned PDFs or image-only documents
- ❌ Advanced formatting elements such as tables, images, headers, and footers are not extracted

---

## Development Phases and Milestones

### Phase 1 — Project Foundation

**Milestone Status:** ✓ COMPLETED

**Goal:** Establish backend, frontend, database, and testing infrastructure.

**Scope:**
- FastAPI application with OpenAPI documentation
- Next.js 16 frontend with TypeScript and Tailwind CSS
- SQLAlchemy 2 ORM with SQLite development database
- CORS configuration for local development
- Health check endpoints
- Pytest testing framework
- Git repository with initial commits

**Backend Work:**
- Create FastAPI app with CORS, lifespan handler, health endpoints
- Set up SQLAlchemy database connection and Base class
- Configure database engine (SQLite)
- Create first test fixtures

**Frontend Work:**
- Initialize Next.js 16 project with TypeScript
- Configure Tailwind CSS and PostCSS
- Create root layout and dashboard page
- Set up TypeScript types for API responses

**Database Work:**
- SQLite development database managed through Alembic migrations
- New local databases require `alembic upgrade head` before API startup

**API Endpoints:**
- `GET /` — Root status message
- `GET /api/health` — Service health check

**Testing Requirements:**
- Health endpoint returns expected structure
- CORS headers present for frontend origin
- Database connection verified on startup

**Definition of Done:**
- Backend starts without errors: `fastapi dev app/main.py`
- Frontend builds without errors: `npm run build`
- Health check responds: `curl http://localhost:8000/api/health`
- All tests pass
- No type errors: `npx tsc --noEmit`

---

### Phase 2 — Verified Candidate Facts Vault

**Milestone Status:** ✓ COMPLETED

**Goal:** Implement core candidate data model and CRUD operations for verified career facts.

**Scope:**
- Candidate profile with contact and preference information
- Education records
- Work experience records
- Project portfolio records
- Skills inventory
- Certifications and credentials

**Required Backend Work:**
- SQLAlchemy models for each entity with typed columns
- Pydantic request/response schemas for validation
- FastAPI routes with CRUD operations
- Database relationships and foreign keys

**Required Frontend Work:**
- React components for form entry
- Type definitions matching backend schemas
- API client functions for each endpoint
- Form state management and validation

**Main API Routes:**
- `GET /api/profile` — Fetch candidate profile
- `PUT /api/profile` — Update candidate profile
- `POST /api/education`, `GET /api/education`, `PUT /api/education/{id}`, `DELETE /api/education/{id}`
- `POST /api/experience`, `GET /api/experience`, `PUT /api/experience/{id}`, `DELETE /api/experience/{id}`
- `POST /api/projects`, `GET /api/projects`, `PUT /api/projects/{id}`, `DELETE /api/projects/{id}`
- `POST /api/skills`, `GET /api/skills`, `PUT /api/skills/{id}`, `DELETE /api/skills/{id}`
- `POST /api/certifications`, `GET /api/certifications`, `PUT /api/certifications/{id}`, `DELETE /api/certifications/{id}`

**Database Schema:**
- `candidate_profiles` (single row, id=1)
- `education`, `experience`, `projects`, `skills`, `certifications` (all with FK to candidate_profiles)
- Unique constraints on appropriate fields
- Timestamps on all tables

**Security Requirements:**
- All input validated via Pydantic
- No direct ORM model exposure
- Safe error messages (no stack traces)
- Timestamps immutable after creation

**Testing Requirements:**
- CRUD operations for each entity
- Validation failure handling
- Foreign key constraint enforcement
- Missing record (404) behavior
- Empty list handling

**Definition of Done:**
- All models and schemas defined
- Routes register without errors
- All CRUD tests pass
- Frontend components render and save/update data
- No type errors in frontend or backend

---

### Phase 3 — CV Document System

#### Phase 3.1 — Secure PDF and DOCX Upload

**Milestone Status:** ✓ COMPLETED

**Goal:** Enable secure upload and storage of CV documents with validation, deduplication, and access controls.

**Scope:**
- Accept PDF and DOCX file uploads
- Validate file extension, media type, and content signature
- Enforce file size limits
- Compute SHA-256 content hashes
- Prevent directory traversal
- Detect and reject duplicate uploads
- Store files outside web root with randomized filenames
- Support primary CV designation
- Provide safe deletion

**Required Backend Work:**
- Document SQLAlchemy model with metadata columns
- Pydantic Document schema for responses
- Document upload route with multi-part form handling
- File validation service (`document_storage.py`)
- Duplicate detection query
- Primary CV designation logic
- Deletion with file cleanup

**Required Frontend Work:**
- File upload form (deferred to Phase 3.8)

**API Endpoints:**
- `POST /api/documents/upload` — Upload CV (multipart/form-data)
- `GET /api/documents` — List candidate documents
- `GET /api/documents/{id}` — Get document metadata
- `PATCH /api/documents/{id}/primary` — Mark as primary CV
- `DELETE /api/documents/{id}` — Delete document

**Database Schema Changes:**
- Create `documents` table with columns:
  - id (pk, auto-increment)
  - candidate_profile_id (fk, cascade delete)
  - original_filename, stored_filename, file_extension, media_type
  - size_bytes, sha256_hash (for deduplication)
  - document_type (enum-like, "original_cv")
  - upload_status ("validated" for Phase 3.1)
  - is_primary (boolean)
  - created_at, updated_at (timestamps)

**Security Requirements:**
- Extension validation: `.pdf`, `.docx` only
- MIME type validation: application/pdf, application/vnd.openxmlformats...
- File signature validation:
  - PDF: `%PDF` or `%PDF-1.x` at byte offset 0
  - DOCX: Valid ZIP with required XML structure
- Path traversal prevention: `assert_within_storage_directory()`
- Size limit enforcement: Default 50 MB (configurable)
- Duplicate prevention: Unique constraint on (candidate_profile_id, sha256_hash)
- Primary CV enforcement: Only one original CV can be primary
- Safe deletion: Files removed from disk; database records retained/soft-deleted

**Testing Requirements:**
- Valid PDF upload succeeds with correct metadata
- Valid DOCX upload succeeds
- Invalid file extension rejected (400 Bad Request)
- Invalid MIME type rejected (400)
- Invalid file signature rejected (400)
- File size exceeds limit rejected (400)
- Duplicate upload detected (409 Conflict)
- Primary CV switch unmarks previous primary
- Document deletion removes file and record
- Path traversal attempt fails safely

**Definition of Done:**
- Document model and schema created
- Upload route implements all validations
- All upload tests pass
- Duplicate detection working
- Primary CV logic correct
- Deletion removes both file and record
- No security vulnerabilities (no path traversal, no unrestricted uploads)
- Stored files outside web root

---

#### Phase 3.2 — Alembic Migration Foundation

**Milestone Status:** ✓ COMPLETED

**Goal:** Establish reversible schema versioning with Alembic.

**Scope:**
- Initialize Alembic
- Create baseline migration of all current schema (Phases 1, 2, 3.1)
- Test migration upgrade and downgrade paths
- Document migration conventions

**Required Backend Work:**
- `alembic init` setup
- Configure `env.py` for SQLAlchemy connection
- Create baseline migration capturing all models
- Test upgrade/downgrade against temporary database

**Database Work:**
- Baseline migration (`6a528be87510_baseline_current_schema.py`) encodes all Phase 1, 2, 3.1 tables
- All tables with correct column types, constraints, indexes
- Foreign key relationships with cascade behavior
- Unique constraints on appropriate fields
- Indexes on foreign keys

**Commands:**
```bash
cd backend
source .venv/bin/activate
alembic upgrade head          # Apply all migrations
alembic downgrade base        # Rollback to empty schema
alembic heads                 # Show current migration head
alembic current               # Show database's current revision
```

**Migration Conventions:**
- All migrations reversible (both `upgrade()` and `downgrade()`)
- No destructive column/table operations without strong justification
- Migration revision ID: Generated by Alembic (8-char hex)
- Down-revision chain: Latest migration's `down_revision` points to previous
- Baseline revision: `down_revision = None`

**Testing Requirements:**
- Baseline migration creates all expected tables
- Columns have correct types and constraints
- Foreign keys work correctly (cascade on delete)
- Downgrade returns schema to baseline
- Upgrade/downgrade cycle preserves candidate data

**Definition of Done:**
- `alembic heads` returns current head revision
- `alembic upgrade head` succeeds on fresh SQLite
- `alembic downgrade base` succeeds without error
- All existing table structures present after upgrade
- Temporary database can be deleted without affecting development database

---

#### Phase 3.3 — PDF and DOCX Text Extraction

**Milestone Status:** ✅ COMPLETED

**Goal:** Extract embedded text from uploaded PDFs and DOCX files; normalize and store for analysis.

**Scope:**
- Extract text from PDF using `pypdf` library
- Extract text from DOCX using XML parsing
- Normalize extracted text (whitespace, line breaks)
- Enforce text size limits
- Track extraction status and metadata
- Handle errors gracefully (encrypted PDFs, malformed files)
- Re-extraction support

**Required Backend Work:**
- Document extraction service (`document_extraction.py`):
  - `extract_document_text(document: Document) -> ExtractionResult`
  - PDF embedded-text extraction with page and character counts
  - DOCX paragraph extraction with safe malformed-file handling
  - `normalize_text(text: str) -> str`
  - Safe error handling with `DocumentExtractionError`
- Document API route: `POST /api/documents/{id}/extract`
- Database migration: Add extraction status columns to documents table

**Required Frontend Work:**
- Deferred to Phase 3.8 (Document Management Frontend)

**API Endpoints:**
- `POST /api/documents/{id}/extract` — Extract text from validated document

**Database Schema Changes:**
- New Document columns (migration `b7a3c8d9e012`):
  - `extraction_status` (String, default "pending"): pending, processing, completed, no_text, failed
  - `extracted_text` (Text, nullable): Extracted document text (NULL if failed)
  - `extraction_error` (Text, nullable): Safe error message if extraction failed
  - `extracted_at` (DateTime, nullable): Extraction timestamp
  - `page_count` (Integer, nullable): Page count (PDF only)
  - `extracted_character_count` (Integer, nullable): Character count of extracted text

**Security Requirements:**
- No code execution during extraction
- Safe error messages (no file paths, stack traces)
- Text size limits enforced (default 5 MB per document)
- Encrypted PDF detection and rejection
- Malformed file handling

**Testing Requirements:**
- Valid PDF extraction succeeds with text and page count
- Valid DOCX extraction succeeds with text
- Encrypted PDF raises error, stored in extraction_error
- Malformed PDF raises error, stored gracefully
- Malformed DOCX raises error, stored gracefully
- Empty document handled
- Text normalization works correctly
- Character count accurate
- Re-extraction clears previous data and re-extracts
- API response includes all metadata

**Out-of-Scope (for Future Phases):**
- OCR for scanned/image-only PDFs
- DOCX headers, footers, text boxes, advanced formatting
- Batch extraction of multiple documents
- Scheduled extraction workers

**Known Limitations:**
- No OCR — Scanned PDFs cannot be extracted
- No advanced DOCX formatting — Headers, footers, images not extracted
- No headers/footers in PDFs — Only main document text
- Character limit — 5 MB max extracted text

**Definition of Done:**
- `document_extraction.py` service written and tested
- Migration `b7a3c8d9e012` committed, validated, and reversible
- API route correctly handles extraction request
- Extraction status and metadata stored in database
- All extraction tests pass
- Safe error handling verified
- No security vulnerabilities

**Dependencies:**
- Requires Phase 3.1 (Secure Upload) ✓
- Requires Phase 3.2 (Alembic Foundation) ✓

---

#### Phase 3.4 — Deterministic CV Section Detection

**Milestone Status:** ✓ COMPLETED

**Goal:** Automatically detect and segment CV sections (contact, experience, education, skills, etc.) from extracted text.

**Scope:**
- Parse extracted text into logical sections
- Identify section boundaries via heading detection
- Map sections to standard CV structure
- Handle missing or non-standard sections
- Provide confidence scores for each detection
- Support re-detection on updated text

**Database Schema Changes:**
- Phase 3.4 depends on the committed repair migration `d8e9f0a1b2c3`, which creates missing Facts Vault tables while preserving committed migration history.
- Repaired migration chain:
  - `6a528be87510`
  - `b7a3c8d9e012`
  - `d8e9f0a1b2c3`
  - `c4e7d9a1b2c3`
- New table `cv_sections`:
  - id, document_id (fk), section_order, section_type, title, start_char, end_char, content_text, confidence, detection_method, created_at
  - Unique constraint: (document_id, section_type, start_char)
- New document section-detection metadata:
  - `section_detection_status`: pending, processing, completed, failed
  - `section_detection_error`: Safe failure message, if any
  - `section_detected_at`: Timestamp of latest detection attempt
  - `section_count`: Number of currently stored detected sections
  - `section_detection_method`: Deterministic parser method version

**Supported Sections:**
- Contact / Personal Information
- Professional Summary / Objective
- Work Experience
- Education
- Skills
- Projects / Portfolio
- Certifications
- Awards / Honors
- Publications
- Volunteering
- Languages
- Interests
- References
- Additional sections (catch-all for unrecognized)

**Algorithm Approach:**
- Heading detection: Look for all-caps lines, numbered lines, common section keywords
- Heading aliases: Support appropriate UK and US variants ("Work History" → "Work Experience", "Technical Skills" → "Skills")
- Contact block inference: Deterministic parsing of document-start phone, email, location, and profile-link patterns
- Section ordering: Preserves source order, including non-standard ordering and repeated genuine section types
- Character ranges: Deterministic, non-overlapping ranges that preserve paragraph and bullet boundaries
- Confidence scoring: Deterministic scores based on heading match quality, section completeness, and known patterns
- Safe fallback handling: Unknown or missing sections are handled without inventing facts
- Safe re-detection: Replaces prior sections without duplicates; failed re-detection preserves previously valid sections and cannot leave status permanently `processing`
- External services: No AI, OCR, embeddings, internet requests, or external services are used
- Candidate Facts Vault: Candidate facts are not modified by section detection

**API Endpoints:**
- `POST /api/documents/{id}/detect-sections` — Trigger section detection
- `GET /api/documents/{id}/sections` — Retrieve detected sections

**Testing Requirements:**
- Standard CV section detection (all sections present)
- Missing sections handled gracefully
- Non-standard order handled
- Contact block correctly identified
- Confidence scores reasonable
- Re-detection updates sections
- Edge cases (empty sections, repeated sections)

**Dependencies:**
- Requires Phase 3.3 (Text Extraction) ✓

**Definition of Done:**
- Section detection algorithm implemented, deterministic, and committed
- API endpoints created and registered
- Database migration for `cv_sections` table and document metadata committed, validated, and applied locally
- 55 backend tests passed
- Python compilation passed
- Alembic has one head: `c4e7d9a1b2c3`
- The real development database was safely adopted by stamping the verified repair revision and applying only the Phase 3.4 migration
- Database integrity passed
- `cv_sections` exists
- Document section-detection metadata exists
- The database schema matches the SQLAlchemy models
- Deterministic section detection, contact inference, aliases, ordering, character ranges, confidence, safe re-detection, and failure recovery are complete
- No AI, OCR, embeddings, or external services are used

---

#### Phase 3.5 — Verified Facts Comparison

**Milestone Status:** ✓ COMPLETED

**Goal:** Compare extracted CV text and detected sections against verified candidate facts; identify matches, mismatches, and unverified claims.

**Scope:**
- Match detected work experience sections to verified experience records
- Match detected education sections to verified education records
- Match detected skills to verified skills
- Match detected projects to verified projects
- Match detected certifications to verified certifications
- Identify unverified claims (text not in vault)
- Identify missing verified facts (vault item not in CV)
- Detect date conflicts, organization mismatches, skill discrepancies
- Flag uncertain matches for manual review

**Database Schema Changes:**
- New migration `e5f6a7b8c9d0_add_fact_comparison.py` follows committed revision `c4e7d9a1b2c3`
- New table `fact_comparison_runs`:
  - id, document_id, status, started_at, completed_at, error
  - total_findings, confirmed_count, mismatch_count, missing_verified_count, unverified_claim_count, manual_review_count
  - comparison_version, is_latest_successful, created_at
- New table `fact_comparison_findings`:
  - id, comparison_run_id, document_section_id, sort_order
  - entity_type, verified_entity_id, field_name, finding_type
  - bounded CV evidence, bounded verified evidence, normalized values
  - confidence, severity, explanation, requires_manual_review, dedupe_key, created_at
- Foreign keys:
  - `fact_comparison_runs.document_id` → `documents.id` with cascade delete
  - `fact_comparison_findings.comparison_run_id` → `fact_comparison_runs.id` with cascade delete
  - `fact_comparison_findings.document_section_id` → `cv_sections.id` with set-null on section deletion
- Unique constraint prevents duplicate findings within a run: `(comparison_run_id, dedupe_key)`

**Match Results:**
- `confirmed` — CV text closely matches verified fact
- `possible_mismatch` — CV text differs from verified fact and needs review
- `missing_verified_fact` — Verified fact not found in CV; absence is not treated as false
- `unverified_claim` — CV claims something not matched to the verified vault
- `date_conflict`, `organisation_conflict`, `skill_conflict` — Deterministic conflict categories requiring review where applicable
- `manual_review` — Ambiguous or weak match that must not be confirmed automatically

**Important Matching Rules:**
- **Never assume absence is falsity** — If a skill is not in the CV but is in the vault, the candidate may have omitted it intentionally for brevity or relevance
- **Flag, don't conclude** — Uncertain matches marked for review, never treated as proof of false claims
- **Only eligible vault truth is used** — Candidate profile fields require `facts_verified=True`; education, work experience, projects, skills, and certifications require `verified=True`
- **No automatic vault changes** — Comparison runs never modify, verify, reject, or delete Candidate Facts Vault records
- **Bounded evidence only** — Findings store bounded excerpts and explanations, not full CV content
- **Manual review required for:**
  - Date discrepancies (e.g., CV says 2020–2022, vault says 2019–2023)
  - Organization name variations (e.g., "Microsoft" vs "Microsoft Corp")
  - Role title variations (e.g., "Senior Engineer" vs "Software Engineer III")
  - New claims not in vault (potential new facts to add)

**API Endpoints:**
- `POST /api/documents/{document_id}/compare-facts` — Trigger deterministic comparison
- `GET /api/documents/{document_id}/fact-comparison` — Retrieve latest successful comparison, falling back to latest run when no success exists
- `GET /api/fact-comparisons/{comparison_id}` — Retrieve a specific comparison run and findings
- `GET /api/documents/{document_id}` — Includes concise `fact_comparison_summary`
- `GET /api/documents` — Excludes findings and comparison summary by design

**Testing Requirements:**
- ✓ Confirmed profile facts and harmless formatting differences
- ✓ Profile mismatch detection
- ✓ Education matching and date conflicts
- ✓ Work-experience company matching, organisation suffix variants, and date conflicts
- ✓ Project matching
- ✓ Skill confirmation, unverified skill claims, and ambiguous manual review
- ✓ Certification matching
- ✓ Missing verified facts and unverified CV claims
- ✓ Only verified/eligible vault records treated as truth
- ✓ Precondition rejection before extraction and section detection
- ✓ Missing document returns 404
- ✓ Stable deterministic ordering
- ✓ Safe re-comparison, no duplicate active findings, previous success preserved after failure
- ✓ Status does not remain `processing`
- ✓ Safe error responses without internal paths or raw exceptions
- ✓ Evidence and explanation length limits
- ✓ Findings excluded from document-list responses; summary included in document detail
- ✓ Alembic metadata parity and migration upgrade/downgrade/re-upgrade

**Dependencies:**
- Requires Phase 2 (Facts Vault) ✓
- Requires Phase 3.3 (Text Extraction) ✓
- Requires Phase 3.4 (Section Detection) ✓

**Definition of Done:**
- Deterministic matching algorithm implemented with no AI, embeddings, OCR, internet requests, or external services
- Comparison run/finding schema created and reversible
- API endpoints created and registered
- All backend tests pass
- Isolated migration upgrade, downgrade to `c4e7d9a1b2c3`, and re-upgrade pass
- Real development database safely upgraded from `c4e7d9a1b2c3` to `e5f6a7b8c9d0`
- No false CV claims are marked as confirmed
- Implementation committed and documented with Git revision `50af2b1`

**Validation Evidence (Completed):**
- ✓ 77 backend tests passed
- ✓ Targeted Phase 3.5 tests passed
- ✓ `python -m compileall app` passed
- ✓ FastAPI import and OpenAPI route registration passed (`openapi_paths=23`)
- ✓ `alembic heads` reports exactly one head: `e5f6a7b8c9d0`
- ✓ Alembic metadata parity test passed
- ✓ Temporary migration target: `/private/tmp/careerpilot-phase35-ack69xh4/migration-validation.db`
- ✓ Isolated upgrade to `e5f6a7b8c9d0`, downgrade to `c4e7d9a1b2c3`, and re-upgrade to `e5f6a7b8c9d0` passed
- ✓ Real development database safely upgraded from `c4e7d9a1b2c3` to `e5f6a7b8c9d0`
- ✓ Database integrity passed
- ✓ `fact_comparison_runs` and `fact_comparison_findings` tables were created successfully
- ✓ Deterministic verified-facts comparison is complete
- ✓ Comparison history and latest-successful-run handling are complete
- ✓ Stable finding ordering and deduplication are complete
- ✓ Safe re-comparison and failure recovery are complete
- ✓ Verified work responsibilities, achievements, and descriptions are not incorrectly reported as unverified claims
- ✓ Verified project features, achievements, and descriptions are not incorrectly reported as unverified claims
- ✓ Descriptive years do not create false date conflicts
- ✓ Genuine unmatched claims and genuine date conflicts remain detectable
- ✓ Ambiguous date evidence is sent for manual review
- ✓ Candidate Facts Vault records remain read-only
- ✓ No AI, embeddings, OCR, external services, or network requests are used

---

#### Phase 3.6 — CV Version Management

**Milestone Status:** COMPLETED

**Goal:** Support multiple CV version metadata records with safe source relationships, parent/child lineage, lifecycle status, primary-version selection, and version history.

**Scope:**
- Track original uploaded CV documents as adoptable `original` CV versions
- Track parsed, verified master, and tailored version metadata without generating new content
- Store source document relationships, parent version relationships, and candidate ownership
- Maintain lifecycle status, archive state, and primary selection per candidate/version type
- Provide concise API responses with metadata only
- Preserve uploaded source documents, detected sections, fact-comparison history, and Candidate Facts Vault records

**Database Schema Changes:**
- New migration `f6a7b8c9d0e1_add_cv_version_management.py` follows committed revision `e5f6a7b8c9d0`
- New table `cv_versions`:
  - id, candidate_profile_id, source_document_id, parent_version_id
  - version_type, status, display_name, description, job_reference
  - is_primary, storage_path, mime_type, file_size, sha256
  - created_at, updated_at, archived_at
- Foreign keys:
  - `cv_versions.candidate_profile_id` → `candidate_profiles.id` with cascade delete
  - `cv_versions.source_document_id` → `documents.id` with set-null on source document deletion
  - `cv_versions.parent_version_id` → `cv_versions.id` with restrict semantics for deliberate history preservation
- Constraints and indexes:
  - Validated version types: `original`, `parsed`, `verified_master`, `tailored`
  - Validated statuses: `draft`, `ready`, `archived`, `failed`
  - Unique source-document relationship prevents duplicate original CV versions for the same uploaded document
  - Partial unique primary index allows only one primary version per candidate and version type
  - Candidate, source-document, parent-version, status, version-type, and candidate/type indexes

**Version Types:**
- `original` — Metadata record for an uploaded original CV document
- `parsed` — Metadata record derived from an original version
- `verified_master` — Metadata record derived from a parsed or earlier verified-master version
- `tailored` — Metadata record derived from a verified-master version, with optional safe job reference text

**Version Relationships:**
- `original` versions may reference validated uploaded original CV documents
- `parsed` versions require an `original` parent
- `verified_master` versions require a `parsed` or earlier `verified_master` parent
- `tailored` versions require a `verified_master` parent
- Parent and child versions must belong to the same candidate
- Source documents and versions must belong to the same candidate
- Self-parent and circular ancestry are rejected
- Deleting versions with child history is rejected by default
- Archiving preserves children and ancestry

**Primary Version:**
- Only one primary CV version per candidate and version type
- Setting a version primary unsets the prior primary of the same type in the same transaction
- Different version types may each have their own primary
- Archived versions cannot remain primary
- Failed versions cannot become primary
- Failed primary-switch writes roll back to the prior valid state

**API Endpoints:**
- `POST /api/documents/{document_id}/cv-version` — Adopt a validated uploaded original CV document as an original CV version
- `POST /api/cv-versions` — Create CV version metadata
- `GET /api/cv-versions` — List candidate CV versions in stable order
- `GET /api/cv-versions/{version_id}` — Retrieve one CV version metadata record
- `PATCH /api/cv-versions/{version_id}` — Update allowed metadata fields
- `PATCH /api/cv-versions/{version_id}/primary` — Set a CV version as primary
- `PATCH /api/cv-versions/{version_id}/archive` — Archive a CV version safely
- `DELETE /api/cv-versions/{version_id}` — Hard-delete only when no child history exists
- `GET /api/cv-versions/{version_id}/history` — Retrieve ancestry and immediate children

**Testing Requirements:**
- ✓ Adopt original version from validated document
- ✓ Adoption is idempotent
- ✓ Missing and invalid source documents are rejected
- ✓ Parsed, verified-master, and tailored parent rules are enforced
- ✓ Invalid parent type, self-parent, circular ancestry, cross-candidate parent, and cross-candidate source document are rejected
- ✓ List ordering is stable
- ✓ Retrieve, update allowed metadata, and reject immutable relationship-field mutation
- ✓ Primary selection, primary switching, separate per-type primaries, archived/failed primary rejection, archive clearing, and failed-switch rollback are covered
- ✓ Archive preserves children and history
- ✓ Unsafe deletion with children is rejected
- ✓ Safe deletion without children succeeds
- ✓ Uploaded source document, detected sections, comparison history, and Candidate Facts Vault records survive CV version deletion/lifecycle changes
- ✓ API responses exclude absolute storage paths, binary content, extracted text, and stored filenames
- ✓ Alembic metadata parity and temporary migration upgrade/downgrade/re-upgrade are validated

**Dependencies:**
- Requires Phase 2 (Facts Vault) ✓
- Requires Phase 3.5 (Facts Comparison) ✓
- Future job-specific tailoring depends on Phase 4+ job records; Phase 3.6 stores only a nullable `job_reference` metadata placeholder

**Definition of Done:**
- Dedicated `CVVersion` model, schemas, service, API routes, and migration implemented
- Version management routes registered and typed
- Source-document adoption implemented and idempotent
- Parent/child history, archive/delete safety, primary selection, and failure rollback implemented
- Migration `f6a7b8c9d0e1` created, reversible, validated, and safely applied to the real development database
- Targeted Phase 3.6 tests passed
- Complete backend suite passed
- Python compilation, FastAPI import, OpenAPI route validation, Alembic metadata parity, `alembic history`, and `alembic heads` passed
- No CV content generation, DOCX/PDF generation, AI, embeddings, OCR, external services, or network requests are introduced
- Candidate Facts Vault records remain read-only
- Implementation committed and documented with Git revision `c3e738f`
- Real development database safely upgraded from `e5f6a7b8c9d0` to `f6a7b8c9d0e1`

**Validation Evidence (Completed):**
- ✓ 39 targeted Phase 3.6 tests passed
- ✓ 116 complete backend tests passed
- ✓ `python -m compileall app` passed
- ✓ FastAPI import and OpenAPI route validation passed
- ✓ Alembic metadata parity test passed
- ✓ `alembic history` includes `e5f6a7b8c9d0 -> f6a7b8c9d0e1`
- ✓ `alembic heads` reports exactly one head: `f6a7b8c9d0e1`
- ✓ Isolated upgrade to `f6a7b8c9d0e1`, downgrade to `e5f6a7b8c9d0`, and re-upgrade to `f6a7b8c9d0e1` passed
- ✓ Metadata parity validation passed after temporary upgrade
- ✓ Downgrade removed only Phase 3.6 CV version objects; Phase 3.5 fact-comparison tables remained
- ✓ Re-upgrade restored the `cv_versions` table and indexes
- ✓ Real development database safely upgraded from `e5f6a7b8c9d0` to `f6a7b8c9d0e1`
- ✓ Database integrity passed
- ✓ `cv_versions` was created successfully
- ✓ Original, parsed, verified-master, and tailored version types are supported
- ✓ Parent-type validation, self-parent prevention, circular-ancestry prevention, and candidate ownership checks are complete
- ✓ Original-document adoption is idempotent
- ✓ Primary switching is atomic and limited to one primary per candidate and version type
- ✓ Archived and failed versions cannot become primary
- ✓ Archiving preserves children, source documents, and version history
- ✓ Unsafe deletion of versions with children is rejected
- ✓ Metadata-only API responses do not expose full CV text, binary data, stored filenames, or absolute storage paths
- ✓ No CV generation, PDF generation, DOCX generation, AI, OCR, embeddings, network requests, or external services were introduced

---

#### Phase 3.7 — Verified Master CV Generation

**Milestone Status:** COMPLETED

**Goal:** Generate truthful, ATS-friendly CV in DOCX and PDF formats from verified candidate facts only.

**Scope:**
- Deterministic canonical CV representation built from eligible verified Facts Vault records only
- DOCX generation with verified facts vault content using `python-docx`
- PDF generation from the same canonical content using `reportlab`
- One-column ATS-friendly format
- Selectable text (not images)
- Consistent fonts and spacing
- Safe download endpoints
- No unsupported claims or inferred data

**Generated CV Structure:**
- Contact: name, title, email, phone, location, LinkedIn, GitHub, portfolio
- Professional Summary (verified facts only)
- Work Experience (from verified experience records)
- Education (from verified education records)
- Skills (from verified skills)
- Projects (from verified projects)
- Certifications (from verified certifications)
- No inferred or generated content

**Implementation Evidence:**
- Implementation committed and reachable from Git history at revision `e52f837`
- New Alembic revision: `a7b8c9d0e1f2` after `f6a7b8c9d0e1`
- New `cv_version_artifacts` table stores DOCX/PDF artifact metadata with one artifact per format per generated version
- `cv_versions` now records safe generation metadata: idempotency key, generation version, source summary, and generation timestamp
- Generated files are stored under configured generated-CV storage, separate from uploaded source documents
- `.gitignore` excludes generated CV storage
- UUID physical filenames and sanitized download filenames are used
- API endpoints implemented:
  - `POST /api/cv-versions/{parent_version_id}/generate-master`
  - `GET /api/cv-versions/{version_id}/artifacts`
  - `GET /api/cv-artifacts/{artifact_id}`
  - `GET /api/cv-artifacts/{artifact_id}/download`
- Idempotency keys prevent repeated identical requests from creating uncontrolled duplicate versions
- Generated versions start as `draft` and become `ready` only after both DOCX and PDF files plus metadata are stored
- Handled generation failures mark the version `failed` and clean partial files
- Archiving preserves generated artifacts; safe leaf deletion removes only generated artifacts and metadata

**DOCX Generation Approach:**
- Use `python-docx` library
- Single-column layout
- Standard fonts and predictable margins
- Paragraph and bullet styles only
- No macros, images, remote templates, scripts, or external resources
- Existing DOCX structure validation and text extractor can recover expected text

**PDF Generation Approach:**
- Use `reportlab` locally from the same canonical CV content
- Use packaged OFL Noto Sans fonts from installed JustMyType font packs:
  - Noto Sans for Latin, Latin Extended, Polish, punctuation, and western text
  - Noto Sans SC for CJK characters not covered by Noto Sans
- Use deterministic glyph-run splitting and FontTools cmap preflight before writing PDF artifacts
- Register both packaged fonts with ReportLab as embedded TrueType font subsets with ToUnicode mappings
- Maintain text selectability; no image rendering, OCR, browser printing, LibreOffice, or external converters
- Standard Letter size (8.5×11")
- Safe pagination for long CVs with stored PDF page count
- Existing PDF validation and text extractor can recover expected text

**Security Requirements:**
- Only verified facts included
- No inferred or uncertain data
- No unsupported dates, metrics, claims
- Safe file download (no path traversal)
- Generated CV stored as CV version artifacts, not uploaded document records
- No storage paths, binary content, full CV text, secrets, stack traces, database URLs, or absolute paths exposed through JSON APIs
- No AI, embeddings, OCR, browser automation, network requests, external converters, or hosted generation services are used
- Generic CV-version metadata creation cannot create `verified_master` versions; verified masters must use the dedicated generation workflow

**Validation Evidence:**
- ✓ 33 targeted Phase 3.7 tests passed, 1 sandbox-blocked Quick Look raster test skipped
- ✓ Focused CV-version and Phase 3.7 tests passed
- ✓ 148 complete backend tests passed, 1 sandbox-blocked Quick Look raster test skipped
- ✓ `python -m compileall app` passed
- ✓ FastAPI import validation passed
- ✓ OpenAPI route validation passed with 33 paths and all required Phase 3.7 routes
- ✓ Alembic metadata parity test passed
- ✓ `alembic history` includes `f6a7b8c9d0e1 -> a7b8c9d0e1f2`
- ✓ `alembic heads` reports exactly one head: `a7b8c9d0e1f2`
- ✓ Isolated temporary-database upgrade to `a7b8c9d0e1f2`, downgrade to `f6a7b8c9d0e1`, and re-upgrade to `a7b8c9d0e1f2` passed
- ✓ Downgrade removed only Phase 3.7 artifact objects and generation metadata; Phase 3.6 `cv_versions` remained
- ✓ Re-upgrade restored Phase 3.7 artifact table and generation metadata
- ✓ Real development database safely upgraded from `f6a7b8c9d0e1` to `a7b8c9d0e1f2`
- ✓ Database integrity passed
- ✓ CV version artifact storage schema was created successfully
- ✓ Verified Master CV generation creates DOCX and PDF artifacts from one canonical representation
- ✓ Generated content uses verified Candidate Facts Vault records only
- ✓ Unverified facts, uploaded CV claims, and fact-comparison findings are excluded
- ✓ No facts, dates, achievements, metrics, technologies, qualifications, responsibilities, or summaries are invented
- ✓ Candidate Facts Vault records remain read-only during generation
- ✓ Canonical section order is Contact, Professional Summary, Work Experience, Education, Skills, Projects, Certifications
- ✓ DOCX output is selectable, ATS-friendly, structurally valid, and re-extractable
- ✓ PDF output is selectable, ATS-friendly, structurally valid, and re-extractable
- ✓ Packaged Noto Sans and Noto Sans SC fonts are embedded using installed dependencies
- ✓ PDF resources contain embedded font streams and ToUnicode mappings
- ✓ Mixed Latin Extended, Polish, punctuation, and CJK text is preserved
- ✓ Unsupported characters fail safely instead of being silently replaced
- ✓ No font binaries are stored in Git
- ✓ PDF pagination checks page capacity before every wrapped visual line
- ✓ Long summaries, project descriptions, paragraphs, and bullets paginate without clipping, omission, duplication, or overlap
- ✓ Long pagination probe used approximately 8,525 characters and approximately 95 wrapped lines over two pages
- ✓ Every rendered text baseline remained above the configured bottom margin
- ✓ Generated artifact path, hash, size, filename, and cleanup tests passed
- ✓ Ready/primary lifecycle validates physical generated artifacts before allowing ready or primary status
- ✓ One valid DOCX and one valid PDF are required before a verified master can become ready or primary
- ✓ Artifact file existence, ownership, path safety, MIME type, size, SHA-256, structure, and PDF page count are validated
- ✓ Generic CV-version creation cannot bypass the verified-master generation lifecycle
- ✓ Database-first deletion leaves artifact files untouched on database commit failure and records safe post-commit cleanup warnings without restoring deleted metadata
- ✓ Post-commit cleanup failure may leave only inaccessible orphan files, not database metadata pointing to missing files
- ✓ Uploaded source documents, extracted text, detected sections, fact comparisons, and Facts Vault records remain untouched
- ✓ Generated files use safe UUID-based physical filenames
- ✓ Download filenames and headers are sanitized
- ✓ No absolute storage paths, physical stored filenames, full CV content, secrets, database URLs, or stack traces are exposed
- ✓ No AI, OCR, browser automation, LibreOffice, hosted conversion, runtime font download, or external network service is used
- ✓ The single skipped test is the sandbox-restricted Quick Look raster check; separate local raster validation and automated geometry, embedding, ToUnicode, and extraction checks passed
- ✓ Generated test artifacts remained in temporary or ignored storage and were not added to Git

**Dependencies:**
- Requires Phase 2 (Facts Vault) ✓
- Requires Phase 3.6 (Version Management) ✓
- Adds `python-docx==1.2.0` for local DOCX generation
- Adds `reportlab==4.4.5` for local selectable-text PDF generation
- Adds `justmytype==0.4.0`, `justmytype-western-core==0.1.0`, `justmytype-intl-cjk==0.1.0`, and `fonttools==4.63.0` for packaged embedded Unicode PDF fonts and glyph coverage checks

**Definition of Done:**
- DOCX generation working with verified facts
- PDF generation working from the same canonical verified content
- Download endpoints secure
- All generation tests pass
- ATS compatibility verified
- Implementation committed and documented with Git revision `e52f837`
- Real development database safely upgraded from `f6a7b8c9d0e1` to `a7b8c9d0e1f2`

---

#### Phase 3.8 — Document Management Frontend

**Milestone Status:** COMPLETED

**Goal:** Provide web UI for document upload, extraction, section detection, and verification workflows.

**Scope:**
- Upload form for CV files
- Progress indication
- Validation error display
- Document list view
- Primary CV selection
- Extraction trigger action
- Extracted text viewer
- Section detection results viewer
- Facts comparison results viewer
- Master CV generation and download
- Delete action

**Required Frontend Components:**
- `DocumentUploadForm` — File input, document_type selector, is_primary checkbox, upload status
- `DocumentList` — List of uploaded documents with status, primary marker
- `DocumentExtraction` — Extraction trigger, status display, extracted text viewer
- `SectionDetector` — Section detection trigger, results table/visualization
- `FactsComparison` — Comparison results showing matches, mismatches, unverified claims
- `MasterCVGenerator` — Generate button, format selector (DOCX/PDF), download links
- `DocumentDelete` — Confirmation dialog, delete button

**Frontend Pages:**
- `/documents` — Document upload and management dashboard
- `/documents/[documentId]` — Single document detail view with extraction/sections/comparison
- `/cv-versions` — CV version management and lifecycle overview
- `/cv-versions/[versionId]` — CV version metadata, ancestry, generation, artifacts, and downloads

**API Integration:**
- POST /api/documents/upload
- GET /api/documents
- GET /api/documents/{id}
- POST /api/documents/{id}/extract
- POST /api/documents/{id}/detect-sections
- GET /api/documents/{id}/sections
- POST /api/documents/{id}/compare-facts
- GET /api/documents/{id}/fact-comparison
- GET /api/fact-comparisons/{comparison_id}
- POST /api/cv-versions/{parent_version_id}/generate-master
- GET /api/cv-versions/{version_id}/artifacts
- GET /api/cv-artifacts/{artifact_id}
- GET /api/cv-artifacts/{artifact_id}/download
- PATCH /api/documents/{document_id}/primary
- POST /api/documents/{document_id}/cv-version
- GET /api/cv-versions
- GET /api/cv-versions/{version_id}
- GET /api/cv-versions/{version_id}/history
- PATCH /api/cv-versions/{version_id}/primary
- PATCH /api/cv-versions/{version_id}/archive
- DELETE /api/cv-versions/{version_id}
- DELETE /api/documents/{id}

**Completion Evidence (Committed — Git revision `9790fa6da6ebd7fef44c9c7a01b08a9a533b95eb`):**
- Frontend test suite passed: 46 tests.
- TypeScript type checking passed.
- ESLint passed.
- Production build passed.
- Backend OpenAPI contract inspection passed with 33 paths.
- No backend application files changed.
- No database files changed.
- No PDF, DOCX, TTF, OTF, TTC, generated CV, uploaded CV, secret, or personal document was added to Git.
- Added App Router pages: `/documents`, `/documents/[documentId]`, `/cv-versions`, `/cv-versions/[versionId]`.
- Added document upload, list, detail, status, extraction, and section-detection UI.
- Added verified-facts comparison UI using existing backend endpoints.
- Added original CV-version adoption.
- Added CV-version listing, detail, ancestry, primary, archive, and safe-delete workflows.
- Added Verified Master CV generation using the dedicated backend endpoint.
- Added DOCX and PDF artifact metadata and explicit download actions.
- Typed frontend API handling supports JSON, multipart upload, and binary downloads separately.
- Backend errors remain authoritative and are displayed safely.
- Extracted CV and backend content is rendered as plain text.
- `dangerouslySetInnerHTML` is not used.
- Storage paths and physical stored filenames are not displayed.
- Destructive archive and delete actions require confirmation.
- Duplicate upload, comparison, and generation submissions are prevented.
- Generation uses a stable idempotency key for one deliberate submission attempt.
- Loading, empty, success, failure, retry, draft, ready, archived, and failed states are represented truthfully.
- Responsive and accessible interface behavior is implemented using existing project conventions.
- No major frontend state-management or UI framework dependency was added.
- Phase 3.8 did not introduce the existing `next/font/google` network requirement.
- Comparison history remains limited to backend capabilities currently exposed.
- Parsed and tailored version creation UI remains out of scope because no corresponding safe frontend workflow was required.
- Generated-document preview rendering remains out of scope; artifacts are downloaded explicitly.

**Optional Future UX Improvements (Not Blockers):**
- Automatically navigate to the newly generated verified-master child version after generation.
- Disable Mark Primary client-side for ineligible draft verified-master versions.
- Consider component-mounted browser tests if the frontend test infrastructure is expanded later.

**Testing Requirements:**
- Upload form validation (file type, size)
- Progress indication during upload
- Document list renders correctly
- Primary CV selection works
- Extraction status updates
- Text viewer displays extracted text
- Section detection results display
- Comparison results display
- Download works (DOCX, PDF)
- Delete confirmation and removal

**Dependencies:**
- Requires Phase 3.1 (Upload Backend) ✓
- Requires Phase 3.3 (Extraction) ✓
- Requires Phase 3.4 (Section Detection) ✓
- Requires Phase 3.5 (Facts Comparison) ✓
- Requires Phase 3.7 (Master CV Generation) ✓

**Definition of Done:**
- All document management components created
- Upload, extraction, detection workflows functional
- Frontend TypeScript strict mode passes
- All component tests pass
- ESLint clean
- Implementation committed and documented with Git revision `9790fa6da6ebd7fef44c9c7a01b08a9a533b95eb`

---

### Phase 4 — Job Discovery

**Phase Status:** COMPLETED (Phases 4.1–4.6 all COMPLETED)

**Goal:** Build compliant job discovery foundations before any live provider integration.

**Approved Phase 4 Planning Decisions:**
- Phase 4 is split into independently reviewable sub-milestones.
- Phase 4.1 is backend schema and compliance-policy foundation only.
- No live source provider is enabled by Phase 4.1.
- No provider credentials or API keys are added.
- No scheduled ingestion worker is added.
- No server-side fetching of user-supplied URLs is allowed.
- User-supplied URLs may be stored only as references.
- Raw source retention target is initially 30 days and is configurable per source.
- Matching, CV tailoring, automatic applications, browser automation, scraping, email import, and frontend job-discovery UI are out of Phase 4.1 scope.

#### Phase 4.1 — Core Job and Job Source Foundation

**Milestone Status:** COMPLETED (Committed — Git revision `cd33a9ae9ba0785635627ded887dd37057608320`)

**Scope:**
- Job sources and source compliance-policy fields
- Normalized jobs with mandatory source ownership and provenance
- Structured job locations
- Structured compensation
- Structured skill requirements
- Core lifecycle status values: `discovered`, `active`, `possibly_stale`, `expired`, `removed`, `unavailable`
- Safe read-only APIs for sources and jobs
- Migration, metadata parity, source compliance, URL safety, pagination, and response-shape tests

**Database Schema:**
- New migration `b8c9d0e1f2a3_add_phase_4_1_job_foundation.py` follows committed Phase 3.7 head `a7b8c9d0e1f2`
- New tables:
  - `job_sources`
  - `normalized_jobs`
  - `job_locations`
  - `job_compensations`
  - `job_skill_requirements`
- Source identity is unique by stable `source_key`
- Normalized job source identity is unique by `(job_source_id, source_job_id)`
- Job location, compensation, and skill records cascade from normalized jobs
- Job source deletion is restricted by normalized job provenance
- List/filter indexes are added for source, lifecycle, employer, employment type, remote mode, and stable child ordering

**Compliance and Safety Rules:**
- Job sources default to disabled, unallowlisted, server-fetch disabled, and `not_reviewed`
- A source cannot be enabled unless allowlisted
- Manual-review sources cannot be enabled until operational review statuses are resolved
- Attribution-required sources cannot be enabled without attribution text or reference
- Server fetching is allowed only for access modes designed for configured server fetching
- User-supplied URL sources remain metadata-only and cannot allow server fetching
- Review statuses are operational statuses, not legal compliance guarantees
- URL references reject malformed, `javascript:`, `data:`, `file:`, localhost, loopback, link-local, private-network, and credential-bearing URLs
- Employer, title, descriptions, requirements, location text, attribution, and source metadata are treated as untrusted text
- Null bytes and invalid control characters are rejected
- Descriptions and source text are bounded
- Salary, sponsorship, seniority, employment type, remote mode, and skills are not inferred

**Read-Only API Endpoints:**
- `GET /api/job-sources`
- `GET /api/job-sources/{source_id}`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`

**Out of Scope for Phase 4.1:**
- Ingestion runs
- Raw provider payload storage
- Provider adapters or HTTP clients
- API credentials
- Background workers or scheduled discovery
- Arbitrary URL fetching
- Greenhouse, Ashby, USAJOBS, Adzuna, Workable, or Lever integrations
- Deduplication across providers
- Job matching
- Saved jobs
- Frontend pages

**Validation Evidence:**
- Targeted Phase 4.1 tests passed: 57 tests
- Complete backend suite passed: 205 tests, 1 sandbox-restricted Quick Look raster test skipped
- Migration validation on a temporary database: upgrade to `b8c9d0e1f2a3`, downgrade to `a7b8c9d0e1f2`, and re-upgrade all clean; fresh-database full cycle (`upgrade head` → `downgrade base` → `upgrade head`) also validated
- Real `backend/careerpilot.db` safely upgraded to Alembic revision `b8c9d0e1f2a3` after review; existing tables and data preserved
- Independent code review passed: compliance gating, response leakage, route hygiene, migration reversibility, data safety, input validation, and test coverage checks — no critical or major findings
- Committed as Git revision `cd33a9ae9ba0785635627ded887dd37057608320`

**Definition of Done:**
- Phase 4.1 implementation is reviewed and committed
- Exactly one Alembic head is present in the committed migration chain
- Migration upgrade/downgrade/re-upgrade is validated on a temporary database outside the repository
- Read-only source and job APIs are registered and typed
- Compliance guardrails and URL safety tests pass
- No provider credentials, source fetching, scheduled ingestion, scraping, matching, saved jobs, or frontend job discovery UI are introduced

#### Phase 4.2 — Ingestion Runs and Source Snapshots

**Milestone Status:** COMPLETED (Committed — Git revision `651170904a5f9f61a562713e97b9f676df2c81ca`)

**Scope:**
- Model ingestion runs and raw/source snapshot metadata
- Track run status, start/end times, source ownership, and safe failure summaries
- Define retention cleanup rules without deleting normalized job provenance
- Keep provider payloads bounded and do not expose them through public APIs

**Database Schema:**
- New migration `c9d0e1f2a3b4_add_phase_4_2_ingestion_runs.py` follows committed Phase 4.1 head `b8c9d0e1f2a3`
- New tables: `ingestion_runs`, `source_snapshots`
- Runs are owned by job sources (`ondelete=RESTRICT`); snapshots cascade from runs and restrict on sources
- Run statuses: `pending`, `running`, `succeeded`, `failed`, `cancelled` with service-enforced transitions
- Non-negative counters (`jobs_discovered`, `jobs_updated`, `snapshots_recorded`); `finished_at` requires `started_at`
- Snapshot constraints: SHA-256 content hash, non-negative payload size, `expires_at > fetched_at`

**Safety Rules:**
- Ingestion runs require an existing, enabled job source
- Failed runs require a bounded, safe failure summary (control characters and null bytes rejected); succeeded runs cannot carry one
- Snapshot payload size bounded by `max_source_snapshot_payload_bytes` (default 10 MiB)
- Snapshot media type and storage reference validated; storage reference is internal-only and never exposed via the API
- Snapshot expiry derived from the source's `configured_retention_days`, capped at the 365-day maximum
- Retention cleanup deletes expired snapshot metadata only — never ingestion runs, job sources, or normalized job provenance

**Read-Only API Endpoints:**
- `GET /api/ingestion-runs`
- `GET /api/ingestion-runs/{run_id}`
- `GET /api/ingestion-runs/{run_id}/snapshots`

**Out of Scope for Phase 4.2:**
- Provider adapters, HTTP clients, or any live fetching
- Raw provider payload storage or exposure
- Background workers or scheduled cleanup
- Write API endpoints for runs or snapshots

**Validation Evidence:**
- Targeted Phase 4.2 tests passed: 36 tests
- Complete backend suite passed: 249 tests, 1 sandbox-restricted Quick Look raster test skipped
- Migration validated on a temporary database: fresh full cycle (`upgrade head` → `downgrade base` → `upgrade head`) and targeted upgrade/downgrade/re-upgrade between `b8c9d0e1f2a3` and `c9d0e1f2a3b4`, with job-source row preservation asserted
- Independent code review completed; blocking findings fixed before commit (IntegrityError handling on run updates, atomic snapshot counter increment, bounded completion counters)
- Real `backend/careerpilot.db` safely upgraded to Alembic revision `c9d0e1f2a3b4` after review; existing data preserved
- Committed as Git revision `651170904a5f9f61a562713e97b9f676df2c81ca`

#### Phase 4.3 — First Approved Provider Adapter

**Milestone Status:** COMPLETED (Committed — Git revision `f9e0e893d1c4fad5aa1dbf1d00d3a94c88194c78`)

**Scope:**
- Add the first explicitly approved provider adapter only after source policy review
- Respect provider access mode, attribution, retention, and server-fetch policy
- Do not add credentials unless explicitly approved for that milestone

**Approved Provider:** Greenhouse Job Board API — explicitly approved by the user for this milestone. Public, keyless endpoint (`boards-api.greenhouse.io/v1/boards/{board}/jobs`); no credentials are used or stored.

**Adapter Behaviour:**
- `app/services/provider_greenhouse.py` with trigger endpoint `POST /api/job-sources/{source_id}/ingest`
- Fetch is compliance-gated: provider type `greenhouse`, source enabled, allowlisted, `server_fetch_allowed`, access mode `api`, all three policy reviews `approved_for_configured_use`, and a strictly validated `boards-api.greenhouse.io` base URL — no fetch occurs otherwise
- Full ingestion lifecycle: run created and started, payload snapshot metadata recorded (hash, size, media type), jobs upserted, run completed with counters or failed with a safe generic summary (no URLs, paths, or exception text)
- Payload bounded by `max_source_snapshot_payload_bytes`; JSON content type enforced; redirects not followed
- Normalization stores only provider-supplied values: title/description HTML deterministically stripped and bounded, location text preserved verbatim, employer from the source display name, attribution copied from source policy; no compensation, skills, seniority, or sponsorship inference
- Repeat ingestion touches existing jobs (`last_seen_at`/`ingested_at`) without duplicates; job writes are transactional (no partial writes on failure)

**Out of Scope for Phase 4.3:**
- Credentials or authenticated providers
- Additional providers (Lever, Ashby, USAJOBS follow as separate milestones)
- Scheduled/background ingestion
- Content-change refresh, deduplication, freshness scoring (Phase 4.4)
- Frontend job discovery UI

**Validation Evidence:**
- Targeted Phase 4.3 tests passed: 25 tests (mocked HTTP transport; no network access in tests)
- Complete backend suite passed: 274 tests, 1 sandbox-restricted Quick Look raster test skipped
- No schema change; no migration required; Alembic head remains `c9d0e1f2a3b4`
- Independent code review passed; snapshot-before-upsert ordering deliberately retained as fetch-audit behaviour (documented by test)
- Committed as Git revision `f9e0e893d1c4fad5aa1dbf1d00d3a94c88194c78`

#### Phase 4.4 — Normalization, Deduplication, and Freshness

**Milestone Status:** COMPLETED (Committed — Git revision `ae36ba6edf065fd7b619ee8bcf7f401d4590f33f`; dev DB migrated to `d0e1f2a3b4c5`)

**Scope:**
- Normalize approved provider data into `normalized_jobs`
- Detect source-scoped and cross-source duplicates
- Evaluate freshness and lifecycle transitions without deleting provenance

**Implementation:**
- Shared provider-agnostic upsert (`app/services/job_normalization.py`); Greenhouse adapter now delegates to it, so future adapters reuse the same validated path
- Content refresh: when a job's provider `content_hash` changes, provider-supplied fields and locations are refreshed deterministically; unchanged jobs are only touched (`last_seen_at`/`ingested_at`)
- Re-seen jobs are promoted to `active` from `discovered`/`possibly_stale`/`expired` via the validated lifecycle state machine
- Duplicate detection uses exact signals only — identical `canonical_url` or identical `content_hash` — recorded as additive links in the new `job_duplicates` table with the earliest-seen job as canonical; fuzzy title matching deliberately excluded (a wrong duplicate link could hide a real job, violating the no-inference rule); jobs are never merged or deleted
- Freshness evaluation: past `expires_at` → `expired`; unseen beyond `job_stale_after_days` (config, default 14) → `possibly_stale`; never deletes rows
- Endpoints: `POST /api/jobs/maintenance` (freshness + dedup pass, returns counts) and `GET /api/jobs/{job_id}/duplicates`
- Migration `d0e1f2a3b4c5` (job_duplicates), reversible and validated

**Validation Evidence:**
- Targeted Phase 4.4 tests passed: 18 tests
- Complete backend suite passed: 292 tests, 1 sandbox-restricted skip
- Fresh-database full migration cycle and targeted up/down/re-up validated

#### Phase 4.5 — Saved Jobs and Review Workflow

**Milestone Status:** COMPLETED (Committed — Git revision `722c1cd95ef99c6ef5b3a9c8bbf7a911f9ddcd40`; dev DB migrated to `e1f2a3b4c5d6`)

**Scope:**
- Allow candidate review and saving of discovered jobs
- Preserve removed, expired, unavailable, and stale jobs for inspection
- Do not implement matching or applications

**Implementation:**
- New `saved_jobs` table (migration `e1f2a3b4c5d6`): one review record per job, `RESTRICT` FK so a saved job's underlying data can never be deleted
- Review workflow: `saved` → `shortlisted`/`dismissed` → `archived` via a validated transition map; `archived` is terminal; records are archived, never deleted (no DELETE endpoint by design)
- Bounded, validated candidate notes (2,000 chars, control characters rejected)
- Jobs remain saveable and inspectable in every lifecycle state including removed/expired/unavailable/stale
- Endpoints: `POST/GET /api/saved-jobs`, `GET/PATCH /api/saved-jobs/{id}` with embedded job summaries
- No matching or application logic introduced

**Validation Evidence:**
- Targeted Phase 4.5 tests passed: 16 tests
- Complete backend suite passed: 308 tests, 1 sandbox-restricted skip
- Migration validated up/down/re-up; RESTRICT deletion protection covered by test

#### Phase 4.6 — Job Discovery Frontend

**Milestone Status:** COMPLETED (revision recorded in Current Project Position)

**Scope:**
- Add frontend views for safe job source/job browsing after backend read and review workflows are ready
- Do not add provider setup, credentials, automatic refresh, matching, or applications

**Implementation:**
- App Router pages: `/jobs` (discovery list with source/lifecycle/employment/remote filters, pagination, save action), `/jobs/[jobId]` (full detail incl. locations, source-stated compensation and skills, attribution, duplicate links), `/saved-jobs` (review workflow with status filters and validated transitions)
- Components in `components/jobs/`, API functions in `lib/api.ts`, types in `types/job.ts` / `types/savedJob.ts` — no `src/` directory, existing conventions preserved
- All provider content rendered as plain text (no `dangerouslySetInnerHTML`); external links use `rel="noopener noreferrer"`; no provider setup, credential, auto-refresh, matching, or application UI (enforced by tests)
- Saved-job UI archives instead of deleting, mirroring the backend workflow
- Dashboard links to Job discovery and Saved jobs added

**Validation Evidence:**
- Frontend test suite passed: 54 tests (8 new Phase 4.6 tests)
- ESLint passed; TypeScript strict check passed
- `npm run build` blocked in the validation sandbox only by the pre-existing `next/font/google` network requirement documented since Phase 3.8; run locally to confirm

---

### Phase 5 — Job Analysis, Matching, and Eligibility

**Milestone Status:** COMPLETED (Committed — Git revision `9738ba88ff764ebb155d397f7e18cff351929a60`; dev DB migrated to `f2a3b4c5d6e7`)

**Implementation Notes (match-algorithm-1):**
- Deterministic, versioned, rule-based scoring in `app/services/job_match.py`; no ML or inference — every score line is explained in the stored `explanation`
- Only `verified = TRUE` vault records count as evidence; unverified records are excluded and surfaced in explanations
- Missing data policy ("unknown ≠ unqualified"): components without enough data score NULL and are excluded from the weighted overall score (weights renormalized); they flag manual review instead of penalizing the candidate
- Component evidence: skills = structured job skill requirements vs verified skill names (required ×1.0, preferred ×0.5); experience = merged non-overlapping verified date ranges vs explicit "N+ years" phrases; education = deterministic degree-tier keywords; projects = verified project technologies covering job skills; location = job locations/remote mode vs declared preferences and relocation willingness; work authorization = declared sponsorship needs vs explicit posting phrases
- Ineligible requires an explicit contradiction (candidate requires sponsorship + posting explicitly refuses); all unknowns → conditionally_eligible with listed review reasons
- `job_matches` table (migration `f2a3b4c5d6e7`) with 0–100 range checks and one match per (job, profile); re-analysis updates in place
- Endpoints: `POST /api/jobs/{id}/analyze`, `GET /api/jobs/{id}/match`

**Validation Evidence:**
- Targeted Phase 5 tests passed: 26 tests (scoring, blockers, eligibility, explainability, no-fact-mutation, endpoints, migration cycle)
- Complete backend suite passed: 334 tests, 1 sandbox-restricted skip
- Analysis proven not to modify candidate facts (dedicated test)

**Goal:** Analyze job requirements, match against candidate qualifications, assess eligibility.

**Scope:**
- Extract key job requirements (skills, experience, education)
- Score candidate match (skills, experience, education, projects, location, work auth)
- Assess eligibility (must-haves vs nice-to-haves)
- Provide explainable matching logic

**Database Schema Changes:**
- New table `job_matches`:
  - id, job_id, candidate_profile_id, match_score (0–100), skills_match, experience_match, education_match, projects_match, location_match, work_auth_match
  - eligibility_status (eligible, conditionally_eligible, ineligible), blocker_reason
  - created_at, updated_at

**Match Score Components:**
- Skills match (20%): Verified skills vs required + preferred skills
- Experience match (30%): Years of relevant experience vs requirements
- Education match (15%): Verified education vs requirements
- Projects match (15%): Relevant projects vs requirements
- Location match (10%): Willing to work location
- Work authorization match (10%): Visa/sponsorship match

**Eligibility Determination:**
- Eligible: All blockers met or have workarounds
- Conditionally eligible: Sponsorship required but available, relocation required but willing
- Ineligible: Blocker (requires sponsorship but none available, location impossible)

**API Endpoints (Planned):**
- `POST /api/jobs/{id}/analyze` — Analyze job
- `GET /api/jobs/{id}/match` — Get match score and eligibility

**Testing Requirements:**
- Match scoring algorithm correct
- All blockers identified
- Eligibility determined correctly
- Scoring explainable

**Dependencies:**
- Requires Phase 2 (Facts Vault) ✓
- Requires Phase 4 (Job Discovery) ✓

**Definition of Done:**
- Matching algorithm implemented
- Eligibility determination working
- All match tests pass
- Scoring transparent and explainable

---

### Phase 6 — Job-Specific CV Tailoring

**Milestone Status:** COMPLETED (Committed — Git revision `76978302cb24dc0d8aaeede64f5b2e4992ae45f6`; dev DB migrated to `a3b4c5d6e7f8`)

**Implementation Notes (cv-tailoring-1):**
- Deterministic tailoring in `app/services/cv_tailoring.py`, reusing the Phase 3.7 verified-master render engine (same DOCX/PDF renderers, artifact validation, and idempotent generation flow)
- Keywords = structured job skill requirements + the candidate's verified skill names literally present in the posting text (word-boundary match); no semantic inference
- Experience selection: technology overlap with keywords, top 5, minimum 3 (backfilled by recency); projects top 5 by same rule; skills reordered matching-first; education/certifications unchanged
- Summary handling: candidate's own summary verbatim plus one deterministic sentence naming matched verified skills — the only generated text, and every word of it is a verified fact
- Tailored CVs are `cv_versions` rows (`version_type='tailored'`) parented to the ready verified-master version; generation keys are job-scoped for idempotency
- Job↔CV link tracked in `job_tailored_cvs` (migration `a3b4c5d6e7f8`, one current tailored CV per job; re-tailoring repoints the link, old versions retained)
- Endpoints: `POST /api/jobs/{id}/tailor-cv`, `GET /api/jobs/{id}/tailored-cv`

**Validation Evidence:**
- Targeted Phase 6 tests passed: 14 tests, including DOCX-content proofs that unverified skills/experiences never appear and the summary adds only verified skill names; vault records proven unmodified
- Complete backend suite passed: 348 tests, 1 sandbox-restricted skip
- Migration validated up/down/re-up; fresh full cycle passed

**Goal:** Generate job-specific CV versions from verified facts, emphasizing relevant experience and skills.

**Scope:**
- Select relevant experience from vault
- Select relevant projects from vault
- Select relevant skills from vault
- Rewrite professional summary emphasizing job fit
- Verify CV claims remain truthful
- Generate DOCX/PDF tailored CV
- Track job-to-CV relationship

**Tailoring Algorithm:**
- Keyword extraction from job description
- Match verified experience to job keywords
- Select top 3–5 most relevant experiences
- Highlight achievements matching job requirements
- Reorder skills by job relevance (most relevant first)
- Update professional summary to address job fit (verified facts only)

**Important Constraints:**
- ❌ No invented experience or skills
- ❌ No changed dates or organizations
- ❌ No unsupported metrics or claims
- ❌ No unverified technologies
- ✓ Reordered content
- ✓ Selective omission of irrelevant facts (if beneficial)
- ✓ Emphasis on matching achievements

**API Endpoints (Planned):**
- `POST /api/jobs/{id}/tailor-cv` — Generate tailored CV
- `GET /api/jobs/{id}/tailored-cv` — Retrieve tailored CV

**Testing Requirements:**
- Tailored CV contains only verified facts
- Relevant experience selected correctly
- No invented claims
- Skills reordered appropriately
- Professional summary updated with verified info only

**Dependencies:**
- Requires Phase 2 (Facts Vault) ✓
- Requires Phase 3.7 (Master CV Generation) ✓
- Requires Phase 5 (Job Analysis) ✓

**Definition of Done:**
- Tailoring algorithm implemented
- Tailored CVs generated correctly
- All facts verified
- All tailoring tests pass

---

### Phase 7 — Salary Recommendation Engine

**Milestone Status:** COMPLETED (Committed — Git revision `d25210c4c2d7377c978977439a1c9a98b7ea5ae9`)

**Implementation Notes (salary-local-1):**
- Local-data-only by explicit decision: no external market APIs (Glassdoor/Levels.fyi/Paysa would require paid/external API approval per change-control rules; can be added as a later milestone upon explicit approval)
- Evidence hierarchy: the posting's own advertised range (confidence **high**) → advertised ranges of stored jobs with the *identical* normalized title, same currency and period, no fuzzy analogies (**medium** at ≥3 comparable jobs, otherwise **low**) → **insufficient_data** with no numbers rather than an invented range
- No currency conversion; dominant (currency, period) group only
- Deterministic safe-answer templates for salary questions that quote only advertised numbers and never reveal the candidate's declared minimum salary; a below-declared-minimum warning is flagged in factors for the candidate's eyes only
- Endpoint: `POST /api/salary-recommendation` — computed on demand, nothing persisted, no schema change or migration
- Full factor list returned with every recommendation for explainability

**Validation Evidence:**
- Targeted Phase 7 tests passed: 10 tests (confidence calibration, exact-title comparability, currency isolation, no-invention proof, minimum-salary non-disclosure)
- Complete backend suite passed: 358 tests, 1 sandbox-restricted skip
- No migration required; Alembic head remains `a3b4c5d6e7f8`

**Goal:** Recommend salary ranges based on role, experience, location, and market data.

**Scope:**
- Input: Role, seniority, location, candidate experience, advertised range
- Source market data (Glassdoor, Levels.fyi, Paysa APIs, etc.)
- Generate recommendation with confidence level
- Provide explanation of factors
- Safe handling of salary questions in applications

**Salary Factors:**
- Role and seniority
- Geographic location
- Experience level (years from vault)
- Education level (from vault)
- Industry
- Company size (if known from job)
- Advertised range (if provided)

**Output:**
- Suggested range (min–max)
- Midpoint/median
- Confidence level (high, medium, low)
- Explanation of factors
- Safe answer for salary questions

**Data Sources (Planned):**
- Glassdoor API (if available)
- Levels.fyi open data
- Paysa API
- Bureau of Labor Statistics (public data)
- Internal database (anonymized historical salaries)

**API Endpoints (Planned):**
- `POST /api/salary-recommendation` — Get salary recommendation

**Testing Requirements:**
- Recommendation algorithm correct
- Salary ranges reasonable by market
- Confidence scoring calibrated
- Explanation factors correct

**Dependencies:**
- Requires Phase 2 (Facts Vault) ✓
- Requires Phase 4 (Job Discovery) ✓

**Definition of Done:**
- Salary recommendation algorithm implemented
- Market data integration working
- Recommendations reasonable and explainable
- All salary recommendation tests pass

---

### Phase 8 — Verified Application Answer Vault

**Milestone Status:** ✓ COMPLETED (Committed — Git revision `ede11b9b7e1e1d59e1f26bc7a28ba99cd8da3e0c`)

**Goal:** Maintain a vault of verified answers to common application questions.

**Scope:**
- Store verified answers to recurring questions
- Cover work authorization, sponsorship, availability, salary, relocation
- Support reusable answers for similar questions
- Manual confirmation for sensitive/legal questions
- Distinguish verified vs unverified answers

**Verified Answer Categories:**
- Work Authorization (e.g., "US Citizen with unrestricted work authorization")
- Sponsorship (e.g., "Does not require sponsorship" or "Requires visa sponsorship — H1-B, L1-B available")
- Availability (e.g., "Available to start immediately")
- Notice Period (e.g., "Two weeks' notice")
- Relocation (e.g., "Willing to relocate to San Francisco Bay Area")
- Remote/Hybrid Preference (e.g., "Prefer remote with occasional on-site")
- Expected Salary (from Phase 7 recommendation)
- Company Interest (e.g., "Interested in AI/ML roles at [Company]")
- Cover Letter (verified achievements and fit)

**Application Question Mapping:**
- "Do you require visa sponsorship?" → Sponsorship answer
- "When can you start?" → Availability answer
- "What is your expected salary?" → Salary recommendation answer
- "Why are you interested in this role?" → Company Interest + role fit (verified facts)

**Important Rules:**
- Manual confirmation required for:
  - Sensitive personal information
  - Legal declarations (work authorization, background check consent)
  - Equal opportunity monitoring questions (demographic info)
  - Health/criminal history questions
  - Irreversible decisions (application submission)

**API Endpoints (Planned):**
- `GET /api/application-answers` — List verified answers
- `POST /api/application-answers` — Create verified answer
- `PUT /api/application-answers/{id}` — Update answer
- `DELETE /api/application-answers/{id}` — Delete answer

**Testing Requirements:**
- Answers stored correctly
- Retrieval by question type works
- Sensitive questions flagged for manual review

**Dependencies:**
- Requires Phase 2 (Facts Vault) ✓
- Requires Phase 7 (Salary Recommendations) ✓

**Definition of Done:**
- Application answer vault implemented
- Sensitive question detection working
- Verified answers retrievable
- All answer management tests pass

**Implementation Notes (Completed):**
- New table `application_answers` (single-candidate, FK `candidate_profile_id` → `candidate_profiles.id` CASCADE) via reversible migration `b4c5d6e7f8a9` (follows `a3b4c5d6e7f8`).
- Fields: `category` (CHECK-constrained enum), `question_label`, `answer_text`, `verified`, `manually_confirmed`, server-derived `requires_manual_confirmation`, `notes`, timestamps. Unique `(candidate_profile_id, category, question_label)` prevents exact duplicates; supports multiple reusable answers per category otherwise.
- Categories: work_authorization, sponsorship, availability, notice_period, relocation, remote_preference, expected_salary, company_interest, cover_letter, other.
- Deterministic sensitivity detection (`app/services/application_answer.py`): sensitive categories (work_authorization, sponsorship) plus keyword signals (visa, citizenship, background check, criminal/felony, demographic/EEO, health, disability, veteran, date of birth, social security, etc.). No AI, embeddings, OCR, network, or external services.
- Truthfulness guard: a sensitive answer cannot be promoted to `verified` unless `manually_confirmed` is true (returns HTTP 400). Sensitive answers may still be stored unverified.
- API endpoints: `GET /api/application-answers` (optional `category` filter), `GET /api/application-answers/{id}`, `POST /api/application-answers`, `PUT /api/application-answers/{id}`, `DELETE /api/application-answers/{id}`.
- Validation: full backend suite 377 passed, 1 environment-restricted skip (run as two shards for sandbox time limits); `compileall app` passed; isolated temp-DB migration upgrade → downgrade to `a3b4c5d6e7f8` → re-upgrade validated (table created, dropped, recreated with correct columns, indexes, and FK); Alembic single head `b4c5d6e7f8a9`; migration-parity test updated and passing.
- No candidate facts are fabricated or mutated; the real development database (`backend/careerpilot.db`) was not modified — applying `alembic upgrade head` to it is a separate change-control step pending approval.

---

### Phase 9 — Application Preparation

**Milestone Status:** ✓ COMPLETED (Committed — Git revision `793bac65404fb62529bbe92d52b037fa7a01b8f6`)

**Goal:** Prepare complete application package with CV, answers, and readiness assessment.

**Scope:**
- Assemble application package: job, CV, cover letter, verified answers, risk warnings
- Check readiness (all required documents present, all answers verified)
- Identify blockers (missing info, CAPTCHA, assessment, legal questions)
- Mark as ready for automatic application or manual submission

**Application Package:**
- Job (source, title, company, requirements)
- Tailored CV (DOCX, PDF)
- Cover letter (generated from verified fit + company interest)
- Verified answers (work auth, salary, availability, etc.)
- Match report (skills, experience, eligibility)
- Risk warnings (if any)
- Readiness status

**Readiness Statuses:**
- `ready_for_automatic_application` — All documents ready, no blockers, can auto-apply
- `needs_user_review` — Documents ready but user review recommended
- `blocked_by_missing_information` — Missing required data (e.g., no salary recommendation)
- `blocked_by_captcha` — Application site requires CAPTCHA
- `blocked_by_mfa` — Application site requires MFA
- `blocked_by_assessment` — Company requires skills assessment or test
- `not_eligible` — Candidate does not meet requirements

**API Endpoints (Planned):**
- `POST /api/jobs/{id}/prepare-application` — Prepare application package
- `GET /api/jobs/{id}/application-package` — Retrieve prepared package
- `PUT /api/jobs/{id}/application-package` — Update/confirm package

**Testing Requirements:**
- Application package assembled correctly
- All required documents present
- Readiness status determined correctly
- Blockers identified accurately

**Dependencies:**
- Requires Phase 3.7 (Master CV Generation) ✓
- Requires Phase 5 (Job Analysis) ✓
- Requires Phase 6 (CV Tailoring) ✓
- Requires Phase 8 (Application Answers) ✓

**Definition of Done:**
- Application package assembly working
- Readiness determination accurate
- All package tests pass

**Implementation Notes (Completed):**
- New table `application_packages` (one per job; FK `job_id` → `normalized_jobs.id` CASCADE, unique; FK `candidate_profile_id` → `candidate_profiles.id` CASCADE) via reversible migration `c5d6e7f8a9b0` (follows `b4c5d6e7f8a9`).
- Fields: `readiness_status` (CHECK-constrained), `cover_letter_text`, `blockers`/`risk_warnings`/`missing_items` (JSON), `user_confirmed`, `user_notes`, `assembly_version`, `prepared_at`, timestamps.
- Assembly (`app/services/application_package.py`) reads existing artifacts only — the Phase 5 match, Phase 6 tailored CV + artifacts, Phase 8 answers — and computes the Phase 7 salary read-only. It never generates missing pieces; absence is reported as missing information, never fabricated.
- Cover letter is deterministic and verified-fact-only: candidate's own verified professional summary (verbatim), a verified `company_interest` answer (verbatim), and verified skills the posting explicitly lists as structured requirements. Returns none when the profile is not marked verified.
- Deterministic readiness precedence: `not_eligible` (match ineligible) > `blocked_by_captcha` > `blocked_by_mfa` > `blocked_by_assessment` (keyword detection in job text) > `blocked_by_missing_information` (missing verified profile, match, tailored CV+artifacts, or required work_authorization/availability answers) > `needs_user_review` (conditional match, unconfirmed sensitive answers, missing recommended answers, salary advisories, stale/expired posting) > `ready_for_automatic_application`.
- Endpoints: `POST /api/jobs/{id}/prepare-application` (upsert + reassess; resets prior confirmation), `GET /api/jobs/{id}/application-package`, `PUT /api/jobs/{id}/application-package` (confirm/notes; confirming a blocked or ineligible package is rejected). CAPTCHA/MFA/assessment always require manual handling; submission stays a deliberate human action.
- Validation: full backend suite 395 passed, 1 environment-restricted skip (run in shards for sandbox time limits); `compileall app` passed; isolated temp-DB migration upgrade → downgrade to `b4c5d6e7f8a9` → re-upgrade validated (table created, dropped, recreated with correct columns, indexes, and both CASCADE FKs); Alembic single head `c5d6e7f8a9b0`; migration-parity test updated and passing.
- No candidate facts fabricated or mutated. Dev database migrated to `c5d6e7f8a9b0` (additive; existing data preserved).

---

### Phase 10 — Browser-Assisted Applications

**Milestone Status:** ✓ COMPLETED (Committed — Git revision `47f1f3d4ada2177afd5015d310259071f6e739a3`)

> **Safety scope note:** Per the authoritative candidate-truth and automation-safety rules (CLAUDE.md, which overrides the roadmap on conflict), this milestone delivers the safe, human-in-the-loop workflow and safety-gate engine — not live, unattended browser submission. The live Playwright driver is intentionally abstracted behind a driver interface and deferred: the default `manual_assist` driver plans and pauses only. It never bypasses CAPTCHA, MFA, bot detection, rate limits, access controls, or terms of service, and it never submits an application on its own. A future live driver must route through these same gates without bypassing site protections, and requires a real (non-sandbox) environment to validate.

**Goal:** Safely assist with job application workflows using browser automation.

**Scope:**
- Use Playwright for browser automation
- Navigate to application site
- Fill forms with verified data
- Submit application
- Pause for CAPTCHA, MFA, assessments, legal questions
- Track submission confirmation
- Safe error handling and retry logic

**Important Safety Gates (Always Pause For):**
- CAPTCHA or puzzle challenges
- Multi-factor authentication (MFA)
- Identity verification (name, email confirmation)
- Skills assessments or coding tests
- Video interview setup
- Legal declarations or consent screens
- Salary negotiation offers
- Irreversible application submission (when approval required)
- Unknown/unexpected form questions
- Sensitive personal questions

**Never Bypass:**
- CAPTCHA bypass tools
- MFA circumvention
- Bot detection
- Rate limits
- Website access controls
- Terms of service restrictions

**Form Filling Strategy:**
- Extract form fields (text, select, checkbox, file upload)
- Match fields to verified answers vault
- Fill with verified data
- Flag unrecognized or sensitive fields for manual review
- Preview completed form before submission
- Request user confirmation before final submit

**API Endpoints (Planned):**
- `POST /api/jobs/{id}/apply` — Start application workflow
- `GET /api/applications/{id}/status` — Application status
- `POST /api/applications/{id}/resume` — Resume after CAPTCHA/MFA
- `POST /api/applications/{id}/cancel` — Cancel application

**Testing Requirements:**
- Form navigation correct
- Data filling accurate
- CAPTCHA/MFA pauses trigger
- Application submission tracked
- Error handling graceful

**Dependencies:**
- Requires Phase 9 (Application Preparation) ✓
- Requires Phase 3.7 (CV Generation) ✓
- Requires Phase 8 (Application Answers) ✓

**Definition of Done:**
- Playwright integration working
- Form filling functional
- Safety gates enforced
- All application tests pass

**Implementation Notes (Completed):**
- New table `application_runs` (FK `job_id` → `normalized_jobs.id` CASCADE, `candidate_profile_id` → `candidate_profiles.id` CASCADE, `application_package_id` → `application_packages.id` SET NULL) via reversible migration `d6e7f8a9b0c1` (follows `c5d6e7f8a9b0`).
- Fields: `status` (CHECK-constrained: paused_for_gate, submitted, cancelled, failed), `pause_reason`, `gates`/`fill_plan`/`manual_fields` (JSON), `confirmation_number`, `submitted_at`, `error`, `attempts`, `driver`, `workflow_version`, timestamps.
- Field mapping (`app/services/application_run.py`) is deterministic and verified-only: identity fields and non-sensitive verified answers are auto-fillable; cover letter and tailored-CV PDF are referenced; sensitive/legal answers (work authorization, sponsorship, anything flagged for manual confirmation) and missing required answers go to `manual_fields` and are never auto-filled.
- Mandatory safety gates with fixed precedence: `captcha` > `mfa` > `assessment` (from the Phase 9 package blockers) > `legal_declaration` (always) > `submission_confirmation` (always, last). The run starts `paused_for_gate`.
- `resume` acknowledges one gate at a time — recording that the candidate handled it externally; it never bypasses a protection. The submission gate clears only when the candidate supplies a `confirmation_number` (the tool never submits on its own), transitioning the run to `submitted`. `cancel` terminates the run. Apply is idempotent (returns the existing active run) and is rejected for `not_eligible`/`blocked_by_missing_information` packages and for unconfirmed ready/needs_review packages.
- Endpoints: `POST /api/jobs/{id}/apply`, `GET /api/application-runs/{id}/status`, `POST /api/application-runs/{id}/resume`, `POST /api/application-runs/{id}/cancel`. (The run-workflow endpoints were placed under `/api/application-runs/...` rather than the roadmap's original `/api/applications/...` to keep the `/api/applications` namespace unambiguous for the Phase 11 tracking records — a run id and a tracking-record id are distinct entities.)
- Validation: full backend suite 405 passed, 1 environment-restricted skip (run in shards for sandbox time limits); `compileall app` passed; isolated temp-DB migration upgrade → downgrade to `c5d6e7f8a9b0` → re-upgrade validated (columns, four indexes, all three FKs incl. SET NULL); Alembic single head `d6e7f8a9b0c1`; migration-parity test updated and passing. Dev database migrated to `d6e7f8a9b0c1` (additive; existing data preserved).
- **Deferred by design (safety):** live Playwright browser driving and any autonomous submission. No new production dependency (Playwright) was added.

---

### Phase 11 — Application Tracking Dashboard

**Milestone Status:** ✓ COMPLETED (Committed — Git revision `e5f21d16f37f1be6e2f34f310d0262536016f6db`)

**Goal:** Track submitted applications and outcomes.

**Scope:**
- Display all discovered jobs with application status
- Track status progression (discovered → analyzed → ready → applied → interview → offer/rejected)
- Capture confirmation numbers and submission dates
- Track interview details and outcomes
- Notes and follow-up tracking
- Timeline view

**Application Statuses:**
- `discovered` — Job found, not analyzed
- `analyzing` — Match analysis in progress
- `not_eligible` — Analysis complete, candidate not eligible
- `matched` — Eligible, match score calculated
- `cv_generated` — Tailored CV generated
- `needs_review` — Application ready for review
- `ready_to_apply` — All documents and answers ready
- `applying` — Application in progress
- `blocked` — Blocked by CAPTCHA/MFA/assessment
- `submitted` — Application submitted, confirmation captured
- `interview` — Interview scheduled or in progress
- `rejected` — Application rejected
- `offer` — Offer received
- `withdrawn` — Candidate withdrew application

**Database Schema Changes:**
- New table `applications`:
  - id, job_id, candidate_profile_id, status, cv_id, applied_at, confirmation_number
  - interview_date, interview_stage (phone screen, technical, final, etc.)
  - offer_details, rejection_reason, outcome_date
  - notes, follow_ups, created_at, updated_at

**API Endpoints (Planned):**
- `GET /api/applications` — List all applications
- `GET /api/applications?status=submitted` — Filter by status
- `GET /api/applications/{id}` — Application detail
- `PUT /api/applications/{id}` — Update application status/notes
- `POST /api/applications/{id}/notes` — Add note
- `POST /api/applications/{id}/follow-up` — Schedule follow-up

**Testing Requirements:**
- Application tracking accurate
- Status transitions correct
- Timeline view generates correctly
- Filtering works

**Dependencies:**
- Requires Phase 5 (Job Analysis) ✓
- Requires Phase 10 (Browser Applications) ✓

**Definition of Done:**
- Application tracking database schema created
- Dashboard displays applications and statuses
- Status updates working
- All tracking tests pass

**Implementation Notes (Completed):**
- New table `applications` (one per job; FK `job_id` → `normalized_jobs.id` CASCADE, `candidate_profile_id` → `candidate_profiles.id` CASCADE, `cv_id` → `cv_versions.id` SET NULL) via reversible migration `e7f8a9b0c1d2` (follows `d6e7f8a9b0c1`).
- Fields: `status` (CHECK-constrained, 14 statuses), `applied_at`, `confirmation_number`, `interview_date`, `interview_stage` (CHECK-constrained, nullable), `offer_details`, `rejection_reason`, `outcome_date`, `notes`/`follow_ups` (JSON), timestamps.
- Initial status is derived deterministically (`app/services/application.py`) from the existing pipeline: submitted/paused runs → submitted/blocked/applying; package readiness → ready_to_apply/needs_review/blocked/not_eligible; else tailored CV → cv_generated; else match → matched/not_eligible; else discovered. No fabrication.
- Status changes are validated against an explicit transition map; terminal states (`rejected`, `withdrawn`) cannot transition out; `withdrawn` is reachable from any non-terminal state; setting `submitted` auto-stamps `applied_at`. Detail responses include a chronologically sorted `timeline` (tracked, applied, interview, outcome, notes, follow-ups).
- Endpoints: `POST /api/jobs/{id}/track` (idempotent create-or-get; the entry point, since the roadmap's planned endpoints assumed records already existed), `GET /api/applications` (+ optional `status` filter), `GET /api/applications/{id}` (detail + timeline), `PUT /api/applications/{id}`, `POST /api/applications/{id}/notes`, `POST /api/applications/{id}/follow-up`.
- Validation: full backend suite 417 passed, 1 environment-restricted skip (run in shards for sandbox time limits); `compileall app` passed; isolated temp-DB migration upgrade → downgrade to `d6e7f8a9b0c1` → re-upgrade validated (four indexes, three FKs incl. two SET NULL/CASCADE); Alembic single head `e7f8a9b0c1d2`; migration-parity test updated. Dev database migrated to `e7f8a9b0c1d2` (additive; existing data preserved).
- Related cleanup in this batch: Phase 10 run-workflow endpoints were moved from `/api/applications/{id}/...` to `/api/application-runs/{id}/...` so the `/api/applications` namespace unambiguously belongs to these tracking records.

---

### Phase 12 — Background Automation

**Milestone Status:** ✓ COMPLETED (Committed — Git revision `f3da9a192417348ac2fa4b77ab78df974ea07e8c`)

> **Safety/architecture scope note:** Workers run as bounded, on-demand cycles (one pass per `POST /api/workers/start`), not always-on daemons — this keeps behaviour deterministic and testable and avoids adding a scheduler/queue production dependency; an external scheduler (cron) is expected to call the endpoint on the desired cadence. There is deliberately **no submission worker** — automation never submits applications (submission stays a human step per the safeguards). The discovery worker respects the source compliance gate (`enabled`, `allowlisted`, `server_fetch_allowed`) and does not perform live network fetches in this environment; a future live fetcher would plug in behind the same gate.

**Goal:** Automated background workers for job discovery, analysis, and application preparation.

**Scope:**
- Scheduled job discovery (daily, weekly)
- Job analysis workers
- Stale job cleanup (expired job detection)
- Application package preparation
- Safe retry logic and failure handling
- Worker health monitoring
- Audit logging of all automated actions

**Workers:**
- **Job Discovery Worker** — Runs daily, discovers new jobs from configured sources
- **Job Analysis Worker** — Analyzes newly discovered jobs, calculates match scores
- **Application Preparation Worker** — Prepares applications for ready-to-apply jobs
- **Expiry Checker** — Marks jobs past deadline as expired
- **Error Handler** — Retries failed operations with exponential backoff

**Important Safeguards:**
- No automatic application submission (always requires user approval)
- Daily limits on discovery and analysis
- Duplicate prevention
- Error notifications
- Detailed audit log of all actions

**API Endpoints (Planned):**
- `POST /api/workers/start` — Start background workers
- `GET /api/workers/status` — Worker health status
- `GET /api/audit-log` — Audit trail of automations

**Testing Requirements:**
- Workers execute on schedule
- Retries work correctly
- Failure handling graceful
- Audit log captures all actions

**Dependencies:**
- Requires Phase 4 (Job Discovery) ✓
- Requires Phase 5 (Job Analysis) ✓
- Requires Phase 9 (Application Preparation) ✓

**Definition of Done:**
- Background worker framework implemented
- All workers functional
- Retry logic working
- Audit logging complete
- All worker tests pass

**Implementation Notes (Completed):**
- New tables `worker_runs` and `audit_log_entries` (FK `worker_run_id` → `worker_runs.id` CASCADE) via reversible migration `f8a9b0c1d2e3` (follows `e7f8a9b0c1d2`).
- `worker_runs`: worker_name, status (CHECK: running/success/partial/failed/skipped), run_date, item counters, retries, error, timing. `audit_log_entries`: worker_run_id, worker_name, action, entity_type/id, level (CHECK: info/warning/error), message, created_at.
- Framework (`app/services/worker.py`): a worker registry with per-worker daily limits (max_runs, max_items), computed exponential-backoff retries (`compute_backoff_seconds`, capped), and a `process_items` helper that retries each item up to 3 attempts, records failures rather than raising (one bad item never aborts the cycle), and defensively rolls back partial work so the session stays usable. Run counters are held off the ORM object to survive mid-cycle rollbacks.
- Workers: `job_discovery` (enumerates compliance-gated, fetch-eligible sources; live network fetch deferred), `job_analysis` (analyzes un-analyzed active/discovered jobs via Phase 5), `application_preparation` (prepares packages for eligible + tailored jobs via Phase 9; never submits), `expiry_checker` (marks jobs past `expires_at` as expired). No submission worker exists.
- Health monitoring (`GET /api/workers/status`) reports per-worker health (healthy/degraded/failed/never_run), last run, and today's count vs. daily limit. Full audit trail via `GET /api/audit-log` (worker/level filters, pagination).
- Endpoints: `POST /api/workers/start` (body `{worker: name|"all"}`; enforces daily limits, returning `skipped` runs when reached), `GET /api/workers/status`, `GET /api/audit-log`.
- Validation: full backend suite 427 passed, 1 environment-restricted skip (run in shards for sandbox time limits); `compileall app` passed; isolated temp-DB migration upgrade → downgrade to `e7f8a9b0c1d2` → re-upgrade validated (both tables, all indexes, CASCADE FK); Alembic single head `f8a9b0c1d2e3`; migration-parity test updated. Retry behaviour, daily limits, graceful failure, and audit capture are covered by targeted tests. Dev database migrated to `f8a9b0c1d2e3` (additive; existing data preserved).

---

### Phase 13 — Authentication, Privacy, and Security

**Milestone Status:** ✓ COMPLETED (Committed — Git revision `693e5c68a0352c07a0c852dac7f3d80a70de7793`)

> **Scope note:** This milestone delivers the self-contained, testable **application-layer** security controls. Infrastructure/deployment controls that cannot be meaningfully or safely implemented in this environment are explicitly deferred to Phase 14: encryption-at-rest (DB/object-storage layer), TLS/HTTPS enforcement, automated backup/restore, and retention automation. CSRF tokens are not applicable to this stateless Bearer-token API (no ambient cookie auth) and are intentionally omitted. Authentication is delivered on new `/auth` and `/privacy` routes with an opt-in session dependency; the existing routes are **not** retrofitted with mandatory auth in this milestone (that global enforcement is a follow-up coordinated with the frontend, to avoid breaking the current suite and the not-yet-auth-aware UI).

**Goal:** Implement user authentication, data privacy, and comprehensive security controls.

**Scope:**
- User authentication (local single-user or OAuth)
- Session management
- Secure document access (JWT tokens)
- Encryption (at rest, in transit)
- Secret management
- Rate limiting on API endpoints
- Comprehensive audit logs
- Input validation and sanitization
- Security headers (HSTS, CSP, X-Frame-Options)
- Data export (GDPR)
- Data deletion (right to be forgotten)
- Retention policy
- Backup and restore testing
- PII protection in logs

**Current Single-User Limitation:**
- Currently, profile id = 1 (hard-coded)
- Phase 13 will support multi-user setup (optional) or strengthen single-user isolation

**Security Controls:**
- Rate limiting on upload, extraction, application endpoints
- HTTPS enforced in production
- Secrets in .env (not source code)
- Database connection string in .env
- Document storage path outside web root
- Uploaded files not web-accessible
- No PII in logs
- Session tokens with short expiry
- CSRF tokens for state-changing operations

**Testing Requirements:**
- Authentication flow working
- Session management correct
- Rate limiting enforced
- Data export working
- Encryption in transit verified
- No PII in logs

**Dependencies:**
- Requires all previous phases ✓

**Definition of Done:**
- Authentication implemented and tested
- Rate limiting enforced
- Security headers set
- Data privacy controls working
- All security tests pass
- No sensitive data in logs

**Implementation Notes (Completed):**
- New tables `auth_credentials` (single-user login credential) and `auth_sessions` (opaque, hashed sessions) via reversible migration `a9b0c1d2e3f4` (follows `f8a9b0c1d2e3`). No FKs to candidate data; sessions indexed on `token_hash` (unique) and `expires_at`.
- Passwords are stored only as PBKDF2-HMAC-SHA256 hashes with a per-credential random salt and stored iteration count (default 480,000, configurable, upgradeable) — standard library only, no new crypto dependency. Verification is constant-time (`secrets.compare_digest`). The password itself is never stored or logged.
- Session tokens are opaque random strings (`secrets.token_urlsafe`); only their SHA-256 hash is persisted, so a database read cannot recover a live token. Sessions expire (default 12h) and are revoked on logout, on password change, and on account erasure.
- Security-headers middleware sets HSTS, `Content-Security-Policy` (default-src 'none'), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, and a minimal `Permissions-Policy` on every response.
- In-process fixed-window rate limiter guards `POST /api/auth/login` against brute force (configurable attempts/window; returns 429 with `Retry-After`). Multi-instance deployments should move this to a shared store (deferred).
- GDPR controls: `GET /api/privacy/export` returns the candidate's own data sanitized of internal storage references (no `storage_path`/`stored_filename`); `POST /api/privacy/delete` performs a confirmed, authenticated right-to-be-forgotten erasure of all candidate-owned records in FK-safe order (breaking the CV-version self-reference first) and revokes all sessions.
- Endpoints: `GET /api/auth/status`, `POST /api/auth/setup`, `POST /api/auth/login`, `GET /api/auth/session`, `POST /api/auth/logout`, `POST /api/auth/change-password`, `GET /api/privacy/export`, `POST /api/privacy/delete`. `/privacy/*` and the stateful `/auth/*` routes require a valid Bearer session.
- Validation: full backend suite 439 passed, 1 environment-restricted skip (run in shards for sandbox time limits); `compileall app` passed; no hardcoded secrets (source scan); isolated temp-DB migration upgrade → downgrade to `f8a9b0c1d2e3` → re-upgrade validated (both tables, indexes); Alembic single head `a9b0c1d2e3f4`; migration-parity test updated. Auth flow, session expiry/revocation, rate limiting, security headers, sanitized export, and guarded erasure (with cascade) are covered by targeted tests. Dev database migrated to `a9b0c1d2e3f4` (additive; existing data preserved).

---

### Phase 14 — Production Database and Deployment

**Milestone Status:** IN PROGRESS — code-level groundwork committed (Git revision `fc72d03`); infrastructure provisioning and deployment remain (require a real target environment).

**Groundwork Completed (code + docs):**
- Configurable database engine: `CAREERPILOT_DATABASE_URL` selects SQLite (dev default) or PostgreSQL; the SQLite foreign-key pragma is dialect-guarded and PostgreSQL uses `pool_pre_ping`. Alembic (`alembic/env.py`) honours the configured URL, so `alembic upgrade head` runs against Postgres when set. Explicit URLs passed by tests are unaffected.
- Object-storage abstraction (`app/services/storage_backend.py`): a `StorageBackend` protocol with a local-filesystem backend (current behaviour) and a lazy-`boto3` S3 backend, sharing key/path-safety validation, plus a `get_storage_backend` factory driven by `CAREERPILOT_STORAGE_BACKEND`.
- Environment-tiered settings (`environment`, storage/S3, Sentry). Sentry initialisation is gated behind `CAREERPILOT_SENTRY_DSN` (inert without it). `GET /api/health` now reports `environment` and `database` backend.
- `docs/deployment.md` operator runbook (Postgres, object storage, backend/frontend hosting, SMTP, scheduler, live ingestion, observability, backups, post-deploy checklist) and `backend/.env.example` (placeholders only; `.gitignore` updated to track example env files). No secrets in source.
- Validation: 9 new infra tests; full backend suite green (468 passed, 1 environment-restricted skip, sharded); Alembic head unchanged; no hardcoded secrets.

**Remaining (infrastructure — needs a real environment):** provisioning PostgreSQL/Supabase and running migrations against it; S3 bucket + migrating existing files and switching services onto the storage abstraction; backend + frontend hosting; TLS enforcement and production CORS; automated backups + restore test; connecting SMTP and a live compliant job source; scheduler wiring.

**Goal:** Migrate from SQLite to production database and deploy system.

**Scope:**
- PostgreSQL or Supabase setup
- Alembic migration to production database
- Object storage setup (S3 or equivalent)
- Backend deployment (Vercel, Railway, Heroku, or self-hosted)
- Frontend deployment (Vercel)
- Worker deployment (if separate service)
- Production CORS and domain configuration
- Environment configuration per tier (dev, staging, production)
- Logging and monitoring
- Error reporting (Sentry)
- Backup and restore procedures
- Deployment documentation

**Database Migration Path:**
1. Create production PostgreSQL database
2. Run Alembic migrations to establish schema
3. Validate migration against temporary database
4. Backup development SQLite database
5. Test migration rollback procedure
6. Schedule production deployment
7. Monitor for errors post-deployment

**Object Storage:**
- Move uploaded documents from local filesystem to S3 or similar
- Maintain same security controls (signed URLs, path validation)
- Document deletion removes from storage
- Backup strategy for storage

**Deployment Checklist:**
- ✓ Environment variables configured per tier
- ✓ Database connection string in production secrets
- ✓ CORS configured for production domain
- ✓ SSL/TLS enforced
- ✓ Logging configured
- ✓ Error reporting (Sentry) connected
- ✓ Backups automated
- ✓ Monitoring and alerts setup
- ✓ Deployment documentation written
- ✓ Rollback procedure tested

**Testing Requirements:**
- Production database migration successful
- All services connect correctly
- Data integrity verified post-migration
- Backup/restore tested
- Failover tested (if HA setup)

**Dependencies:**
- Requires all previous phases ✓

**Definition of Done:**
- PostgreSQL/Supabase configured
- Alembic migrations tested and validated
- Backend deployed and accessible
- Frontend deployed and accessible
- Workers deployed and operational
- Monitoring and logging functional
- Backup procedures tested
- Deployment documentation complete

---

### Phase 16 — One-Click Auto-Apply (Consented Automatic Submission)

**Milestone Status:** ✓ COMPLETED (Committed — Git revision `264c166caa14357e41b04ece234daf08fbb5b16c`)

**Scope:** The candidate selects a job and clicks "Apply automatically" once. That click records explicit per-job consent (acknowledging the legal declarations and the irreversible submission). The run then auto-prepares everything missing — match analysis, tailored CV, application package (via the existing verified-facts services; nothing is ever fabricated) — and either submits through a source-permitted channel or pauses and notifies the candidate by email.

**Safety model (unchanged guarantees):**
- CAPTCHA / MFA / assessment gates always pause the run and are never bypassed; consent cannot pre-acknowledge them (schema-enforced).
- Sensitive/legal answers (`requires_manual_confirmation`) and missing required answers block automatic submission (`pause_reason: manual_fields_required`).
- `needs_user_review` packages are never auto-confirmed; only `ready_for_automatic_application` is confirmed by the consent click.
- Submission happens only through a registered per-`provider_type` adapter (`app/services/submission.py`). No adapter is registered by default — no currently integrated source offers a permitted candidate-side submission API — so today's runs end paused at the `submission_confirmation` gate exactly like manual assist, with the candidate notified by email. Adapter failures are contained (run pauses, safe error recorded).
- Email notifications reuse the notifications outbox (`manual_action_required`, `application_submitted`) with per-run dedupe keys and immediate best-effort SMTP delivery when configured; pending otherwise (never lost).

**Changes:**
- Migration `f4a5b6c7d8e9` (reversible, additive): `application_runs.consented_at`, `application_runs.submission_method`.
- `POST /api/jobs/{job_id}/apply` accepts an optional body (`driver`, `acknowledged_gates`); no body preserves manual-assist behaviour. Manual resume now records `submission_method: "manual"` and sends a submitted-confirmation notification.
- Frontend: "One-click apply" panel on the prepare page (two explicit consent checkboxes gate the button; submitted / action-needed outcome states).
- Tests: `backend/tests/test_auto_submit_phase16.py` (14 tests: consent enforcement, safety-gate protection, unsupported-source pause+notify, permitted-adapter submission, contained adapter failure, manual-fields blocking, captcha pause, needs_user_review rejection, consent-confirms-ready-package, auto package preparation, manual-assist regression).

**Validation (this milestone):** full backend suite green (526 passed, 1 environment-restricted skip, run in shards); `compileall app` passed; migration upgrade → downgrade → re-upgrade validated on SQLite; migration-parity head updated to `f4a5b6c7d8e9`; frontend `tsc --noEmit`, ESLint, and 54 node tests pass.

**Deferred:** real submission adapters (require a source whose terms permit API submission with candidate-authorized credentials); per-profile worker loop (Phase 15 remainder); SMTP provider configuration (recommended: Resend SMTP endpoint via existing `CAREERPILOT_SMTP_*` settings).

---

### Phase 16.1 — Security Hardening and Cleanup

**Milestone Status:** ✓ COMPLETED (Committed — Git revision `268c76f44248e21afa2b9d0a2bcfbbcac4a7e5f2`)

**Scope (from the July 2026 code audit):**
- Authentication required on ALL previously open routes: every `job.py` endpoint (analyze, match, tailor-cv, tailored-cv, salary-recommendation, maintenance, listings, duplicates), all `worker.py` endpoints (start, status, audit-log), all `ingestion.py` endpoints. Anonymous callers can no longer read candidate data, trigger CV generation, or drive the auto-apply pipeline.
- Per-profile scoping of candidate-fact queries: `analyze_job_match`, `get_job_match_or_404`, `recommend_salary`, `load_job_match`, and `matched_verified_skill_names` now require and filter by `candidate_profile_id` — one profile's verified facts can never appear in another profile's match report or cover letter (candidate-truth rule). `get_tailored_cv_or_404` enforces CV-version ownership. Worker job-selection queries scoped to the worker profile.
- `facts_verified` removed from `CandidateProfileUpsert`: verification state changes only via `POST /profile/verify-all`, never by direct client write (in either direction). Frontend no longer sends it.
- Cleanup: removed empty `app/repositories/` and `app/utils/` packages and dead/unreachable frontend branches in `JobDetailPage`.
- Tests updated to authenticate against the protected routes (401 paths asserted), plus a new regression test that a PUT can neither set nor unset `facts_verified`.

**Validation:** full backend suite green (527 passed, 1 environment-restricted skip); `compileall` passed; frontend `tsc --noEmit`, ESLint, and node tests (54) pass. No route renamed or removed; no schema/database migration required.

**Known remaining (documented, not yet fixed):** rate-limiter proxy awareness (M2/M3). H1, H3, and the per-profile worker loop were fixed in Phase 16.2 below.

---

### Phase 16.2 — Multi-Tenant Ownership, GDPR File Erasure, Per-User Workers, Frontend Fixes

**Milestone Status:** ✓ COMPLETED (Committed — Git revision `87763e50a5c41713a31cd4a5b1000668e776ab94`)

**Scope:**
- **Per-profile ownership (audit H1).** Migration `a5b6c7d8e9f0` (reversible): `application_packages` and `applications` unique per `(job_id, candidate_profile_id)` instead of per job globally; `job_tailored_cvs` gains a backfilled `candidate_profile_id` (FK, index) and per-profile uniqueness. Services scoped: `get_package_or_404`, `update_application_package`, `prepare_application_package` lookup, `load_tailored_cv` (ownership via the CV version's owner), `link_tailored_cv`, `get_tailored_cv_or_404`, `track_application`, `derive_initial_status`, `latest_run`, `active_run_for_job`. Two accounts can now each apply to the same job, and no account can reach another's package/CV/application/run. New isolation test: both users track the same job independently.
- **GDPR file erasure (audit H3).** `delete_candidate_data` now collects the candidate's uploaded document filenames and generated CV artifact paths before row deletion and best-effort removes the files afterwards (failures logged and counted, never raised; no paths in the response). Response gains `files_deleted` / `files_failed`. New test proves both file classes are removed from disk.
- **Per-user background workers (Phase 15 remainder).** `CANDIDATE_PROFILE_ID = 1` removed; `job_analysis`, `application_preparation`, and `auto_apply_pipeline` iterate every candidate profile with per-profile job selection and per-profile notification dedupe keys. Daily limits unchanged (per worker).
- **Frontend audit fixes (medium/low):** delete-document no longer re-fetches the deleted document; ApplicationPrepPage distinguishes real errors from "no package yet"; SavedJobs pagination controls; `/jobs?source=` filter honoured (Suspense-wrapped `useSearchParams`); session check no longer signs out on network blips; verify-all refetches in place instead of `window.location.reload`; loading state resets on id change; errors render as errors (role="alert"), not success notices; 300 ms search debounce; confirm before answer delete; `safeExternalHref` guards all external links (`javascript:` URLs neutralised).
- **Follow-up (committed separately):** one-click apply re-prepares a stale package stuck in a rejected state (`blocked_by_missing_information` / `not_eligible`) once the missing verified data exists, instead of requiring a manual Re-prepare; a candidate's confirmation on a reviewable package is never reset by the auto chain (both behaviours tested).

**Validation:** full backend suite green (529 passed, 1 environment-restricted skip); migration upgrade → downgrade → re-upgrade validated on SQLite; `compileall` passed; frontend `tsc --noEmit`, ESLint, and 54 node tests pass.

---

### Phase 17 — Free Job Source Catalog (Lever, Ashby, Remotive, Arbeitnow, Adzuna, Reed)

**Milestone Status:** ✓ COMPLETED (Committed — Git revision `d6c9401`)

**Scope:** Six free job sources join Greenhouse through one shared, compliance-gated pipeline (`app/services/provider_catalog.py`):
- **Lever** and **Ashby** — per-company ATS boards via public keyless JSON APIs, connected by board slug exactly like Greenhouse.
- **Remotive** and **Arbeitnow** — free keyless remote-job feeds; one global source each, per-job employer names, remote_mode mapped from the feed.
- **Adzuna** and **Reed** — aggregator APIs behind free API keys supplied only via environment settings (`CAREERPILOT_ADZUNA_APP_ID/APP_KEY`, `CAREERPILOT_REED_API_KEY`); connectors stay inert with a clear message until keys exist. Keys are attached at fetch time only — never stored on the source row, never logged, never echoed.

**Safety model:** every source passes the same gates as Greenhouse before any fetch (enabled, allowlisted, fetch permission, approved terms/robots/commercial review, pinned base-URL regex per provider); payload size caps and JSON-only responses enforced; a tampered base URL or disabled source never fetches (tested). Adapters map only provider-supplied fields; compensation mapping deliberately deferred. Ingested jobs flow through the existing normalization/upsert, matching, tailoring, and apply pipeline unchanged.

**Changes:** migration `b6c7d8e9f0a1` (constraint-only, reversible) extends `job_sources.provider_type` with remotive/arbeitnow/reed; `POST /api/job-sources/connect` (new route; Greenhouse route untouched); ingestion route dispatches by provider; settings gain the three key fields; render.yaml documents them; frontend Job Sources page gains a source selector with per-provider fields.

**Validation:** 16 new tests (`tests/test_provider_catalog_phase17.py`) covering connect/ingest per provider, key gating, fetch-time-only credentials, basic-auth header, compliance-gate blocking, dispatch, API roundtrip, and auth; full backend suite green (33 files, 549+ passed); migration up/down/up validated; `compileall`, `tsc`, ESLint, 54 frontend tests pass.

---

## Dependency Map

```
Phase 1 — Project Foundation
  ↓
Phase 2 — Verified Candidate Facts Vault
  ↓
Phase 3.1 — Secure Upload ← Phase 2
  ↓
Phase 3.2 — Alembic Foundation ← Phase 3.1
  ↓
Phase 3.3 — Text Extraction ← Phase 3.2
  ↓
Phase 3.4 — Section Detection ← Phase 3.3
  ↓
Phase 3.5 — Facts Comparison ← Phase 2, 3.4
  ↓
Phase 3.6 — Version Management ← Phase 3.5
  ↓
Phase 3.7 — Master CV Generation ← Phase 2, 3.6
  ↓
Phase 3.8 — Document Management Frontend ← Phase 3.1, 3.3, 3.4, 3.5, 3.7
  ↓
Phase 4.1 — Core Job and Job Source Foundation ← Phase 1
  ↓
Phase 4.2 — Ingestion Runs and Source Snapshots ← Phase 4.1
  ↓
Phase 4.3 — First Approved Provider Adapter ← Phase 4.2
  ↓
Phase 4.4 — Normalization, Deduplication, and Freshness ← Phase 4.3
  ↓
Phase 4.5 — Saved Jobs and Review Workflow ← Phase 4.4
  ↓
Phase 4.6 — Job Discovery Frontend ← Phase 4.5
  ↓
Phase 5 — Job Analysis & Matching ← Phase 2, 4
  ↓
Phase 6 — Job-Specific CV Tailoring ← Phase 2, 3.7, 5
  ↓
Phase 7 — Salary Recommendations ← Phase 2, 4
  ↓
Phase 8 — Application Answer Vault ← Phase 2, 7
  ↓
Phase 9 — Application Preparation ← Phase 3.7, 5, 6, 8
  ↓
Phase 10 — Browser Automation ← Phase 9, 3.7, 8
  ↓
Phase 11 — Application Tracking ← Phase 5, 10
  ↓
Phase 12 — Background Automation ← Phase 4, 5, 9
  ↓
Phase 13 — Auth & Security ← All phases
  ↓
Phase 14 — Production & Deployment ← All phases
```

---

## Risk Register

| Risk | Severity | Likelihood | Mitigation | Owner Phase |
|------|----------|------------|-----------|-------------|
| **Fabricated Candidate Claims** | CRITICAL | Medium | Strict vault-first design, comparison flagging for review, automated tests for unsupported claims | Phase 3.5 |
| **Candidate Data Loss** | CRITICAL | Low | Alembic reversible migrations, automated backups, data preservation tests | Phase 3.2, 14 |
| **Unsafe File Uploads** | CRITICAL | Low | File signature validation, size limits, path traversal prevention, all upload tests | Phase 3.1 |
| **Secret Exposure** | CRITICAL | Low | .env ignored, no secrets in source code, environment variable injection only | All phases |
| **Incorrect CV Claims** | HIGH | Medium | Verified facts vault, section detection accuracy, facts comparison review | Phase 3.5 |
| **Job Source ToS Violations** | HIGH | Medium | Whitelist-only sources, no unauthorized scraping, explicit compliance rules | Phase 4 |
| **Duplicate Applications** | HIGH | Low | Duplicate detection query, confirmation number tracking | Phase 11 |
| **Browser Automation Failures** | HIGH | Medium | Proper error handling, manual resumption for CAPTCHA/MFA, audit logging | Phase 10 |
| **Database Migration Failure** | HIGH | Low | Reversible migrations, test on temporary database before production, rollback procedure | Phase 3.2, 14 |
| **Unhandled Extraction Errors** | MEDIUM | Medium | Try-catch blocks, safe error messages, extraction_error column | Phase 3.3 |
| **Incorrect Job Matching** | MEDIUM | Medium | Match algorithm testing, explainable scoring, manual review before auto-apply | Phase 5, 9 |
| **Salary Data Uncertainty** | MEDIUM | Medium | Confidence scoring, multiple data sources, user review before use | Phase 7 |
| **Legal Declaration Misses** | MEDIUM | Low | Manual review gate for legal questions, no automatic legal questions answered | Phase 10 |
| **Production Performance** | MEDIUM | Low | Monitoring, profiling, database indexing, async workers | Phase 14 |
| **PII in Logs** | MEDIUM | Low | Log sanitization, audit trail for sensitive operations only | Phase 13 |

---

## Validation Matrix

### Backend Changes

Every backend change must pass:

```bash
cd backend
source .venv/bin/activate
pytest -q
python -m compileall app
git diff --check
```

**Expected Results:**
- All tests pass (no failures or errors)
- No Python syntax errors
- No trailing whitespace or other formatting issues
- FastAPI app imports correctly
- All routes register

### Frontend Changes

Every frontend change must pass:

```bash
cd frontend
npm run lint
npx tsc --noEmit
npm run build
git diff --check
```

**Expected Results:**
- ESLint clean (no warnings or errors)
- TypeScript strict mode passes
- Production build succeeds
- No trailing whitespace

### Database Changes

Every database or migration change must:

1. Review the migration file (`alembic/versions/*.py`)
   - Check `upgrade()` and `downgrade()` are both present
   - Verify no data loss in downgrade
   - Check foreign key constraints and indexes
   - Verify column types and constraints

2. Test on temporary database:
   ```bash
   cd backend
   source .venv/bin/activate
   alembic upgrade head    # Apply all migrations
   alembic current         # Verify head reached
   alembic downgrade base  # Rollback to empty
   alembic upgrade head    # Apply again (verify idempotency)
   ```

3. Verify data preservation:
   - No required columns without defaults (unless intentional)
   - Cascade delete policies correct
   - Unique constraints not too restrictive

### Security-Sensitive Changes

Security-related changes (upload, extraction, auth, secrets) require:

- ✓ No hardcoded secrets or credentials in source code
- ✓ File upload validation tests (size, extension, signature)
- ✓ Path traversal tests
- ✓ Access control tests
- ✓ Error messages safe (no stack traces, paths, secrets)
- ✓ Input validation tests
- ✓ No PII in logs
- ✓ Secret values in .env (Git-ignored)

---

## Standard Milestone Workflow

Follow this workflow for every milestone:

1. **Read all guidance:**
   - Read root `CLAUDE.md` (Claude sessions) or `AGENTS.md` (Codex sessions)
   - Read `docs/roadmap.md` (this file)
   - Understand current milestone status and blockers

2. **Check Git status:**
   ```bash
   cd /Users/pavan/Desktop/careerpilot-ai
   git status --short
   ```

3. **Confirm the current milestone:**
   - Identify the next NOT STARTED milestone
   - Review dependencies (ensure prerequisites are COMPLETED)
   - Check for blockers

4. **Show a concise plan:**
   - List files to create/modify
   - State expected migration changes (if any)
   - Identify new API endpoints
   - List component changes (frontend)
   - Mention testing requirements
   - State expected validation commands

5. **Implement only this milestone:**
   - Do not start the next milestone
   - Create focused, single-purpose changes
   - Add/update only required files
   - Avoid scope creep

6. **Add focused tests:**
   - Test success behavior
   - Test validation failures
   - Test edge cases
   - Test security boundaries

7. **Validate everything:**
   - Run backend tests: `pytest -q`
   - Run Python compilation: `python -m compileall app`
   - Run frontend lint: `npm run lint`
   - Run TypeScript check: `npx tsc --noEmit`
   - Build frontend: `npm run build`
   - Review migration reversibility (if applicable)

8. **Review the diff:**
   ```bash
   git diff --check
   git status --short
   ```

9. **Report all changes:**
   - List created files
   - List modified files
   - List deleted files (if any)
   - Report test results
   - Report validation results
   - Clearly state any unresolved issues

10. **Review the milestone:**
    - Confirm all work completed
    - Confirm tests passing
    - Confirm validation complete
    - Confirm no security issues
    - Confirm no secrets exposed

11. **Commit one milestone:**
    - Create a single, focused commit
    - Use clear commit message (e.g., "Complete Phase 3.4 Section Detection")
    - Reference roadmap status
    - Do not push automatically

12. **Update roadmap status:**
    - Change milestone status from IN PROGRESS to COMPLETED
    - Update Git revision in roadmap
    - Commit roadmap update if requested

13. **Start next milestone only after explicit request:**
    - Wait for user confirmation to proceed
    - Do not automatically begin next phase
    - Report current project position

---

## Current Project Position

**Last Completed Milestone:** Phase 13 — Authentication, Privacy, and Security (Committed — Git revision `693e5c68a0352c07a0c852dac7f3d80a70de7793`). Phase 14 code-level groundwork committed (Git revision `fc72d03`); Phase 14 remains IN PROGRESS pending infrastructure provisioning/deployment.

**Phase 4 Commit Chain:**
- Phase 4.1 `cd33a9ae9ba0785635627ded887dd37057608320`
- Phase 4.2 `651170904a5f9f61a562713e97b9f676df2c81ca`
- Phase 4.3 `f9e0e893d1c4fad5aa1dbf1d00d3a94c88194c78`
- Phase 4.4 `ae36ba6edf065fd7b619ee8bcf7f401d4590f33f`
- Phase 4.5 `722c1cd95ef99c6ef5b3a9c8bbf7a911f9ddcd40`
- Phase 4.6 — see final Phase 4 commit in `git log`

**Current Status:** Phases 1–13 COMPLETED; Phase 14 IN PROGRESS (code groundwork committed; deployed to Supabase + Render + Vercel). Phase 15 — Multi-tenant accounts IN PROGRESS: 15A (users table, username+password login, per-account sessions/profile) COMMITTED; 15B (all personal API routes scoped to the authenticated user's candidate profile; cross-user isolation tests) COMPLETE and validated (full suite green; upgrade/downgrade validated on SQLite and real PostgreSQL). 15C (frontend registration + username login) and per-user background workers (the auto-apply/matching pipeline still operates on a single candidate profile and must be looped over all profiles) remain. Phase 16 — One-Click Auto-Apply COMPLETED (Committed — Git revision `264c166caa14357e41b04ece234daf08fbb5b16c`; alembic head `f4a5b6c7d8e9`; full suite 526 passed) — see the Phase 16 milestone section.

**First Not-Started Milestone:** Phase 14 infrastructure/deployment steps (provisioning, hosting, backups) — see `docs/deployment.md`.

**Immediate Next Action:** Complete Phase 14 by following `docs/deployment.md` in a real environment: provision PostgreSQL, run `alembic upgrade head` against it, configure object storage/SMTP/Sentry/scheduler, deploy backend and frontend, restrict CORS, enforce TLS, and automate + test backups. Committed Alembic head is now `a9b0c1d2e3f4` (Phase 13), and the real dev database (`backend/careerpilot.db`) has been upgraded to it (additive; existing data preserved). Standing reminders: (1) Phase 10's live Playwright driver and (2) Phase 13's infrastructure security controls (encryption-at-rest, TLS enforcement, backup/restore, retention automation) and (3) global auth enforcement on existing routes are all deferred to Phase 14 / deployment and coordinated with the frontend; Phase 12 workers never auto-submit. Note: Phase 14 is largely a deployment/infrastructure milestone (PostgreSQL/Supabase, object storage, hosting, Sentry, backups) — much of it cannot be executed or validated inside this sandbox and will need a real target environment; scope it explicitly before starting. Local `npm run build` should be run once to confirm the production build (sandbox validation was blocked only by the pre-existing `next/font/google` network requirement).

**Validation Summary:**
- ✓ Phase 4.2 implementation committed with Git revision `651170904a5f9f61a562713e97b9f676df2c81ca`
- ✓ Phase 4.2 targeted tests passed: 36 tests; complete backend suite: 249 passed, 1 environment-restricted skip
- ✓ Python compile check passed (`python -m compileall app`)
- ✓ Ruff passed on all Phase 4.2 files
- ✓ Migration `c9d0e1f2a3b4` validated: fresh-database full cycle and targeted upgrade/downgrade/re-upgrade with job-source row preservation
- ✓ Real `backend/careerpilot.db` upgraded to `c9d0e1f2a3b4`; existing tables preserved
- ✓ Independent code review completed; blocking findings fixed pre-commit (IntegrityError handling, atomic counter increment, bounded counters)
- ✓ New read-only endpoints registered: `GET /api/ingestion-runs`, `GET /api/ingestion-runs/{run_id}`, `GET /api/ingestion-runs/{run_id}/snapshots`
- ✓ Snapshot responses never expose provider payloads or internal storage references; retention cleanup preserves runs, sources, and normalized job provenance
- ✓ Phase 4.1 completed previously with Git revision `cd33a9ae9ba0785635627ded887dd37057608320` (57 targeted tests)
- ✓ Phase 3.8 added document upload, list, detail, status, extraction, section-detection, verified-facts comparison, original CV-version adoption, CV-version lifecycle, Verified Master CV generation, and artifact download UI
- ✓ Phase 3.8 renders extracted CV and backend content as plain text, does not use `dangerouslySetInnerHTML`, and does not display storage paths or physical stored filenames
- ✓ Phase 3.8 requires confirmation for destructive archive/delete actions, prevents duplicate upload/comparison/generation submissions, and uses a stable idempotency key for one deliberate generation attempt
- ✓ Phase 3.8 changed no backend application files and no database files
- ✓ Phase 3.8 added no PDF, DOCX, TTF, OTF, TTC, generated CV, uploaded CV, secret, or personal document to Git
- ✓ Phase 3 CV Document System is COMPLETED
- ✓ Phase 4.1 backend schema and read-only API implementation is COMPLETED (Git revision `cd33a9ae9ba0785635627ded887dd37057608320`)
- ✓ Phase 4.1 adds no provider credentials, source fetching, scheduled ingestion, scraping, matching, saved jobs, automatic applications, browser automation, or frontend job-discovery UI
- ✓ Phase 4.1 targeted backend tests passed: 57 tests
- ✓ Complete backend suite passed: 205 tests, 1 sandbox-restricted Quick Look raster test skipped
- ✓ Alembic has exactly one committed head: `c9d0e1f2a3b4`
- ✓ Committed migration chain: `6a528be87510` → `b7a3c8d9e012` → `d8e9f0a1b2c3` → `c4e7d9a1b2c3` → `e5f6a7b8c9d0` → `f6a7b8c9d0e1` → `a7b8c9d0e1f2` → `b8c9d0e1f2a3` → `c9d0e1f2a3b4`
- ✓ Temporary upgrade to `c9d0e1f2a3b4`, downgrade to `b8c9d0e1f2a3`, and re-upgrade to `c9d0e1f2a3b4` passed
- ✓ Real development database safely upgraded to revision `c9d0e1f2a3b4` after review; existing data preserved

**Immediate Blockers:** None

---

## Glossary

- **Verified Fact** — Candidate information entered directly into the vault (education, experience, skills, etc.)
- **Unverified Claim** — Text in CV or document not confirmed against vault (flagged for review)
- **Facts Vault** — Database of candidate profile, education, experience, projects, skills, certifications
- **CV Section** — Logical segment of CV (contact, experience, education, skills, etc.)
- **Section Detection** — Parsing CV text to identify section boundaries and types
- **Facts Comparison** — Matching CV sections to vault facts; identifying matches, mismatches, unverified claims
- **Master CV** — ATS-friendly CV generated from verified facts only (no unverified claims)
- **Tailored CV** — Master CV modified for specific job (selective fact emphasis)
- **Application Package** — Job, CV, cover letter, answers, match report, ready for application
- **Application Readiness** — Status of application package (ready, blocked, needs review)
- **Job Source** — Permitted source of job data (API or approved career page)
- **Match Score** — Numerical assessment of candidate fit for job (0–100)
- **Eligibility** — Determination of whether candidate meets job requirements
- **Blocker** — Issue preventing application (missing info, CAPTCHA, assessment, legal question)
- **Application Workflow** — End-to-end process: discover job → analyze → prepare → apply → track

---

**Roadmap Version:** 0.9.10
**Last Updated:** 2026-07-02
**Repository:** https://github.com/[your-org]/careerpilot-ai  
**Maintainer:** CareerPilot AI Development Team  
**Status:** Actively maintained — Phases 1–13 COMPLETED; Phase 14 IN PROGRESS (code groundwork committed; infrastructure/deployment remaining)
