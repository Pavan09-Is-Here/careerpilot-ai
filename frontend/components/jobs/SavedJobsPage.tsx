"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  getSavedJobs,
  isAbortError,
  updateSavedJob,
} from "@/lib/api";

import type {
  SavedJob,
  SavedJobPage,
  SavedJobReviewStatus,
} from "@/types/savedJob";

import {
  LifecycleBadge,
  ReviewBadge,
  formatDateTime,
  humanizeToken,
} from "@/components/jobs/JobPrimitives";

import EmptyState from "@/components/ui/EmptyState";
import ErrorNotice from "@/components/ui/ErrorNotice";
import Spinner from "@/components/ui/Spinner";

const STATUS_FILTERS: SavedJobReviewStatus[] = [
  "saved",
  "shortlisted",
  "dismissed",
  "archived",
];

const NEXT_ACTIONS: Record<
  SavedJobReviewStatus,
  SavedJobReviewStatus[]
> = {
  saved: ["shortlisted", "dismissed", "archived"],
  shortlisted: ["saved", "dismissed", "archived"],
  dismissed: ["saved", "archived"],
  archived: [],
};

export default function SavedJobsPage() {
  const [savedPage, setSavedPage] =
    useState<SavedJobPage | null>(null);
  const [statusFilter, setStatusFilter] = useState<
    SavedJobReviewStatus | undefined
  >(undefined);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(
    null,
  );
  const [updatingId, setUpdatingId] = useState<
    number | null
  >(null);
  const [notice, setNotice] = useState<{
    tone: "success" | "error";
    message: string;
  } | null>(null);

  const loadSavedJobs = useCallback(
    (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);

      getSavedJobs(page, 50, statusFilter, signal)
        .then((result) => {
          setSavedPage(result);
          setLoading(false);
        })
        .catch((requestError: unknown) => {
          if (isAbortError(requestError)) {
            return;
          }
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Failed to load saved jobs.",
          );
          setLoading(false);
        });
    },
    [page, statusFilter],
  );

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      loadSavedJobs(controller.signal);
    });
    return () => controller.abort();
  }, [loadSavedJobs]);

  const handleTransition = (
    saved: SavedJob,
    nextStatus: SavedJobReviewStatus,
  ) => {
    setUpdatingId(saved.id);
    setNotice(null);

    updateSavedJob(saved.id, {
      review_status: nextStatus,
    })
      .then(() => {
        setNotice({
          tone: "success",
          message: `Moved to ${humanizeToken(nextStatus)}.`,
        });
        loadSavedJobs();
      })
      .catch((requestError: unknown) => {
        setNotice({
          tone: "error",
          message:
            requestError instanceof Error
              ? requestError.message
              : "Failed to update the saved job.",
        });
      })
      .finally(() => setUpdatingId(null));
  };

  const totalPages = savedPage
    ? Math.max(
        1,
        Math.ceil(
          savedPage.total / savedPage.page_size,
        ),
      )
    : 1;

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <Link
        href="/"
        className="text-sm font-medium text-violet-600 transition hover:text-violet-700"
      >
        ← Back to dashboard
      </Link>
      <header className="mt-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Saved Jobs
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Review saved jobs. Records are archived,
            never deleted, and remain inspectable in
            every lifecycle state.
          </p>
        </div>
        <Link
          href="/jobs"
          className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 transition hover:border-violet-400 hover:text-violet-700"
        >
          Discover jobs
        </Link>
      </header>

      <nav
        aria-label="Review status filter"
        className="mt-6 flex flex-wrap gap-2 text-sm"
      >
        <button
          type="button"
          onClick={() => {
            setPage(1);
            setStatusFilter(undefined);
          }}
          className={`rounded-md border px-3 py-1.5 transition ${
            statusFilter === undefined
              ? "border-violet-400 bg-violet-50 text-violet-700"
              : "border-slate-300 text-slate-600 hover:border-violet-400 hover:text-violet-700"
          }`}
        >
          All
        </button>
        {STATUS_FILTERS.map((status) => (
          <button
            key={status}
            type="button"
            onClick={() => {
              setPage(1);
              setStatusFilter(status);
            }}
            className={`rounded-md border px-3 py-1.5 transition ${
              statusFilter === status
                ? "border-violet-400 bg-violet-50 text-violet-700"
                : "border-slate-300 text-slate-600 hover:border-violet-400 hover:text-violet-700"
            }`}
          >
            {humanizeToken(status)}
          </button>
        ))}
      </nav>

      {notice ? (
        notice.tone === "error" ? (
          <ErrorNotice className="mt-4">
            {notice.message}
          </ErrorNotice>
        ) : (
          <p
            role="status"
            className="mt-4 text-sm text-violet-700"
          >
            {notice.message}
          </p>
        )
      ) : null}

      <section
        className="mt-6"
        aria-label="Saved job list"
      >
        {error ? (
          <ErrorNotice>{error}</ErrorNotice>
        ) : loading ? (
          <Spinner label="Loading saved jobs…" />
        ) : !savedPage ||
          savedPage.items.length === 0 ? (
          <EmptyState
            title="No saved jobs"
            description="Save jobs from the discovery page to review them here."
            actionLabel="Discover jobs"
            actionHref="/jobs"
          />
        ) : (
          <ul className="grid gap-4">
            {savedPage.items.map((saved) => (
              <li
                key={saved.id}
                className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                  <div className="min-w-0">
                    <h2 className="break-words text-lg font-semibold text-slate-900">
                      <Link
                        href={`/jobs/${saved.job_id}`}
                        className="transition hover:text-violet-700"
                      >
                        {saved.job.title}
                      </Link>
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                      {saved.job.employer_name} ·
                      Saved{" "}
                      {formatDateTime(
                        saved.created_at,
                      )}
                    </p>
                    {saved.notes ? (
                      <p className="mt-2 break-words text-sm text-slate-600">
                        {saved.notes}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 flex-col items-start gap-2 sm:items-end">
                    <div className="flex gap-2">
                      <ReviewBadge
                        status={saved.review_status}
                      />
                      <LifecycleBadge
                        status={
                          saved.job.lifecycle_status
                        }
                      />
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {NEXT_ACTIONS[
                        saved.review_status
                      ].map((nextStatus) => (
                        <button
                          key={nextStatus}
                          type="button"
                          disabled={
                            updatingId === saved.id
                          }
                          onClick={() =>
                            handleTransition(
                              saved,
                              nextStatus,
                            )
                          }
                          className="rounded-md border border-slate-300 px-2.5 py-1 text-xs text-slate-700 transition hover:border-violet-400 hover:text-violet-700 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {humanizeToken(nextStatus)}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {savedPage &&
      savedPage.total > savedPage.page_size ? (
        <nav
          aria-label="Pagination"
          className="mt-6 flex items-center justify-between text-sm text-slate-600"
        >
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
            className="rounded-md border border-slate-300 px-3 py-1.5 transition hover:border-violet-400 hover:text-violet-700 disabled:cursor-not-allowed disabled:opacity-40"
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
            className="rounded-md border border-slate-300 px-3 py-1.5 transition hover:border-violet-400 hover:text-violet-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Next
          </button>
        </nav>
      ) : null}
    </main>
  );
}
