import Link from "next/link";

import {
  DetailRow,
  EmptyState,
  StatusBadge,
  formatBytes,
  formatDateTime,
  humanizeToken,
  isMasterGenerationParent,
  versionSummaryGrid,
} from "@/components/documents/DocumentPrimitives";

import type { CVVersion } from "@/types/cvVersion";

type CVVersionCardsProps = {
  versions: CVVersion[];
  busyAction: string | null;
  onSetPrimary: (version: CVVersion) => void;
  onArchive: (version: CVVersion) => void;
  onDelete: (version: CVVersion) => void;
  showGenerateLink?: boolean;
  emptyTitle?: string;
};

export default function CVVersionCards({
  versions,
  busyAction,
  onSetPrimary,
  onArchive,
  onDelete,
  showGenerateLink = true,
  emptyTitle = "No CV versions",
}: CVVersionCardsProps) {
  if (versions.length === 0) {
    return <EmptyState title={emptyTitle} />;
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {versions.map((version) => {
        const setPrimaryBusy =
          busyAction === `primary-version-${version.id}`;
        const archiveBusy =
          busyAction === `archive-version-${version.id}`;
        const deleteBusy =
          busyAction === `delete-version-${version.id}`;

        return (
          <article
            key={version.id}
            className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
              <div className="min-w-0">
                <h3 className="break-words text-lg font-semibold text-slate-900">
                  <Link
                    href={`/cv-versions/${version.id}`}
                    className="transition hover:text-violet-700 focus:outline-none focus:ring-2 focus:ring-violet-200"
                  >
                    {version.display_name}
                  </Link>
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  Version #{version.id}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                {version.is_primary ? (
                  <StatusBadge
                    status="ready"
                    label="Primary"
                  />
                ) : null}
                <StatusBadge status={version.status} />
              </div>
            </div>

            {version.description ? (
              <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                {version.description}
              </p>
            ) : null}

            <dl className="mt-5 grid gap-4 sm:grid-cols-2">
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

            <div className="mt-5 flex flex-wrap gap-3">
              <Link
                href={`/cv-versions/${version.id}`}
                className="inline-flex rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-violet-700 transition hover:border-violet-400 hover:bg-violet-50 focus:outline-none focus:ring-2 focus:ring-violet-200"
              >
                Open version
              </Link>

              <button
                type="button"
                disabled={
                  version.is_primary ||
                  version.status === "archived" ||
                  version.status === "failed" ||
                  setPrimaryBusy
                }
                onClick={() => onSetPrimary(version)}
                className="inline-flex rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-violet-400 hover:text-violet-700 focus:outline-none focus:ring-2 focus:ring-violet-200 disabled:cursor-not-allowed disabled:text-slate-400"
              >
                {setPrimaryBusy
                  ? "Setting primary..."
                  : "Mark primary"}
              </button>

              {version.status !== "archived" ? (
                <button
                  type="button"
                  disabled={archiveBusy}
                  onClick={() => onArchive(version)}
                  className="inline-flex rounded-lg border border-amber-300 px-4 py-2 text-sm font-semibold text-amber-700 transition hover:border-amber-400 hover:bg-amber-50 focus:outline-none focus:ring-2 focus:ring-amber-200 disabled:cursor-not-allowed disabled:text-slate-400"
                >
                  {archiveBusy
                    ? "Archiving..."
                    : "Archive"}
                </button>
              ) : null}

              <button
                type="button"
                disabled={deleteBusy}
                onClick={() => onDelete(version)}
                className="inline-flex rounded-lg border border-rose-300 px-4 py-2 text-sm font-semibold text-rose-700 transition hover:border-rose-400 hover:bg-rose-50 focus:outline-none focus:ring-2 focus:ring-rose-200 disabled:cursor-not-allowed disabled:text-slate-400"
              >
                {deleteBusy ? "Deleting..." : "Delete"}
              </button>

              {showGenerateLink &&
              isMasterGenerationParent(version) ? (
                <Link
                  href={`/cv-versions/${version.id}`}
                  className="inline-flex rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-300"
                >
                  Generate master
                </Link>
              ) : null}
            </div>

            <p className="mt-4 text-xs text-slate-500">
              {humanizeToken(version.version_type)}
            </p>
          </article>
        );
      })}
    </div>
  );
}
