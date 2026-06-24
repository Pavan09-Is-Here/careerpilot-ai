export type ProjectInput = {
  name: string;
  role: string | null;
  project_type: string | null;
  description: string;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  project_url: string | null;
  github_url: string | null;
  technologies: string[];
  features: string[];
  achievements: string[];
  verified: boolean;
};

export type Project = ProjectInput & {
  id: number;
  candidate_profile_id: number;
  created_at: string;
  updated_at: string;
};