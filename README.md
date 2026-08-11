# CareerPilot AI

A personal career automation platform built around one hard rule: **the system never invents candidate facts.**

Every claim that appears in a generated CV, cover letter, or application answer must trace back to a verified record in the candidate facts vault. Anything uncertain is flagged for manual review rather than quietly accepted — and absence from the vault is never treated as proof a claim is false.

> **Status:** A single-user personal project, developed milestone-by-milestone against [`docs/roadmap.md`](docs/roadmap.md). It is not a hosted service and has no multi-tenant guarantees beyond what the roadmap records as complete. Use it as your own deployment, or as a reference.

## What it does

- **Verified facts vault** — profile, work experience, education, projects, skills, and certifications, entered directly rather than inferred.
- **CV document pipeline** — secure PDF/DOCX upload with signature validation and content hashing, text extraction, deterministic section detection, and comparison of uploaded CV text against the vault to surface unsupported claims.
- **Truthful CV generation** — ATS-friendly DOCX and PDF built only from verified fields, with version lineage and primary-version selection.
- **Job discovery** — compliance-gated ingestion from Greenhouse, Lever, Ashby, Remotive, Arbeitnow, Adzuna, and Reed, with normalization, deduplication, and freshness tracking.
- **Matching and analysis** — explainable eligibility scoring and salary recommendations grounded in verified records.
- **Application workflows** — job-specific CV tailoring, a verified answer vault, application packages, and tracked application runs.
- **Safety gates** — the system pauses for CAPTCHA, MFA, assessments, legal declarations, sensitive questions, and any irreversible submission. It does not automate sites that prohibit automation, and it never bypasses access controls or misrepresents the candidate.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy 2, Pydantic v2, Alembic |
| Database | SQLite (development), PostgreSQL / Supabase (production) |
| Frontend | Next.js 16 App Router, React 19, TypeScript (strict), Tailwind CSS 4 |
| Storage | Local filesystem or S3-compatible object storage |
| Hosting | Render (API) + Vercel (frontend), via [`render.yaml`](render.yaml) |

## Repository layout

```text
careerpilot-ai/
├── backend/          # FastAPI service
│   ├── app/          # api/routes, core, models, schemas, services
│   ├── alembic/      # migrations
│   └── tests/
├── frontend/         # Next.js App Router (no src/ directory)
│   ├── app/  components/  lib/  types/
├── docs/
│   ├── roadmap.md    # Authoritative development roadmap
│   └── deployment.md
├── CLAUDE.md         # Instructions for Claude sessions
└── AGENTS.md         # Same ruleset, Codex format
```

## Getting started

Requires Python 3.12+ and Node.js 20+. (Render pins 3.12.8 for production; local development runs fine on newer.)

**Backend** (from `backend/`):

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt
```

`requirements-dev.txt` includes the runtime pins from `requirements.txt` plus pytest, mypy, and ruff. For a production install, use `requirements.txt` alone.

Copy the environment template and fill it in — it contains placeholder names only, no secrets:

```bash
cp .env.example .env
```

Apply migrations, then run the dev server on `http://127.0.0.1:8000`:

```bash
alembic upgrade head && fastapi dev app/main.py
```

**Frontend** (from `frontend/`, npm only):

```bash
npm install && npm run dev
```

The frontend defaults to `http://127.0.0.1:8000` for the API, so no configuration is needed locally. To point it elsewhere, set `NEXT_PUBLIC_API_URL` in `frontend/.env.local`.

## Configuration

All backend settings use the `CAREERPILOT_` prefix and are documented in [`backend/.env.example`](backend/.env.example). Everything optional stays inert until configured — without an SMTP host, notifications are recorded but not sent; without Adzuna/Reed keys, those connectors return a clear message instead of failing.

Secrets belong in the environment and are never committed. `.env` files, the local SQLite database, and all uploaded or generated candidate documents are gitignored by design.

## Validation

```bash
cd backend && pytest && python -m compileall app
```

```bash
cd frontend && npm run lint && npx tsc --noEmit && npm test
```

## Documentation

- [`docs/roadmap.md`](docs/roadmap.md) — the authoritative roadmap: phase status, milestone scope, validation records, and committed revisions.
- [`docs/deployment.md`](docs/deployment.md) — production deployment guidance.
- [`docs/deploy-render-supabase-vercel.md`](docs/deploy-render-supabase-vercel.md) — a concrete Render + Supabase + Vercel walkthrough.

## License

[MIT](LICENSE)
