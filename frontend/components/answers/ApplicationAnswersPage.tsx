"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  createApplicationAnswer,
  deleteApplicationAnswer,
  getApplicationAnswers,
  isAbortError,
  updateApplicationAnswer,
} from "@/lib/api";

import type {
  ApplicationAnswer,
  ApplicationAnswerCategory,
  ApplicationAnswerInput,
} from "@/types/applicationAnswer";

const CATEGORIES: ApplicationAnswerCategory[] = [
  "work_authorization",
  "sponsorship",
  "availability",
  "notice_period",
  "relocation",
  "remote_preference",
  "expected_salary",
  "company_interest",
  "cover_letter",
  "other",
];

function humanize(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

const EMPTY_FORM: ApplicationAnswerInput = {
  category: "availability",
  question_label: "",
  answer_text: "",
  verified: false,
  manually_confirmed: false,
  notes: null,
};

export default function ApplicationAnswersPage() {
  const [answers, setAnswers] = useState<ApplicationAnswer[]>(
    [],
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(
    null,
  );
  const [form, setForm] =
    useState<ApplicationAnswerInput>(EMPTY_FORM);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);

    try {
      setAnswers(await getApplicationAnswers(undefined, signal));
    } catch (loadError) {
      if (isAbortError(loadError)) {
        return;
      }

      setError(
        loadError instanceof Error
          ? loadError.message
          : "Could not load answers.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      void load(controller.signal);
    });
    return () => controller.abort();
  }, [load]);

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
  };

  const startEdit = (answer: ApplicationAnswer) => {
    setEditingId(answer.id);
    setForm({
      category: answer.category,
      question_label: answer.question_label,
      answer_text: answer.answer_text,
      verified: answer.verified,
      manually_confirmed: answer.manually_confirmed,
      notes: answer.notes,
    });
  };

  const submit = useCallback(async () => {
    setBusy(true);
    setError(null);

    try {
      if (editingId === null) {
        await createApplicationAnswer(form);
      } else {
        await updateApplicationAnswer(editingId, form);
      }
      resetForm();
      await load();
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Could not save the answer.",
      );
    } finally {
      setBusy(false);
    }
  }, [editingId, form, load]);

  const remove = useCallback(
    async (answerId: number) => {
      setBusy(true);
      setError(null);

      try {
        await deleteApplicationAnswer(answerId);
        if (editingId === answerId) {
          resetForm();
        }
        await load();
      } catch (removeError) {
        setError(
          removeError instanceof Error
            ? removeError.message
            : "Could not delete the answer.",
        );
      } finally {
        setBusy(false);
      }
    },
    [editingId, load],
  );

  return (
    <main className="cp-page">
      <div className="mx-auto max-w-4xl">
        <header className="mb-8">
          <Link
            href="/"
            className="text-sm text-violet-700 hover:text-violet-800"
          >
            ← Dashboard
          </Link>
          <h1 className="mt-3 text-3xl font-bold text-slate-900">
            Application answers
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            Reusable answers to common application questions. Only
            verified answers are used in prepared applications.
            Sensitive or legal answers (work authorization,
            sponsorship) must be manually confirmed before they can
            be verified.
          </p>
        </header>

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
            {editingId === null ? "Add answer" : "Edit answer"}
          </h2>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-xs text-slate-500">
              Category
              <select
                value={form.category}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    category: event.target
                      .value as ApplicationAnswerCategory,
                  }))
                }
                className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
              >
                {CATEGORIES.map((value) => (
                  <option key={value} value={value}>
                    {humanize(value)}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1 text-xs text-slate-500">
              Question label
              <input
                type="text"
                value={form.question_label}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    question_label: event.target.value,
                  }))
                }
                placeholder="e.g. Do you require visa sponsorship?"
                className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
              />
            </label>
          </div>

          <label className="mt-3 flex flex-col gap-1 text-xs text-slate-500">
            Answer
            <textarea
              value={form.answer_text}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  answer_text: event.target.value,
                }))
              }
              rows={3}
              className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
            />
          </label>

          <label className="mt-3 flex flex-col gap-1 text-xs text-slate-500">
            Notes (optional)
            <input
              type="text"
              value={form.notes ?? ""}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  notes: event.target.value || null,
                }))
              }
              className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-200"
            />
          </label>

          <div className="mt-4 flex flex-wrap items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={form.verified}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    verified: event.target.checked,
                  }))
                }
              />
              Verified
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={form.manually_confirmed}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    manually_confirmed: event.target.checked,
                  }))
                }
              />
              Manually confirmed (for sensitive/legal answers)
            </label>

            <div className="ml-auto flex gap-2">
              {editingId !== null && (
                <button
                  type="button"
                  onClick={resetForm}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 transition hover:border-violet-400 hover:text-violet-700"
                >
                  Cancel
                </button>
              )}
              <button
                type="button"
                disabled={
                  busy ||
                  form.question_label.trim() === "" ||
                  form.answer_text.trim() === ""
                }
                onClick={submit}
                className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
              >
                {editingId === null ? "Add answer" : "Save changes"}
              </button>
            </div>
          </div>
        </section>

        {loading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : answers.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500 shadow-sm">
            No answers yet.
          </div>
        ) : (
          <ul className="space-y-3">
            {answers.map((answer) => {
              const needsConfirmation =
                answer.requires_manual_confirmation &&
                !answer.manually_confirmed;

              return (
                <li
                  key={answer.id}
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600">
                      {humanize(answer.category)}
                    </span>
                    {answer.verified ? (
                      <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs text-emerald-700">
                        Verified
                      </span>
                    ) : (
                      <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-500">
                        Unverified
                      </span>
                    )}
                    {needsConfirmation && (
                      <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs text-amber-700">
                        Needs manual confirmation
                      </span>
                    )}
                    <div className="ml-auto flex gap-2">
                      <button
                        type="button"
                        onClick={() => startEdit(answer)}
                        className="text-xs text-violet-700 hover:text-violet-800"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => remove(answer.id)}
                        className="text-xs text-red-700 hover:text-red-800 disabled:opacity-50"
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  <p className="mt-3 text-sm font-medium text-slate-900">
                    {answer.question_label}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-slate-600">
                    {answer.answer_text}
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </main>
  );
}
