import type {
  CandidateProfile,
  CandidateProfileInput,
} from "@/types/candidate";

import type {
  Education,
  EducationInput,
} from "@/types/education";

import type {
  Experience,
  ExperienceInput,
} from "@/types/experience";

import type {
  Project,
  ProjectInput,
} from "@/types/project";

import type {
  Skill,
  SkillInput,
} from "@/types/skill";

import type {
  Certification,
  CertificationInput,
} from "@/types/certification";

import type {
  CVDocument,
  CVDocumentListItem,
  CVSection,
  DocumentExtractionResult,
  DocumentSectionDetectionResult,
  DocumentUploadInput,
  FactComparisonRun,
} from "@/types/document";

import type {
  CVMasterGenerationInput,
  CVMasterGenerationResponse,
  CVVersion,
  CVVersionAdoptInput,
  CVVersionArtifact,
  CVVersionHistory,
  DownloadedArtifact,
} from "@/types/cvVersion";

import type {
  GreenhouseBoardConnectInput,
  IngestionRunResult,
  JobDuplicateList,
  JobListFilters,
  JobSource,
  JobSourcePage,
  NormalizedJobDetail,
  NormalizedJobPage,
} from "@/types/job";

import type {
  SavedJob,
  SavedJobPage,
  SavedJobReviewStatus,
  SavedJobUpdateInput,
} from "@/types/savedJob";

import type {
  Notification,
  NotificationDeliverResult,
  NotificationFilters,
  NotificationPage,
} from "@/types/notification";

import type {
  ApplyProfileSuggestionInput,
  ApplyProfileSuggestionResult,
  ProfileSuggestion,
} from "@/types/profileSuggestion";

import type {
  Application,
  ApplicationDetail,
  ApplicationFollowUpInput,
  ApplicationNoteInput,
  ApplicationStatus,
  ApplicationUpdateInput,
} from "@/types/application";

import type {
  ApplicationAnswer,
  ApplicationAnswerCategory,
  ApplicationAnswerInput,
} from "@/types/applicationAnswer";

import type {
  ApplicationPackage,
  ApplicationPackageUpdateInput,
} from "@/types/applicationPackage";

import type { ApplicationRun } from "@/types/applicationRun";

import type {
  AuthSession,
  AuthStatus,
  LoginResult,
  MessageResult,
  RegisterInput,
} from "@/types/auth";

import { authHeader, clearAuthToken } from "@/lib/auth";

// A 401 means the caller needs to sign in (session missing or expired).
// Clear any stored token and send them to the sign-in page. We never
// redirect while already on /auth, so login failures still show their
// error inline there.
function handleUnauthorized(status: number): void {
  if (status !== 401 || typeof window === "undefined") {
    return;
  }
  if (window.location.pathname !== "/auth") {
    clearAuthToken();
    window.location.href = "/auth";
  }
}

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";

export type HealthResponse = {
  service: string;
  status: string;
  version: string;
};

type ValidationError = {
  msg?: string;
  loc?: Array<string | number>;
};

type ErrorResponse = {
  detail?: string | ValidationError[];
};

async function readErrorMessage(
  response: Response,
): Promise<string> {
  handleUnauthorized(response.status);
  try {
    const body =
      (await response.json()) as ErrorResponse;

    if (typeof body.detail === "string") {
      return body.detail;
    }

    if (Array.isArray(body.detail)) {
      return body.detail
        .map((error) => {
          const location = error.loc
            ?.filter(
              (item) =>
                item !== "body" &&
                item !== "query" &&
                item !== "path",
            )
            .join(".");

          const message =
            error.msg ?? "Validation error";

          return location
            ? `${location}: ${message}`
            : message;
        })
        .join(", ");
    }
  } catch {
    // The response did not contain JSON.
  }

  return `Request failed with status ${response.status}`;
}

export function isAbortError(error: unknown): boolean {
  return (
    error instanceof DOMException &&
    error.name === "AbortError"
  );
}

function assertPositiveIntegerId(
  value: number,
  label: string,
): void {
  if (
    !Number.isInteger(value) ||
    value <= 0 ||
    !Number.isSafeInteger(value)
  ) {
    throw new Error(`Invalid ${label}.`);
  }
}

async function requestJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...authHeader(),
      ...init.headers,
    },
    cache: init.cache ?? "no-store",
  });

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<T>;
}

async function requestJsonBody<T>(
  path: string,
  method: string,
  body: object,
  signal?: AbortSignal,
): Promise<T> {
  return requestJson<T>(path, {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    signal,
  });
}

function safeDownloadFilename(
  filename: string | null,
): string | null {
  if (!filename) {
    return null;
  }

  const cleaned = filename
    .replace(/[/\\]/g, "_")
    .replace(/[\u0000-\u001f\u007f]/g, "")
    .trim();

  return cleaned || null;
}

function parseContentDispositionFilename(
  value: string | null,
): string | null {
  if (!value) {
    return null;
  }

  const parts = value.split(";").map((part) => part.trim());
  const encoded = parts.find((part) =>
    part.toLowerCase().startsWith("filename*="),
  );

  if (encoded) {
    const rawValue = encoded.split("=").slice(1).join("=");
    const utf8Prefix = "UTF-8''";

    try {
      const encodedValue = rawValue
        .replace(/^"/, "")
        .replace(/"$/, "");

      if (encodedValue.startsWith(utf8Prefix)) {
        return safeDownloadFilename(
          decodeURIComponent(
            encodedValue.slice(utf8Prefix.length),
          ),
        );
      }
    } catch {
      return null;
    }
  }

  const plain = parts.find((part) =>
    part.toLowerCase().startsWith("filename="),
  );

  if (!plain) {
    return null;
  }

  return safeDownloadFilename(
    plain
      .split("=")
      .slice(1)
      .join("=")
      .replace(/^"/, "")
      .replace(/"$/, ""),
  );
}

/*
|--------------------------------------------------------------------------
| Backend health
|--------------------------------------------------------------------------
*/

export async function getBackendHealth(): Promise<HealthResponse> {
  const response = await fetch(
    `${API_URL}/api/health`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...authHeader(),
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<HealthResponse>;
}

/*
|--------------------------------------------------------------------------
| Candidate profile
|--------------------------------------------------------------------------
*/

export async function getCandidateProfile(): Promise<
  CandidateProfile | null
> {
  const response = await fetch(
    `${API_URL}/api/profile`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...authHeader(),
      },
      cache: "no-store",
    },
  );

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<CandidateProfile>;
}

export async function saveCandidateProfile(
  profile: CandidateProfileInput,
): Promise<CandidateProfile> {
  const response = await fetch(
    `${API_URL}/api/profile`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        ...authHeader(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(profile),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<CandidateProfile>;
}

export type VerifyAllResult = {
  verified: Record<string, number>;
  total: number;
};

export async function verifyAllProfileFacts(): Promise<VerifyAllResult> {
  return requestJson<VerifyAllResult>("/api/profile/verify-all", {
    method: "POST",
  });
}

/*
|--------------------------------------------------------------------------
| Education
|--------------------------------------------------------------------------
*/

export async function getEducationRecords(): Promise<
  Education[]
> {
  const response = await fetch(
    `${API_URL}/api/education`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...authHeader(),
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Education[]>;
}

export async function createEducation(
  education: EducationInput,
): Promise<Education> {
  const response = await fetch(
    `${API_URL}/api/education`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        ...authHeader(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(education),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Education>;
}

export async function updateEducation(
  educationId: number,
  education: EducationInput,
): Promise<Education> {
  const response = await fetch(
    `${API_URL}/api/education/${educationId}`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        ...authHeader(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(education),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Education>;
}

export async function deleteEducation(
  educationId: number,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/api/education/${educationId}`,
    {
      method: "DELETE",
      headers: { ...authHeader() },
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }
}

/*
|--------------------------------------------------------------------------
| Work experience
|--------------------------------------------------------------------------
*/

export async function getExperienceRecords(): Promise<
  Experience[]
> {
  const response = await fetch(
    `${API_URL}/api/experience`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...authHeader(),
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Experience[]>;
}

export async function createExperience(
  experience: ExperienceInput,
): Promise<Experience> {
  const response = await fetch(
    `${API_URL}/api/experience`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        ...authHeader(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(experience),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Experience>;
}

export async function updateExperience(
  experienceId: number,
  experience: ExperienceInput,
): Promise<Experience> {
  const response = await fetch(
    `${API_URL}/api/experience/${experienceId}`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        ...authHeader(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(experience),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Experience>;
}

export async function deleteExperience(
  experienceId: number,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/api/experience/${experienceId}`,
    {
      method: "DELETE",
      headers: { ...authHeader() },
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }
}

/*
|--------------------------------------------------------------------------
| Projects
|--------------------------------------------------------------------------
*/

export async function getProjectRecords(): Promise<
  Project[]
> {
  const response = await fetch(
    `${API_URL}/api/projects`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...authHeader(),
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Project[]>;
}

export async function createProject(
  project: ProjectInput,
): Promise<Project> {
  const response = await fetch(
    `${API_URL}/api/projects`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        ...authHeader(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(project),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Project>;
}

export async function updateProject(
  projectId: number,
  project: ProjectInput,
): Promise<Project> {
  const response = await fetch(
    `${API_URL}/api/projects/${projectId}`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        ...authHeader(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(project),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Project>;
}

export async function deleteProject(
  projectId: number,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/api/projects/${projectId}`,
    {
      method: "DELETE",
      headers: { ...authHeader() },
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }
}

/*
|--------------------------------------------------------------------------
| Skills
|--------------------------------------------------------------------------
*/

export async function getSkillRecords(): Promise<
  Skill[]
> {
  const response = await fetch(
    `${API_URL}/api/skills`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...authHeader(),
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Skill[]>;
}

export async function createSkill(
  skill: SkillInput,
): Promise<Skill> {
  const response = await fetch(
    `${API_URL}/api/skills`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        ...authHeader(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(skill),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Skill>;
}

export async function updateSkill(
  skillId: number,
  skill: SkillInput,
): Promise<Skill> {
  const response = await fetch(
    `${API_URL}/api/skills/${skillId}`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        ...authHeader(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(skill),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Skill>;
}

export async function deleteSkill(
  skillId: number,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/api/skills/${skillId}`,
    {
      method: "DELETE",
      headers: { ...authHeader() },
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }
}
/*
|--------------------------------------------------------------------------
| Certifications
|--------------------------------------------------------------------------
*/

export async function getCertificationRecords(): Promise<
  Certification[]
> {
  const response = await fetch(
    `${API_URL}/api/certifications`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...authHeader(),
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<
    Certification[]
  >;
}

export async function createCertification(
  certification: CertificationInput,
): Promise<Certification> {
  const response = await fetch(
    `${API_URL}/api/certifications`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        ...authHeader(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(certification),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Certification>;
}

export async function updateCertification(
  certificationId: number,
  certification: CertificationInput,
): Promise<Certification> {
  const response = await fetch(
    `${API_URL}/api/certifications/${certificationId}`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        ...authHeader(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(certification),
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<Certification>;
}

export async function deleteCertification(
  certificationId: number,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/api/certifications/${certificationId}`,
    {
      method: "DELETE",
      headers: { ...authHeader() },
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }
}

/*
|--------------------------------------------------------------------------
| Documents
|--------------------------------------------------------------------------
*/

export async function getDocuments(
  signal?: AbortSignal,
): Promise<CVDocumentListItem[]> {
  return requestJson<CVDocumentListItem[]>(
    "/api/documents",
    {
      method: "GET",
      signal,
    },
  );
}

export async function uploadDocument(
  input: DocumentUploadInput,
  signal?: AbortSignal,
): Promise<CVDocument> {
  const formData = new FormData();
  formData.append("file", input.file);
  formData.append(
    "document_type",
    input.document_type,
  );
  formData.append(
    "is_primary",
    input.is_primary ? "true" : "false",
  );

  return requestJson<CVDocument>(
    "/api/documents/upload",
    {
      method: "POST",
      body: formData,
      signal,
    },
  );
}

export async function getDocument(
  documentId: number,
  signal?: AbortSignal,
): Promise<CVDocument> {
  assertPositiveIntegerId(documentId, "document id");

  return requestJson<CVDocument>(
    `/api/documents/${documentId}`,
    {
      method: "GET",
      signal,
    },
  );
}

export async function extractDocument(
  documentId: number,
): Promise<DocumentExtractionResult> {
  assertPositiveIntegerId(documentId, "document id");

  return requestJson<DocumentExtractionResult>(
    `/api/documents/${documentId}/extract`,
    {
      method: "POST",
    },
  );
}

export async function detectDocumentSections(
  documentId: number,
): Promise<DocumentSectionDetectionResult> {
  assertPositiveIntegerId(documentId, "document id");

  return requestJson<DocumentSectionDetectionResult>(
    `/api/documents/${documentId}/detect-sections`,
    {
      method: "POST",
    },
  );
}

export async function getDocumentSections(
  documentId: number,
  signal?: AbortSignal,
): Promise<CVSection[]> {
  assertPositiveIntegerId(documentId, "document id");

  return requestJson<CVSection[]>(
    `/api/documents/${documentId}/sections`,
    {
      method: "GET",
      signal,
    },
  );
}

export async function setPrimaryDocument(
  documentId: number,
): Promise<CVDocument> {
  assertPositiveIntegerId(documentId, "document id");

  return requestJson<CVDocument>(
    `/api/documents/${documentId}/primary`,
    {
      method: "PATCH",
    },
  );
}

export async function deleteDocument(
  documentId: number,
): Promise<void> {
  assertPositiveIntegerId(documentId, "document id");

  const response = await fetch(
    `${API_URL}/api/documents/${documentId}`,
    {
      method: "DELETE",
      headers: { ...authHeader() },
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }
}

export async function compareDocumentFacts(
  documentId: number,
): Promise<FactComparisonRun> {
  assertPositiveIntegerId(documentId, "document id");

  return requestJson<FactComparisonRun>(
    `/api/documents/${documentId}/compare-facts`,
    {
      method: "POST",
    },
  );
}

export async function getLatestDocumentFactComparison(
  documentId: number,
  signal?: AbortSignal,
): Promise<FactComparisonRun | null> {
  assertPositiveIntegerId(documentId, "document id");

  const response = await fetch(
    `${API_URL}/api/documents/${documentId}/fact-comparison`,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...authHeader(),
      },
      cache: "no-store",
      signal,
    },
  );

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return response.json() as Promise<FactComparisonRun>;
}

export async function getFactComparison(
  comparisonId: number,
  signal?: AbortSignal,
): Promise<FactComparisonRun> {
  assertPositiveIntegerId(
    comparisonId,
    "fact comparison id",
  );

  return requestJson<FactComparisonRun>(
    `/api/fact-comparisons/${comparisonId}`,
    {
      method: "GET",
      signal,
    },
  );
}

/*
|--------------------------------------------------------------------------
| CV versions and generated artifacts
|--------------------------------------------------------------------------
*/

export async function adoptDocumentAsCVVersion(
  documentId: number,
  input: CVVersionAdoptInput,
): Promise<CVVersion> {
  assertPositiveIntegerId(documentId, "document id");

  return requestJsonBody<CVVersion>(
    `/api/documents/${documentId}/cv-version`,
    "POST",
    input,
  );
}

export async function getCVVersions(
  signal?: AbortSignal,
): Promise<CVVersion[]> {
  return requestJson<CVVersion[]>(
    "/api/cv-versions",
    {
      method: "GET",
      signal,
    },
  );
}

export async function getCVVersion(
  versionId: number,
  signal?: AbortSignal,
): Promise<CVVersion> {
  assertPositiveIntegerId(versionId, "CV version id");

  return requestJson<CVVersion>(
    `/api/cv-versions/${versionId}`,
    {
      method: "GET",
      signal,
    },
  );
}

export async function getCVVersionHistory(
  versionId: number,
  signal?: AbortSignal,
): Promise<CVVersionHistory> {
  assertPositiveIntegerId(versionId, "CV version id");

  return requestJson<CVVersionHistory>(
    `/api/cv-versions/${versionId}/history`,
    {
      method: "GET",
      signal,
    },
  );
}

export async function setPrimaryCVVersion(
  versionId: number,
): Promise<CVVersion> {
  assertPositiveIntegerId(versionId, "CV version id");

  return requestJson<CVVersion>(
    `/api/cv-versions/${versionId}/primary`,
    {
      method: "PATCH",
    },
  );
}

export async function archiveCVVersion(
  versionId: number,
): Promise<CVVersion> {
  assertPositiveIntegerId(versionId, "CV version id");

  return requestJson<CVVersion>(
    `/api/cv-versions/${versionId}/archive`,
    {
      method: "PATCH",
    },
  );
}

export async function deleteCVVersion(
  versionId: number,
): Promise<void> {
  assertPositiveIntegerId(versionId, "CV version id");

  const response = await fetch(
    `${API_URL}/api/cv-versions/${versionId}`,
    {
      method: "DELETE",
      headers: { ...authHeader() },
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }
}

export async function generateVerifiedMasterCV(
  parentVersionId: number,
  input: CVMasterGenerationInput,
): Promise<CVMasterGenerationResponse> {
  assertPositiveIntegerId(
    parentVersionId,
    "parent CV version id",
  );

  return requestJsonBody<CVMasterGenerationResponse>(
    `/api/cv-versions/${parentVersionId}/generate-master`,
    "POST",
    input,
  );
}

export async function getCVVersionArtifacts(
  versionId: number,
  signal?: AbortSignal,
): Promise<CVVersionArtifact[]> {
  assertPositiveIntegerId(versionId, "CV version id");

  return requestJson<CVVersionArtifact[]>(
    `/api/cv-versions/${versionId}/artifacts`,
    {
      method: "GET",
      signal,
    },
  );
}

export async function getCVArtifact(
  artifactId: number,
  signal?: AbortSignal,
): Promise<CVVersionArtifact> {
  assertPositiveIntegerId(
    artifactId,
    "CV artifact id",
  );

  return requestJson<CVVersionArtifact>(
    `/api/cv-artifacts/${artifactId}`,
    {
      method: "GET",
      signal,
    },
  );
}

export async function downloadCVArtifact(
  artifactId: number,
  signal?: AbortSignal,
): Promise<DownloadedArtifact> {
  assertPositiveIntegerId(
    artifactId,
    "CV artifact id",
  );

  const response = await fetch(
    `${API_URL}/api/cv-artifacts/${artifactId}/download`,
    {
      method: "GET",
      headers: { ...authHeader() },
      signal,
    },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response),
    );
  }

  return {
    blob: await response.blob(),
    filename: parseContentDispositionFilename(
      response.headers.get("Content-Disposition"),
    ),
    mime_type: response.headers.get("Content-Type"),
  };
}

export async function getJobSources(
  page = 1,
  pageSize = 50,
  signal?: AbortSignal,
): Promise<JobSourcePage> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  return requestJson<JobSourcePage>(
    `/api/job-sources?${params.toString()}`,
    { signal },
  );
}

export async function connectGreenhouseBoard(
  input: GreenhouseBoardConnectInput,
  signal?: AbortSignal,
): Promise<JobSource> {
  return requestJsonBody<JobSource>(
    "/api/job-sources/greenhouse",
    "POST",
    input,
    signal,
  );
}

export async function ingestJobSource(
  sourceId: number,
  signal?: AbortSignal,
): Promise<IngestionRunResult> {
  assertPositiveIntegerId(sourceId, "source id");

  return requestJson<IngestionRunResult>(
    `/api/job-sources/${sourceId}/ingest`,
    { method: "POST", signal },
  );
}

export async function getJobs(
  filters: JobListFilters = {},
  signal?: AbortSignal,
): Promise<NormalizedJobPage> {
  const params = new URLSearchParams({
    page: String(filters.page ?? 1),
    page_size: String(filters.pageSize ?? 50),
  });

  if (filters.sourceId) {
    params.set("source", String(filters.sourceId));
  }

  if (filters.lifecycleStatus) {
    params.set(
      "lifecycle_status",
      filters.lifecycleStatus,
    );
  }

  if (filters.employer) {
    params.set("employer", filters.employer);
  }

  if (filters.employmentType) {
    params.set(
      "employment_type",
      filters.employmentType,
    );
  }

  if (filters.remoteMode) {
    params.set("remote_mode", filters.remoteMode);
  }

  if (filters.postedWithinHours) {
    params.set(
      "posted_within_hours",
      String(filters.postedWithinHours),
    );
  }

  return requestJson<NormalizedJobPage>(
    `/api/jobs?${params.toString()}`,
    { signal },
  );
}

export async function getJob(
  jobId: number,
  signal?: AbortSignal,
): Promise<NormalizedJobDetail> {
  assertPositiveIntegerId(jobId, "job id");

  return requestJson<NormalizedJobDetail>(
    `/api/jobs/${jobId}`,
    { signal },
  );
}

export async function getJobDuplicates(
  jobId: number,
  signal?: AbortSignal,
): Promise<JobDuplicateList> {
  assertPositiveIntegerId(jobId, "job id");

  return requestJson<JobDuplicateList>(
    `/api/jobs/${jobId}/duplicates`,
    { signal },
  );
}

export async function saveJob(
  jobId: number,
  notes?: string,
  signal?: AbortSignal,
): Promise<SavedJob> {
  assertPositiveIntegerId(jobId, "job id");

  return requestJsonBody<SavedJob>(
    "/api/saved-jobs",
    "POST",
    notes ? { job_id: jobId, notes } : { job_id: jobId },
    signal,
  );
}

export async function getSavedJobs(
  page = 1,
  pageSize = 50,
  reviewStatus?: SavedJobReviewStatus,
  signal?: AbortSignal,
): Promise<SavedJobPage> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  if (reviewStatus) {
    params.set("review_status", reviewStatus);
  }

  return requestJson<SavedJobPage>(
    `/api/saved-jobs?${params.toString()}`,
    { signal },
  );
}

export async function updateSavedJob(
  savedJobId: number,
  input: SavedJobUpdateInput,
  signal?: AbortSignal,
): Promise<SavedJob> {
  assertPositiveIntegerId(
    savedJobId,
    "saved job id",
  );

  return requestJsonBody<SavedJob>(
    `/api/saved-jobs/${savedJobId}`,
    "PATCH",
    input,
    signal,
  );
}

export async function getNotifications(
  filters: NotificationFilters = {},
  signal?: AbortSignal,
): Promise<NotificationPage> {
  const params = new URLSearchParams({
    limit: String(filters.limit ?? 100),
    offset: String(filters.offset ?? 0),
  });

  if (filters.category) {
    params.set("category", filters.category);
  }

  if (filters.status) {
    params.set("status", filters.status);
  }

  return requestJson<NotificationPage>(
    `/api/notifications?${params.toString()}`,
    { signal },
  );
}

export async function getNotification(
  notificationId: number,
  signal?: AbortSignal,
): Promise<Notification> {
  assertPositiveIntegerId(
    notificationId,
    "notification id",
  );

  return requestJson<Notification>(
    `/api/notifications/${notificationId}`,
    { signal },
  );
}

export async function deliverNotifications(
  signal?: AbortSignal,
): Promise<NotificationDeliverResult> {
  return requestJsonBody<NotificationDeliverResult>(
    "/api/notifications/deliver",
    "POST",
    {},
    signal,
  );
}

export async function getDocumentProfileSuggestion(
  documentId: number,
  signal?: AbortSignal,
): Promise<ProfileSuggestion> {
  assertPositiveIntegerId(documentId, "document id");

  return requestJson<ProfileSuggestion>(
    `/api/documents/${documentId}/profile-suggestion`,
    { signal },
  );
}

export async function applyDocumentProfileSuggestion(
  documentId: number,
  input: ApplyProfileSuggestionInput = {},
  signal?: AbortSignal,
): Promise<ApplyProfileSuggestionResult> {
  assertPositiveIntegerId(documentId, "document id");

  return requestJsonBody<ApplyProfileSuggestionResult>(
    `/api/documents/${documentId}/apply-profile-suggestion`,
    "POST",
    {
      apply_profile: input.applyProfile ?? true,
      apply_skills: input.applySkills ?? true,
      apply_education: input.applyEducation ?? true,
      apply_experience: input.applyExperience ?? true,
      apply_projects: input.applyProjects ?? true,
      apply_certifications: input.applyCertifications ?? true,
      include_sensitive: input.includeSensitive ?? false,
      overwrite: input.overwrite ?? false,
    },
    signal,
  );
}

export async function trackJobApplication(
  jobId: number,
  signal?: AbortSignal,
): Promise<Application> {
  assertPositiveIntegerId(jobId, "job id");

  return requestJsonBody<Application>(
    `/api/jobs/${jobId}/track`,
    "POST",
    {},
    signal,
  );
}

export async function getApplications(
  status?: ApplicationStatus,
  signal?: AbortSignal,
): Promise<Application[]> {
  const params = new URLSearchParams();

  if (status) {
    params.set("status", status);
  }

  const query = params.toString();

  return requestJson<Application[]>(
    query ? `/api/applications?${query}` : "/api/applications",
    { signal },
  );
}

export async function getApplication(
  applicationId: number,
  signal?: AbortSignal,
): Promise<ApplicationDetail> {
  assertPositiveIntegerId(applicationId, "application id");

  return requestJson<ApplicationDetail>(
    `/api/applications/${applicationId}`,
    { signal },
  );
}

export async function updateApplication(
  applicationId: number,
  input: ApplicationUpdateInput,
  signal?: AbortSignal,
): Promise<Application> {
  assertPositiveIntegerId(applicationId, "application id");

  return requestJsonBody<Application>(
    `/api/applications/${applicationId}`,
    "PUT",
    input,
    signal,
  );
}

export async function addApplicationNote(
  applicationId: number,
  input: ApplicationNoteInput,
  signal?: AbortSignal,
): Promise<Application> {
  assertPositiveIntegerId(applicationId, "application id");

  return requestJsonBody<Application>(
    `/api/applications/${applicationId}/notes`,
    "POST",
    input,
    signal,
  );
}

export async function addApplicationFollowUp(
  applicationId: number,
  input: ApplicationFollowUpInput,
  signal?: AbortSignal,
): Promise<Application> {
  assertPositiveIntegerId(applicationId, "application id");

  return requestJsonBody<Application>(
    `/api/applications/${applicationId}/follow-up`,
    "POST",
    input,
    signal,
  );
}

export async function getApplicationAnswers(
  category?: ApplicationAnswerCategory,
  signal?: AbortSignal,
): Promise<ApplicationAnswer[]> {
  const params = new URLSearchParams();

  if (category) {
    params.set("category", category);
  }

  const query = params.toString();

  return requestJson<ApplicationAnswer[]>(
    query
      ? `/api/application-answers?${query}`
      : "/api/application-answers",
    { signal },
  );
}

export async function createApplicationAnswer(
  input: ApplicationAnswerInput,
  signal?: AbortSignal,
): Promise<ApplicationAnswer> {
  return requestJsonBody<ApplicationAnswer>(
    "/api/application-answers",
    "POST",
    input,
    signal,
  );
}

export async function updateApplicationAnswer(
  answerId: number,
  input: ApplicationAnswerInput,
  signal?: AbortSignal,
): Promise<ApplicationAnswer> {
  assertPositiveIntegerId(answerId, "answer id");

  return requestJsonBody<ApplicationAnswer>(
    `/api/application-answers/${answerId}`,
    "PUT",
    input,
    signal,
  );
}

export async function deleteApplicationAnswer(
  answerId: number,
  signal?: AbortSignal,
): Promise<void> {
  assertPositiveIntegerId(answerId, "answer id");

  const response = await fetch(
    `${API_URL}/api/application-answers/${answerId}`,
    { method: "DELETE", headers: { ...authHeader() }, signal },
  );

  if (!response.ok && response.status !== 204) {
    throw new Error(await readErrorMessage(response));
  }
}

export async function prepareApplication(
  jobId: number,
  signal?: AbortSignal,
): Promise<ApplicationPackage> {
  assertPositiveIntegerId(jobId, "job id");

  return requestJsonBody<ApplicationPackage>(
    `/api/jobs/${jobId}/prepare-application`,
    "POST",
    {},
    signal,
  );
}

export async function getApplicationPackage(
  jobId: number,
  signal?: AbortSignal,
): Promise<ApplicationPackage> {
  assertPositiveIntegerId(jobId, "job id");

  return requestJson<ApplicationPackage>(
    `/api/jobs/${jobId}/application-package`,
    { signal },
  );
}

export async function updateApplicationPackage(
  jobId: number,
  input: ApplicationPackageUpdateInput,
  signal?: AbortSignal,
): Promise<ApplicationPackage> {
  assertPositiveIntegerId(jobId, "job id");

  return requestJsonBody<ApplicationPackage>(
    `/api/jobs/${jobId}/application-package`,
    "PUT",
    input,
    signal,
  );
}

export async function startApplicationRun(
  jobId: number,
  signal?: AbortSignal,
): Promise<ApplicationRun> {
  assertPositiveIntegerId(jobId, "job id");

  return requestJsonBody<ApplicationRun>(
    `/api/jobs/${jobId}/apply`,
    "POST",
    {},
    signal,
  );
}

export async function getApplicationRun(
  runId: number,
  signal?: AbortSignal,
): Promise<ApplicationRun> {
  assertPositiveIntegerId(runId, "run id");

  return requestJson<ApplicationRun>(
    `/api/application-runs/${runId}/status`,
    { signal },
  );
}

export async function resumeApplicationRun(
  runId: number,
  confirmationNumber?: string,
  signal?: AbortSignal,
): Promise<ApplicationRun> {
  assertPositiveIntegerId(runId, "run id");

  return requestJsonBody<ApplicationRun>(
    `/api/application-runs/${runId}/resume`,
    "POST",
    confirmationNumber
      ? { confirmation_number: confirmationNumber }
      : {},
    signal,
  );
}

export async function cancelApplicationRun(
  runId: number,
  signal?: AbortSignal,
): Promise<ApplicationRun> {
  assertPositiveIntegerId(runId, "run id");

  return requestJsonBody<ApplicationRun>(
    `/api/application-runs/${runId}/cancel`,
    "POST",
    {},
    signal,
  );
}

export async function getAuthStatus(
  signal?: AbortSignal,
): Promise<AuthStatus> {
  return requestJson<AuthStatus>("/api/auth/status", { signal });
}

export async function register(
  input: RegisterInput,
  signal?: AbortSignal,
): Promise<LoginResult> {
  return requestJsonBody<LoginResult>(
    "/api/auth/register",
    "POST",
    { ...input },
    signal,
  );
}

export async function login(
  username: string,
  password: string,
  signal?: AbortSignal,
): Promise<LoginResult> {
  return requestJsonBody<LoginResult>(
    "/api/auth/login",
    "POST",
    { username, password },
    signal,
  );
}

export async function getSession(
  signal?: AbortSignal,
): Promise<AuthSession> {
  return requestJson<AuthSession>("/api/auth/session", { signal });
}

export async function logout(
  signal?: AbortSignal,
): Promise<MessageResult> {
  return requestJsonBody<MessageResult>(
    "/api/auth/logout",
    "POST",
    {},
    signal,
  );
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
  signal?: AbortSignal,
): Promise<MessageResult> {
  return requestJsonBody<MessageResult>(
    "/api/auth/change-password",
    "POST",
    {
      current_password: currentPassword,
      new_password: newPassword,
    },
    signal,
  );
}

export async function verifyEmail(
  token: string,
  signal?: AbortSignal,
): Promise<MessageResult> {
  return requestJsonBody<MessageResult>(
    "/api/auth/verify-email",
    "POST",
    { token },
    signal,
  );
}

export async function resendVerification(
  signal?: AbortSignal,
): Promise<MessageResult> {
  return requestJsonBody<MessageResult>(
    "/api/auth/resend-verification",
    "POST",
    {},
    signal,
  );
}

export type TestEmailResult = {
  ok: boolean;
  detail: string;
  recipient: string;
};

export async function sendTestEmail(
  signal?: AbortSignal,
): Promise<TestEmailResult> {
  return requestJsonBody<TestEmailResult>(
    "/api/auth/test-email",
    "POST",
    {},
    signal,
  );
}

export async function forgotPassword(
  email: string,
  signal?: AbortSignal,
): Promise<MessageResult> {
  return requestJsonBody<MessageResult>(
    "/api/auth/forgot-password",
    "POST",
    { email },
    signal,
  );
}

export async function resetPassword(
  token: string,
  newPassword: string,
  signal?: AbortSignal,
): Promise<MessageResult> {
  return requestJsonBody<MessageResult>(
    "/api/auth/reset-password",
    "POST",
    { token, new_password: newPassword },
    signal,
  );
}
