"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  getJob,
  getJobDuplicates,
  isAbortError,
  saveJob,
  trackJobApplication,
} from "@/lib/api";

import type {
  JobDuplicate,
  NormalizedJobDetail,
} from "@/types/job";

import {
  EmptyState,
  ErrorBanner,
  LifecycleBadge,
  formatDateTime,
  humanizeToken,
} from "@/components/jobs/JobPrimitives";

type JobDetailPageProps = {
  jobId: number;
};

function TextSection({
  title,
  value,
}: {
  title: string;
  value: string | null;
}) {
  if (!value) {
    return null;
  }

  return (
    <section className="mt-6">
      <h2 className="text-base font-semibold text-white">
        {title}
      </h2>
      <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-300">
        {value}
      </p>
    </section>
  );
}

export default function JobDetailPage({
  jobId,
}: JobDetailPageProps) {
  const [job, setJob] =
    useState<NormalizedJobDetail | null>(null);
  const [duplicates, setDuplicates] = useState<
    JobDuplicate[]
  >([]);
  const [error, setError] = useState<string | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(
    null,
  );

  useEffect(() => {
    const controller = new AbortController();

    Promise.all([
      getJob(jobId, controller.signal),
      getJobDuplicates(jobId, controller.signal),
    ])
      .then(([jobDetail, duplicateList]) => {
        setJob(jobDetail);
        setDuplicates(duplicateList.items);
        setLoading(false);
      })
      .catch((requestError: unknown) => {
        if (isAbortError(requestError)) {
          return;
        }
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Failed to load the job.",
        );
        setLoading(false);
      });

    return () => controller.abort();
  }, [jobId]);

  const router = useRouter();
  const [tracking, setTracking] = useState(false);

  const handleSave = () => {
    setSaving(true);
    setNotice(null);

    saveJob(jobId)
      .then(() =>
        setNotice("Job saved for review."),
      )
      .catch((requestError: unknown) => {
        setNotice(
          requestError instanceof Error
            ? requestError.message
            : "Failed to save job.",
        );
      })
      .finally(() => setSaving(false));
  };

  const handleTrack = () => {
    setTracking(true);
    setNotice(null);

    trackJobApplication(jobId)
      .then((application) => {
        router.push(`/applications/${application.id}`);
      })
      .catch((requestError: unknown) => {
        setNotice(
          requestError instanceof Error
            ? requestError.message
            : "Failed to track application.",
        );
        setTracking(false);
      });
  };

  if (loading) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-10">
        <p className="text-sm text-slate-400">
          Loading job…
        </p>
      </main>
    );
  }

  if (error || !job) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-10">
        <ErrorBanner
          message={error ?? "Job was not found."}
        />
        <Link
          href="/jobs"
          className="mt-4 inline-block text-sm text-blue-300 hover:underline"
        >
          Back to job discovery
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <Link
        href="/jobs"
        className="text-sm text-blue-300 hover:underline"
      >
        ← Back to job discovery
      </Link>

      <header className="mt-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div className="min-w-0">
          <h1 className="break-words text-2xl font-bold text-white">
            {job.title}
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            {job.employer_name}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <LifecycleBadge
              status={job.lifecycle_status}
            />
            <span>
              {humanizeToken(job.employment_type)}
            </span>
            <span>
              {humanizeToken(job.remote_mode)}
            </span>
            <span>
              Last seen{" "}
              {formatDateTime(job.last_seen_at)}
            </span>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <button
            type="button"
            disabled={saving}
            onClick={handleSave}
            className="rounded-md border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-blue-400 hover:text-blue-300 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save for review"}
          </button>
          <button
            type="button"
            disabled={tracking}
            onClick={handleTrack}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700"
          >
            {tracking ? "Tracking…" : "Track application"}
          </button>
        </div>
      </header>

      {notice ? (
        <p
          role="status"
          className="mt-3 text-sm text-blue-300"
        >
          {notice}
        </p>
      ) : null}

      <section className="mt-6 rounded-lg border border-slate-800 bg-slate-900 p-4 text-sm text-slate-300">
        <p>
          Original posting:{" "}
          <a
            href={job.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="break-all text-blue-300 hover:underline"
          >
            {job.source_url}
          </a>
        </p>
        {job.source_attribution_text ? (
          <p className="mt-2 text-xs text-slate-400">
            {job.source_attribution_text}
          </p>
        ) : null}
      </section>

      {job.locations.length > 0 ? (
        <section className="mt-6">
          <h2 className="text-base font-semibold text-white">
            Locations
          </h2>
          <ul className="mt-2 flex flex-wrap gap-2 text-sm text-slate-300">
            {job.locations.map((location) => (
              <li
                key={location.id}
                className="rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5"
              >
                {location.raw_location_text ??
                  [
                    location.city,
                    location.region,
                    location.country,
                  ]
                    .filter(Boolean)
                    .join(", ") ??
                  "—"}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {job.compensations.length > 0 ? (
        <section className="mt-6">
          <h2 className="text-base font-semibold text-white">
            Compensation (as stated by the source)
          </h2>
          <ul className="mt-2 grid gap-2 text-sm text-slate-300">
            {job.compensations.map((compensation) => (
              <li
                key={compensation.id}
                className="rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5"
              >
                {compensation.source_text ??
                  `${compensation.min_amount ?? "?"} – ${compensation.max_amount ?? "?"} ${compensation.currency ?? ""} (${humanizeToken(compensation.compensation_period)})`}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {job.skill_requirements.length > 0 ? (
        <section className="mt-6">
          <h2 className="text-base font-semibold text-white">
            Skills (as stated by the source)
          </h2>
          <ul className="mt-2 flex flex-wrap gap-2 text-sm text-slate-300">
            {job.skill_requirements.map((skill) => (
              <li
                key={skill.id}
                className="rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5"
              >
                {skill.skill_text} ·{" "}
                {humanizeToken(skill.requirement_type)}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <TextSection
        title="Description"
        value={job.description_text}
      />
      <TextSection
        title="Responsibilities"
        value={job.responsibilities_text}
      />
      <TextSection
        title="Required qualifications"
        value={job.required_qualifications_text}
      />
      <TextSection
        title="Preferred qualifications"
        value={job.preferred_qualifications_text}
      />
      <TextSection
        title="Sponsorship / visa (source wording)"
        value={job.source_sponsorship_visa_text}
      />

      <section className="mt-8">
        <h2 className="text-base font-semibold text-white">
          Possible duplicates
        </h2>
        {duplicates.length === 0 ? (
          <p className="mt-2 text-sm text-slate-400">
            No duplicate links detected for this job.
          </p>
        ) : (
          <ul className="mt-2 grid gap-2 text-sm text-slate-300">
            {duplicates.map((duplicate) => {
              const otherJobId =
                duplicate.job_id === job.id
                  ? duplicate.duplicate_of_job_id
                  : duplicate.job_id;

              return (
                <li
                  key={duplicate.id}
                  className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2"
                >
                  <Link
                    href={`/jobs/${otherJobId}`}
                    className="text-blue-300 hover:underline"
                  >
                    Job #{otherJobId}
                  </Link>{" "}
                  · matched by{" "}
                  {humanizeToken(
                    duplicate.detection_method,
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {duplicates.length === 0 && !job ? (
        <EmptyState title="No data">
          Nothing to display.
        </EmptyState>
      ) : null}
    </main>
  );
}
