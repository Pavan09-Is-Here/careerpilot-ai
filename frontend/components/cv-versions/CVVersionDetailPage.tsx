"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import GeneratedArtifactsPanel from "@/components/cv-versions/GeneratedArtifactsPanel";
import MasterGenerationPanel from "@/components/cv-versions/MasterGenerationPanel";

import {
  DetailRow,
  EmptyState,
  ErrorNotice,
  LoadingState,
  SectionPanel,
  SuccessNotice,
  formatBytes,
  formatDateTime,
  humanizeToken,
  isMasterGenerationParent,
  versionSummaryGrid,
} from "@/components/documents/DocumentPrimitives";

import {
  archiveCVVersion,
  deleteCVVersion,
  getCVVersion,
  getCVVersionArtifacts,
  getCVVersionHistory,
  isAbortError,
  setPrimaryCVVersion,
} from "@/lib/api";

import type {
  CVMasterGenerationResponse,
  CVVersion,
  CVVersionArtifact,
  CVVersionHistory,
} from "@/types/cvVersion";

type CVVersionDetailPageProps = {
  versionId: number;
};

function VersionLink({
  version,
}: {
  version: CVVersion;
}) {
  return (
    <Link
      href={`/cv-versions/${version.id}`}
      className="rounded-lg border border-slate-800 bg-slate-950 px-4 py-3 transition hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
    >
      <span className="block font-semibold text-slate-100">
        {version.display_name}
      </span>
      <span className="mt-1 block text-sm text-slate-400">
        #{version.id} / {humanizeToken(version.version_type)} /{" "}
        {humanizeToken(version.status)}
      </span>
    </Link>
  );
}

export default function CVVersionDetailPage({
  versionId,
}: CVVersionDetailPageProps) {
  const router = useRouter();
  const [version, setVersion] =
    useState<CVVersion | null>(null);
  const [history, setHistory] =
    useState<CVVersionHistory | null>(null);
  const [artifacts, setArtifacts] = useState<
    CVVersionArtifact[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] =
    useState(false);
  const [busyAction, setBusyAction] = useState<
    string | null
  >(null);
  const [errorMessage, setErrorMessage] =
    useState("");
  const [successMessage, setSuccessMessage] =
    useState("");

  const loadVersion = useCallback(async function loadVersion(
    signal?: AbortSignal,
  ): Promise<void> {
    if (
      !Number.isInteger(versionId) ||
      versionId <= 0
    ) {
      setErrorMessage("Invalid CV version id.");
      setLoading(false);
      return;
    }

    try {
      setErrorMessage("");
      const [
        loadedVersion,
        loadedHistory,
        loadedArtifacts,
      ] = await Promise.all([
        getCVVersion(versionId, signal),
        getCVVersionHistory(versionId, signal),
        getCVVersionArtifacts(versionId, signal),
      ]);

      setVersion(loadedVersion);
      setHistory(loadedHistory);
      setArtifacts(loadedArtifacts);
    } catch (error) {
      if (isAbortError(error)) {
        return;
      }

      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to load CV version.",
      );
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [versionId]);

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      void loadVersion(controller.signal);
    });

    return () => controller.abort();
  }, [loadVersion]);

  async function runAction(
    actionId: string,
    action: () => Promise<string>,
    options: { reload?: boolean } = {},
  ): Promise<void> {
    if (busyAction !== null) {
      return;
    }

    try {
      setBusyAction(actionId);
      setErrorMessage("");
      setSuccessMessage("");

      const message = await action();
      setSuccessMessage(message);

      if (options.reload !== false) {
        await loadVersion();
      }
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Action failed.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  function refresh(): void {
    setRefreshing(true);
    void loadVersion();
  }

  function handleGenerated(
    response: CVMasterGenerationResponse,
  ): void {
    setVersion(response.version);
    setArtifacts(response.artifacts);
    setSuccessMessage(
      response.created
        ? "Verified master CV is ready."
        : "Existing verified master CV loaded.",
    );
    void loadVersion();
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 px-5 py-8 text-white">
        <div className="mx-auto max-w-7xl">
          <LoadingState label="Loading CV version..." />
        </div>
      </main>
    );
  }

  if (!version) {
    return (
      <main className="min-h-screen bg-slate-950 px-5 py-8 text-white">
        <div className="mx-auto max-w-7xl space-y-5">
          <Link
            href="/cv-versions"
            className="text-sm font-semibold text-blue-300 transition hover:text-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            CV versions
          </Link>
          {errorMessage ? (
            <ErrorNotice>{errorMessage}</ErrorNotice>
          ) : (
            <EmptyState title="CV version not found" />
          )}
        </div>
      </main>
    );
  }

  const children = history?.children ?? [];
  const ancestry = history?.ancestry ?? [version];
  const canDelete = children.length === 0;

  return (
    <main className="min-h-screen bg-slate-950 px-5 py-8 text-white">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <Link
              href="/cv-versions"
              className="text-sm font-semibold text-blue-300 transition hover:text-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-400"
            >
              CV versions
            </Link>
            <h1 className="mt-3 break-words text-3xl font-bold sm:text-4xl">
              {version.display_name}
            </h1>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <Link
              href="/documents"
              className="inline-flex justify-center rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-blue-200 transition hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
            >
              Documents
            </Link>
            <button
              type="button"
              onClick={refresh}
              disabled={refreshing}
              className="inline-flex justify-center rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:cursor-not-allowed disabled:text-slate-500"
            >
              {refreshing ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </header>

        <div
          className="mb-6 space-y-3"
          aria-live="polite"
        >
          {errorMessage ? (
            <ErrorNotice>{errorMessage}</ErrorNotice>
          ) : null}
          {successMessage ? (
            <SuccessNotice>
              {successMessage}
            </SuccessNotice>
          ) : null}
        </div>

        <div className="space-y-6">
          <SectionPanel title="Version metadata">
            <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {versionSummaryGrid(version).map(
                ([label, value]) => (
                  <DetailRow
                    key={label}
                    label={label}
                    value={value}
                  />
                ),
              )}
              <DetailRow
                label="MIME type"
                value={
                  version.mime_type ?? "Not available"
                }
              />
              <DetailRow
                label="File size"
                value={formatBytes(version.file_size)}
              />
              <DetailRow
                label="Generated"
                value={formatDateTime(
                  version.generated_at,
                )}
              />
              <DetailRow
                label="Generation version"
                value={
                  version.generation_version ??
                  "Not available"
                }
              />
            </dl>

            {version.description ? (
              <p className="mt-5 whitespace-pre-wrap text-sm leading-6 text-slate-300">
                {version.description}
              </p>
            ) : null}
          </SectionPanel>

          <SectionPanel title="Version ancestry">
            <div className="grid gap-3 md:grid-cols-2">
              {ancestry.map((item) => (
                <VersionLink
                  key={item.id}
                  version={item}
                />
              ))}
            </div>
          </SectionPanel>

          <SectionPanel title="Child versions">
            {children.length === 0 ? (
              <EmptyState title="No child versions" />
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {children.map((child) => (
                  <VersionLink
                    key={child.id}
                    version={child}
                  />
                ))}
              </div>
            )}
          </SectionPanel>

          {isMasterGenerationParent(version) ? (
            <MasterGenerationPanel
              parentVersion={version}
              onGenerated={handleGenerated}
            />
          ) : null}

          <SectionPanel title="Generated artifacts">
            <GeneratedArtifactsPanel
              artifacts={artifacts}
            />
          </SectionPanel>

          <SectionPanel title="Available actions">
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                disabled={
                  version.is_primary ||
                  version.status === "archived" ||
                  version.status === "failed" ||
                  busyAction !== null
                }
                onClick={() =>
                  void runAction(
                    "primary-version",
                    async () => {
                      await setPrimaryCVVersion(
                        version.id,
                      );
                      return "CV version marked primary.";
                    },
                  )
                }
                className="inline-flex rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:cursor-not-allowed disabled:text-slate-500"
              >
                {busyAction === "primary-version"
                  ? "Setting primary..."
                  : "Mark primary"}
              </button>

              {version.status !== "archived" ? (
                <button
                  type="button"
                  disabled={busyAction !== null}
                  onClick={() => {
                    const confirmed = window.confirm(
                      `Archive CV version "${version.display_name}"?`,
                    );

                    if (!confirmed) {
                      return;
                    }

                    void runAction(
                      "archive-version",
                      async () => {
                        await archiveCVVersion(
                          version.id,
                        );
                        return "CV version archived.";
                      },
                    );
                  }}
                  className="inline-flex rounded-lg border border-amber-500/60 px-4 py-2 text-sm font-semibold text-amber-100 transition hover:border-amber-300 focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:cursor-not-allowed disabled:text-slate-500"
                >
                  {busyAction === "archive-version"
                    ? "Archiving..."
                    : "Archive"}
                </button>
              ) : null}

              <button
                type="button"
                disabled={
                  busyAction !== null || !canDelete
                }
                onClick={() => {
                  const confirmed = window.confirm(
                    `Delete CV version "${version.display_name}"? This cannot be undone.`,
                  );

                  if (!confirmed) {
                    return;
                  }

                  void runAction(
                    "delete-version",
                    async () => {
                      await deleteCVVersion(version.id);
                      router.push("/cv-versions");
                      return "CV version deleted.";
                    },
                    { reload: false },
                  );
                }}
                className="inline-flex rounded-lg border border-rose-500/60 px-4 py-2 text-sm font-semibold text-rose-100 transition hover:border-rose-300 focus:outline-none focus:ring-2 focus:ring-rose-300 disabled:cursor-not-allowed disabled:text-slate-500"
              >
                {busyAction === "delete-version"
                  ? "Deleting..."
                  : "Delete"}
              </button>
            </div>

            {!canDelete ? (
              <p className="mt-4 text-sm text-amber-100">
                Versions with child history must remain
                available.
              </p>
            ) : null}
          </SectionPanel>
        </div>
      </div>
    </main>
  );
}
