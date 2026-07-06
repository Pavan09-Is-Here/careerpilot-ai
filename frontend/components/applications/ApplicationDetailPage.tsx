"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  addApplicationFollowUp,
  addApplicationNote,
  getApplication,
  isAbortError,
  updateApplication,
} from "@/lib/api";

import type {
  ApplicationDetail,
  ApplicationStatus,
} from "@/types/application";

import {
  APPLICATION_STATUSES,
  formatDateTime,
  humanizeStatus,
  statusClasses,
} from "@/components/applications/applicationHelpers";

import { safeExternalHref } from "@/lib/url";

const SUBMIT_READY_STATUSES: ApplicationStatus[] = [
  "ready_to_apply",
  "applying",
  "blocked",
  "needs_review",
];

export default function ApplicationDetailPage({
  applicationId,
}: {
  applicationId: number;
}) {
  const [application, setApplication] =
    useState<ApplicationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [statusChoice, setStatusChoice] =
    useState<ApplicationStatus | "">("");
  const [confirmation, setConfirmation] = useState("");
  const [noteText, setNoteText] = useState("");
  const [followUpText, setFollowUpText] = useState("");
  const [followUpDue, setFollowUpDue] = useState("");

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);

      try {
        setApplication(await getApplication(applicationId, signal));
      } catch (loadError) {
        if (isAbortError(loadError)) {
          return;
        }

        setError(
          loadError instanceof Error
            ? loadError.message
            : "Could not load this application.",
        );
      } finally {
        setLoading(false);
      }
    },
    [applicationId],
  );

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      void load(controller.signal);
    });
    return () => controller.abort();
  }, [load]);

  const runAction = useCallback(
    async (action: () => Promise<unknown>) => {
      setBusy(true);
      setError(null);

      try {
        await action();
        await load();
      } catch (actionError) {
        setError(
          actionError instanceof Error
            ? actionError.message
            : "Action failed.",
        );
      } finally {
        setBusy(false);
      }
    },
    [load],
  );

  if (loading) {
    return (
      <main className="cp-page">
        <div className="mx-auto max-w-4xl">
          <p className="text-sm text-slate-500">Loading…</p>
        </div>
      </main>
    );
  }

  if (!application) {
    return (
      <main className="cp-page">
        <div className="mx-auto max-w-4xl space-y-4">
          <Link
            href="/applications"
            className="text-sm text-violet-700 hover:text-violet-800"
          >
            ← Applications
          </Link>
          <p className="text-sm text-red-700">
            {error ?? "Application not found."}
          </p>
        </div>
      </main>
    );
  }

  const canSubmit = SUBMIT_READY_STATUSES.includes(application.status);
  const jobPostingHref = safeExternalHref(
    application.job.source_url,
  );

  return (
    <main className="cp-page">
      <div className="mx-auto max-w-4xl space-y-6">
        <div>
          <Link
            href="/applications"
            className="text-sm text-violet-700 hover:text-violet-800"
          >
            ← Applications
          </Link>

          <div className="mt-3 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">
              {application.job.title}
            </h1>
            <span
              className={`rounded-full border px-3 py-1 text-xs font-medium ${statusClasses(
                application.status,
              )}`}
            >
              {humanizeStatus(application.status)}
            </span>
          </div>

          <p className="mt-1 text-sm text-slate-500">
            {application.job.employer_name}
            {jobPostingHref ? (
              <>
                {" "}
                ·{" "}
                <a
                  href={jobPostingHref}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="text-violet-700 hover:text-violet-800"
                >
                  Job posting
                </a>
              </>
            ) : null}
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {canSubmit && (
          <Panel title="Record submission">
            <p className="text-sm text-slate-500">
              After you submit the application on the employer&rsquo;s
              site, record it here with the confirmation number. The
              tool never submits on your behalf.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <input
                type="text"
                value={confirmation}
                onChange={(event) =>
                  setConfirmation(event.target.value)
                }
                placeholder="Confirmation number (optional)"
                className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
              />
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  runAction(() =>
                    updateApplication(application.id, {
                      status: "submitted",
                      confirmation_number:
                        confirmation.trim() || null,
                    }),
                  )
                }
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50"
              >
                Mark submitted
              </button>
            </div>
          </Panel>
        )}

        <Panel title="Update status">
          <div className="flex flex-wrap gap-2">
            <select
              value={statusChoice}
              onChange={(event) =>
                setStatusChoice(
                  event.target.value as ApplicationStatus | "",
                )
              }
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
            >
              <option value="">Choose a status…</option>
              {APPLICATION_STATUSES.map((value) => (
                <option key={value} value={value}>
                  {humanizeStatus(value)}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={busy || statusChoice === ""}
              onClick={() =>
                runAction(() =>
                  updateApplication(application.id, {
                    status: statusChoice as ApplicationStatus,
                  }),
                )
              }
              className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
            >
              Update
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Only valid transitions are accepted; invalid ones are
            rejected.
          </p>
        </Panel>

        <Panel title="Timeline">
          {application.timeline.length === 0 ? (
            <p className="text-sm text-slate-500">No events yet.</p>
          ) : (
            <ul className="space-y-2">
              {application.timeline.map((entry, index) => (
                <li
                  key={`${entry.at}-${index}`}
                  className="flex gap-3 text-sm"
                >
                  <span className="w-44 shrink-0 text-slate-500">
                    {formatDateTime(entry.at)}
                  </span>
                  <span className="text-slate-700">
                    {entry.label}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Notes">
          <div className="flex flex-wrap gap-2">
            <input
              type="text"
              value={noteText}
              onChange={(event) => setNoteText(event.target.value)}
              placeholder="Add a note…"
              className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
            />
            <button
              type="button"
              disabled={busy || noteText.trim() === ""}
              onClick={() =>
                runAction(async () => {
                  await addApplicationNote(application.id, {
                    text: noteText.trim(),
                  });
                  setNoteText("");
                })
              }
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-violet-700 transition hover:border-violet-400 hover:bg-violet-50 disabled:opacity-50"
            >
              Add note
            </button>
          </div>
          {application.notes.length > 0 && (
            <ul className="mt-3 space-y-2">
              {application.notes.map((note, index) => (
                <li
                  key={`${note.created_at}-${index}`}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600"
                >
                  <span className="text-slate-700">{note.text}</span>
                  <span className="ml-2 text-xs text-slate-500">
                    {formatDateTime(note.created_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Follow-ups">
          <div className="flex flex-wrap gap-2">
            <input
              type="text"
              value={followUpText}
              onChange={(event) =>
                setFollowUpText(event.target.value)
              }
              placeholder="Follow-up (e.g. Send thank-you)…"
              className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
            />
            <input
              type="date"
              value={followUpDue}
              onChange={(event) =>
                setFollowUpDue(event.target.value)
              }
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
            />
            <button
              type="button"
              disabled={busy || followUpText.trim() === ""}
              onClick={() =>
                runAction(async () => {
                  await addApplicationFollowUp(application.id, {
                    description: followUpText.trim(),
                    due_date: followUpDue || null,
                  });
                  setFollowUpText("");
                  setFollowUpDue("");
                })
              }
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-violet-700 transition hover:border-violet-400 hover:bg-violet-50 disabled:opacity-50"
            >
              Schedule
            </button>
          </div>
          {application.follow_ups.length > 0 && (
            <ul className="mt-3 space-y-2">
              {application.follow_ups.map((followUp, index) => (
                <li
                  key={`${followUp.created_at}-${index}`}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600"
                >
                  {followUp.description}
                  {followUp.due_date && (
                    <span className="ml-2 text-xs text-amber-700">
                      due {followUp.due_date}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </main>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h2>
      {children}
    </section>
  );
}
