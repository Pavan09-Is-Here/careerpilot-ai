export type CandidateProfileInput = {
  full_name: string;
  email: string;
  phone: string | null;
  location: string | null;
  professional_title: string | null;
  professional_summary: string | null;
  linkedin_url: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  work_authorization: string | null;
  requires_sponsorship: boolean;
  willing_to_relocate: boolean;
  preferred_work_modes: string[];
  target_roles: string[];
  preferred_locations: string[];
  minimum_salary: number | null;
  salary_currency: string;
  minimum_match_score: number;
  auto_apply_enabled: boolean;
};

export type CandidateProfile = CandidateProfileInput & {
  id: number;
  created_at: string;
  updated_at: string;
  // Read-only: changes only via the verification workflow
  // (POST /profile/verify-all), never via profile upsert.
  facts_verified: boolean;
};
