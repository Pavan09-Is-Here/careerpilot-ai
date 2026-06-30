export type DocumentType =
  | "original_cv"
  | "cover_letter"
  | "supporting_document";

export type UploadStatus =
  | "uploaded"
  | "validated"
  | "rejected"
  | "processing_failed";

export type ExtractionStatus =
  | "pending"
  | "processing"
  | "completed"
  | "no_text"
  | "partial"
  | "failed";

export type SectionDetectionStatus =
  | "pending"
  | "processing"
  | "completed"
  | "partial"
  | "failed";

export type CVSectionType =
  | "contact"
  | "summary"
  | "work_experience"
  | "education"
  | "skills"
  | "projects"
  | "certifications"
  | "awards"
  | "publications"
  | "volunteering"
  | "languages"
  | "interests"
  | "references"
  | "additional";

export type ComparisonRunStatus =
  | "pending"
  | "processing"
  | "completed"
  | "partial"
  | "failed";

export type ComparisonEntityType =
  | "candidate_profile"
  | "education"
  | "work_experience"
  | "project"
  | "skill"
  | "certification";

export type ComparisonFindingType =
  | "confirmed"
  | "possible_mismatch"
  | "missing_verified_fact"
  | "unverified_claim"
  | "date_conflict"
  | "organisation_conflict"
  | "skill_conflict"
  | "manual_review";

export type ComparisonSeverity =
  | "info"
  | "review"
  | "warning";

export type FactComparisonSummary = {
  id: number;
  document_id: number;
  status: ComparisonRunStatus;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  total_findings: number;
  confirmed_count: number;
  mismatch_count: number;
  missing_verified_count: number;
  unverified_claim_count: number;
  manual_review_count: number;
  comparison_version: string;
  is_latest_successful: boolean;
  created_at: string;
};

export type FactComparisonFinding = {
  id: number;
  comparison_run_id: number;
  document_section_id: number | null;
  sort_order: number;
  entity_type: ComparisonEntityType;
  verified_entity_id: number | null;
  field_name: string | null;
  finding_type: ComparisonFindingType;
  cv_value: string | null;
  verified_value: string | null;
  normalized_cv_value: string | null;
  normalized_verified_value: string | null;
  confidence: number;
  severity: ComparisonSeverity;
  explanation: string;
  requires_manual_review: boolean;
  created_at: string;
};

export type FactComparisonRun =
  FactComparisonSummary & {
    findings: FactComparisonFinding[];
  };

export type CVDocumentListItem = {
  id: number;
  candidate_profile_id: number;
  original_filename: string;
  file_extension: string;
  media_type: string;
  size_bytes: number;
  document_type: DocumentType;
  upload_status: UploadStatus;
  is_primary: boolean;
  extraction_status: ExtractionStatus;
  extraction_error: string | null;
  extracted_at: string | null;
  page_count: number | null;
  extracted_character_count: number | null;
  section_detection_status: SectionDetectionStatus;
  section_detection_error: string | null;
  section_detected_at: string | null;
  section_count: number;
  section_detection_method: string | null;
  fact_comparison_summary?: FactComparisonSummary | null;
  created_at: string;
  updated_at: string;
};

export type CVDocument = CVDocumentListItem & {
  extracted_text: string | null;
  fact_comparison_summary: FactComparisonSummary | null;
};

export type DocumentExtractionResult = {
  id: number;
  extraction_status: ExtractionStatus;
  extraction_error: string | null;
  extracted_at: string | null;
  page_count: number | null;
  extracted_character_count: number | null;
};

export type CVSection = {
  id: number;
  document_id: number;
  section_order: number;
  section_type: CVSectionType;
  title: string | null;
  start_char: number;
  end_char: number;
  content_text: string;
  confidence: number;
  detection_method: string;
  created_at: string;
};

export type DocumentSectionDetectionResult = {
  id: number;
  section_detection_status: SectionDetectionStatus;
  section_detection_error: string | null;
  section_detected_at: string | null;
  section_count: number;
  section_detection_method: string | null;
  sections: CVSection[];
};

export type DocumentUploadInput = {
  file: File;
  document_type: DocumentType;
  is_primary: boolean;
};
