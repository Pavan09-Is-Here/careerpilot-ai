# CareerPilot AI — Codex Instructions

## Project purpose

CareerPilot AI is a personal career automation platform.

Its planned capabilities include:

* Maintaining a verified candidate facts vault
* Uploading and parsing CV documents
* Generating truthful ATS-friendly CV versions
* Discovering jobs from permitted sources
* Analysing job eligibility and match quality
* Recommending salary ranges
* Preparing application answers
* Assisting with permitted job applications
* Tracking submitted applications

This system must never invent candidate facts or make unsupported claims.

## Repository layout

The repository root contains both the backend and frontend.

```text
careerpilot-ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   └── .venv/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── types/
├── AGENTS.md
├── README.md
└── .gitignore
```

Always inspect the real repository before assuming a file or directory exists.

Do not rebuild or replace the project from scratch.

## Technology stack

### Backend

* Python
* FastAPI
* SQLAlchemy 2
* Pydantic
* SQLite for local development
* PostgreSQL or Supabase may be introduced later for production

### Frontend

* Next.js App Router
* TypeScript
* Tailwind CSS
* No `src` directory unless the existing repository is intentionally migrated

## Existing completed functionality

Preserve the following working features:

* Backend health endpoint
* Frontend and backend connection
* Candidate profile
* Education records
* Work experience records
* Project records
* Skills records
* Certification records
* Verification fields
* SQLite persistence
* Profile management frontend

Expected existing API areas include:

* `/api/health`
* `/api/profile`
* `/api/education`
* `/api/experience`
* `/api/projects`
* `/api/skills`
* `/api/certifications`

Do not rename or remove existing routes unless explicitly requested.

## Core candidate-truth rules

Never fabricate or infer unsupported candidate information.

Do not invent or alter:

* Employment
* Job titles
* Employers
* Employment dates
* Education
* Degrees
* Grades
* Projects
* Skills
* Technologies
* Certifications
* Credential IDs
* Achievements
* Metrics
* Years of experience
* Work-authorisation status
* Sponsorship status
* Salary history
* Personal declarations

Only verified facts may be used as confirmed claims in generated CVs or applications.

When evidence is uncertain:

* Mark it for manual review.
* Do not treat absence from the facts vault as proof that a claim is false.
* Do not silently modify candidate records.
* Do not convert an uncertain claim into a verified claim.

## Application automation safety

Do not automate websites that prohibit automation.

Do not attempt to bypass:

* CAPTCHA
* MFA
* Identity verification
* Bot detection
* Rate limits
* Access controls
* Assessments
* Video interviews
* Legal declarations
* Consent screens

Pause and require user action for:

* CAPTCHA
* MFA
* Identity checks
* Assessments
* Legal or regulatory declarations
* Sensitive personal questions
* Unknown application questions
* Questions requiring personal judgement
* Irreversible application submission when approval is required

Never misrepresent the candidate.

## General working process

For every substantial task:

1. Read this file.
2. Inspect the relevant existing files.
3. Check `git status`.
4. Identify the smallest safe implementation.
5. State a concise plan.
6. Modify only files required for the task.
7. Add or update focused tests.
8. Run relevant validation commands.
9. Review the final diff.
10. Report all created, modified, and deleted files.
11. Report commands run and their results.
12. Report remaining errors or limitations.

Do not continue into an unrelated phase unless the prompt explicitly requests it.

## Change-control rules

Do not:

* Commit automatically
* Push automatically
* Deploy automatically
* Rewrite Git history
* Force-push
* Delete branches
* Delete the repository
* Delete the database
* Recreate the database
* Remove existing candidate data
* Run destructive migrations
* Run commands with `sudo`
* Modify files outside this repository
* Print secret environment values
* Add secrets to source control
* Replace working modules without first inspecting them
* Make large architectural changes without explaining them
* Add production dependencies without explaining why they are necessary

Before a potentially destructive operation, stop and request approval.

## Git rules

Before editing:

```bash
git status
```

After editing:

```bash
git diff --check
git status
```

Do not automatically run:

```bash
git commit
git push
git reset --hard
git clean -fd
```

Do not remove untracked files unless their purpose has been inspected.

Do not modify or delete the SQLite database file.

## Secret and environment-file rules

Never display or commit real secret values.

Files containing secrets must remain ignored, including where applicable:

```text
.env
.env.local
.env.development.local
.env.production.local
backend/.env
frontend/.env.local
```

An `.env.example` file may contain variable names and safe placeholder values only.

Never place real API keys, database passwords, tokens, cookies, or credentials in:

* Source code
* Tests
* Documentation
* `AGENTS.md`
* Commit messages
* Terminal output
* Generated reports

## Uploaded-file rules

Uploaded CVs and generated application documents must not be committed to Git.

Store them outside the frontend public directory.

Uploaded filenames must not be trusted.

For uploaded documents:

* Validate size
* Validate extension
* Validate declared media type
* Validate actual file signature or structure
* Generate a server-side random filename
* Prevent directory traversal
* Calculate a content hash where appropriate
* Remove partial files after failure
* Never expose absolute storage paths through the API

## Database rules

Preserve all existing data.

Do not delete or recreate the SQLite database.

For schema changes:

1. Inspect the current migration setup.
2. Use the existing migration framework when present.
3. Create reversible migrations.
4. Review generated migration operations.
5. Avoid destructive column or table operations.
6. Validate migrations against a safe test database.
7. Never apply an unreviewed destructive migration to the real development database.

If migration tooling is absent, report this before introducing a migration framework.

Do not rely on `create_all()` as a substitute for proper production migrations once migration tooling is established.

## Backend conventions

Use typed Python.

Maintain separation between:

* SQLAlchemy models
* Pydantic schemas
* API routes
* Business services
* Storage services
* Configuration
* Tests

Keep filesystem operations and complex business logic out of route functions.

Use dependency injection for database sessions and application services where appropriate.

Return safe API errors without:

* Absolute filesystem paths
* Stack traces
* Database connection strings
* Secret values
* Internal credentials

Use appropriate HTTP status codes.

Keep response models explicit.

Do not return database objects or fields that are not intended for the client.

## Frontend conventions

Use:

* Next.js App Router
* TypeScript
* Tailwind CSS
* Existing project aliases and import conventions

Do not introduce a `src` directory unless explicitly requested.

Keep:

* API request functions in `frontend/lib`
* Shared TypeScript types in `frontend/types`
* Reusable UI components in `frontend/components`
* Route-level files in `frontend/app`

Avoid placing large business-logic implementations directly inside route pages.

Do not duplicate API functions across components.

Maintain strict TypeScript compatibility.

Preserve existing frontend routes and profile functionality.

## Dependency rules

Before adding a dependency:

1. Check whether the project already has an appropriate dependency.
2. Explain why a new dependency is needed.
3. Prefer maintained and narrowly scoped packages.
4. Avoid adding multiple libraries for the same purpose.
5. Update the correct dependency file.
6. Run installation and validation.
7. Report the dependency and its purpose.

Do not add a paid service or external API requirement without explicit approval.

## Backend commands

Start from the repository root unless the task requires otherwise.

Activate the backend environment:

```bash
cd backend
source .venv/bin/activate
```

Run the backend development server:

```bash
fastapi dev app/main.py
```

Run tests when configured:

```bash
pytest
```

Run Python compilation validation:

```bash
python -m compileall app
```

Before using additional formatting, linting, migration, or test commands, inspect the repository configuration and use the commands already defined by the project.

## Frontend commands

From the frontend directory:

```bash
cd frontend
npm run dev
```

Run linting:

```bash
npm run lint
```

Run the TypeScript compiler check:

```bash
npx tsc --noEmit
```

Run a production build:

```bash
npm run build
```

Use the package manager already established by the repository.

Do not replace npm with another package manager without explicit approval.

## Testing expectations

For new behaviour:

* Add focused tests.
* Test successful behaviour.
* Test validation failures.
* Test missing-record behaviour.
* Test security boundaries.
* Test relevant data-preservation behaviour.
* Test API response shape where important.

Do not write tests that merely repeat implementation details without validating behaviour.

Do not weaken or delete existing tests to make a change pass.

When a test fails:

1. Investigate the cause.
2. Fix the implementation when appropriate.
3. Do not simply disable the test.
4. Report unresolved failures.

## Verification before declaring completion

A backend change is not complete until relevant checks have been run, including where available:

```bash
pytest
python -m compileall app
```

A frontend change is not complete until relevant checks have been run, including:

```bash
npm run lint
npx tsc --noEmit
npm run build
```

A database change is not complete until:

* The migration has been reviewed.
* Upgrade behaviour has been tested safely.
* Existing data preservation has been considered.
* Downgrade or rollback behaviour has been considered.

A full-stack change is not complete until:

* API routes register successfully.
* Frontend API types match backend responses.
* Error states are handled.
* Existing features remain intact.
* The final diff has been reviewed.

If a command cannot be run, report exactly why.

## Code-review guidelines

Review changes for:

* Fabricated candidate claims
* Candidate data loss
* Broken existing routes
* Database migration risks
* Missing authentication or authorisation boundaries
* Unsafe file handling
* Directory traversal
* Unbounded file uploads
* Secret leakage
* Personally identifiable information in logs
* Incorrect API response exposure
* Weak validation
* Type mismatches
* Unhandled frontend errors
* Duplicate code
* Missing tests
* Tests that do not validate real behaviour
* Accidental generated files
* Uploaded documents added to Git
* Build or cache files added to Git

Treat candidate-data loss, secret exposure, unsafe file upload, and false CV claims as critical issues.

## Definition of done

A task is complete only when:

* The requested scope is implemented.
* Existing functionality is preserved.
* Relevant tests pass.
* Relevant lint and type checks pass.
* Relevant builds succeed.
* Database safety has been checked.
* No secrets were exposed.
* No uploaded candidate documents were committed.
* The final diff was reviewed.
* Changed files were reported.
* Remaining limitations were clearly reported.

Do not claim success when validation has not been completed.

## Communication style

Be direct and precise.

When beginning a substantial task:

* Give a concise plan.
* Mention important risks.
* Avoid repeating the complete prompt.

When finishing:

* Summarise what changed.
* List changed files.
* List validation commands and outcomes.
* Clearly identify unresolved issues.
* Do not automatically begin the next phase.
