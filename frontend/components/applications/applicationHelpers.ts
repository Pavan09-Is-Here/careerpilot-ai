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
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
    case "interview":
      return "border-violet-200 bg-violet-50 text-violet-700";
    case "ready_to_apply":
      return "border-cyan-200 bg-cyan-50 text-cyan-700";
    case "blocked":
    case "needs_review":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "rejected":
    case "not_eligible":
    case "withdrawn":
      return "border-rose-200 bg-rose-50 text-rose-700";
    default:
      return "border-slate-200 bg-slate-50 text-slate-600";
  }
}
