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
