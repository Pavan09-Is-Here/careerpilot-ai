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
  discovered: "bg-sky-950 text-sky-300",
  active: "bg-emerald-950 text-emerald-300",
  possibly_stale: "bg-amber-950 text-amber-300",
  expired: "bg-slate-800 text-slate-400",
  removed: "bg-rose-950 text-rose-300",
  unavailable: "bg-slate-800 text-slate-500",
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
  saved: "bg-sky-950 text-sky-300",
  shortlisted: "bg-emerald-950 text-emerald-300",
  dismissed: "bg-rose-950 text-rose-300",
  archived: "bg-slate-800 text-slate-400",
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
    <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/50 p-8 text-center">
      <h2 className="text-lg font-semibold text-white">
        {title}
      </h2>
      <p className="mt-2 text-sm text-slate-400">
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
      className="rounded-lg border border-rose-900 bg-rose-950/60 p-4 text-sm text-rose-200"
    >
      {message}
    </div>
  );
}
