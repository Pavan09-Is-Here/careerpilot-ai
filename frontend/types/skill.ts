export type SkillProficiency =
  | "Beginner"
  | "Intermediate"
  | "Advanced"
  | "Expert";

export type SkillInput = {
  name: string;
  category: string | null;
  proficiency: SkillProficiency;
  years_experience: number | null;
  evidence: string | null;
  is_primary: boolean;
  verified: boolean;
};

export type Skill = SkillInput & {
  id: number;
  candidate_profile_id: number;
  created_at: string;
  updated_at: string;
};