import type { ApplicationStatus } from "@/types/application";

export const APPLICATION_STATUSES: ApplicationStatus[] = [
  "discovered",
  "analyzing",
  "not_eligible",
  "matched",
  "cv_generated",
  "needs_review",
  "ready_to_apply",
  "applying",
  "blocked",
  "submitted",
  "interview",
  "rejected",
  "offer",
  "withdrawn",
];

export function humanizeStatus(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatDateTime(value: string | null): string {
  if (!value) {
    return "—";
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

export function statusClasses(status: string): string {
  switch (status) {
    case "submitted":
    case "offer":
      return "border-emerald-500/40 text-emerald-300";
    case "interview":
      return "border-blue-500/40 text-blue-300";
    case "ready_to_apply":
      return "border-cyan-500/40 text-cyan-300";
    case "blocked":
    case "needs_review":
      return "border-amber-500/40 text-amber-300";
    case "rejected":
    case "not_eligible":
    case "withdrawn":
      return "border-rose-500/40 text-rose-300";
    default:
      return "border-slate-600 text-slate-300";
  }
}
