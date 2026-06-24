export type EducationInput = {
  institution: string;
  degree: string;
  field_of_study: string | null;
  start_date: string;
  end_date: string | null;
  grade: string | null;
  location: string | null;
  description: string | null;
  is_current: boolean;
  verified: boolean;
};

export type Education = EducationInput & {
  id: number;
  candidate_profile_id: number;
  created_at: string;
  updated_at: string;
};