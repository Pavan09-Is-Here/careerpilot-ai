"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import DocumentList from "@/components/documents/DocumentList";
import DocumentUploadForm from "@/components/documents/DocumentUploadForm";

import {
  ErrorNotice,
  LoadingState,
  SuccessNotice,
} from "@/components/documents/DocumentPrimitives";

import {
  getDocuments,
  isAbortError,
} from "@/lib/api";

import type {
  CVDocument,
  CVDocumentListItem,
} from "@/types/document";

export default function DocumentManagementPage() {
  const [documents, setDocuments] = useState<
    CVDocumentListItem[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] =
    useState("");
  const [successMessage, setSuccessMessage] =
    useState("");

  const loadDocuments = useCallback(async function loadDocuments(
    signal?: AbortSignal,
  ): Promise<void> {
    try {
      setErrorMessage("");
      const items = await getDocuments(signal);
      setDocuments(items);
    } catch (error) {
      if (isAbortError(error)) {
        return;
      }

      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to load documents.",
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
      void loadDocuments(controller.signal);
    });

    return () => controller.abort();
  }, [loadDocuments]);

  async function handleRefresh(): Promise<void> {
    setRefreshing(true);
    setSuccessMessage("");
    await loadDocuments();
  }

  function handleUploaded(
    uploadedDocument: CVDocument,
  ): void {
    setSuccessMessage(
      `${uploadedDocument.original_filename} uploaded.`,
    );
    setDocuments((currentDocuments) => [
      uploadedDocument,
      ...currentDocuments.filter(
        (document) =>
          document.id !== uploadedDocument.id,
      ),
    ]);
    void loadDocuments();
  }

  return (
    <main className="cp-page">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <Link
              href="/"
              className="text-sm font-semibold text-violet-600 transition hover:text-violet-700 focus:outline-none focus:ring-2 focus:ring-violet-300"
            >
              Dashboard
            </Link>
            <h1 className="mt-3 text-3xl font-bold text-slate-900 sm:text-4xl">
              Documents
            </h1>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <Link
              href="/cv-versions"
              className="inline-flex justify-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-violet-700 transition hover:border-violet-400 hover:bg-violet-50 focus:outline-none focus:ring-2 focus:ring-violet-300"
            >
              CV versions
            </Link>
            <button
              type="button"
              onClick={handleRefresh}
              disabled={refreshing}
              className="inline-flex justify-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-violet-400 hover:text-violet-700 focus:outline-none focus:ring-2 focus:ring-slate-300 disabled:cursor-not-allowed disabled:text-slate-400"
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

        <div className="grid gap-6 xl:grid-cols-[minmax(320px,420px)_1fr]">
          <DocumentUploadForm
            onUploaded={handleUploaded}
          />

          <section>
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="text-xl font-semibold text-slate-900">
                Uploaded documents
              </h2>
              <span className="text-sm text-slate-500">
                {documents.length} total
              </span>
            </div>

            {loading ? (
              <LoadingState label="Loading documents..." />
            ) : (
              <DocumentList documents={documents} />
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
