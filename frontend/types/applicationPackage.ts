export type ApplicationPackageReadiness =
  | "ready_for_automatic_application"
  | "needs_user_review"
  | "blocked_by_missing_information"
  | "blocked_by_captcha"
  | "blocked_by_mfa"
  | "blocked_by_assessment"
  | "not_eligible";

export type ApplicationPackageBlocker = {
  code: "captcha" | "mfa" | "assessment";
  detail: string;
};

export type ApplicationPackageJob = {
  id: number;
  title: string;
  employer_name: string;
  source_url: string;
  lifecycle_status: string;
  remote_mode: string;
  employment_type: string;
};

export type ApplicationPackageMatch = {
  match_score: number | null;
  eligibility_status: string;
  blocker_reason: string | null;
};

export type ApplicationPackageArtifact = {
  artifact_type: string;
  safe_filename: string;
  file_size: number;
  page_count: number | null;
};

export type ApplicationPackageCV = {
  cv_version_id: number;
  status: string;
  artifacts: ApplicationPackageArtifact[];
};

export type ApplicationPackageAnswer = {
  id: number;
  category: string;
  question_label: string;
  verified: boolean;
  requires_manual_confirmation: boolean;
  manually_confirmed: boolean;
};

export type ApplicationPackageSalary = {
  currency: string | null;
  minimum: string | null;
  maximum: string | null;
  midpoint: string | null;
  confidence: string;
  basis: string;
  safe_answer: string;
  below_declared_minimum: boolean;
};

export type ApplicationPackage = {
  job_id: number;
  readiness_status: ApplicationPackageReadiness;
  prepared_at: string;
  assembly_version: string;
  user_confirmed: boolean;
  user_notes: string | null;
  cover_letter_text: string | null;
  blockers: ApplicationPackageBlocker[];
  risk_warnings: string[];
  missing_items: string[];
  job: ApplicationPackageJob;
  match: ApplicationPackageMatch | null;
  tailored_cv: ApplicationPackageCV | null;
  verified_answers: ApplicationPackageAnswer[];
  salary: ApplicationPackageSalary | null;
};

export type ApplicationPackageUpdateInput = {
  user_confirmed: boolean;
  user_notes?: string | null;
};
