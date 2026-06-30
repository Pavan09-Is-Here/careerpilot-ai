import type { ReactNode } from "react";

import type {
  CVDocument,
  CVDocumentListItem,
  CVSection,
  FactComparisonFinding,
  FactComparisonRun,
} from "@/types/document";

import type {
  CVVersion,
  CVVersionArtifact,
} from "@/types/cvVersion";

export const supportedDocumentMimes = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

export const supportedDocumentExtensions = [
  ".pdf",
  ".docx",
];

const terminalStatuses = new Set([
  "completed",
  "failed",
  "no_text",
  "partial",
  "ready",
  "archived",
]);

export function isTerminalStatus(status: string): boolean {
  return terminalStatuses.has(status);
}

export function isSupportedDocumentFile(
  file: File,
): string | null {
  const lowerName = file.name.toLowerCase();
  const hasSupportedExtension =
    supportedDocumentExtensions.some((extension) =>
      lowerName.endsWith(extension),
    );

  if (!hasSupportedExtension) {
    return "Choose a PDF or DOCX file.";
  }

  if (
    file.type &&
    !supportedDocumentMimes.includes(file.type)
  ) {
    return "The selected file type does not match PDF or DOCX.";
  }

  return null;
}

export function formatBytes(
  value: number | null | undefined,
): string {
  if (value === null || value === undefined) {
    return "Not available";
  }

  if (value < 1024) {
    return `${value} B`;
  }

  const units = ["KB", "MB", "GB"];
  let size = value / 1024;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  return `${size.toFixed(size >= 10 ? 1 : 2)} ${units[unitIndex]}`;
}

export function formatDateTime(
  value: string | null | undefined,
): string {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Not available";
  }

  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function humanizeToken(
  value: string | null | undefined,
): string {
  if (!value) {
    return "Not available";
  }

  return value
    .split("_")
    .map((part) =>
      part
        ? `${part[0].toUpperCase()}${part.slice(1)}`
        : part,
    )
    .join(" ");
}

export function confidenceLabel(
  value: number,
): string {
  return `${Math.round(value * 100)}%`;
}

export function canRunExtraction(
  document: CVDocument | CVDocumentListItem,
): boolean {
  return (
    document.upload_status === "validated" &&
    document.extraction_status !== "processing"
  );
}

export function canRunSectionDetection(
  document: CVDocument | CVDocumentListItem,
): boolean {
  return (
    document.extraction_status === "completed" &&
    document.section_detection_status !== "processing"
  );
}

export function canRunFactComparison(
  document: CVDocument | CVDocumentListItem,
): boolean {
  return (
    document.upload_status === "validated" &&
    document.extraction_status === "completed" &&
    document.section_detection_status === "completed" &&
    document.section_count > 0
  );
}

export function canAdoptDocument(
  document: CVDocument | CVDocumentListItem,
): boolean {
  return (
    document.document_type === "original_cv" &&
    document.upload_status === "validated"
  );
}

export function isMasterGenerationParent(
  version: CVVersion,
): boolean {
  return (
    version.status === "ready" &&
    (version.version_type === "parsed" ||
      version.version_type === "verified_master")
  );
}

export function sortSections(
  sections: CVSection[],
): CVSection[] {
  return [...sections].sort(
    (left, right) =>
      left.section_order - right.section_order ||
      left.start_char - right.start_char ||
      left.id - right.id,
  );
}

export function comparisonStatusText(
  comparison: FactComparisonRun | null,
): string {
  if (!comparison) {
    return "No comparison yet";
  }

  return humanizeToken(comparison.status);
}

export function findingLabel(
  finding: FactComparisonFinding,
): string {
  if (finding.requires_manual_review) {
    return "Manual review";
  }

  return humanizeToken(finding.finding_type);
}

function statusClasses(status: string): string {
  if (
    status === "completed" ||
    status === "ready" ||
    status === "validated" ||
    status === "confirmed"
  ) {
    return "border-emerald-400/40 bg-emerald-500/10 text-emerald-200";
  }

  if (
    status === "processing" ||
    status === "pending" ||
    status === "draft" ||
    status === "partial"
  ) {
    return "border-sky-400/40 bg-sky-500/10 text-sky-200";
  }

  if (
    status === "failed" ||
    status === "rejected" ||
    status === "processing_failed" ||
    status.includes("conflict") ||
    status.includes("mismatch")
  ) {
    return "border-rose-400/40 bg-rose-500/10 text-rose-200";
  }

  if (
    status === "archived" ||
    status === "manual_review" ||
    status === "review" ||
    status === "warning" ||
    status === "unverified_claim" ||
    status === "missing_verified_fact"
  ) {
    return "border-amber-400/40 bg-amber-500/10 text-amber-100";
  }

  return "border-slate-500/40 bg-slate-800 text-slate-200";
}

export function StatusBadge({
  status,
  label,
}: {
  status: string;
  label?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-semibold ${statusClasses(
        status,
      )}`}
    >
      {label ?? humanizeToken(status)}
    </span>
  );
}

export function ErrorNotice({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-rose-500/40 bg-rose-950/40 px-4 py-3 text-sm text-rose-100"
    >
      {children}
    </div>
  );
}

export function SuccessNotice({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="rounded-lg border border-emerald-500/40 bg-emerald-950/40 px-4 py-3 text-sm text-emerald-100"
    >
      {children}
    </div>
  );
}

export function EmptyState({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/60 px-5 py-8 text-center">
      <p className="font-semibold text-slate-100">
        {title}
      </p>
      {children ? (
        <div className="mt-2 text-sm leading-6 text-slate-400">
          {children}
        </div>
      ) : null}
    </div>
  );
}

export function LoadingState({
  label,
}: {
  label: string;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="rounded-lg border border-slate-800 bg-slate-900 px-5 py-6 text-sm text-slate-300"
    >
      {label}
    </div>
  );
}

export function DetailRow({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase text-slate-500">
        {label}
      </dt>
      <dd className="mt-1 text-sm text-slate-200">
        {value}
      </dd>
    </div>
  );
}

export function SectionPanel({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-5">
      <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <h2 className="text-lg font-semibold text-white">
          {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function documentSummaryGrid(
  document: CVDocument | CVDocumentListItem,
): Array<[string, ReactNode]> {
  return [
    ["File type", document.file_extension.toUpperCase()],
    ["Size", formatBytes(document.size_bytes)],
    ["Uploaded", formatDateTime(document.created_at)],
    ["Document type", humanizeToken(document.document_type)],
    [
      "Extraction",
      <StatusBadge
        key="extraction"
        status={document.extraction_status}
      />,
    ],
    [
      "Sections",
      `${document.section_count} detected`,
    ],
  ];
}

export function versionSummaryGrid(
  version: CVVersion,
): Array<[string, ReactNode]> {
  return [
    ["Type", humanizeToken(version.version_type)],
    [
      "Status",
      <StatusBadge key="status" status={version.status} />,
    ],
    ["Primary", version.is_primary ? "Yes" : "No"],
    [
      "Parent",
      version.parent_version_id
        ? `#${version.parent_version_id}`
        : "None",
    ],
    [
      "Source document",
      version.source_document_id
        ? `#${version.source_document_id}`
        : "None",
    ],
    ["Created", formatDateTime(version.created_at)],
    ["Updated", formatDateTime(version.updated_at)],
    ["Archived", formatDateTime(version.archived_at)],
  ];
}

export function artifactLabel(
  artifact: CVVersionArtifact,
): string {
  return artifact.artifact_type.toUpperCase();
}
