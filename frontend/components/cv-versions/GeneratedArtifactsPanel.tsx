"use client";

import { useState } from "react";

import { downloadCVArtifact } from "@/lib/api";

import {
  DetailRow,
  EmptyState,
  ErrorNotice,
  StatusBadge,
  artifactLabel,
  formatBytes,
  formatDateTime,
} from "@/components/documents/DocumentPrimitives";

import type {
  CVArtifactType,
  CVVersionArtifact,
} from "@/types/cvVersion";

type GeneratedArtifactsPanelProps = {
  artifacts: CVVersionArtifact[];
};

function fallbackDownloadName(
  artifact: CVVersionArtifact,
): string {
  return (
    artifact.safe_filename ||
    `careerpilot-cv.${artifact.artifact_type}`
  );
}

export default function GeneratedArtifactsPanel({
  artifacts,
}: GeneratedArtifactsPanelProps) {
  const [downloadingId, setDownloadingId] =
    useState<number | null>(null);
  const [errorMessage, setErrorMessage] =
    useState("");

  async function handleDownload(
    artifact: CVVersionArtifact,
  ): Promise<void> {
    if (downloadingId !== null) {
      return;
    }

    try {
      setErrorMessage("");
      setDownloadingId(artifact.id);

      const download = await downloadCVArtifact(
        artifact.id,
      );
      const href = URL.createObjectURL(download.blob);
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.download =
        download.filename ??
        fallbackDownloadName(artifact);
      anchor.rel = "noopener";
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(href);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to download artifact.",
      );
    } finally {
      setDownloadingId(null);
    }
  }

  if (artifacts.length === 0) {
    return (
      <EmptyState title="No generated artifacts">
        Generated DOCX and PDF files appear after a
        verified master CV is ready.
      </EmptyState>
    );
  }

  const artifactsByType = new Map<
    CVArtifactType,
    CVVersionArtifact
  >();

  for (const artifact of artifacts) {
    artifactsByType.set(
      artifact.artifact_type,
      artifact,
    );
  }

  return (
    <div className="space-y-4">
      {errorMessage ? (
        <ErrorNotice>{errorMessage}</ErrorNotice>
      ) : null}

      {(["docx", "pdf"] as CVArtifactType[]).map(
        (artifactType) => {
          const artifact =
            artifactsByType.get(artifactType);

          if (!artifact) {
            return (
              <div
                key={artifactType}
                className="rounded-lg border border-dashed border-slate-700 bg-slate-950 p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-semibold text-slate-100">
                    {artifactType.toUpperCase()}
                  </h3>
                  <StatusBadge
                    status="pending"
                    label="Missing"
                  />
                </div>
              </div>
            );
          }

          return (
            <article
              key={artifact.id}
              className="rounded-lg border border-slate-800 bg-slate-950 p-4"
            >
              <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                <div>
                  <h3 className="font-semibold text-slate-100">
                    {artifactLabel(artifact)}
                  </h3>
                  <p className="mt-1 text-sm text-slate-400">
                    {artifact.mime_type}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    void handleDownload(artifact)
                  }
                  disabled={
                    downloadingId !== null &&
                    downloadingId !== artifact.id
                  }
                  className="inline-flex justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:cursor-not-allowed disabled:bg-slate-700"
                >
                  {downloadingId === artifact.id
                    ? `Downloading ${artifact.artifact_type.toUpperCase()}...`
                    : `Download ${artifact.artifact_type.toUpperCase()}`}
                </button>
              </div>

              <dl className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <DetailRow
                  label="Format"
                  value={artifact.artifact_type.toUpperCase()}
                />
                <DetailRow
                  label="Size"
                  value={formatBytes(artifact.file_size)}
                />
                <DetailRow
                  label="Page count"
                  value={
                    artifact.page_count ?? "Not available"
                  }
                />
                <DetailRow
                  label="Created"
                  value={formatDateTime(
                    artifact.created_at,
                  )}
                />
              </dl>
            </article>
          );
        },
      )}
    </div>
  );
}
