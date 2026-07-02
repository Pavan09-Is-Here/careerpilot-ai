"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  getJobSources,
  getJobs,
  isAbortError,
  saveJob,
} from "@/lib/api";

import type {
  JobEmploymentType,
  JobLifecycleStatus,
  JobRemoteMode,
  JobSource,
  NormalizedJobPage,
} from "@/types/job";

import {
  EmptyState,
  ErrorBanner,
  LifecycleBadge,
  formatDateTime,
  humanizeToken,
} from "@/components/jobs/JobPrimitives";

const LIFECYCLE_OPTIONS: JobLifecycleStatus[] = [
  "discovered",
  "active",
  "possibly_stale",
  "expired",
  "removed",
  "unavailable",
];

const EMPLOYMENT_OPTIONS: JobEmploymentType[] = [
  "full_time",
  "part_time",
  "contract",
  "temporary",
  "internship",
  "other",
];

const REMOTE_OPTIONS: JobRemoteMode[] = [
  "onsite",
  "hybrid",
  "remote",
  "flexible",
];

export default function JobDiscoveryPage() {
  const [jobPage, setJobPage] =
    useState<NormalizedJobPage | null>(null);
  const [sources, setSources] = useState<JobSource[]>(
    [],
  );
  const [page, setPage] = useState(1);
  const [sourceId, setSourceId] = useState<
    number | undefined
  >(undefined);
  const [lifecycleStatus, setLifecycleStatus] =
    useState<JobLifecycleStatus | undefined>(
      undefined,
    );
  const [employmentType, setEmploymentType] =
    useState<JobEmploymentType | undefined>(
      undefined,
    );
  const [remoteMode, setRemoteMode] = useState<
    JobRemoteMode | undefined
  >(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(
    null,
  );
  const [savingJobId, setSavingJobId] = useState<
    number | null
  >(null);
  const [savedJobIds, setSavedJobIds] = useState<
    Set<number>
  >(new Set());
  const [notice, setNotice] = useState<string | null>(
    null,
  );

  useEffect(() => {
    const controller = new AbortController();

    getJobSources(1, 100, controller.signal)
      .then((result) => setSources(result.items))
      .catch((requestError: unknown) => {
        if (!isAbortError(requestError)) {
          setSources([]);
        }
      });

    return () => controller.abort();
  }, []);

  const loadJobs = useCallback(
    (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);

      getJobs(
        {
          page,
          sourceId,
          lifecycleStatus,
          employmentType,
          remoteMode,
        },
        signal,
      )
        .then((result) => {
          setJobPage(result);
          setLoading(false);
        })
        .catch((requestError: unknown) => {
          if (isAbortError(requestError)) {
            return;
          }
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Failed to load jobs.",
          );
          setLoading(false);
        });
    },
    [
      page,
      sourceId,
      lifecycleStatus,
      employmentType,
      remoteMode,
    ],
  );

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      loadJobs(controller.signal);
    });
    return () => controller.abort();
  }, [loadJobs]);

  const handleSave = (jobId: number) => {
    setSavingJobId(jobId);
    setNotice(null);

    saveJob(jobId)
      .then(() => {
        setSavedJobIds((previous) => {
          const next = new Set(previous);
          next.add(jobId);
          return next;
        });
        setNotice("Job saved for review.");
      })
      .catch((requestError: unknown) => {
        setNotice(
          requestError instanceof Error
            ? requestError.message
            : "Failed to save job.",
        );
      })
      .finally(() => setSavingJobId(null));
  };

  const totalPages = jobPage
    ? Math.max(
        1,
        Math.ceil(jobPage.total / jobPage.page_size),
      )
    : 1;

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Job Discovery
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Browse jobs ingested from approved,
            compliance-reviewed sources.
          </p>
        </div>
        <Link
          href="/saved-jobs"
          className="rounded-md border border-slate-700 px-4 py-2 text-sm text-slate-200 transition hover:border-blue-400 hover:text-blue-300"
        >
          Saved jobs
        </Link>
      </header>

      <section
        aria-label="Job filters"
        className="mt-6 grid gap-3 rounded-lg border border-slate-800 bg-slate-900 p-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          Source
          <select
            className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-200"
            value={sourceId ?? ""}
            onChange={(event) => {
              setPage(1);
              setSourceId(
                event.target.value
                  ? Number(event.target.value)
                  : undefined,
              );
            }}
          >
            <option value="">All sources</option>
            {sources.map((source) => (
              <option
                key={source.id}
                value={source.id}
              >
                {source.display_name}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs text-slate-400">
          Lifecycle
          <select
            className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-200"
            value={lifecycleStatus ?? ""}
            onChange={(event) => {
              setPage(1);
              setLifecycleStatus(
                (event.target.value ||
                  undefined) as
                  | JobLifecycleStatus
                  | undefined,
              );
            }}
          >
            <option value="">All statuses</option>
            {LIFECYCLE_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {humanizeToken(status)}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs text-slate-400">
          Employment type
          <select
            className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-200"
            value={employmentType ?? ""}
            onChange={(event) => {
              setPage(1);
              setEmploymentType(
                (event.target.value ||
                  undefined) as
                  | JobEmploymentType
                  | undefined,
              );
            }}
          >
            <option value="">All types</option>
            {EMPLOYMENT_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {humanizeToken(option)}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs text-slate-400">
          Remote mode
          <select
            className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-200"
            value={remoteMode ?? ""}
            onChange={(event) => {
              setPage(1);
              setRemoteMode(
                (event.target.value ||
                  undefined) as
                  | JobRemoteMode
                  | undefined,
              );
            }}
          >
            <option value="">All modes</option>
            {REMOTE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {humanizeToken(option)}
              </option>
            ))}
          </select>
        </label>
      </section>

      {notice ? (
        <p
          role="status"
          className="mt-4 text-sm text-blue-300"
        >
          {notice}
        </p>
      ) : null}

      <section className="mt-6" aria-label="Job list">
        {error ? (
          <ErrorBanner message={error} />
        ) : loading ? (
          <p className="text-sm text-slate-400">
            Loading jobs…
          </p>
        ) : !jobPage || jobPage.items.length === 0 ? (
          <EmptyState title="No jobs found">
            Ingest an approved job source or adjust
            the filters.
          </EmptyState>
        ) : (
          <ul className="grid gap-4">
            {jobPage.items.map((job) => (
              <li
                key={job.id}
                className="rounded-lg border border-slate-800 bg-slate-900 p-5"
              >
                <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                  <div className="min-w-0">
                    <h2 className="break-words text-lg font-semibold text-white">
                      <Link
                        href={`/jobs/${job.id}`}
                        className="transition hover:text-blue-300"
                      >
                        {job.title}
                      </Link>
                    </h2>
                    <p className="mt-1 text-sm text-slate-400">
                      {job.employer_name} · Last seen{" "}
                      {formatDateTime(
                        job.last_seen_at,
                      )}
                    </p>
                    {job.description_excerpt ? (
                      <p className="mt-2 break-words text-sm text-slate-300">
                        {job.description_excerpt}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 flex-col items-start gap-2 sm:items-end">
                    <LifecycleBadge
                      status={job.lifecycle_status}
                    />
                    <button
                      type="button"
                      disabled={
                        savingJobId === job.id ||
                        savedJobIds.has(job.id)
                      }
                      onClick={() =>
                        handleSave(job.id)
                      }
                      className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700"
                    >
                      {savedJobIds.has(job.id)
                        ? "Saved"
                        : savingJobId === job.id
                          ? "Saving…"
                          : "Save"}
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {jobPage && jobPage.total > jobPage.page_size ? (
        <nav
          aria-label="Pagination"
          className="mt-6 flex items-center justify-between text-sm text-slate-300"
        >
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
            className="rounded-md border border-slate-700 px-3 py-1.5 transition hover:border-blue-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Previous
          </button>
          <span>
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
            className="rounded-md border border-slate-700 px-3 py-1.5 transition hover:border-blue-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Next
          </button>
        </nav>
      ) : null}
    </main>
  );
}
