export type ExperienceInput = {
  company: string;
  job_title: string;
  employment_type: string | null;
  location: string | null;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  description: string | null;
  responsibilities: string[];
  achievements: string[];
  technologies: string[];
  verified: boolean;
};

export type Experience = ExperienceInput & {
  id: number;
  candidate_profile_id: number;
  created_at: string;
  updated_at: string;
};