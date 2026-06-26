# CareerPilot AI Development Roadmap

**Version:** 0.7.0  
**Last Updated:** 2026-06-26  
**Status:** Actively in development — Phase 3.3 (Document Text Extraction) completed

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

**Not Started:**
- Phase 3.4: Deterministic CV Section Detection
- Phase 3.5: Verified Facts Comparison
- Phase 3.6: CV Version Management
- Phase 3.7: Verified Master CV Generation
- Phase 3.8: Document Management Frontend
- Phase 4–14: Job discovery, analysis, matching, tailoring, salary recommendations, application answers, browser automation, tracking, authentication, production deployment

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
│   │       └── document.py        # Document upload, extraction, management
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
│   │   └── document.py
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── candidate_profile.py
│   │   ├── education.py
│   │   ├── experience.py
│   │   ├── project.py
│   │   ├── skill.py
│   │   ├── certification.py
│   │   └── document.py
│   ├── services/                  # Business logic
│   │   ├── document_storage.py    # File validation, safe storage
│   │   └── document_extraction.py # PDF/DOCX text extraction
│   ├── repositories/              # Database access layer (extensible)
│   └── utils/
├── alembic/
│   ├── env.py                     # Alembic configuration
│   ├── versions/                  # Versioned migrations
│   │   ├── 6a528be87510_baseline_current_schema.py
│   │   └── b7a3c8d9e012_add_document_extraction_metadata.py (committed)
│   └── alembic.ini                # Migration settings
├── tests/
│   ├── conftest.py                # Fixtures, test database setup
│   ├── test_profile_resources.py  # Candidate facts vault tests
│   ├── test_documents.py          # Upload and document tests
│   └── test_document_extraction.py # Text extraction tests
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
- `python-docx` — DOCX paragraph extraction
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
  - Creates baseline schema for all Phase 1 and 2 tables
  - Includes candidate_profiles, education, experience, projects, skills, certifications, documents
  - Revisions properly configured; down_revision set to None (baseline)
- **Reversible Migrations**: All migrations include `upgrade()` and `downgrade()` functions
- **Migration Commands**:
  - `alembic heads` — Check current migration head (currently `6a528be87510`)
  - `alembic upgrade head` — Apply all pending migrations
  - `alembic downgrade -1` — Rollback one migration

**Validation Strategy:**
- Baseline migration tested against temporary SQLite database
- Schema creation verified with `alembic upgrade head`
- Downgrade path verified with `alembic downgrade base`
- Existing candidate data preserved across upgrade/downgrade

**Current Migration Head:**
- `6a528be87510_baseline_current_schema` (Phase 1, 2 schema)
- `b7a3c8d9e012_add_document_extraction_metadata` (Phase 3.3, committed and validated)

**Validation:** ✓ Baseline migration tested; reversible structure confirmed  
**Data Preservation:** ✓ No data loss on upgrade/downgrade

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
- SQLite `.db` file created at startup
- Tables auto-created via `Base.metadata.create_all()`

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

**Milestone Status:** NOT STARTED

**Goal:** Automatically detect and segment CV sections (contact, experience, education, skills, etc.) from extracted text.

**Scope:**
- Parse extracted text into logical sections
- Identify section boundaries via heading detection
- Map sections to standard CV structure
- Handle missing or non-standard sections
- Provide confidence scores for each detection
- Support re-detection on updated text

**Database Schema Changes:**
- New table `cv_sections`:
  - id, document_id (fk), section_type, title, start_char, end_char, content_text, confidence, created_at
  - Unique constraint: (document_id, section_type, start_char)

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
- Heading aliases: Support variations ("Work History" → "Work Experience", "Technical Skills" → "Skills")
- Contact block inference: Parse text at document start for phone, email, location patterns
- Section ordering: Most CVs follow standard order (contact, summary, experience, education, skills)
- Character ranges: Each section has approximate character positions
- Confidence scoring: Based on heading match quality, section completeness, known patterns

**API Endpoints (Planned):**
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
- Section detection algorithm implemented
- API endpoints created
- Database migration for cv_sections table
- All detection tests pass
- Confidence scoring calibrated

---

#### Phase 3.5 — Verified Facts Comparison

**Milestone Status:** NOT STARTED

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
- New table `cv_fact_matches`:
  - id, document_id, section_id, fact_type (education, experience, skill, etc.), verified_fact_id, match_status (confirmed, possible_mismatch, unverified, missing)
  - Match confidence score
  - Discrepancies noted (date mismatch, org mismatch, etc.)
  - Manual_review_required (boolean)

**Match Results:**
- `confirmed` — CV text closely matches verified fact
- `possible_mismatch` — CV text differs from verified fact (date, organization, detail)
- `unverified` — CV claims something not in vault (requires review)
- `missing` — Verified fact not found in CV (potential CV gap)

**Important Matching Rules:**
- **Never assume absence is falsity** — If a skill is not in the CV but is in the vault, the candidate may have omitted it intentionally for brevity or relevance
- **Flag, don't conclude** — Uncertain matches marked for review, never treated as proof of false claims
- **Manual review required for:**
  - Date discrepancies (e.g., CV says 2020–2022, vault says 2019–2023)
  - Organization name variations (e.g., "Microsoft" vs "Microsoft Corp")
  - Role title variations (e.g., "Senior Engineer" vs "Software Engineer III")
  - New claims not in vault (potential new facts to add)

**API Endpoints (Planned):**
- `POST /api/documents/{id}/compare-facts` — Trigger comparison
- `GET /api/documents/{id}/fact-matches` — Retrieve all matches
- `PATCH /api/fact-matches/{id}` — Mark as manually reviewed

**Testing Requirements:**
- Exact matches detected (experience, education, skills)
- Date mismatches flagged
- Organization name variations identified
- Unverified claims flagged
- Missing vault facts detected
- Manual review items correct
- No false positives

**Dependencies:**
- Requires Phase 2 (Facts Vault) ✓
- Requires Phase 3.3 (Text Extraction) ✓
- Requires Phase 3.4 (Section Detection) ✓

**Definition of Done:**
- Matching algorithm implemented
- All comparison tests pass
- Database schema for fact_matches created and migrated
- API endpoints created
- No false CV claims marked as confirmed

---

#### Phase 3.6 — CV Version Management

**Milestone Status:** NOT STARTED

**Goal:** Support multiple CV versions (original, parsed, verified, tailored) with parent/source relationships and version history.

**Scope:**
- Track original uploaded CV
- Track parsed/extracted text version
- Maintain verified master CV (generated from vault facts)
- Support job-specific tailored CVs
- Store parent/source document relationships
- Manage version statuses and lifecycle

**Database Schema Changes:**
- Extend `documents` table with:
  - `version_type` (original, parsed, verified_master, tailored)
  - `parent_document_id` (fk to parent version)
  - `version_status` (active, archived, superseded)
  - `version_number` (1, 2, 3...)
  - `job_id` (fk to job if tailored, nullable)

**Version Types:**
- `original_cv` — User-uploaded document (PDF/DOCX)
- `parsed_cv` — Extracted text representation (for reference)
- `verified_master_cv` — Generated DOCX/PDF from verified facts vault only
- `tailored_cv` — Job-specific CV (Verified Master + tailoring)

**Version Relationships:**
- Original → Parsed (1-to-1)
- Parsed → Verified Master (1-to-1)
- Verified Master → Tailored (1-to-many, one per job)

**Primary Version:**
- Only one `is_primary` original CV
- Only one active verified master CV
- Multiple tailored CVs, one per job

**API Endpoints (Planned):**
- `GET /api/documents?version_type=verified_master` — Get verified master CV
- `POST /api/documents/{id}/create-verified-master` — Generate master from vault
- `GET /api/documents?version_type=tailored&job_id={job_id}` — Get tailored CV for job

**Testing Requirements:**
- Version hierarchy correct
- Parent-child relationships maintained
- Only one primary original CV
- Verified master generation from vault facts
- Tailored CV creation with job reference
- Version status transitions (active → archived)

**Dependencies:**
- Requires Phase 2 (Facts Vault) ✓
- Requires Phase 3.5 (Facts Comparison) ✓
- Requires Phase 4 (Job Discovery) for job-specific tailoring

**Definition of Done:**
- Document model extended with version tracking
- Migration for version fields created
- Version management routes implemented
- API supports querying by version type

---

#### Phase 3.7 — Verified Master CV Generation

**Milestone Status:** NOT STARTED

**Goal:** Generate truthful, ATS-friendly CV in DOCX and PDF formats from verified candidate facts only.

**Scope:**
- DOCX generation with verified facts vault content
- PDF generation from DOCX (via conversion library)
- One-column ATS-friendly format
- Selectable text (not images)
- Consistent fonts and spacing
- Safe download endpoints
- No unsupported claims or inferred data

**Generated CV Structure:**
- Header: Name, email, phone, location
- Professional Summary (verified facts only)
- Work Experience (from verified experience records)
- Education (from verified education records)
- Skills (from verified skills)
- Projects (from verified projects)
- Certifications (from verified certifications)
- No inferred or generated content

**DOCX Generation Approach:**
- Use `python-docx` library
- Single-column layout
- Standard fonts (Calibri, Arial)
- 1-inch margins
- 11-pt body, 14-pt headings
- No colors, images, tables (for ATS compatibility)

**PDF Generation Approach:**
- Convert DOCX to PDF (via `LibreOffice`, `docx2pdf`, or similar)
- Maintain text selectability (not scanned image)
- Standard Letter size (8.5×11")

**API Endpoints (Planned):**
- `POST /api/documents/generate-verified-master` — Generate verified master CV
- `GET /api/documents/{id}/download` — Download as DOCX
- `GET /api/documents/{id}/download?format=pdf` — Download as PDF

**Security Requirements:**
- Only verified facts included
- No inferred or uncertain data
- No unsupported dates, metrics, claims
- Safe file download (no path traversal)
- Generated CV stored as document record

**Testing Requirements:**
- DOCX structure correct
- All verified facts included
- No inferred data present
- PDF conversion successful
- Text selectable in PDF
- ATS-friendly format (no complex formatting)
- Download endpoints secure

**Dependencies:**
- Requires Phase 2 (Facts Vault) ✓
- Requires Phase 3.6 (Version Management) ✓

**Definition of Done:**
- DOCX generation working with verified facts
- PDF generation from DOCX working
- Download endpoints secure
- All generation tests pass
- ATS compatibility verified

---

#### Phase 3.8 — Document Management Frontend

**Milestone Status:** NOT STARTED

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
- `/documents/{id}` — Single document detail view with extraction/sections/comparison

**API Integration:**
- POST /api/documents/upload
- GET /api/documents
- GET /api/documents/{id}
- POST /api/documents/{id}/extract
- POST /api/documents/{id}/detect-sections
- GET /api/documents/{id}/sections
- POST /api/documents/{id}/compare-facts
- GET /api/documents/{id}/fact-matches
- POST /api/documents/generate-verified-master
- GET /api/documents/{id}/download
- DELETE /api/documents/{id}

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

---

### Phase 4 — Job Discovery

**Milestone Status:** NOT STARTED

**Goal:** Discover job opportunities from compliant sources.

**Scope:**
- Integrate with job APIs (Greenhouse, Lever, Ashby, Workable, Adzuna)
- Parse job postings
- Detect duplicates
- Track job expiry
- Scheduled discovery workers
- Compliance enforcement (no unauthorized scraping)

**Supported Job Sources:**
- Greenhouse (API)
- Lever (API)
- Ashby (API)
- Workable (API)
- Adzuna (API)
- Approved company career pages (explicit permits only)

**Prohibited Sources:**
- LinkedIn Jobs (terms-of-service violations)
- Indeed (web scraping prohibited)
- Unauthorized scraping of any site

**Database Schema Changes:**
- New table `jobs`:
  - id, source (greenhouse, lever, etc.), source_job_id, source_url
  - company, title, location, employment_type, salary_min, salary_max, salary_currency
  - description, required_skills, preferred_skills, required_experience, required_education
  - work_authorization_required, sponsorship_available
  - posted_at, deadline, discovered_at, last_checked_at, status (active, expired, withdrawn)

**API Endpoints (Planned):**
- `POST /api/jobs/discover` — Trigger job discovery
- `GET /api/jobs` — List discovered jobs
- `GET /api/jobs/{id}` — Job detail

**Compliance Requirements:**
- No unauthorized scraping
- All sources explicitly permitted in code
- API rate limiting respected
- User-Agent headers correct
- Robots.txt respected

**Testing Requirements:**
- API integration works
- Job parsing correct
- Duplicate detection working
- Expiry tracking accurate

**Dependencies:**
- Requires Phase 1 (Project Foundation) ✓

**Definition of Done:**
- Job discovery integration implemented
- Database schema for jobs created and migrated
- Scheduled discovery workers functional
- All discovery tests pass
- Compliance verified

---

### Phase 5 — Job Analysis, Matching, and Eligibility

**Milestone Status:** NOT STARTED

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

**Milestone Status:** NOT STARTED

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

**Milestone Status:** NOT STARTED

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

**Milestone Status:** NOT STARTED

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

---

### Phase 9 — Application Preparation

**Milestone Status:** NOT STARTED

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

---

### Phase 10 — Browser-Assisted Applications

**Milestone Status:** NOT STARTED

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

---

### Phase 11 — Application Tracking Dashboard

**Milestone Status:** NOT STARTED

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

---

### Phase 12 — Background Automation

**Milestone Status:** NOT STARTED

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

---

### Phase 13 — Authentication, Privacy, and Security

**Milestone Status:** NOT STARTED

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

---

### Phase 14 — Production Database and Deployment

**Milestone Status:** NOT STARTED

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
Phase 3.8 — Document Frontend ← Phase 3.1, 3.3, 3.4, 3.5, 3.7
  ↓
Phase 4 — Job Discovery ← Phase 1
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
   - Read root `AGENTS.md`
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

**Last Completed Milestone:** Phase 3.3 — PDF and DOCX Text Extraction (Committed)

**First Not-Started Milestone:** Phase 3.4 — Deterministic CV Section Detection

**Immediate Next Action:** Phase 3.4 — Deterministic CV Section Detection

**Validation Summary:**
- ✓ 43 backend tests passed
- ✓ Python compilation passed
- ✓ Alembic head: `b7a3c8d9e012`
- ✓ Upgrade, downgrade, and re-upgrade validated on an isolated temporary SQLite database
- ✓ The real development database remained unchanged during the final validation

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

**Roadmap Version:** 0.7.0  
**Last Updated:** 2026-06-26  
**Repository:** https://github.com/[your-org]/careerpilot-ai  
**Maintainer:** CareerPilot AI Development Team  
**Status:** Actively maintained — in development phase 3
