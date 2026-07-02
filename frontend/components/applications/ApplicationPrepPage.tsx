"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  cancelApplicationRun,
  getApplicationPackage,
  prepareApplication,
  resumeApplicationRun,
  startApplicationRun,
  updateApplicationPackage,
} from "@/lib/api";

import type { ApplicationPackage } from "@/types/applicationPackage";
import type {
  ApplicationRun,
  ApplicationRunGate,
} from "@/types/applicationRun";

function humanize(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

const READY_STATUSES = new Set([
  "ready_for_automatic_application",
  "needs_user_review",
]);

function readinessClasses(status: string): string {
  if (status === "ready_for_automatic_application") {
    return "border-emerald-500/40 text-emerald-300";
  }
  if (status === "needs_user_review") {
    return "border-amber-500/40 text-amber-300";
  }
  return "border-rose-500/40 text-rose-300";
}

export default function ApplicationPrepPage({
  jobId,
}: {
  jobId: number;
}) {
  const [pkg, setPkg] = useState<ApplicationPackage | null>(null);
  const [run, setRun] = useState<ApplicationRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [confirmation, setConfirmation] = useState("");

  const loadPackage = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);

      try {
        const loaded = await getApplicationPackage(jobId, signal);
        setPkg(loaded);
        setNotes(loaded.user_notes ?? "");
      } catch {
        // No package prepared yet — that is expected.
        setPkg(null);
      } finally {
        setLoading(false);
      }
    },
    [jobId],
  );

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      void loadPackage(controller.signal);
    });
    return () => controller.abort();
  }, [loadPackage]);

  const run_action = useCallback(
    async (action: () => Promise<unknown>) => {
      setBusy(true);
      setError(null);
      try {
        await action();
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
    [],
  );

  const currentGate: ApplicationRunGate | undefined = run?.gates.find(
    (gate) => !gate.acknowledged,
  );
  const atSubmissionGate =
    currentGate?.code === "submission_confirmation";

  return (
    <main className="min-h-screen bg-slate-950 px-5 py-10 text-white">
      <div className="mx-auto max-w-4xl space-y-6">
        <div>
          <Link
            href={`/jobs/${jobId}`}
            className="text-sm text-blue-300 hover:text-blue-200"
          >
            ← Back to job
          </Link>
          <h1 className="mt-3 text-2xl font-bold">
            Prepare &amp; apply
          </h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-400">
            Assemble the tailored application, review what&rsquo;s
            ready or blocked, then step through the safety gates. The
            tool never submits for you — you perform the final
            submission and record it here.
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-sm text-slate-400">Loading…</p>
        ) : (
          <>
            <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                  Application package
                </h2>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    run_action(async () => {
                      const prepared = await prepareApplication(jobId);
                      setPkg(prepared);
                      setNotes(prepared.user_notes ?? "");
                      setRun(null);
                    })
                  }
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold transition hover:bg-blue-500 disabled:opacity-50"
                >
                  {pkg ? "Re-prepare" : "Prepare application"}
                </button>
              </div>

              {!pkg ? (
                <p className="mt-3 text-sm text-slate-400">
                  No package yet. Prepare one to tailor the CV and
                  assemble the application.
                </p>
              ) : (
                <div className="mt-4 space-y-4">
                  <span
                    className={`inline-block rounded-full border px-3 py-1 text-xs font-medium ${readinessClasses(
                      pkg.readiness_status,
                    )}`}
                  >
                    {humanize(pkg.readiness_status)}
                  </span>

                  {pkg.blockers.length > 0 && (
                    <ItemList
                      title="Blockers"
                      tone="rose"
                      items={pkg.blockers.map(
                        (blocker) =>
                          `${humanize(blocker.code)}: ${blocker.detail}`,
                      )}
                    />
                  )}
                  {pkg.missing_items.length > 0 && (
                    <ItemList
                      title="Missing information"
                      tone="amber"
                      items={pkg.missing_items}
                    />
                  )}
                  {pkg.risk_warnings.length > 0 && (
                    <ItemList
                      title="For your review"
                      tone="amber"
                      items={pkg.risk_warnings}
                    />
                  )}

                  <div className="grid gap-3 sm:grid-cols-2">
                    <Fact
                      label="Match"
                      value={
                        pkg.match
                          ? `${humanize(pkg.match.eligibility_status)}${
                              pkg.match.match_score !== null
                                ? ` · ${pkg.match.match_score}`
                                : ""
                            }`
                          : "Not analyzed"
                      }
                    />
                    <Fact
                      label="Tailored CV"
                      value={
                        pkg.tailored_cv
                          ? `${pkg.tailored_cv.artifacts
                              .map((a) => a.artifact_type.toUpperCase())
                              .join(" + ")} (${pkg.tailored_cv.status})`
                          : "Not tailored"
                      }
                    />
                    <Fact
                      label="Verified answers"
                      value={String(
                        pkg.verified_answers.filter((a) => a.verified)
                          .length,
                      )}
                    />
                    <Fact
                      label="Salary guidance"
                      value={
                        pkg.salary
                          ? humanize(pkg.salary.basis)
                          : "None"
                      }
                    />
                  </div>

                  {pkg.cover_letter_text && (
                    <details className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                      <summary className="cursor-pointer text-sm text-slate-300">
                        Cover letter preview
                      </summary>
                      <p className="mt-2 whitespace-pre-wrap text-sm text-slate-400">
                        {pkg.cover_letter_text}
                      </p>
                    </details>
                  )}

                  <div className="border-t border-slate-800 pt-4">
                    <label className="flex flex-col gap-1 text-xs text-slate-400">
                      Notes for yourself
                      <input
                        type="text"
                        value={notes}
                        onChange={(event) =>
                          setNotes(event.target.value)
                        }
                        className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-200"
                      />
                    </label>
                    <div className="mt-3 flex items-center gap-3">
                      <button
                        type="button"
                        disabled={
                          busy || !READY_STATUSES.has(pkg.readiness_status)
                        }
                        onClick={() =>
                          run_action(async () => {
                            const updated =
                              await updateApplicationPackage(jobId, {
                                user_confirmed: true,
                                user_notes: notes || null,
                              });
                            setPkg(updated);
                          })
                        }
                        className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold transition hover:bg-emerald-500 disabled:opacity-50"
                      >
                        {pkg.user_confirmed
                          ? "Confirmed ✓"
                          : "Confirm package"}
                      </button>
                      {!READY_STATUSES.has(pkg.readiness_status) && (
                        <span className="text-xs text-slate-500">
                          Resolve blockers before confirming.
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </section>

            {pkg && (
              <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                    Guided submission
                  </h2>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      run_action(async () => {
                        setRun(await startApplicationRun(jobId));
                      })
                    }
                    className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-blue-300 transition hover:border-blue-500 disabled:opacity-50"
                  >
                    {run ? "Restart run" : "Start guided run"}
                  </button>
                </div>

                {!run ? (
                  <p className="mt-3 text-sm text-slate-400">
                    Start a guided run to step through the safety
                    gates (CAPTCHA, MFA, legal declarations) and
                    record the final submission.
                  </p>
                ) : (
                  <div className="mt-4 space-y-4">
                    <p className="text-sm text-slate-300">
                      Status:{" "}
                      <span className="font-medium">
                        {humanize(run.status)}
                      </span>
                      {run.confirmation_number
                        ? ` · Confirmation ${run.confirmation_number}`
                        : ""}
                    </p>

                    <ol className="space-y-2">
                      {run.gates.map((gate) => (
                        <li
                          key={gate.code}
                          className={`rounded-lg border px-3 py-2 text-sm ${
                            gate.acknowledged
                              ? "border-emerald-500/30 text-emerald-300"
                              : gate === currentGate
                                ? "border-amber-500/40 text-amber-200"
                                : "border-slate-800 text-slate-400"
                          }`}
                        >
                          <span className="font-medium">
                            {gate.acknowledged ? "✓ " : ""}
                            {humanize(gate.code)}
                          </span>
                          <span className="ml-2 text-slate-500">
                            {gate.detail}
                          </span>
                        </li>
                      ))}
                    </ol>

                    {run.status === "paused_for_gate" &&
                      currentGate &&
                      !atSubmissionGate && (
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() =>
                            run_action(async () => {
                              setRun(
                                await resumeApplicationRun(run.id),
                              );
                            })
                          }
                          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold transition hover:bg-blue-500 disabled:opacity-50"
                        >
                          I&rsquo;ve handled &ldquo;
                          {humanize(currentGate.code)}&rdquo; — continue
                        </button>
                      )}

                    {run.status === "paused_for_gate" &&
                      atSubmissionGate && (
                        <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                          <p className="text-sm text-slate-300">
                            Submit the application on the
                            employer&rsquo;s site, then record the
                            confirmation number here.
                          </p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            <input
                              type="text"
                              value={confirmation}
                              onChange={(event) =>
                                setConfirmation(event.target.value)
                              }
                              placeholder="Confirmation number"
                              className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
                            />
                            <button
                              type="button"
                              disabled={
                                busy || confirmation.trim() === ""
                              }
                              onClick={() =>
                                run_action(async () => {
                                  setRun(
                                    await resumeApplicationRun(
                                      run.id,
                                      confirmation.trim(),
                                    ),
                                  );
                                })
                              }
                              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold transition hover:bg-emerald-500 disabled:opacity-50"
                            >
                              Record submission
                            </button>
                          </div>
                        </div>
                      )}

                    {run.manual_fields.length > 0 && (
                      <ItemList
                        title="Fill manually"
                        tone="amber"
                        items={run.manual_fields.map(
                          (field) =>
                            `${humanize(field.field)} — ${field.reason}`,
                        )}
                      />
                    )}

                    {run.status === "paused_for_gate" && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() =>
                          run_action(async () => {
                            setRun(
                              await cancelApplicationRun(run.id),
                            );
                          })
                        }
                        className="text-xs text-rose-300 hover:text-rose-200"
                      >
                        Cancel run
                      </button>
                    )}
                  </div>
                )}
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}

function ItemList({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "rose" | "amber";
}) {
  const color =
    tone === "rose" ? "text-rose-300" : "text-amber-300";
  return (
    <div>
      <h3
        className={`text-xs font-semibold uppercase tracking-wide ${color}`}
      >
        {title}
      </h3>
      <ul className="mt-1 space-y-1 text-sm text-slate-400">
        {items.map((item, index) => (
          <li key={`${item}-${index}`}>• {item}</li>
        ))}
      </ul>
    </div>
  );
}

function Fact({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-0.5 text-sm text-slate-200">{value}</p>
    </div>
  );
}
