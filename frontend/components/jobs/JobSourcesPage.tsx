"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  connectGreenhouseBoard,
  connectJobSourceProvider,
  getJobSources,
  ingestJobSource,
  isAbortError,
} from "@/lib/api";

import type {
  ConnectableProviderType,
  JobSource,
} from "@/types/job";

type ProviderChoice = "greenhouse" | ConnectableProviderType;

type ProviderOption = {
  id: ProviderChoice;
  label: string;
  description: string;
  needsBoard: boolean;
  boardHint?: string;
  boardPlaceholder?: string;
  needsCountry?: boolean;
  needsLocation?: boolean;
  needsQuery?: boolean;
  fixedDisplayName?: string;
};

const PROVIDER_OPTIONS: ProviderOption[] = [
  {
    id: "greenhouse",
    label: "Greenhouse — company board",
    description:
      "The board name from boards.greenhouse.io/<name>.",
    needsBoard: true,
    boardHint: "The slug from boards.greenhouse.io/<name>",
    boardPlaceholder: "stripe",
  },
  {
    id: "lever",
    label: "Lever — company board",
    description: "The board name from jobs.lever.co/<name>.",
    needsBoard: true,
    boardHint: "The slug from jobs.lever.co/<name>",
    boardPlaceholder: "netflix",
  },
  {
    id: "ashby",
    label: "Ashby — company board",
    description: "The board name from jobs.ashbyhq.com/<name>.",
    needsBoard: true,
    boardHint: "The name from jobs.ashbyhq.com/<name>",
    boardPlaceholder: "openai",
  },
  {
    id: "remotive",
    label: "Remotive — remote jobs feed",
    description:
      "One connection streams all active remote listings.",
    needsBoard: false,
    fixedDisplayName: "Remotive",
  },
  {
    id: "arbeitnow",
    label: "Arbeitnow — remote jobs feed",
    description:
      "Free remote/European jobs feed — no setup needed.",
    needsBoard: false,
    fixedDisplayName: "Arbeitnow",
  },
  {
    id: "adzuna",
    label: "Adzuna — aggregator (server key required)",
    description:
      "Broad aggregator across 19 countries. Requires the free "
      + "Adzuna keys in the server environment.",
    needsBoard: false,
    needsCountry: true,
    needsQuery: true,
  },
  {
    id: "reed",
    label: "Reed — UK aggregator (server key required)",
    description:
      "Strong UK coverage. Requires the free Reed key in the "
      + "server environment.",
    needsBoard: false,
    needsLocation: true,
    needsQuery: true,
  },
];

function boardApiToBoardUrl(baseUrl: string | null): string | null {
  if (!baseUrl) {
    return null;
  }
  const marker = "/v1/boards/";
  const index = baseUrl.indexOf(marker);
  if (index === -1) {
    return baseUrl;
  }
  const token = baseUrl.slice(index + marker.length);
  return `https://boards.greenhouse.io/${token}`;
}

function StatusChip({ source }: { source: JobSource }) {
  const approved =
    source.enabled &&
    source.allowlisted &&
    source.server_fetch_allowed;
  const label = approved ? "Ready to ingest" : "Not ready";
  const tone = approved
    ? "bg-emerald-50 text-emerald-700"
    : "bg-amber-50 text-amber-700";

  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${tone}`}
    >
      {label}
    </span>
  );
}

export default function JobSourcesPage() {
  const [sources, setSources] = useState<JobSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(
    null,
  );

  const [provider, setProvider] =
    useState<ProviderChoice>("greenhouse");
  const [boardToken, setBoardToken] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [country, setCountry] = useState("gb");
  const [searchQuery, setSearchQuery] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<
    string | null
  >(null);
  const [connectNotice, setConnectNotice] = useState<
    string | null
  >(null);

  const [ingestingId, setIngestingId] = useState<
    number | null
  >(null);
  const [ingestNotices, setIngestNotices] = useState<
    Record<number, string>
  >({});
  const [ingestErrors, setIngestErrors] = useState<
    Record<number, string>
  >({});

  const loadSources = useCallback((signal?: AbortSignal) => {
    setLoading(true);
    setListError(null);

    getJobSources(1, 100, signal)
      .then((result) => {
        setSources(result.items);
        setLoading(false);
      })
      .catch((requestError: unknown) => {
        if (isAbortError(requestError)) {
          return;
        }
        setListError(
          requestError instanceof Error
            ? requestError.message
            : "Failed to load connected boards.",
        );
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      loadSources(controller.signal);
    });
    return () => controller.abort();
  }, [loadSources]);

  const providerOption =
    PROVIDER_OPTIONS.find((option) => option.id === provider) ??
    PROVIDER_OPTIONS[0];

  const effectiveDisplayName = (
    providerOption.fixedDisplayName ?? displayName
  ).trim();

  const handleConnect = (event: React.FormEvent) => {
    event.preventDefault();
    setConnecting(true);
    setConnectError(null);
    setConnectNotice(null);

    const request =
      provider === "greenhouse"
        ? connectGreenhouseBoard({
            board_token: boardToken.trim(),
            display_name: effectiveDisplayName,
          })
        : connectJobSourceProvider({
            provider_type: provider,
            display_name: effectiveDisplayName,
            ...(providerOption.needsBoard
              ? { board_token: boardToken.trim() }
              : {}),
            ...(providerOption.needsCountry
              ? { country: country.trim() }
              : {}),
            ...(providerOption.needsLocation && country.trim()
              ? { country: country.trim() }
              : {}),
            ...(providerOption.needsQuery && searchQuery.trim()
              ? { search_query: searchQuery.trim() }
              : {}),
          });

    request
      .then((source) => {
        setConnectNotice(
          `Connected ${source.display_name}. Ingest its latest jobs below.`,
        );
        setBoardToken("");
        setDisplayName("");
        setSearchQuery("");
        loadSources();
      })
      .catch((requestError: unknown) => {
        setConnectError(
          requestError instanceof Error
            ? requestError.message
            : "Failed to connect the job source.",
        );
      })
      .finally(() => setConnecting(false));
  };

  const handleIngest = (sourceId: number) => {
    setIngestingId(sourceId);
    setIngestErrors((previous) => {
      const next = { ...previous };
      delete next[sourceId];
      return next;
    });
    setIngestNotices((previous) => {
      const next = { ...previous };
      delete next[sourceId];
      return next;
    });

    ingestJobSource(sourceId)
      .then((run) => {
        if (run.run_status === "succeeded") {
          const count = run.jobs_discovered + run.jobs_updated;
          setIngestNotices((previous) => ({
            ...previous,
            [sourceId]:
              count === 0
                ? "No new jobs were found. The board is up to date."
                : `Ingested ${count} job${count === 1 ? "" : "s"}. View them in Job discovery.`,
          }));
        } else {
          setIngestErrors((previous) => ({
            ...previous,
            [sourceId]:
              run.failure_summary ??
              "The ingest run did not complete.",
          }));
        }
      })
      .catch((requestError: unknown) => {
        setIngestErrors((previous) => ({
          ...previous,
          [sourceId]:
            requestError instanceof Error
              ? requestError.message
              : "Failed to ingest jobs.",
        }));
      })
      .finally(() => setIngestingId(null));
  };

  return (
    <main className="cp-page">
      <div className="mx-auto max-w-4xl">
        <Link
          href="/"
          className="text-sm font-medium text-violet-600 transition hover:text-violet-700"
        >
          ← Back to dashboard
        </Link>
        <header className="mt-4 mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="cp-eyebrow">Job discovery</p>
            <h1 className="mt-3 text-3xl font-bold text-slate-900">
              Connect job sources
            </h1>
            <p className="mt-3 max-w-2xl leading-7 cp-muted">
              Point CareerPilot at free public job sources — company
              boards on Greenhouse, Lever, or Ashby, remote-job feeds,
              and aggregators — and their latest roles flow into job
              discovery. Every source is compliance-gated and read
              through official public APIs only.
            </p>
          </div>
          <Link href="/jobs" className="cp-btn-outline shrink-0">
            View jobs
          </Link>
        </header>

        <section className="cp-card">
          <h2 className="text-xl font-semibold text-slate-900">
            Connect a job source
          </h2>
          <p className="mt-2 text-sm leading-6 cp-muted">
            {providerOption.description}
          </p>

          <form
            onSubmit={handleConnect}
            className="mt-5 grid gap-4 sm:grid-cols-2"
          >
            <label className="flex flex-col gap-1 text-sm text-slate-700 sm:col-span-2">
              Source
              <select
                className="cp-input"
                value={provider}
                onChange={(event) => {
                  const next = event.target
                    .value as ProviderChoice;
                  setProvider(next);
                  setBoardToken("");
                  setCountry(next === "adzuna" ? "gb" : "");
                  setSearchQuery("");
                  setConnectError(null);
                  setConnectNotice(null);
                }}
              >
                {PROVIDER_OPTIONS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            {providerOption.needsBoard ? (
              <label className="flex flex-col gap-1 text-sm text-slate-700">
                Board name
                <input
                  className="cp-input"
                  value={boardToken}
                  onChange={(event) =>
                    setBoardToken(event.target.value)
                  }
                  placeholder={providerOption.boardPlaceholder}
                  autoComplete="off"
                  required
                />
                <span className="text-xs cp-muted">
                  {providerOption.boardHint}
                </span>
              </label>
            ) : null}

            {providerOption.needsCountry ? (
              <label className="flex flex-col gap-1 text-sm text-slate-700">
                Country code
                <input
                  className="cp-input"
                  value={country}
                  onChange={(event) =>
                    setCountry(event.target.value)
                  }
                  placeholder="gb"
                  autoComplete="off"
                  required
                />
                <span className="text-xs cp-muted">
                  Two-letter Adzuna country, e.g. gb or us.
                </span>
              </label>
            ) : null}

            {providerOption.needsLocation ? (
              <label className="flex flex-col gap-1 text-sm text-slate-700">
                Location (optional)
                <input
                  className="cp-input"
                  value={country}
                  onChange={(event) =>
                    setCountry(event.target.value)
                  }
                  placeholder="London"
                  autoComplete="off"
                />
                <span className="text-xs cp-muted">
                  Narrow Reed results to a place.
                </span>
              </label>
            ) : null}

            {providerOption.needsQuery ? (
              <label className="flex flex-col gap-1 text-sm text-slate-700">
                Search terms (optional)
                <input
                  className="cp-input"
                  value={searchQuery}
                  onChange={(event) =>
                    setSearchQuery(event.target.value)
                  }
                  placeholder="platform engineer"
                  autoComplete="off"
                />
                <span className="text-xs cp-muted">
                  Narrow this source to your target role.
                </span>
              </label>
            ) : null}

            {providerOption.fixedDisplayName ? null : (
              <label className="flex flex-col gap-1 text-sm text-slate-700">
                Display name
                <input
                  className="cp-input"
                  value={displayName}
                  onChange={(event) =>
                    setDisplayName(event.target.value)
                  }
                  placeholder={
                    providerOption.needsBoard
                      ? "Stripe"
                      : "Adzuna UK — platform roles"
                  }
                  autoComplete="off"
                  required
                />
                <span className="text-xs cp-muted">
                  How this source is shown in your job list.
                </span>
              </label>
            )}

            <div className="sm:col-span-2">
              <button
                type="submit"
                className="cp-btn-primary"
                disabled={
                  connecting ||
                  (providerOption.needsBoard &&
                    !boardToken.trim()) ||
                  (providerOption.needsCountry &&
                    !country.trim()) ||
                  !effectiveDisplayName
                }
              >
                {connecting ? "Connecting…" : "Connect"}
              </button>
            </div>
          </form>

          {connectNotice ? (
            <p
              role="status"
              className="mt-4 rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700"
            >
              {connectNotice}
            </p>
          ) : null}

          {connectError ? (
            <p
              role="alert"
              className="mt-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700"
            >
              {connectError}
            </p>
          ) : null}
        </section>

        <section className="mt-8" aria-label="Connected boards">
          <h2 className="text-xl font-semibold text-slate-900">
            Connected boards
          </h2>

          {listError ? (
            <p
              role="alert"
              className="mt-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700"
            >
              {listError}
            </p>
          ) : loading ? (
            <p className="mt-4 text-sm cp-muted">
              Loading connected boards…
            </p>
          ) : sources.length === 0 ? (
            <div className="mt-4 cp-card border-dashed text-center">
              <p className="text-sm cp-muted">
                No boards connected yet. Connect a company&apos;s
                public Greenhouse board above to load its latest
                roles.
              </p>
            </div>
          ) : (
            <ul className="mt-4 grid gap-4">
              {sources.map((source) => {
                const boardUrl = boardApiToBoardUrl(
                  source.base_url,
                );
                return (
                  <li key={source.id} className="cp-card">
                    <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-lg font-semibold text-slate-900">
                            {source.display_name}
                          </h3>
                          <StatusChip source={source} />
                        </div>
                        {boardUrl ? (
                          <a
                            href={boardUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-1 block break-all text-sm text-violet-700 hover:underline"
                          >
                            {boardUrl}
                          </a>
                        ) : null}
                        <p className="mt-1 text-xs cp-muted">
                          {source.provider_type} ·{" "}
                          {source.source_category}
                        </p>
                      </div>
                      <div className="flex shrink-0 flex-col items-start gap-2 sm:items-end">
                        <button
                          type="button"
                          className="cp-btn-primary"
                          disabled={ingestingId === source.id}
                          onClick={() =>
                            handleIngest(source.id)
                          }
                        >
                          {ingestingId === source.id
                            ? "Ingesting…"
                            : "Ingest latest jobs"}
                        </button>
                        <Link
                          href={`/jobs?source=${source.id}`}
                          className="text-sm text-violet-700 hover:underline"
                        >
                          View jobs
                        </Link>
                      </div>
                    </div>

                    {ingestNotices[source.id] ? (
                      <p
                        role="status"
                        className="mt-3 rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700"
                      >
                        {ingestNotices[source.id]}
                      </p>
                    ) : null}

                    {ingestErrors[source.id] ? (
                      <p
                        role="alert"
                        className="mt-3 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700"
                      >
                        {ingestErrors[source.id]}
                      </p>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
