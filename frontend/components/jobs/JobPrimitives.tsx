import type { JobLifecycleStatus } from "@/types/job";
import type { SavedJobReviewStatus } from "@/types/savedJob";

export function humanizeToken(value: string): string {
  return value
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() + part.slice(1),
    )
    .join(" ");
}

export function formatDateTime(
  value: string | null,
): string {
  if (!value) {
    return "—";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "—";
  }

  return parsed.toLocaleString();
}

const LIFECYCLE_BADGE_CLASSES: Record<
  JobLifecycleStatus,
  string
> = {
  discovered: "bg-sky-50 text-sky-700 border border-sky-200",
  active: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  possibly_stale: "bg-amber-50 text-amber-700 border border-amber-200",
  expired: "bg-slate-100 text-slate-500 border border-slate-200",
  removed: "bg-rose-50 text-rose-700 border border-rose-200",
  unavailable: "bg-slate-100 text-slate-500 border border-slate-200",
};

export function LifecycleBadge({
  status,
}: {
  status: JobLifecycleStatus;
}) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${LIFECYCLE_BADGE_CLASSES[status]}`}
    >
      {humanizeToken(status)}
    </span>
  );
}

const REVIEW_BADGE_CLASSES: Record<
  SavedJobReviewStatus,
  string
> = {
  saved: "bg-sky-50 text-sky-700 border border-sky-200",
  shortlisted: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  dismissed: "bg-rose-50 text-rose-700 border border-rose-200",
  archived: "bg-slate-100 text-slate-500 border border-slate-200",
};

export function ReviewBadge({
  status,
}: {
  status: SavedJobReviewStatus;
}) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${REVIEW_BADGE_CLASSES[status]}`}
    >
      {humanizeToken(status)}
    </span>
  );
}

export function EmptyState({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
      <h2 className="text-lg font-semibold text-slate-900">
        {title}
      </h2>
      <p className="mt-2 text-sm text-slate-500">
        {children}
      </p>
    </div>
  );
}

export function ErrorBanner({
  message,
}: {
  message: string;
}) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700"
    >
      {message}
    </div>
  );
}
