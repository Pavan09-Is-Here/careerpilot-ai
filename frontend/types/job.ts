export type JobLifecycleStatus =
  | "discovered"
  | "active"
  | "possibly_stale"
  | "expired"
  | "removed"
  | "unavailable";

export type JobRemoteMode =
  | "unspecified"
  | "onsite"
  | "hybrid"
  | "remote"
  | "flexible";

export type JobEmploymentType =
  | "unspecified"
  | "full_time"
  | "part_time"
  | "contract"
  | "temporary"
  | "internship"
  | "apprenticeship"
  | "volunteer"
  | "per_diem"
  | "other";

export type JobSource = {
  id: number;
  source_key: string;
  display_name: string;
  source_category: string;
  provider_type: string;
  base_url: string | null;
  enabled: boolean;
  allowlisted: boolean;
  access_mode: string;
  attribution_required: boolean;
  attribution_text: string | null;
  attribution_url: string | null;
  created_at: string;
  updated_at: string;
};

export type JobSourcePage = {
  items: JobSource[];
  total: number;
  page: number;
  page_size: number;
};

export type NormalizedJobListItem = {
  id: number;
  job_source_id: number;
  source_job_id: string;
  canonical_url: string | null;
  source_url: string;
  employer_name: string;
  title: string;
  normalized_title: string | null;
  remote_mode: JobRemoteMode;
  employment_type: JobEmploymentType;
  seniority: string;
  posted_at: string | null;
  expires_at: string | null;
  first_seen_at: string;
  last_seen_at: string;
  ingested_at: string;
  lifecycle_status: JobLifecycleStatus;
  description_excerpt: string | null;
  created_at: string;
  updated_at: string;
};

export type NormalizedJobPage = {
  items: NormalizedJobListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type JobLocation = {
  id: number;
  job_id: number;
  sort_order: number;
  raw_location_text: string | null;
  country: string | null;
  region: string | null;
  city: string | null;
  postal_code: string | null;
  remote_mode: JobRemoteMode | null;
  source_provided: boolean;
};

export type JobCompensation = {
  id: number;
  job_id: number;
  min_amount: string | null;
  max_amount: string | null;
  currency: string | null;
  compensation_period: string;
  source_text: string | null;
};

export type JobSkillRequirement = {
  id: number;
  job_id: number;
  skill_text: string;
  requirement_type: string;
};

export type NormalizedJobDetail = NormalizedJobListItem & {
  employer_external_id: string | null;
  description_text: string | null;
  responsibilities_text: string | null;
  required_qualifications_text: string | null;
  preferred_qualifications_text: string | null;
  source_sponsorship_visa_text: string | null;
  source_updated_at: string | null;
  source_attribution_text: string | null;
  source_attribution_url: string | null;
  source_license_reference: string | null;
  content_hash: string;
  normalization_version: string;
  locations: JobLocation[];
  compensations: JobCompensation[];
  skill_requirements: JobSkillRequirement[];
};

export type JobDuplicate = {
  id: number;
  job_id: number;
  duplicate_of_job_id: number;
  detection_method: "canonical_url" | "content_hash";
  detected_at: string;
};

export type JobDuplicateList = {
  items: JobDuplicate[];
  total: number;
};

export type JobListFilters = {
  page?: number;
  pageSize?: number;
  sourceId?: number;
  lifecycleStatus?: JobLifecycleStatus;
  employer?: string;
  employmentType?: JobEmploymentType;
  remoteMode?: JobRemoteMode;
  postedWithinHours?: number;
};
