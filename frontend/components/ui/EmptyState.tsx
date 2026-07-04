import Link from "next/link";
import type { ReactNode } from "react";

type EmptyStateProps = {
  title: string;
  description?: ReactNode;
  /** Optional next-step action rendered as a violet button. */
  actionLabel?: string;
  actionHref?: string;
  onAction?: () => void;
  icon?: ReactNode;
};

const defaultIcon = (
  <svg
    className="h-6 w-6 text-violet-600"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    aria-hidden="true"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M9 12h6m-6 4h6m2 5H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2z"
    />
  </svg>
);

/**
 * Friendly empty-list state with an icon, title, description and an
 * optional next-step button. Provide either `actionHref` (link) or
 * `onAction` (button); if both are absent no action is rendered.
 */
export default function EmptyState({
  title,
  description,
  actionLabel,
  actionHref,
  onAction,
  icon,
}: EmptyStateProps) {
  const action =
    actionLabel && actionHref ? (
      <Link href={actionHref} className="cp-btn-primary">
        {actionLabel}
      </Link>
    ) : actionLabel && onAction ? (
      <button
        type="button"
        onClick={onAction}
        className="cp-btn-primary"
      >
        {actionLabel}
      </button>
    ) : null;

  return (
    <div className="cp-card flex flex-col items-center gap-3 border-dashed py-12 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-violet-50">
        {icon ?? defaultIcon}
      </span>
      <h3 className="text-base font-medium text-slate-900">
        {title}
      </h3>
      {description ? (
        <p className="max-w-md text-sm leading-6 cp-muted">
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
