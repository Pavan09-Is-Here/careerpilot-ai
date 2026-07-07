"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  cancelApplicationRun,
  createApplicationAnswer,
  getApplicationPackage,
  isAbortError,
  prepareApplication,
  resumeApplicationRun,
  startApplicationRun,
  updateApplicationPackage,
} from "@/lib/api";

import type { ApplicationPackage } from "@/types/applicationPackage";
import type { ApplicationAnswerCategory } from "@/types/applicationAnswer";
import type {
  ApplicationRun,
  ApplicationRunConsentGate,
  ApplicationRunGate,
} from "@/types/applicationRun";

const ANSWER_QUESTIONS: Record<ApplicationAnswerCategory, string> = {
  work_authorization:
    "Are you legally authorized to work in the job's country?",
  sponsorship:
    "Do you now, or will you in the future, require visa sponsorship?",
  availability: "When are you available to start?",
  notice_period: "What is your notice period?",
  relocation: "Are you willing to relocate for this role?",
  remote_preference: "What is your remote / on-site preference?",
  expected_salary: "What is your expected salary?",
  company_interest: "Why are you interested in this company?",
  cover_letter: "Cover letter",
  other: "Application question",
};

const ANSWER_PLACEHOLDERS: Partial<
  Record<ApplicationAnswerCategory, string>
> = {
  work_authorization:
    'e.g. "UK citizen — authorized to work in the UK"',
  sponsorship: 'e.g. "No, I do not require sponsorship"',
  availability: 'e.g. "Available immediately"',
  notice_period: 'e.g. "One month"',
  relocation: 'e.g. "Yes, willing to relocate within the UK"',
  expected_salary: 'e.g. "£55,000 depending on the full package"',
};

const KNOWN_CATEGORIES = new Set<string>(
  Object.keys(ANSWER_QUESTIONS),
);

/** Answer categories referenced by the package's missing items and
 * review warnings, in first-mention order. */
function missingAnswerCategories(
  pkg: ApplicationPackage,
): ApplicationAnswerCategory[] {
  const found: ApplicationAnswerCategory[] = [];
  const texts = [...pkg.missing_items, ...pkg.risk_warnings];
  for (const text of texts) {
    const match = /'([a-z_]+)'/.exec(text);
    if (
      match &&
      KNOWN_CATEGORIES.has(match[1]) &&
      !found.includes(match[1] as ApplicationAnswerCategory)
    ) {
      found.push(match[1] as ApplicationAnswerCategory);
    }
  }
  return found;
}

function needsProfileVerification(pkg: ApplicationPackage): boolean {
  return pkg.missing_items.some((item) =>
    item.includes("verified candidate profile"),
  );
}

const CONSENT_GATES: ApplicationRunConsentGate[] = [
  "legal_declaration",
  "submission_confirmation",
];

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
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (status === "needs_user_review") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-rose-200 bg-rose-50 text-rose-700";
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
  const [consentLegal, setConsentLegal] = useState(false);
  const [consentSubmit, setConsentSubmit] = useState(false);
  const [answerDrafts, setAnswerDrafts] = useState<
    Partial<Record<ApplicationAnswerCategory, string>>
  >({});
  const [answerConfirms, setAnswerConfirms] = useState<
    Partial<Record<ApplicationAnswerCategory, boolean>>
  >({});

  const loadPackage = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);

      try {
        const loaded = await getApplicationPackage(jobId, signal);
        setPkg(loaded);
        setNotes(loaded.user_notes ?? "");
      } catch (loadError) {
        if (isAbortError(loadError)) {
          return;
        }

        const message =
          loadError instanceof Error
            ? loadError.message
            : "Failed to load the application package.";

        // The backend answers 404 with this detail when the
        // package has not been prepared yet — that is expected.
        if (
          message.startsWith("No application package exists") ||
          message === "Job was not found."
        ) {
          setPkg(null);
        } else {
          setError(message);
        }
      } finally {
        if (!signal?.aborted) {
          setLoading(false);
        }
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

  const quickFixCategories = pkg ? missingAnswerCategories(pkg) : [];
  const profileNeedsVerification = pkg
    ? needsProfileVerification(pkg)
    : false;
  const cvIsMissing =
    pkg?.missing_items.some((item) =>
      item.includes("tailored CV"),
    ) ?? false;

  const saveQuickAnswer = (category: ApplicationAnswerCategory) =>
    run_action(async () => {
      const text = (answerDrafts[category] ?? "").trim();
      if (!text) {
        return;
      }
      await createApplicationAnswer({
        category,
        question_label: ANSWER_QUESTIONS[category],
        answer_text: text,
        verified: true,
        manually_confirmed: true,
        notes: null,
      });
      // Re-prepare so the readiness and the missing list update
      // immediately — no manual Re-prepare click needed.
      const updated = await prepareApplication(jobId);
      setPkg(updated);
      setNotes(updated.user_notes ?? "");
      setAnswerDrafts((previous) => ({
        ...previous,
        [category]: "",
      }));
      setAnswerConfirms((previous) => ({
        ...previous,
        [category]: false,
      }));
    });

  return (
    <main className="cp-page">
      <div className="mx-auto max-w-4xl space-y-6">
        <div>
          <Link
            href={`/jobs/${jobId}`}
            className="text-sm text-violet-700 hover:text-violet-800"
          >
            ← Back to job
          </Link>
          <h1 className="mt-3 text-2xl font-bold text-slate-900">
            Prepare &amp; apply
          </h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
            Assemble the tailored application, review what&rsquo;s
            ready or blocked, then apply. With your explicit consent
            the application is submitted automatically where the job
            source permits it; anything that needs you (CAPTCHAs,
            sensitive questions, or the final submission on other
            sites) pauses the run and notifies you by email.
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : (
          <>
            <section className="rounded-2xl border border-violet-200 bg-violet-50/50 p-5 shadow-sm">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-violet-700">
                One-click apply
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                Analyzes the match, tailors your CV and cover letter
                from verified facts, and prepares the application in
                one step. Nothing is ever invented, safety checks are
                never bypassed, and you&rsquo;ll get an email if any
                step needs you — and when the application is
                submitted.
              </p>
              <div className="mt-3 space-y-2">
                <label className="flex items-start gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={consentLegal}
                    onChange={(event) =>
                      setConsentLegal(event.target.checked)
                    }
                    className="mt-0.5"
                  />
                  I have reviewed my legal declarations (work
                  authorization, background-check consent) and they
                  are accurate.
                </label>
                <label className="flex items-start gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={consentSubmit}
                    onChange={(event) =>
                      setConsentSubmit(event.target.checked)
                    }
                    className="mt-0.5"
                  />
                  I authorize submitting this application on my
                  behalf where the job source permits it. Submission
                  is irreversible.
                </label>
              </div>
              <button
                type="button"
                disabled={busy || !consentLegal || !consentSubmit}
                onClick={() =>
                  run_action(async () => {
                    setRun(
                      await startApplicationRun(jobId, {
                        driver: "auto_submit",
                        acknowledged_gates: CONSENT_GATES,
                      }),
                    );
                    await loadPackage();
                  })
                }
                className="mt-4 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
              >
                Apply automatically
              </button>
              {run?.driver === "auto_submit" &&
                run.status === "submitted" && (
                  <p
                    role="status"
                    className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700"
                  >
                    Application submitted
                    {run.submission_method &&
                    run.submission_method !== "manual"
                      ? ` via ${humanize(run.submission_method)}`
                      : ""}
                    {run.confirmation_number
                      ? ` — confirmation ${run.confirmation_number}`
                      : ""}
                    . A confirmation email has been recorded for you.
                  </p>
                )}
              {run?.driver === "auto_submit" &&
                run.status === "paused_for_gate" && (
                  <p
                    role="alert"
                    className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
                  >
                    {run.pause_reason === "manual_fields_required"
                      ? "Some entries need you before submission — see the list below. You've been notified by email."
                      : run.pause_reason === "submission_confirmation"
                        ? "Everything is prepared, but this job source has no permitted automatic submission channel. Submit it yourself below and record the confirmation number. You've been notified by email."
                        : `Paused: ${humanize(
                            run.pause_reason ?? "action needed",
                          )} — complete this step yourself below. You've been notified by email.`}
                  </p>
                )}
            </section>
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
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
                  className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
                >
                  {pkg ? "Re-prepare" : "Prepare application"}
                </button>
              </div>

              {!pkg ? (
                <p className="mt-3 text-sm text-slate-500">
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

                  {(quickFixCategories.length > 0 ||
                    profileNeedsVerification ||
                    cvIsMissing) && (
                    <div className="rounded-xl border border-violet-200 bg-violet-50/40 p-4">
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-violet-700">
                        Fix it here
                      </h3>
                      {profileNeedsVerification && (
                        <p className="mt-2 text-sm text-slate-700">
                          Your profile facts aren&rsquo;t verified
                          yet —{" "}
                          <Link
                            href="/profile"
                            className="font-medium text-violet-700 hover:underline"
                          >
                            open your profile
                          </Link>{" "}
                          and click &ldquo;Verify all facts&rdquo;,
                          then come back.
                        </p>
                      )}
                      {cvIsMissing && (
                        <p className="mt-2 text-sm text-slate-600">
                          The tailored CV is created for you
                          automatically when you click Apply
                          automatically. It&rsquo;s built from the CV
                          you uploaded — if you haven&rsquo;t
                          uploaded one yet, do that first on the{" "}
                          <Link
                            href="/documents"
                            className="font-medium text-violet-700 hover:underline"
                          >
                            Documents page
                          </Link>
                          .
                        </p>
                      )}
                      {quickFixCategories.length > 0 && (
                        <div className="mt-3 space-y-4">
                          <p className="text-sm text-slate-600">
                            Answer these once — they&rsquo;re saved
                            to your vault as verified answers and
                            reused for every future application.
                          </p>
                          {quickFixCategories.map((category) => (
                            <div key={category}>
                              <label className="flex flex-col gap-1 text-sm text-slate-700">
                                <span className="font-medium">
                                  {ANSWER_QUESTIONS[category]}
                                </span>
                                <input
                                  type="text"
                                  value={
                                    answerDrafts[category] ?? ""
                                  }
                                  placeholder={
                                    ANSWER_PLACEHOLDERS[category] ??
                                    "Your answer"
                                  }
                                  onChange={(event) =>
                                    setAnswerDrafts(
                                      (previous) => ({
                                        ...previous,
                                        [category]:
                                          event.target.value,
                                      }),
                                    )
                                  }
                                  className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
                                />
                              </label>
                              <div className="mt-1.5 flex flex-wrap items-center gap-3">
                                <label className="flex items-center gap-2 text-xs text-slate-600">
                                  <input
                                    type="checkbox"
                                    checked={
                                      answerConfirms[category] ??
                                      false
                                    }
                                    onChange={(event) =>
                                      setAnswerConfirms(
                                        (previous) => ({
                                          ...previous,
                                          [category]:
                                            event.target.checked,
                                        }),
                                      )
                                    }
                                  />
                                  I confirm this answer is true and
                                  accurate.
                                </label>
                                <button
                                  type="button"
                                  disabled={
                                    busy ||
                                    !(
                                      answerDrafts[category] ?? ""
                                    ).trim() ||
                                    !(
                                      answerConfirms[category] ??
                                      false
                                    )
                                  }
                                  onClick={() =>
                                    saveQuickAnswer(category)
                                  }
                                  className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
                                >
                                  Save verified answer
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
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
                    <details className="rounded-lg border border-slate-200 bg-white p-3">
                      <summary className="cursor-pointer text-sm text-slate-600">
                        Cover letter preview
                      </summary>
                      <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">
                        {pkg.cover_letter_text}
                      </p>
                    </details>
                  )}

                  <div className="border-t border-slate-200 pt-4">
                    <label className="flex flex-col gap-1 text-xs text-slate-500">
                      Notes for yourself
                      <input
                        type="text"
                        value={notes}
                        onChange={(event) =>
                          setNotes(event.target.value)
                        }
                        className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
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
                        className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50"
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
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
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
                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-violet-700 transition hover:border-violet-400 hover:bg-violet-50 disabled:opacity-50"
                  >
                    {run ? "Restart run" : "Start guided run"}
                  </button>
                </div>

                {!run ? (
                  <p className="mt-3 text-sm text-slate-500">
                    Start a guided run to step through the safety
                    gates (CAPTCHA, MFA, legal declarations) and
                    record the final submission.
                  </p>
                ) : (
                  <div className="mt-4 space-y-4">
                    <p className="text-sm text-slate-700">
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
                              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                              : gate === currentGate
                                ? "border-amber-200 bg-amber-50 text-amber-700"
                                : "border-slate-200 bg-white text-slate-600"
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
                          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
                        >
                          I&rsquo;ve handled &ldquo;
                          {humanize(currentGate.code)}&rdquo; — continue
                        </button>
                      )}

                    {run.status === "paused_for_gate" &&
                      atSubmissionGate && (
                        <div className="rounded-lg border border-slate-200 bg-white p-3">
                          <p className="text-sm text-slate-600">
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
                              className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
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
                              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50"
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
                        className="text-xs text-rose-700 hover:text-rose-800"
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
    tone === "rose" ? "text-rose-700" : "text-amber-700";
  return (
    <div>
      <h3
        className={`text-xs font-semibold uppercase tracking-wide ${color}`}
      >
        {title}
      </h3>
      <ul className="mt-1 space-y-1 text-sm text-slate-600">
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
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-0.5 text-sm text-slate-700">{value}</p>
    </div>
  );
}
