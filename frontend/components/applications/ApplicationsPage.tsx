"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import { getApplications, isAbortError } from "@/lib/api";

import type {
  Application,
  ApplicationStatus,
} from "@/types/application";

import {
  APPLICATION_STATUSES,
  formatDateTime,
  humanizeStatus,
  statusClasses,
} from "@/components/applications/applicationHelpers";

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<
    Application[]
  >([]);
  const [status, setStatus] = useState<
    ApplicationStatus | undefined
  >(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);

      try {
        setApplications(await getApplications(status, signal));
      } catch (loadError) {
        if (isAbortError(loadError)) {
          return;
        }

        setError(
          loadError instanceof Error
            ? loadError.message
            : "Could not load applications.",
        );
      } finally {
        setLoading(false);
      }
    },
    [status],
  );

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      void load(controller.signal);
    });
    return () => controller.abort();
  }, [load]);

  return (
    <main className="cp-page">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8">
          <Link
            href="/"
            className="text-sm text-violet-700 hover:text-violet-800"
          >
            ← Dashboard
          </Link>

          <h1 className="mt-3 text-3xl font-bold text-slate-900">Applications</h1>

          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            Track every application through its lifecycle — from
            prepared and ready-to-submit through interview and
            outcome. Recording a submission is a deliberate action
            here and triggers a confirmation notification.
          </p>
        </header>

        <div className="mb-6 flex flex-wrap gap-2">
          <FilterChip
            label="All"
            active={status === undefined}
            onClick={() => setStatus(undefined)}
          />
          {APPLICATION_STATUSES.map((value) => (
            <FilterChip
              key={value}
              label={humanizeStatus(value)}
              active={status === value}
              onClick={() => setStatus(value)}
            />
          ))}
        </div>

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : applications.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500 shadow-sm">
            No tracked applications yet. Open a job and choose
            &ldquo;Track application&rdquo; to start.
          </div>
        ) : (
          <ul className="space-y-3">
            {applications.map((application) => (
              <li
                key={application.id}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div className="flex flex-wrap items-center gap-3">
                  <span
                    className={`rounded-full border px-3 py-1 text-xs font-medium ${statusClasses(
                      application.status,
                    )}`}
                  >
                    {humanizeStatus(application.status)}
                  </span>
                  <span className="ml-auto text-xs text-slate-500">
                    Updated {formatDateTime(application.updated_at)}
                  </span>
                </div>

                <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm text-slate-600">
                      Job #{application.job_id}
                      {application.confirmation_number
                        ? ` · Confirmation ${application.confirmation_number}`
                        : ""}
                    </p>
                    {application.applied_at && (
                      <p className="text-xs text-slate-500">
                        Applied{" "}
                        {formatDateTime(application.applied_at)}
                      </p>
                    )}
                  </div>

                  <Link
                    href={`/applications/${application.id}`}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-violet-700 transition hover:border-violet-400 hover:bg-violet-50"
                  >
                    Open
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
        active
          ? "border-violet-200 bg-violet-50 text-violet-700"
          : "border-slate-300 text-slate-500 hover:border-violet-400 hover:text-violet-700"
      }`}
    >
      {label}
    </button>
  );
}
