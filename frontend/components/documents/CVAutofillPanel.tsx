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

function formatYear(value: string | null): string {
  if (!value) {
    return "";
  }
  return value.slice(0, 4);
}

function formatSpan(
  start: string,
  end: string | null,
  isCurrent: boolean,
): string {
  const startYear = formatYear(start);
  if (isCurrent) {
    return `${startYear} – Present`;
  }
  const endYear = formatYear(end);
  return endYear ? `${startYear} – ${endYear}` : startYear;
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
    <section className="mt-6 cp-card border-violet-200 bg-violet-50/60">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <p className="cp-eyebrow">Start from your CV</p>
          <h2 className="mt-2 text-lg font-semibold text-slate-900">
            Fill profile from this CV
          </h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-600">
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
          className="shrink-0 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
        >
          {loading ? "Reading…" : "Preview details"}
        </button>
      </div>

      {error && (
        <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {suggestion && (
        <div className="mt-5 space-y-5">
          <div>
            <h3 className="cp-eyebrow text-xs tracking-wide">
              Auto-fillable (unverified)
            </h3>
            {autoFields.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">
                No profile fields detected.
              </p>
            ) : (
              <ul className="mt-2 space-y-2">
                {autoFields.map((field) => (
                  <li
                    key={field.field}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                  >
                    <span className="font-medium text-slate-900">
                      {humanizeField(field.field)}:
                    </span>{" "}
                    <span className="text-slate-600">
                      {field.value}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {suggestion.skills.length > 0 && (
            <div>
              <h3 className="cp-eyebrow text-xs tracking-wide">
                Skills ({suggestion.skills.length})
              </h3>
              <div className="mt-2 flex flex-wrap gap-2">
                {suggestion.skills.map((skill) => (
                  <span
                    key={skill.name}
                    className="cp-chip"
                  >
                    {skill.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {suggestion.education.length > 0 && (
            <div>
              <h3 className="cp-eyebrow text-xs tracking-wide">
                Education ({suggestion.education.length}) — draft, unverified
              </h3>
              <ul className="mt-2 space-y-2">
                {suggestion.education.map((entry, index) => (
                  <li
                    key={`${entry.institution}-${entry.degree}-${index}`}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                  >
                    <p className="font-medium text-slate-900">
                      {entry.degree}
                    </p>
                    <p className="text-slate-600">{entry.institution}</p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {formatSpan(
                        entry.start_date,
                        entry.end_date,
                        entry.is_current,
                      )}
                      {entry.grade ? ` · ${entry.grade}` : ""}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {suggestion.experience.length > 0 && (
            <div>
              <h3 className="cp-eyebrow text-xs tracking-wide">
                Work experience ({suggestion.experience.length}) — draft,
                unverified
              </h3>
              <ul className="mt-2 space-y-2">
                {suggestion.experience.map((entry, index) => (
                  <li
                    key={`${entry.company}-${entry.job_title}-${index}`}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                  >
                    <p className="font-medium text-slate-900">
                      {entry.job_title}
                    </p>
                    <p className="text-slate-600">{entry.company}</p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {formatSpan(
                        entry.start_date,
                        entry.end_date,
                        entry.is_current,
                      )}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {suggestion.projects.length > 0 && (
            <div>
              <h3 className="cp-eyebrow text-xs tracking-wide">
                Projects ({suggestion.projects.length}) — draft, unverified
              </h3>
              <ul className="mt-2 space-y-2">
                {suggestion.projects.map((entry, index) => (
                  <li
                    key={`${entry.name}-${index}`}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                  >
                    <p className="font-medium text-slate-900">
                      {entry.name}
                    </p>
                    <p className="line-clamp-2 text-slate-600">
                      {entry.description}
                    </p>
                    {entry.technologies.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {entry.technologies.map((tech) => (
                          <span key={tech} className="cp-chip">
                            {tech}
                          </span>
                        ))}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {suggestion.certifications.length > 0 && (
            <div>
              <h3 className="cp-eyebrow text-xs tracking-wide">
                Certifications ({suggestion.certifications.length}) — draft,
                unverified
              </h3>
              <ul className="mt-2 space-y-2">
                {suggestion.certifications.map((entry, index) => (
                  <li
                    key={`${entry.name}-${index}`}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
                  >
                    <p className="font-medium text-slate-900">
                      {entry.name}
                    </p>
                    <p className="text-slate-600">
                      {entry.issuing_organization}
                    </p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {formatYear(entry.issue_date)}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(sensitiveFields.length > 0 ||
            suggestion.manual_review.length > 0) && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-[0.25em] text-amber-600">
                Needs manual entry
              </h3>
              <ul className="mt-2 space-y-1 text-sm text-slate-600">
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

          <div className="flex flex-wrap items-center gap-4 border-t border-slate-200 pt-4">
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={overwrite}
                onChange={(event) =>
                  setOverwrite(event.target.checked)
                }
              />
              Overwrite existing values
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-600">
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
              className="ml-auto rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:opacity-50"
            >
              {applying ? "Applying…" : "Apply to profile"}
            </button>
          </div>
        </div>
      )}

      {result && (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          Applied {result.applied_fields.length} field(s) and added{" "}
          {result.added_skills.length} skill(s),{" "}
          {result.added_education.length} education,{" "}
          {result.added_experience.length} experience,{" "}
          {result.added_projects.length} project(s), and{" "}
          {result.added_certifications.length} certification(s) — all as
          unverified drafts.
          {result.skipped_existing_fields.length > 0 && (
            <span className="text-emerald-700/80">
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
