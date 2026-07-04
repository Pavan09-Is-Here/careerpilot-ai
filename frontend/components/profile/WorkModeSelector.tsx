"use client";

import { useMemo, type ReactNode } from "react";

type WorkModeSelectorProps = {
  value: string;
  onChange: (next: string) => void;
  label?: string;
};

type WorkModeOption = {
  label: string;
  icon: ReactNode;
};

const WORK_MODES: WorkModeOption[] = [
  {
    label: "Remote",
    icon: (
      <svg
        viewBox="0 0 24 24"
        className="h-4 w-4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M3 11l9-7 9 7" />
        <path d="M5 10v9a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-9" />
        <path d="M10 20v-5h4v5" />
      </svg>
    ),
  },
  {
    label: "Hybrid",
    icon: (
      <svg
        viewBox="0 0 24 24"
        className="h-4 w-4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M4 8h13l-3-3" />
        <path d="M20 16H7l3 3" />
      </svg>
    ),
  },
  {
    label: "Onsite",
    icon: (
      <svg
        viewBox="0 0 24 24"
        className="h-4 w-4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M5 21V5a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v16" />
        <path d="M15 9h3a1 1 0 0 1 1 1v11" />
        <path d="M3 21h18" />
        <path d="M8 8h0M11 8h0M8 12h0M11 12h0M8 16h0M11 16h0" />
      </svg>
    ),
  },
];

function parseSelected(value: string): string[] {
  const seen = new Map<string, string>();

  for (const item of value.split(",")) {
    const cleaned = item.trim();

    if (cleaned) {
      seen.set(cleaned.toLowerCase(), cleaned);
    }
  }

  return Array.from(seen.values());
}

export default function WorkModeSelector({
  value,
  onChange,
  label = "Preferred work modes",
}: WorkModeSelectorProps) {
  const selectedKeys = useMemo(() => {
    return new Set(
      parseSelected(value).map((item) =>
        item.toLowerCase(),
      ),
    );
  }, [value]);

  function toggle(mode: string): void {
    const current = parseSelected(value);
    const key = mode.toLowerCase();

    const next = selectedKeys.has(key)
      ? current.filter(
          (item) => item.toLowerCase() !== key,
        )
      : [...current, mode];

    onChange(next.join(", "));
  }

  return (
    <div className="block">
      <span className="mb-2 block text-sm font-medium text-slate-700">
        {label}
      </span>

      <div className="flex flex-wrap gap-3">
        {WORK_MODES.map((mode) => {
          const active = selectedKeys.has(
            mode.label.toLowerCase(),
          );

          return (
            <button
              key={mode.label}
              type="button"
              aria-pressed={active}
              onClick={() => toggle(mode.label)}
              className={`inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition ${
                active
                  ? "border border-violet-600 bg-violet-600 text-white"
                  : "border border-slate-300 bg-white text-slate-700 hover:border-violet-400 hover:text-violet-700"
              }`}
            >
              {mode.icon}
              {mode.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
