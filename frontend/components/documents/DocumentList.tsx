import Link from "next/link";

import {
  DetailRow,
  EmptyState,
  StatusBadge,
  documentSummaryGrid,
  formatDateTime,
  humanizeToken,
} from "@/components/documents/DocumentPrimitives";

import type { CVDocumentListItem } from "@/types/document";

type DocumentListProps = {
  documents: CVDocumentListItem[];
};

export default function DocumentList({
  documents,
}: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <EmptyState title="No documents uploaded">
        Upload a PDF or DOCX CV to begin processing.
      </EmptyState>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {documents.map((document) => (
        <article
          key={document.id}
          className="rounded-lg border border-slate-800 bg-slate-900 p-5"
        >
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
            <div className="min-w-0">
              <h2 className="break-words text-lg font-semibold text-white">
                <Link
                  href={`/documents/${document.id}`}
                  className="transition hover:text-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-400"
                >
                  {document.original_filename}
                </Link>
              </h2>
              <p className="mt-1 text-sm text-slate-400">
                Uploaded {formatDateTime(document.created_at)}
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              {document.is_primary ? (
                <StatusBadge status="ready" label="Primary" />
              ) : null}
              <StatusBadge
                status={document.upload_status}
              />
            </div>
          </div>

          <dl className="mt-5 grid gap-4 sm:grid-cols-2">
            {documentSummaryGrid(document).map(
              ([label, value]) => (
                <DetailRow
                  key={label}
                  label={label}
                  value={value}
                />
              ),
            )}
            <DetailRow
              label="Section detection"
              value={
                <StatusBadge
                  status={
                    document.section_detection_status
                  }
                />
              }
            />
            <DetailRow
              label="Fact comparison"
              value={
                document.fact_comparison_summary ? (
                  `${humanizeToken(
                    document.fact_comparison_summary.status,
                  )}: ${
                    document.fact_comparison_summary
                      .total_findings
                  } findings`
                ) : (
                  "Open detail"
                )
              }
            />
          </dl>

          <div className="mt-5">
            <Link
              href={`/documents/${document.id}`}
              className="inline-flex rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-blue-200 transition hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
            >
              Open document
            </Link>
          </div>
        </article>
      ))}
    </div>
  );
}
