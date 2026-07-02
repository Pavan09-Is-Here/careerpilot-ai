"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  deliverNotifications,
  getNotifications,
  isAbortError,
} from "@/lib/api";

import type {
  Notification,
  NotificationCategory,
  NotificationDeliverResult,
  NotificationPage,
  NotificationStatus,
} from "@/types/notification";

const CATEGORY_FILTERS: NotificationCategory[] = [
  "application_prepared",
  "application_submitted",
  "manual_action_required",
  "new_matching_jobs",
];

const STATUS_FILTERS: NotificationStatus[] = [
  "pending",
  "sent",
  "failed",
  "suppressed",
];

function humanize(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "—";
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function categoryClasses(category: string): string {
  switch (category) {
    case "application_submitted":
      return "border-emerald-500/40 text-emerald-300";
    case "application_prepared":
      return "border-blue-500/40 text-blue-300";
    case "manual_action_required":
      return "border-amber-500/40 text-amber-300";
    default:
      return "border-slate-600 text-slate-300";
  }
}

export default function NotificationsPage() {
  const [notificationPage, setNotificationPage] =
    useState<NotificationPage | null>(null);
  const [category, setCategory] = useState<
    NotificationCategory | undefined
  >(undefined);
  const [status, setStatus] = useState<
    NotificationStatus | undefined
  >(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [delivering, setDelivering] = useState(false);
  const [deliverResult, setDeliverResult] =
    useState<NotificationDeliverResult | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);

      try {
        const result = await getNotifications(
          { category, status, limit: 100, offset: 0 },
          signal,
        );
        setNotificationPage(result);
      } catch (loadError) {
        if (isAbortError(loadError)) {
          return;
        }

        setError(
          loadError instanceof Error
            ? loadError.message
            : "Could not load notifications.",
        );
      } finally {
        setLoading(false);
      }
    },
    [category, status],
  );

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      void load(controller.signal);
    });
    return () => controller.abort();
  }, [load]);

  const handleDeliver = useCallback(async () => {
    setDelivering(true);
    setDeliverResult(null);
    setError(null);

    try {
      const result = await deliverNotifications();
      setDeliverResult(result);
      await load();
    } catch (deliverError) {
      setError(
        deliverError instanceof Error
          ? deliverError.message
          : "Could not deliver notifications.",
      );
    } finally {
      setDelivering(false);
    }
  }, [load]);

  const items: Notification[] = notificationPage?.items ?? [];

  return (
    <main className="min-h-screen bg-slate-950 px-5 py-10 text-white">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <Link
              href="/"
              className="text-sm text-blue-300 hover:text-blue-200"
            >
              ← Dashboard
            </Link>

            <h1 className="mt-3 text-3xl font-bold">
              Notifications
            </h1>

            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
              Alerts when applications are prepared and ready to
              submit, when a submission is recorded, and when
              something needs your input. Email delivery runs only
              when SMTP is configured; otherwise messages stay
              pending here.
            </p>
          </div>

          <button
            type="button"
            onClick={handleDeliver}
            disabled={delivering}
            className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold transition hover:bg-blue-500 disabled:opacity-50"
          >
            {delivering ? "Delivering…" : "Deliver pending"}
          </button>
        </header>

        {deliverResult && (
          <div className="mb-6 rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-300">
            Delivery attempt — sent {deliverResult.sent}, failed{" "}
            {deliverResult.failed}, skipped {deliverResult.skipped}.
            {deliverResult.skipped > 0 && (
              <span className="text-slate-400">
                {" "}
                Skipped messages stay pending until SMTP is
                configured.
              </span>
            )}
          </div>
        )}

        <div className="mb-6 flex flex-wrap gap-2">
          <FilterChip
            label="All categories"
            active={category === undefined}
            onClick={() => setCategory(undefined)}
          />
          {CATEGORY_FILTERS.map((value) => (
            <FilterChip
              key={value}
              label={humanize(value)}
              active={category === value}
              onClick={() => setCategory(value)}
            />
          ))}
        </div>

        <div className="mb-8 flex flex-wrap gap-2">
          <FilterChip
            label="Any status"
            active={status === undefined}
            onClick={() => setStatus(undefined)}
          />
          {STATUS_FILTERS.map((value) => (
            <FilterChip
              key={value}
              label={humanize(value)}
              active={status === value}
              onClick={() => setStatus(value)}
            />
          ))}
        </div>

        {error && (
          <div className="mb-6 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-sm text-slate-400">Loading…</p>
        ) : items.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center text-sm text-slate-400">
            No notifications yet.
          </div>
        ) : (
          <ul className="space-y-3">
            {items.map((notification) => (
              <li
                key={notification.id}
                className="rounded-2xl border border-slate-800 bg-slate-900 p-5"
              >
                <div className="flex flex-wrap items-center gap-3">
                  <span
                    className={`rounded-full border px-3 py-1 text-xs font-medium ${categoryClasses(
                      notification.category,
                    )}`}
                  >
                    {humanize(notification.category)}
                  </span>

                  <span className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-400">
                    {humanize(notification.status)}
                  </span>

                  <span className="ml-auto text-xs text-slate-500">
                    {formatDateTime(notification.created_at)}
                  </span>
                </div>

                <h2 className="mt-3 text-base font-semibold text-slate-100">
                  {notification.subject}
                </h2>

                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-300">
                  {notification.body}
                </p>

                <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
                  <span>To: {notification.recipient}</span>
                  {notification.related_job_id && (
                    <Link
                      href={`/jobs/${notification.related_job_id}`}
                      className="text-blue-300 hover:text-blue-200"
                    >
                      View job #{notification.related_job_id}
                    </Link>
                  )}
                  {notification.error && (
                    <span className="text-red-300">
                      {notification.error}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
        active
          ? "border-blue-500 bg-blue-500/10 text-blue-200"
          : "border-slate-700 text-slate-400 hover:border-slate-500"
      }`}
    >
      {label}
    </button>
  );
}
