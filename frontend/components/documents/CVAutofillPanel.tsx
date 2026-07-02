"use client";

import { useCallback, useState } from "react";

import {
  applyDocumentProfileSuggestion,
  getDocumentProfileSuggestion,
} from "@/lib/api";

import type {
  ApplyProfileSuggestionResult,
  ProfileSuggestion,
} from "@/types/profileSuggestion";

function humanizeField(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function CVAutofillPanel({
  documentId,
}: {
  documentId: number;
}) {
  const [suggestion, setSuggestion] =
    useState<ProfileSuggestion | null>(null);
  const [result, setResult] =
    useState<ApplyProfileSuggestionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [includeSensitive, setIncludeSensitive] = useState(false);
  const [overwrite, setOverwrite] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPreview = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      setSuggestion(
        await getDocumentProfileSuggestion(documentId),
      );
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Could not read details from this CV.",
      );
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  const applySuggestion = useCallback(async () => {
    setApplying(true);
    setError(null);

    try {
      const applied = await applyDocumentProfileSuggestion(
        documentId,
        { includeSensitive, overwrite },
      );
      setResult(applied);
    } catch (applyError) {
      setError(
        applyError instanceof Error
          ? applyError.message
          : "Could not fill the profile from this CV.",
      );
    } finally {
      setApplying(false);
    }
  }, [documentId, includeSensitive, overwrite]);

  const autoFields =
    suggestion?.fields.filter((field) => field.auto_fill) ?? [];
  const sensitiveFields =
    suggestion?.fields.filter((field) => field.sensitive) ?? [];

  return (
    <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-lg font-semibold text-white">
            Fill profile from this CV
          </h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-400">
            Extract candidate details from the CV text. Everything
            pulled from a CV is unverified until you confirm it,
            and private details (phone, location) and dated history
            (education, experience) are left for you to enter
            manually.
          </p>
        </div>

        <button
          type="button"
          onClick={loadPreview}
          disabled={loading}
          className="shrink-0 rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-blue-300 transition hover:border-blue-500 disabled:opacity-50"
        >
          {loading ? "Reading…" : "Preview details"}
        </button>
      </div>

      {error && (
        <p className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      {suggestion && (
        <div className="mt-5 space-y-5">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Auto-fillable (unverified)
            </h3>
            {autoFields.length === 0 ? (
              <p className="mt-2 text-sm text-slate-400">
                No profile fields detected.
              </p>
            ) : (
              <ul className="mt-2 space-y-2">
                {autoFields.map((field) => (
                  <li
                    key={field.field}
                    className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm"
                  >
                    <span className="font-medium text-slate-200">
                      {humanizeField(field.field)}:
                    </span>{" "}
                    <span className="text-slate-300">
                      {field.value}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {suggestion.skills.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Skills ({suggestion.skills.length})
              </h3>
              <div className="mt-2 flex flex-wrap gap-2">
                {suggestion.skills.map((skill) => (
                  <span
                    key={skill.name}
                    className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300"
                  >
                    {skill.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {(sensitiveFields.length > 0 ||
            suggestion.manual_review.length > 0) && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-amber-400">
                Needs manual entry
              </h3>
              <ul className="mt-2 space-y-1 text-sm text-slate-400">
                {sensitiveFields.map((field) => (
                  <li key={field.field}>
                    {humanizeField(field.field)} — private detail,
                    confirm manually.
                  </li>
                ))}
                {suggestion.manual_review.map((manual) => (
                  <li key={manual.category}>
                    {humanizeField(manual.category)} — {manual.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-4 border-t border-slate-800 pt-4">
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={overwrite}
                onChange={(event) =>
                  setOverwrite(event.target.checked)
                }
              />
              Overwrite existing values
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={includeSensitive}
                onChange={(event) =>
                  setIncludeSensitive(event.target.checked)
                }
              />
              Also apply private fields
            </label>

            <button
              type="button"
              onClick={applySuggestion}
              disabled={applying}
              className="ml-auto rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold transition hover:bg-blue-500 disabled:opacity-50"
            >
              {applying ? "Applying…" : "Apply to profile"}
            </button>
          </div>
        </div>
      )}

      {result && (
        <div className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
          Applied {result.applied_fields.length} field(s) and added{" "}
          {result.added_skills.length} skill(s), all as unverified.
          {result.skipped_existing_fields.length > 0 && (
            <span className="text-emerald-300/80">
              {" "}
              Kept {result.skipped_existing_fields.length} existing
              value(s).
            </span>
          )}{" "}
          Review and verify them on the profile page.
        </div>
      )}
    </section>
  );
}
