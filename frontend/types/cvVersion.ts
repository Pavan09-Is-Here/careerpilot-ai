export type CVVersionType =
  | "original"
  | "parsed"
  | "verified_master"
  | "tailored";

export type CVVersionStatus =
  | "draft"
  | "ready"
  | "archived"
  | "failed";

export type CVArtifactType = "docx" | "pdf";

export type CVVersion = {
  id: number;
  candidate_profile_id: number;
  source_document_id: number | null;
  parent_version_id: number | null;
  version_type: CVVersionType;
  status: CVVersionStatus;
  display_name: string;
  description: string | null;
  job_reference: string | null;
  is_primary: boolean;
  mime_type: string | null;
  file_size: number | null;
  generation_version: string | null;
  source_summary: Record<string, unknown> | null;
  generated_at: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type CVVersionAdoptInput = {
  display_name?: string | null;
  description?: string | null;
  status?: CVVersionStatus;
  is_primary?: boolean;
};

export type CVMasterGenerationInput = {
  display_name?: string | null;
  description?: string | null;
  idempotency_key: string;
  is_primary: boolean;
};

export type CVVersionArtifact = {
  id: number;
  cv_version_id: number;
  artifact_type: CVArtifactType;
  mime_type: string;
  safe_filename: string;
  file_size: number;
  page_count: number | null;
  renderer_version: string;
  content_version: string;
  created_at: string;
};

export type CVMasterGenerationResponse = {
  version: CVVersion;
  artifacts: CVVersionArtifact[];
  created: boolean;
};

export type CVVersionHistory = {
  version: CVVersion;
  ancestry: CVVersion[];
  children: CVVersion[];
};

export type DownloadedArtifact = {
  blob: Blob;
  filename: string | null;
  mime_type: string | null;
};
