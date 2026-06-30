"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import CVVersionCards from "@/components/cv-versions/CVVersionCards";

import {
  ErrorNotice,
  LoadingState,
  SuccessNotice,
} from "@/components/documents/DocumentPrimitives";

import {
  archiveCVVersion,
  deleteCVVersion,
  getCVVersions,
  isAbortError,
  setPrimaryCVVersion,
} from "@/lib/api";

import type { CVVersion } from "@/types/cvVersion";

export default function CVVersionsPage() {
  const [versions, setVersions] = useState<
    CVVersion[]
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

  const loadVersions = useCallback(async function loadVersions(
    signal?: AbortSignal,
  ): Promise<void> {
    try {
      setErrorMessage("");
      const loadedVersions = await getCVVersions(
        signal,
      );
      setVersions(loadedVersions);
    } catch (error) {
      if (isAbortError(error)) {
        return;
      }

      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to load CV versions.",
      );
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      void loadVersions(controller.signal);
    });

    return () => controller.abort();
  }, [loadVersions]);

  async function runAction(
    actionId: string,
    action: () => Promise<string>,
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
      await loadVersions();
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
    void loadVersions();
  }

  return (
    <main className="min-h-screen bg-slate-950 px-5 py-8 text-white">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <Link
              href="/"
              className="text-sm font-semibold text-blue-300 transition hover:text-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-400"
            >
              Dashboard
            </Link>
            <h1 className="mt-3 text-3xl font-bold sm:text-4xl">
              CV versions
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

        {loading ? (
          <LoadingState label="Loading CV versions..." />
        ) : (
          <CVVersionCards
            versions={versions}
            busyAction={busyAction}
            onSetPrimary={(version) =>
              void runAction(
                `primary-version-${version.id}`,
                async () => {
                  await setPrimaryCVVersion(version.id);
                  return "CV version marked primary.";
                },
              )
            }
            onArchive={(version) => {
              const confirmed = window.confirm(
                `Archive CV version "${version.display_name}"?`,
              );

              if (!confirmed) {
                return;
              }

              void runAction(
                `archive-version-${version.id}`,
                async () => {
                  await archiveCVVersion(version.id);
                  return "CV version archived.";
                },
              );
            }}
            onDelete={(version) => {
              const confirmed = window.confirm(
                `Delete CV version "${version.display_name}"? This cannot be undone.`,
              );

              if (!confirmed) {
                return;
              }

              void runAction(
                `delete-version-${version.id}`,
                async () => {
                  await deleteCVVersion(version.id);
                  return "CV version deleted.";
                },
              );
            }}
          />
        )}
      </div>
    </main>
  );
}
