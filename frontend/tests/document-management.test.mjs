import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function source(path) {
  return readFile(new URL(path, import.meta.url), "utf8");
}

const files = {
  api: "../lib/api.ts",
  primitives:
    "../components/documents/DocumentPrimitives.tsx",
  upload:
    "../components/documents/DocumentUploadForm.tsx",
  list: "../components/documents/DocumentList.tsx",
  documentsPage:
    "../components/documents/DocumentManagementPage.tsx",
  documentDetail:
    "../components/documents/DocumentDetailPage.tsx",
  versionsPage:
    "../components/cv-versions/CVVersionsPage.tsx",
  versionDetail:
    "../components/cv-versions/CVVersionDetailPage.tsx",
  versionCards:
    "../components/cv-versions/CVVersionCards.tsx",
  generation:
    "../components/cv-versions/MasterGenerationPanel.tsx",
  artifacts:
    "../components/cv-versions/GeneratedArtifactsPanel.tsx",
  documentsRoute: "../app/documents/page.tsx",
  documentDetailRoute:
    "../app/documents/[documentId]/page.tsx",
  versionsRoute: "../app/cv-versions/page.tsx",
  versionDetailRoute:
    "../app/cv-versions/[versionId]/page.tsx",
  documentTypes: "../types/document.ts",
  versionTypes: "../types/cvVersion.ts",
  dashboard: "../app/page.tsx",
};

test("documents route renders the document management workspace", async () => {
  const route = await source(files.documentsRoute);

  assert.match(route, /DocumentManagementPage/);
});

test("document detail route passes the dynamic document id", async () => {
  const route = await source(files.documentDetailRoute);

  assert.match(route, /params:\s*Promise/);
  assert.match(route, /documentId=\{Number\(documentId\)\}/);
});

test("cv version routes render list and detail workspaces", async () => {
  const listRoute = await source(files.versionsRoute);
  const detailRoute = await source(files.versionDetailRoute);

  assert.match(listRoute, /CVVersionsPage/);
  assert.match(detailRoute, /CVVersionDetailPage/);
  assert.match(detailRoute, /versionId=\{Number\(versionId\)\}/);
});

test("dashboard links to documents and cv versions", async () => {
  const dashboard = await source(files.dashboard);

  assert.match(dashboard, /href="\/documents"/);
  assert.match(dashboard, /href:\s*"\/cv-versions"/);
});

test("api client centralizes backend base URL handling", async () => {
  const api = await source(files.api);

  assert.match(api, /NEXT_PUBLIC_API_URL/);
  assert.match(api, /const API_URL/);
  assert.doesNotMatch(api, /localhost:3000/);
});

test("api client covers document upload, list, detail, and processing endpoints", async () => {
  const api = await source(files.api);

  assert.match(api, /\/api\/documents\/upload/);
  assert.match(api, /"\/api\/documents"/);
  assert.match(api, /\/api\/documents\/\$\{documentId\}`/);
  assert.match(api, /\/extract`/);
  assert.match(api, /\/detect-sections`/);
  assert.match(api, /\/sections`/);
});

test("api client covers comparison endpoints", async () => {
  const api = await source(files.api);

  assert.match(api, /compare-facts/);
  assert.match(api, /fact-comparison/);
  assert.match(api, /fact-comparisons/);
});

test("api client covers cv version lifecycle endpoints", async () => {
  const api = await source(files.api);

  assert.match(api, /cv-version/);
  assert.match(api, /cv-versions/);
  assert.match(api, /\/primary`/);
  assert.match(api, /\/archive`/);
  assert.match(api, /method:\s*"DELETE"/);
});

test("api client covers verified master generation and artifacts", async () => {
  const api = await source(files.api);

  assert.match(api, /generate-master/);
  assert.match(api, /cv-artifacts/);
  assert.match(api, /downloadCVArtifact/);
  assert.match(api, /response\.blob\(\)/);
});

test("api client validates numeric ids before constructing paths", async () => {
  const api = await source(files.api);

  assert.match(api, /assertPositiveIntegerId/);
  assert.match(api, /Number\.isSafeInteger/);
});

test("api client parses safe backend validation errors", async () => {
  const api = await source(files.api);

  assert.match(api, /readErrorMessage/);
  assert.match(api, /Validation error/);
  assert.match(api, /body\.detail/);
});

test("api client supports AbortController cancellation", async () => {
  const api = await source(files.api);
  const documentsPage = await source(files.documentsPage);

  assert.match(api, /signal\?: AbortSignal/);
  assert.match(documentsPage, /new AbortController/);
  assert.match(documentsPage, /controller\.abort/);
});

test("document upload accepts only pdf and docx convenience types", async () => {
  const primitives = await source(files.primitives);
  const upload = await source(files.upload);

  assert.match(primitives, /\.pdf/);
  assert.match(primitives, /\.docx/);
  assert.match(primitives, /application\/pdf/);
  assert.match(
    primitives,
    /application\/vnd\.openxmlformats-officedocument\.wordprocessingml\.document/,
  );
  assert.match(upload, /accept=\{/);
});

test("document upload shows selected filename and readable size", async () => {
  const upload = await source(files.upload);

  assert.match(upload, /selectedFile\.name/);
  assert.match(upload, /formatBytes\(selectedFile\.size\)/);
});

test("document upload validates unsupported file selection", async () => {
  const upload = await source(files.upload);
  const primitives = await source(files.primitives);

  assert.match(upload, /handleFileChange/);
  assert.match(upload, /isSupportedDocumentFile/);
  assert.match(primitives, /Choose a PDF or DOCX file/);
});

test("document upload handles successful upload and reset", async () => {
  const upload = await source(files.upload);

  assert.match(upload, /await uploadDocument/);
  assert.match(upload, /resetForm\(\)/);
  assert.match(upload, /Document uploaded/);
  assert.match(upload, /onUploaded\(uploadedDocument\)/);
});

test("document upload surfaces backend validation failure", async () => {
  const upload = await source(files.upload);

  assert.match(upload, /error instanceof Error/);
  assert.match(upload, /Unable to upload document/);
});

test("document upload prevents duplicate submit clicks", async () => {
  const upload = await source(files.upload);

  assert.match(upload, /if \(submitting\)/);
  assert.match(upload, /disabled=\{submitting\}/);
});

test("documents page includes loading, empty, error, and retry states", async () => {
  const page = await source(files.documentsPage);
  const list = await source(files.list);

  assert.match(page, /Loading documents/);
  assert.match(list, /No documents uploaded/);
  assert.match(page, /Unable to load documents/);
  assert.match(page, /Refresh/);
});

test("document list renders safe metadata and stable navigation", async () => {
  const list = await source(files.list);
  const primitives = await source(files.primitives);
  const combined = `${list}\n${primitives}`;

  assert.match(combined, /original_filename/);
  assert.match(combined, /file_extension/);
  assert.match(combined, /size_bytes/);
  assert.match(combined, /extraction_status/);
  assert.match(combined, /section_detection_status/);
  assert.match(list, /\/documents\/\$\{document\.id\}/);
});

test("document detail renders required workflow sections", async () => {
  const detail = await source(files.documentDetail);

  for (const heading of [
    "Document overview",
    "Processing status",
    "Extracted-content summary",
    "Detected sections",
    "Verified-facts comparison",
    "CV version relationships",
    "Available actions",
  ]) {
    assert.match(detail, new RegExp(heading));
  }
});

test("document detail supports extraction pending, completed, partial, failed status labels", async () => {
  const types = await source(files.documentTypes);
  const primitives = await source(files.primitives);

  for (const status of [
    "pending",
    "processing",
    "completed",
    "partial",
    "failed",
    "no_text",
  ]) {
    assert.match(`${types}\n${primitives}`, new RegExp(status));
  }
});

test("document detail runs extraction and section detection through existing api functions", async () => {
  const detail = await source(files.documentDetail);

  assert.match(detail, /extractDocument/);
  assert.match(detail, /detectDocumentSections/);
  assert.match(detail, /Run extraction/);
  assert.match(detail, /Detect sections/);
});

test("section rendering preserves text safely without html injection", async () => {
  const detail = await source(files.documentDetail);
  const allUi = [
    detail,
    await source(files.primitives),
    await source(files.upload),
    await source(files.list),
  ].join("\n");

  assert.match(detail, /whitespace-pre-wrap/);
  assert.match(detail, /content_text/);
  assert.doesNotMatch(allUi, /dangerouslySetInnerHTML/);
});

test("long sections expose expand and collapse controls", async () => {
  const detail = await source(files.documentDetail);

  assert.match(detail, /sectionPreviewLimit/);
  assert.match(detail, /aria-expanded/);
  assert.match(detail, /Expand section/);
  assert.match(detail, /Collapse section/);
});

test("fact comparison start action and findings are represented", async () => {
  const detail = await source(files.documentDetail);

  assert.match(detail, /compareDocumentFacts/);
  assert.match(detail, /Run fact comparison/);
  assert.match(detail, /FindingCard/);
});

test("comparison finding categories match backend vocabulary", async () => {
  const types = await source(files.documentTypes);

  for (const category of [
    "confirmed",
    "possible_mismatch",
    "missing_verified_fact",
    "unverified_claim",
    "date_conflict",
    "organisation_conflict",
    "skill_conflict",
    "manual_review",
  ]) {
    assert.match(types, new RegExp(category));
  }
});

test("comparison failure state is displayed safely", async () => {
  const detail = await source(files.documentDetail);

  assert.match(detail, /comparison\.error/);
  assert.match(detail, /ErrorNotice/);
});

test("original-version adoption uses existing document endpoint", async () => {
  const detail = await source(files.documentDetail);
  const api = await source(files.api);

  assert.match(detail, /Adopt as original/);
  assert.match(detail, /existingOriginalVersion/);
  assert.match(api, /\/cv-version/);
});

test("cv version listing and ancestry are rendered", async () => {
  const page = await source(files.versionsPage);
  const detail = await source(files.versionDetail);

  assert.match(page, /CVVersionCards/);
  assert.match(detail, /Version ancestry/);
  assert.match(detail, /Child versions/);
});

test("cv version primary, archive, and delete actions require backend confirmation", async () => {
  const cards = await source(files.versionCards);
  const detail = await source(files.versionDetail);

  assert.match(cards, /Mark primary/);
  assert.match(cards, /Archive/);
  assert.match(cards, /Delete/);
  assert.match(`${cards}\n${detail}`, /window\.confirm/);
});

test("unsafe cv version deletion error can be surfaced", async () => {
  const versionsPage = await source(files.versionsPage);
  const versionDetail = await source(files.versionDetail);

  assert.match(versionsPage, /setErrorMessage/);
  assert.match(versionDetail, /children\.length === 0/);
  assert.match(versionDetail, /Versions with child history/);
});

test("verified master generation is shown only for eligible parents", async () => {
  const primitives = await source(files.primitives);
  const detail = await source(files.versionDetail);

  assert.match(primitives, /isMasterGenerationParent/);
  assert.match(primitives, /version_type === "parsed"/);
  assert.match(primitives, /version_type === "verified_master"/);
  assert.match(primitives, /status === "ready"/);
  assert.match(detail, /MasterGenerationPanel/);
});

test("verified master generation uses stable idempotency key per submit and blocks duplicates", async () => {
  const generation = await source(files.generation);

  assert.match(generation, /createIdempotencyKey/);
  assert.match(generation, /idempotency_key: idempotencyKey/);
  assert.match(generation, /if \(activeKey !== null\)/);
  assert.match(generation, /disabled=\{generating\}/);
});

test("cv version statuses and types use exact backend vocabulary", async () => {
  const types = await source(files.versionTypes);

  for (const token of [
    "original",
    "parsed",
    "verified_master",
    "tailored",
    "draft",
    "ready",
    "archived",
    "failed",
  ]) {
    assert.match(types, new RegExp(token));
  }
});

test("artifact metadata renders docx and pdf separately", async () => {
  const artifacts = await source(files.artifacts);

  assert.match(artifacts, /\["docx", "pdf"\]/);
  assert.match(artifacts, /artifact_type/);
  assert.match(artifacts, /mime_type/);
  assert.match(artifacts, /file_size/);
  assert.match(artifacts, /page_count/);
  assert.match(artifacts, /created_at/);
});

test("artifact download fetches binary only on user action", async () => {
  const artifacts = await source(files.artifacts);

  assert.match(artifacts, /handleDownload/);
  assert.match(artifacts, /downloadCVArtifact/);
  assert.match(artifacts, /URL\.createObjectURL/);
  assert.match(artifacts, /URL\.revokeObjectURL/);
  assert.match(artifacts, /Download \$\{artifact\.artifact_type\.toUpperCase\(\)\}/);
});

test("missing artifacts are shown without preview rendering dependencies", async () => {
  const artifacts = await source(files.artifacts);
  const packageJson = await source("../package.json");

  assert.match(artifacts, /Missing/);
  assert.match(artifacts, /No generated artifacts/);
  assert.doesNotMatch(packageJson, /pdfjs|mammoth|docx-preview/);
});

test("frontend does not display backend storage paths or physical filenames", async () => {
  const allFrontendSource = (
    await Promise.all(
      Object.values(files).map((file) => source(file)),
    )
  ).join("\n");

  assert.doesNotMatch(allFrontendSource, /stored_filename/);
  assert.doesNotMatch(allFrontendSource, /storage_path/);
  assert.doesNotMatch(allFrontendSource, /sha256_hash/);
  assert.doesNotMatch(allFrontendSource, /console\.log/);
});

test("critical controls expose accessible labels and live status", async () => {
  const upload = await source(files.upload);
  const detail = await source(files.documentDetail);
  const documentsPage = await source(files.documentsPage);

  assert.match(upload, /htmlFor="cv-document-file"/);
  assert.match(upload, /htmlFor="document-type"/);
  assert.match(detail, /aria-expanded/);
  assert.match(`${documentsPage}\n${detail}`, /aria-live="polite"/);
});

test("responsive layout classes cover mobile and wider screens", async () => {
  const combined = [
    await source(files.documentsPage),
    await source(files.documentDetail),
    await source(files.versionsPage),
    await source(files.versionDetail),
  ].join("\n");

  assert.match(combined, /sm:/);
  assert.match(combined, /lg:/);
  assert.match(combined, /xl:/);
});

test("no generic frontend creation of verified master versions exists", async () => {
  const api = await source(files.api);

  assert.doesNotMatch(api, /createCVVersion/);
  assert.match(api, /generateVerifiedMasterCV/);
});

test("document deletion uses explicit confirmation", async () => {
  const detail = await source(files.documentDetail);

  assert.match(detail, /Delete document/);
  assert.match(detail, /window\.confirm/);
  assert.match(detail, /deleteDocument/);
});
