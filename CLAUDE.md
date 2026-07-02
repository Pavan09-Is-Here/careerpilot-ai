# CareerPilot AI — Claude Instructions

CareerPilot AI is a personal career automation platform: a single-user verified candidate facts vault, truthful ATS-friendly CV generation, compliant job discovery, eligibility analysis, and application assistance.

**This system must never invent candidate facts or make unsupported claims.**

> `AGENTS.md` (root) is the equivalent ruleset kept for Codex compatibility. If the two ever conflict, this file wins for Claude sessions. `docs/roadmap.md` is the authoritative development roadmap.

## Repository layout

```text
careerpilot-ai/
├── backend/          # FastAPI + SQLAlchemy 2 + Pydantic + Alembic, SQLite (dev)
│   └── app/          # api/routes, core, models, schemas, services
├── frontend/         # Next.js App Router + TypeScript + Tailwind (no src/ dir)
│   ├── app/  components/  lib/  types/
├── docs/roadmap.md   # Authoritative roadmap — read before any milestone work
├── AGENTS.md         # Codex-format instructions (kept in sync manually)
└── CLAUDE.md         # This file
```

Always inspect the real repository before assuming a file or directory exists. Do not rebuild or replace the project from scratch.

## Core candidate-truth rules (critical)

Never fabricate or infer unsupported candidate information: employment, titles, employers, dates, education, degrees, grades, projects, skills, technologies, certifications, credential IDs, achievements, metrics, years of experience, work-authorisation/sponsorship status, salary history, or personal declarations.

Only verified facts may appear as confirmed claims in generated CVs or applications. When evidence is uncertain: mark it for manual review; do not treat absence from the facts vault as proof a claim is false; do not silently modify candidate records; do not promote an uncertain claim to verified.

## Application automation safety

Do not automate websites that prohibit automation. Never bypass CAPTCHA, MFA, identity verification, bot detection, rate limits, access controls, assessments, video interviews, legal declarations, or consent screens. Pause and require user action for any of those, plus sensitive personal questions, unknown application questions, judgement calls, and irreversible submissions. Never misrepresent the candidate.

## Roadmap-driven workflow

`docs/roadmap.md` drives all feature work. Before any milestone:

1. Read `docs/roadmap.md`; identify current phase and the next NOT STARTED milestone.
2. Verify dependency phases are COMPLETED.
3. Implement only the explicitly requested milestone — never auto-continue to the next phase.
4. A milestone is COMPLETED only when code exists, tests pass, migrations are validated and reversible, work is committed and reachable in `git log`, and the roadmap documents the Git revision. Uncommitted work is IN REVIEW / IN PROGRESS.

## Standard task process

For every substantial task: inspect relevant files → check `git status` → find the smallest safe implementation → state a concise plan → modify only required files → add focused tests → run validation → review the diff → report created/modified/deleted files, commands run, and remaining limitations.

## Change control — never do without explicit approval

- Commit, push, deploy, rewrite history, force-push, delete branches
- Delete/recreate the database or remove candidate data; run destructive migrations
- Modify or delete `backend/careerpilot.db`
- Use `sudo`; modify files outside this repository
- Print secret values; add secrets to source control
- Replace working modules without inspecting them first
- Large architectural changes or new production dependencies without explanation
- Rename or remove existing API routes

Before any potentially destructive operation, stop and ask.

## Secrets and uploaded files

Never display or commit real secrets (`.env`, `frontend/.env.local`, `backend/.env` stay Git-ignored; `.env.example` may hold placeholder names only). No real keys/tokens/credentials in source, tests, docs, commit messages, terminal output, or reports.

Uploaded CVs and generated documents must never be committed or placed in `frontend/public`. For uploads: validate size, extension, declared media type, and actual file signature; generate server-side random filenames; prevent directory traversal; hash content where appropriate; clean up partial files on failure; never expose absolute storage paths via the API.

## Database rules

Preserve all existing data. Use Alembic for schema changes: create reversible migrations, review generated operations, avoid destructive column/table operations, validate against a safe test database (`backend/tests/test_alembic_migration_parity.py` checks model/migration parity). Do not rely on `create_all()` in place of migrations.

## Backend conventions

Typed Python. Keep SQLAlchemy models, Pydantic schemas, routes, services, storage, config, and tests separated. No filesystem operations or business logic in route functions; use dependency injection for sessions/services. Safe API errors only (no paths, stack traces, connection strings, secrets). Explicit response models; never leak fields not intended for the client.

## Frontend conventions

Next.js App Router, TypeScript strict, Tailwind. API functions in `frontend/lib`, shared types in `frontend/types`, reusable components in `frontend/components`, routes in `frontend/app`. No `src/` directory. Don't duplicate API functions or put heavy logic in route pages. Preserve existing routes and profile functionality. Also read `frontend/CLAUDE.md` / `frontend/AGENTS.md` (Next.js version-specific rules) before frontend work.

## Commands

Backend (from `backend/`, with `.venv` activated):

```bash
fastapi dev app/main.py      # dev server
pytest                       # tests
python -m compileall app     # compile check
alembic upgrade head         # migrations
```

Frontend (from `frontend/`, npm only):

```bash
npm run dev
npm run lint
npx tsc --noEmit
npm run build
```

## Definition of done

Requested scope implemented; existing functionality preserved; tests, lint, type checks, and builds pass; database safety verified; no secrets or uploaded documents exposed/committed; diff reviewed; changed files and remaining limitations reported. Never claim success without running validation — if a command can't run, say exactly why.

## Testing expectations

Test success paths, validation failures, missing-record behaviour, security boundaries, data preservation, and response shape where important. Never weaken or delete existing tests to make a change pass; investigate failures, fix the implementation, and report unresolved failures.

## Communication

Be direct and precise. Start substantial tasks with a concise plan and key risks. Finish with what changed, files touched, validation results, and unresolved issues. Do not automatically begin the next phase.

## Current project status

See `docs/roadmap.md` → **Current Project Position** for the latest status (roadmap v0.8.7: Phase 4.2 COMPLETED; Phase 4.3 — First Approved Provider Adapter — NOT STARTED).
