# Deploy CareerPilot AI — Supabase + Render + Vercel

Exact steps to put the backend on Render, the database on Supabase, and
the frontend on Vercel. Do them in order. Anything marked **secret**
goes only in the platform's dashboard, never in the repo.

Prerequisite: push this repository to GitHub (Render and Vercel deploy
from a Git repo).

---

## 1. Supabase — database

1. Create a Supabase project. Choose a strong database password.
2. In **Project Settings → Database → Connection string**, copy the
   URI (use the **Session pooler** or direct connection). It looks like:
   `postgresql://postgres:PASSWORD@db.<ref>.supabase.co:5432/postgres`
3. Turn it into the value CareerPilot expects by changing the scheme
   and (usually) requiring SSL:
   `postgresql+psycopg://postgres:PASSWORD@db.<ref>.supabase.co:5432/postgres?sslmode=require`
   Keep this as **`CAREERPILOT_DATABASE_URL`** (secret) for step 2.

(Optional, for file storage) In **Storage**, create a bucket named
`careerpilot` and keep it **private**. In **Project Settings → Storage
→ S3 connection**, note the endpoint, region, and generate S3 access
keys — used in step 2's storage vars.

---

## 2. Render — backend

1. In Render: **New + → Blueprint**, connect this GitHub repo. Render
   reads `render.yaml` and proposes the `careerpilot-api` web service.
2. Set the environment variables (dashboard → the service → Environment):
   - **`CAREERPILOT_DATABASE_URL`** = the URL from step 1 (secret).
   - **`CAREERPILOT_CORS_ORIGINS`** = your Vercel URL (fill in after
     step 3, e.g. `https://careerpilot.vercel.app`). You can set it now
     to your expected URL and adjust later.
   - `CAREERPILOT_ENVIRONMENT` = `production` (already in the blueprint).
   - (Optional storage) set `CAREERPILOT_STORAGE_BACKEND=s3`,
     `CAREERPILOT_S3_BUCKET=careerpilot`, `CAREERPILOT_S3_REGION`,
     `CAREERPILOT_S3_ENDPOINT_URL` (Supabase S3 endpoint), and
     `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (the Supabase S3
     keys). If you skip this, leave `local` — but note Render's disk is
     ephemeral, so uploaded files are lost on redeploy.
   - (Optional email) `CAREERPILOT_SMTP_HOST`, `_SMTP_USERNAME`,
     `_SMTP_PASSWORD`, `_NOTIFICATION_FROM_ADDRESS`.
3. Deploy. The start command runs `alembic upgrade head` (creating all
   tables in Supabase) and then starts the API. Render's health check
   hits `GET /api/health`.
4. When live, open `https://<your-render-service>.onrender.com/api/health`
   — it should return `{"status":"healthy","environment":"production",
   "database":"postgresql", ...}`. Note this backend base URL.

---

## 3. Vercel — frontend

1. In Vercel: **Add New → Project**, import the same repo.
2. Set **Root Directory = `frontend`** (Vercel auto-detects Next.js).
3. Add an environment variable:
   - **`NEXT_PUBLIC_API_URL`** = your Render backend base URL from
     step 2 (e.g. `https://careerpilot-api.onrender.com`).
4. Deploy. Note the Vercel URL (e.g. `https://careerpilot.vercel.app`).
5. Go back to Render and make sure **`CAREERPILOT_CORS_ORIGINS`**
   equals that Vercel URL, then redeploy the backend so CORS allows it.

---

## 4. First run

1. Open the Vercel app. Go to **Account** and set a password.
2. Fill in your **profile**, or upload a CV on **Documents** and use
   **Fill profile from this CV**, then review/verify the details.
3. Add **Application answers** (work authorization, availability, etc.)
   and mark the verified ones (sensitive ones need manual confirmation).
4. Generate a **verified master CV** (CV versions) so tailoring works.

At this point matching, tailoring, package preparation, tracking, and
notifications all work over data in your database.

---

## 5. Keep it running (scheduler)

The background workers are on-demand, not daemons. Use a scheduler to
call the backend on a cadence. Options:

- **Render Cron Job** (New + → Cron Job) or any external cron, running
  e.g. hourly:
  ```
  curl -X POST "$API/api/workers/start" \
       -H 'Content-Type: application/json' -d '{"worker":"all"}'
  curl -X POST "$API/api/notifications/deliver"
  ```
  where `$API` is your Render backend base URL.

No scheduled action ever submits an application — the pipeline prepares
and notifies; you perform and record the final submission.

---

## 6. Fresh jobs (optional, to make "latest jobs" real)

The pipeline only sees jobs already in the database. To ingest genuinely
fresh postings, connect an approved, compliance-reviewed job source and
run ingestion (the Greenhouse adapter is a keyless example). Only
enable/allowlist sources whose terms and robots policies you have
reviewed.

---

## Notes & safety

- Secrets live only in Render/Vercel/Supabase dashboards — never commit
  them. `.env.example` holds placeholder names only.
- Applications are never auto-submitted. This is intentional and must
  not be changed.
- See `docs/deployment.md` for the platform-agnostic reference and the
  full post-deploy checklist.
