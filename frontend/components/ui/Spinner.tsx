type SpinnerProps = {
  label?: string;
  className?: string;
};

/**
 * Small violet spinner. When a `label` is provided it renders a centered
 * loading block suitable for replacing ad-hoc "Loading…" text.
 */
export default function Spinner({
  label,
  className,
}: SpinnerProps) {
  const icon = (
    <svg
      className="h-5 w-5 animate-spin text-violet-600"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-90"
        fill="currentColor"
        d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z"
      />
    </svg>
  );

  if (!label) {
    return <span className={className}>{icon}</span>;
  }

  return (
    <div
      role="status"
      className={`flex flex-col items-center justify-center gap-3 py-12 text-sm text-slate-500 ${
        className ?? ""
      }`}
    >
      {icon}
      <span>{label}</span>
    </div>
  );
}
