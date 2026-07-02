export type ApplicationAnswerCategory =
  | "work_authorization"
  | "sponsorship"
  | "availability"
  | "notice_period"
  | "relocation"
  | "remote_preference"
  | "expected_salary"
  | "company_interest"
  | "cover_letter"
  | "other";

export type ApplicationAnswer = {
  id: number;
  candidate_profile_id: number;
  category: ApplicationAnswerCategory;
  question_label: string;
  answer_text: string;
  verified: boolean;
  manually_confirmed: boolean;
  requires_manual_confirmation: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type ApplicationAnswerInput = {
  category: ApplicationAnswerCategory;
  question_label: string;
  answer_text: string;
  verified: boolean;
  manually_confirmed: boolean;
  notes: string | null;
};
