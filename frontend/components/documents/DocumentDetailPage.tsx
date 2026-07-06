"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import CVVersionCards from "@/components/cv-versions/CVVersionCards";
import CVAutofillPanel from "@/components/documents/CVAutofillPanel";

import {
  DetailRow,
  EmptyState,
  ErrorNotice,
  LoadingState,
  SectionPanel,
  StatusBadge,
  SuccessNotice,
  canAdoptDocument,
  canRunExtraction,
  canRunFactComparison,
  canRunSectionDetection,
  comparisonStatusText,
  confidenceLabel,
  documentSummaryGrid,
  findingLabel,
  formatBytes,
  formatDateTime,
  humanizeToken,
  sortSections,
} from "@/components/documents/DocumentPrimitives";

import {
  adoptDocumentAsCVVersion,
  archiveCVVersion,
  compareDocumentFacts,
  deleteCVVersion,
  deleteDocument,
  detectDocumentSections,
  extractDocument,
  getCVVersions,
  getDocument,
  getDocumentSections,
  getFactComparison,
  getLatestDocumentFactComparison,
  isAbortError,
  setPrimaryCVVersion,
  setPrimaryDocument,
} from "@/lib/api";

import type {
  CVDocument,
  CVSection,
  FactComparisonFinding,
  FactComparisonRun,
} from "@/types/document";

import type { CVVersion } from "@/types/cvVersion";

type DocumentDetailPageProps = {
  documentId: number;
};

const sectionPreviewLimit = 900;

function ActionButton({
  children,
  onClick,
  disabled,
  tone = "default",
}: {
  children: string;
  onClick: () => void;
  disabled?: boolean;
  tone?: "default" | "primary" | "danger" | "warning";
}) {
  const toneClass =
    tone === "primary"
      ? "bg-violet-600 text-white hover:bg-violet-500 focus:ring-violet-300 disabled:bg-slate-300"
      : tone === "danger"
      ? "border-red-200 text-red-700 hover:border-red-300 hover:bg-red-50 focus:ring-red-300"
      : tone === "warning"
      ? "border-amber-200 text-amber-700 hover:border-amber-300 hover:bg-amber-50 focus:ring-amber-300"
      : "border-slate-300 text-slate-700 hover:border-violet-400 hover:text-violet-700 focus:ring-slate-300";

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex justify-center rounded-lg border px-4 py-2 text-sm font-semibold transition focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:text-slate-400 ${toneClass}`}
    >
      {children}
    </button>
  );
}

function ExtractedContent({
  document,
}: {
  document: CVDocument;
}) {
  const [expanded, setExpanded] = useState(false);
  const text = document.extracted_text ?? "";

  return (
    <div className="space-y-4">
      <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DetailRow
          label="Page count"
          value={document.page_count ?? "Not available"}
        />
        <DetailRow
          label="Characters"
          value={
            document.extracted_character_count ??
            "Not available"
          }
        />
        <DetailRow
          label="Extracted"
          value={formatDateTime(document.extracted_at)}
        />
        <DetailRow
          label="Status"
          value={
            <StatusBadge
              status={document.extraction_status}
            />
          }
        />
      </dl>

      {document.extraction_error ? (
        <ErrorNotice>
          {document.extraction_error}
        </ErrorNotice>
      ) : null}

      {text ? (
        <div>
          <button
            type="button"
            aria-expanded={expanded}
            onClick={() =>
              setExpanded((current) => !current)
            }
            className="mb-3 inline-flex rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-violet-400 focus:outline-none focus:ring-2 focus:ring-slate-300"
          >
            {expanded
              ? "Hide extracted text"
              : "Show extracted text"}
          </button>

          {expanded ? (
            <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-700">
              {text}
            </pre>
          ) : null}
        </div>
      ) : (
        <EmptyState title="No extracted text" />
      )}
    </div>
  );
}

function DetectedSections({
  sections,
}: {
  sections: CVSection[];
}) {
  const [expandedSections, setExpandedSections] =
    useState<Set<number>>(new Set());
  const orderedSections = sortSections(sections);

  function toggleSection(sectionId: number): void {
    setExpandedSections((current) => {
      const next = new Set(current);

      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }

      return next;
    });
  }

  if (orderedSections.length === 0) {
    return <EmptyState title="No sections detected" />;
  }

  return (
    <div className="space-y-4">
      {orderedSections.map((section) => {
        const expanded = expandedSections.has(section.id);
        const isLong =
          section.content_text.length > sectionPreviewLimit;
        const content =
          expanded || !isLong
            ? section.content_text
            : `${section.content_text.slice(
                0,
                sectionPreviewLimit,
              )}...`;

        return (
          <article
            key={section.id}
            className="rounded-lg border border-slate-200 bg-white p-4"
          >
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  {section.title ||
                    humanizeToken(section.section_type)}
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  {humanizeToken(section.section_type)}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <StatusBadge
                  status="completed"
                  label={confidenceLabel(
                    section.confidence,
                  )}
                />
                <StatusBadge
                  status="pending"
                  label={section.detection_method}
                />
              </div>
            </div>

            <pre className="mt-4 whitespace-pre-wrap break-words rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-700">
              {content}
            </pre>

            {isLong ? (
              <button
                type="button"
                aria-expanded={expanded}
                onClick={() =>
                  toggleSection(section.id)
                }
                className="mt-3 inline-flex rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-violet-400 focus:outline-none focus:ring-2 focus:ring-slate-300"
              >
                {expanded
                  ? "Collapse section"
                  : "Expand section"}
              </button>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}

function FindingCard({
  finding,
}: {
  finding: FactComparisonFinding;
}) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          <h3 className="font-semibold text-slate-900">
            {findingLabel(finding)}
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            {humanizeToken(finding.entity_type)}
            {finding.field_name
              ? ` / ${humanizeToken(
                  finding.field_name,
                )}`
              : ""}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <StatusBadge status={finding.finding_type} />
          <StatusBadge status={finding.severity} />
        </div>
      </div>

      <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-slate-700">
        {finding.explanation}
      </p>

      <dl className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DetailRow
          label="CV value"
          value={finding.cv_value ?? "Not available"}
        />
        <DetailRow
          label="Verified value"
          value={
            finding.verified_value ?? "Not available"
          }
        />
        <DetailRow
          label="Verified reference"
          value={
            finding.verified_entity_id
              ? `#${finding.verified_entity_id}`
              : "Not available"
          }
        />
        <DetailRow
          label="Confidence"
          value={confidenceLabel(finding.confidence)}
        />
      </dl>
    </article>
  );
}

function FactComparisonPanel({
  comparison,
}: {
  comparison: FactComparisonRun | null;
}) {
  if (!comparison) {
    return (
      <EmptyState title="No fact comparison run">
        Run comparison after extraction and section detection
        complete.
      </EmptyState>
    );
  }

  const findings = [...comparison.findings].sort(
    (left, right) =>
      left.sort_order - right.sort_order ||
      left.id - right.id,
  );

  return (
    <div className="space-y-5">
      <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DetailRow
          label="Status"
          value={
            <StatusBadge status={comparison.status} />
          }
        />
        <DetailRow
          label="Findings"
          value={comparison.total_findings}
        />
        <DetailRow
          label="Confirmed"
          value={comparison.confirmed_count}
        />
        <DetailRow
          label="Manual review"
          value={comparison.manual_review_count}
        />
        <DetailRow
          label="Mismatches"
          value={comparison.mismatch_count}
        />
        <DetailRow
          label="Missing verified facts"
          value={comparison.missing_verified_count}
        />
        <DetailRow
          label="Unverified claims"
          value={comparison.unverified_claim_count}
        />
        <DetailRow
          label="Completed"
          value={formatDateTime(
            comparison.completed_at,
          )}
        />
      </dl>

      {comparison.error ? (
        <ErrorNotice>{comparison.error}</ErrorNotice>
      ) : null}

      {findings.length === 0 ? (
        <EmptyState title="No findings" />
      ) : (
        <div className="space-y-4">
          {findings.map((finding) => (
            <FindingCard
              key={finding.id}
              finding={finding}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function DocumentDetailPage({
  documentId,
}: DocumentDetailPageProps) {
  const router = useRouter();
  const [document, setDocument] =
    useState<CVDocument | null>(null);
  const [sections, setSections] = useState<
    CVSection[]
  >([]);
  const [comparison, setComparison] =
    useState<FactComparisonRun | null>(null);
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

  const associatedVersions = useMemo(
    () =>
      versions.filter(
        (version) =>
          version.source_document_id === documentId,
      ),
    [versions, documentId],
  );

  const loadDetail = useCallback(async function loadDetail(
    signal?: AbortSignal,
  ): Promise<void> {
    if (
      !Number.isInteger(documentId) ||
      documentId <= 0
    ) {
      setErrorMessage("Invalid document id.");
      setLoading(false);
      return;
    }

    try {
      setErrorMessage("");

      const [loadedDocument, loadedSections, allVersions] =
        await Promise.all([
          getDocument(documentId, signal),
          getDocumentSections(documentId, signal),
          getCVVersions(signal),
        ]);

      const loadedComparison =
        loadedDocument.fact_comparison_summary
          ? await getFactComparison(
              loadedDocument.fact_comparison_summary.id,
              signal,
            )
          : await getLatestDocumentFactComparison(
              documentId,
              signal,
            );

      setDocument(loadedDocument);
      setSections(loadedSections);
      setComparison(loadedComparison);
      setVersions(allVersions);
    } catch (error) {
      if (isAbortError(error)) {
        return;
      }

      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to load document.",
      );
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [documentId]);

  useEffect(() => {
    const controller = new AbortController();
    queueMicrotask(() => {
      setLoading(true);
      void loadDetail(controller.signal);
    });

    return () => controller.abort();
  }, [loadDetail]);

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
        await loadDetail();
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
    void loadDetail();
  }

  if (loading) {
    return (
      <main className="cp-page">
        <div className="mx-auto max-w-7xl">
          <LoadingState label="Loading document..." />
        </div>
      </main>
    );
  }

  if (!document) {
    return (
      <main className="cp-page">
        <div className="mx-auto max-w-7xl space-y-5">
          <Link
            href="/documents"
            className="text-sm font-semibold text-violet-600 transition hover:text-violet-700 focus:outline-none focus:ring-2 focus:ring-violet-300"
          >
            Documents
          </Link>
          {errorMessage ? (
            <ErrorNotice>{errorMessage}</ErrorNotice>
          ) : (
            <EmptyState title="Document not found" />
          )}
        </div>
      </main>
    );
  }

  const existingOriginalVersion =
    associatedVersions.find(
      (version) => version.version_type === "original",
    );
  const canAdopt =
    canAdoptDocument(document) &&
    !existingOriginalVersion;
  const comparisonLabel =
    comparisonStatusText(comparison);

  return (
    <main className="cp-page">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <Link
              href="/documents"
              className="text-sm font-semibold text-violet-600 transition hover:text-violet-700 focus:outline-none focus:ring-2 focus:ring-violet-300"
            >
              Documents
            </Link>
            <h1 className="mt-3 break-words text-3xl font-bold text-slate-900 sm:text-4xl">
              {document.original_filename}
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
              onClick={refresh}
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

        <div className="space-y-6">
          <SectionPanel title="Document overview">
            <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
                label="Content type"
                value={document.media_type}
              />
              <DetailRow
                label="Upload status"
                value={
                  <StatusBadge
                    status={document.upload_status}
                  />
                }
              />
              <DetailRow
                label="Primary document"
                value={document.is_primary ? "Yes" : "No"}
              />
              <DetailRow
                label="Comparison"
                value={comparisonLabel}
              />
            </dl>
          </SectionPanel>

          <SectionPanel title="Processing status">
            <div className="flex flex-wrap gap-3">
              <ActionButton
                tone="primary"
                disabled={
                  !canRunExtraction(document) ||
                  busyAction !== null
                }
                onClick={() =>
                  void runAction("extract", async () => {
                    await extractDocument(document.id);
                    return "Text extraction finished.";
                  })
                }
              >
                {busyAction === "extract"
                  ? "Extracting..."
                  : "Run extraction"}
              </ActionButton>

              <ActionButton
                tone="primary"
                disabled={
                  !canRunSectionDetection(document) ||
                  busyAction !== null
                }
                onClick={() =>
                  void runAction(
                    "detect-sections",
                    async () => {
                      await detectDocumentSections(
                        document.id,
                      );
                      return "Section detection finished.";
                    },
                  )
                }
              >
                {busyAction === "detect-sections"
                  ? "Detecting..."
                  : "Detect sections"}
              </ActionButton>

              <ActionButton
                tone="primary"
                disabled={
                  !canRunFactComparison(document) ||
                  busyAction !== null
                }
                onClick={() =>
                  void runAction(
                    "compare-facts",
                    async () => {
                      const run =
                        await compareDocumentFacts(
                          document.id,
                        );
                      setComparison(run);
                      return "Fact comparison finished.";
                    },
                  )
                }
              >
                {busyAction === "compare-facts"
                  ? "Comparing..."
                  : "Run fact comparison"}
              </ActionButton>
            </div>

            <dl className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <DetailRow
                label="Extraction"
                value={
                  <StatusBadge
                    status={document.extraction_status}
                  />
                }
              />
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
                label="Detected at"
                value={formatDateTime(
                  document.section_detected_at,
                )}
              />
              <DetailRow
                label="Detection method"
                value={
                  document.section_detection_method ??
                  "Not available"
                }
              />
            </dl>

            {document.section_detection_error ? (
              <div className="mt-4">
                <ErrorNotice>
                  {document.section_detection_error}
                </ErrorNotice>
              </div>
            ) : null}
          </SectionPanel>

          <SectionPanel title="Extracted-content summary">
            <ExtractedContent document={document} />
          </SectionPanel>

          <SectionPanel title="Detected sections">
            <DetectedSections sections={sections} />
          </SectionPanel>

          <SectionPanel title="Verified-facts comparison">
            <FactComparisonPanel
              comparison={comparison}
            />
          </SectionPanel>

          <SectionPanel
            title="CV version relationships"
            action={
              canAdopt ? (
                <ActionButton
                  tone="primary"
                  disabled={busyAction !== null}
                  onClick={() =>
                    void runAction(
                      "adopt-original",
                      async () => {
                        await adoptDocumentAsCVVersion(
                          document.id,
                          {
                            status: "ready",
                            is_primary: false,
                          },
                        );
                        return "Original CV version adopted.";
                      },
                    )
                  }
                >
                  {busyAction === "adopt-original"
                    ? "Adopting..."
                    : "Adopt as original"}
                </ActionButton>
              ) : null
            }
          >
            {existingOriginalVersion ? (
              <p className="mb-4 text-sm text-slate-500">
                Original version #
                {existingOriginalVersion.id} is linked to
                this document.
              </p>
            ) : null}

            <CVVersionCards
              versions={associatedVersions}
              busyAction={busyAction}
              emptyTitle="No linked CV versions"
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
          </SectionPanel>

          <SectionPanel title="Available actions">
            <div className="flex flex-wrap gap-3">
              <ActionButton
                disabled={
                  document.is_primary ||
                  document.document_type !== "original_cv" ||
                  busyAction !== null
                }
                onClick={() =>
                  void runAction(
                    "primary-document",
                    async () => {
                      await setPrimaryDocument(document.id);
                      return "Document marked primary.";
                    },
                  )
                }
              >
                {busyAction === "primary-document"
                  ? "Marking primary..."
                  : "Mark document primary"}
              </ActionButton>

              <ActionButton
                tone="danger"
                disabled={busyAction !== null}
                onClick={() => {
                  const confirmed = window.confirm(
                    `Delete document "${document.original_filename}"? This removes the uploaded document record and file.`,
                  );

                  if (!confirmed) {
                    return;
                  }

                  void runAction(
                    "delete-document",
                    async () => {
                      await deleteDocument(document.id);
                      router.push("/documents");
                      return "Document deleted.";
                    },
                    { reload: false },
                  );
                }}
              >
                {busyAction === "delete-document"
                  ? "Deleting..."
                  : "Delete document"}
              </ActionButton>
            </div>

            <p className="mt-4 text-sm text-slate-500">
              File size {formatBytes(document.size_bytes)}
            </p>
          </SectionPanel>
        </div>

        <CVAutofillPanel documentId={documentId} />
      </div>
    </main>
  );
}
