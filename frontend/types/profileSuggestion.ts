export type ProfileSuggestionField = {
  field: string;
  value: string;
  evidence: string;
  sensitive: boolean;
  auto_fill: boolean;
  note: string;
};

export type ProfileSuggestionSkill = {
  name: string;
  evidence: string;
};

export type ProfileSuggestionManual = {
  category: string;
  content: string;
  reason: string;
};

export type ProfileSuggestionEducation = {
  institution: string;
  degree: string;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  field_of_study: string | null;
  grade: string | null;
  description: string;
  evidence: string;
};

export type ProfileSuggestionExperience = {
  company: string;
  job_title: string;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  location: string | null;
  description: string;
  responsibilities: string[];
  evidence: string;
};

export type ProfileSuggestionProject = {
  name: string;
  description: string;
  technologies: string[];
  features: string[];
  project_url: string | null;
  github_url: string | null;
  evidence: string;
};

export type ProfileSuggestionCertification = {
  name: string;
  issuing_organization: string;
  issue_date: string;
  credential_id: string | null;
  description: string;
  evidence: string;
};

export type ProfileSuggestion = {
  document_id: number;
  extraction_version: string;
  verified: boolean;
  fields: ProfileSuggestionField[];
  skills: ProfileSuggestionSkill[];
  education: ProfileSuggestionEducation[];
  experience: ProfileSuggestionExperience[];
  projects: ProfileSuggestionProject[];
  certifications: ProfileSuggestionCertification[];
  manual_review: ProfileSuggestionManual[];
};

export type ApplyProfileSuggestionInput = {
  applyProfile?: boolean;
  applySkills?: boolean;
  applyEducation?: boolean;
  applyExperience?: boolean;
  applyProjects?: boolean;
  applyCertifications?: boolean;
  includeSensitive?: boolean;
  overwrite?: boolean;
};

export type ApplyProfileSuggestionResult = {
  document_id: number;
  verified: boolean;
  applied_fields: string[];
  skipped_existing_fields: string[];
  added_skills: string[];
  added_education: string[];
  added_experience: string[];
  added_projects: string[];
  added_certifications: string[];
  manual_review: Array<Record<string, unknown>>;
};
