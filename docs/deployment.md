# CareerPilot AI — Deployment Runbook (Phase 14)

This is the operator checklist for taking CareerPilot AI from the local
SQLite development setup to a running deployment. The application code
is environment-agnostic; the steps below are the infrastructure work
that must happen in a real target environment.

> **Safety invariants that must survive deployment**
> - The system never fabricates candidate facts.
> - Applications are **never** auto-submitted. The pipeline prepares
>   and notifies; a human performs and records every submission.
> - Live browser automation, if ever added, must route through the
>   existing safety gates and must not bypass CAPTCHA/MFA/bot detection
>   or a site's terms of service.

---

## 1. Configuration

All backend settings use the `CAREERPILOT_` env prefix. See
`backend/.env.example`. Never commit real secrets; provide them through
your platform's secret manager or environment.

Key variables:

| Variable | Purpose |
|----------|---------|
| `CAREERPILOT_ENVIRONMENT` | `development` / `staging` / `production` |
| `CAREERPILOT_DATABASE_URL` | PostgreSQL URL in production |
| `CAREERPILOT_STORAGE_BACKEND` | `local` or `s3` |
| `CAREERPILOT_S3_*` | S3 bucket/region/prefix/endpoint |
| `CAREERPILOT_SMTP_*` | Email delivery for notifications |
| `CAREERPILOT_SENTRY_DSN` | Error reporting (inert if unset) |

`GET /api/health` reports `environment` and `database` so you can
confirm a deployment is wired to the right tier and backend.

---

## 2. PostgreSQL database

1. Provision a PostgreSQL instance (managed Postgres or Supabase).
2. Install the driver in the backend image, e.g. `psycopg[binary]`.
3. Set `CAREERPILOT_DATABASE_URL`, e.g.
   `postgresql+psycopg://USER:PASSWORD@HOST:5432/careerpilot`.
4. Run migrations against it (Alembic honours the env URL):
   ```bash
   cd backend
   alembic upgrade head
   ```
5. Validate against a throwaway database first (upgrade → downgrade →
   re-upgrade) before pointing at production.

The current single committed head is the latest Alembic revision; the
migration chain is linear and reversible.

---

## 3. Object storage for documents

Uploaded CVs and generated artifacts must not be web-accessible and
must keep their path-safety controls.

- `CAREERPILOT_STORAGE_BACKEND=s3` with `CAREERPILOT_S3_BUCKET` (and
  region/prefix/endpoint as needed). Requires `boto3` in the image.
- The `app/services/storage_backend.py` abstraction provides local and
  S3 backends with shared key validation; migrate the existing
  document/generated-CV storage services onto it as part of the S3
  cutover, and back-fill existing files into the bucket.
- Credentials come from an instance role or the environment, never
  source.

---

## 4. Backend deployment

1. Build the FastAPI app (`app.main:app`) into a container or platform
   service (Railway, Fly, Render, ECS, etc.).
2. Set all `CAREERPILOT_` env vars and secrets.
3. Run `alembic upgrade head` on release (migration step).
4. Serve behind HTTPS/TLS (terminate at the platform or a reverse
   proxy). The security-headers middleware already sets HSTS/CSP/etc.
5. Restrict CORS to your production frontend origin (currently the app
   allows localhost dev origins — tighten this for production).

---

## 5. Frontend deployment

1. Deploy the Next.js app (`frontend/`) to Vercel or equivalent.
2. Set `NEXT_PUBLIC_API_URL` to the deployed backend base URL.
3. `npm run build` (note: the build fetches Google Fonts via
   `next/font/google`; ensure network access at build time or vendor
   the fonts).

---

## 6. Email notifications (SMTP)

Set `CAREERPILOT_SMTP_HOST` and related vars. Until configured,
notifications are recorded (status `pending`) but not sent —
`POST /api/notifications/deliver` reports them as skipped. Once SMTP is
set, that endpoint (or a scheduled call to it) delivers pending mail.

---

## 7. Scheduling the automation

The background workers run as bounded, on-demand cycles — they are not
daemons. Drive them with an external scheduler (cron, platform
scheduler) that calls, on your cadence:

- `POST /api/workers/start` with `{"worker":"all"}` (or a named worker)
  — discovery, analysis, application preparation, expiry, and the
  auto-apply pipeline. Daily limits are enforced server-side.
- `POST /api/notifications/deliver` — flush pending email.

Example (hourly): `0 * * * * curl -XPOST https://api.example.com/api/workers/start -d '{"worker":"all"}' -H 'Content-Type: application/json'`

No scheduled action ever submits an application.

---

## 8. Live job ingestion

The pipeline only operates over jobs already in the database. To get
genuinely fresh "latest" jobs you must connect an approved, compliant
job source and run ingestion (the Greenhouse provider adapter exists as
a keyless, compliance-gated example). Only enable, allowlist, and
mark `server_fetch_allowed` for sources you have reviewed for terms and
robots compliance.

---

## 9. Observability & backups

- Set `CAREERPILOT_SENTRY_DSN` for error reporting.
- Configure automated database backups and test a restore.
- Configure log aggregation; ensure no PII or secrets are logged.

---

## 10. Post-deploy checklist

- [ ] `GET /api/health` returns the expected `environment` and
      `database`.
- [ ] Migrations applied; `alembic current` at head.
- [ ] Documents stored in object storage, not web-accessible.
- [ ] TLS enforced; CORS restricted to the production frontend.
- [ ] SMTP verified with a test notification delivery.
- [ ] Scheduler calling `/api/workers/start` on the intended cadence.
- [ ] Backups automated and a restore tested.
- [ ] Confirmed: nothing auto-submits applications.
