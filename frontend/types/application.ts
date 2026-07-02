export type ApplicationStatus =
  | "discovered"
  | "analyzing"
  | "not_eligible"
  | "matched"
  | "cv_generated"
  | "needs_review"
  | "ready_to_apply"
  | "applying"
  | "blocked"
  | "submitted"
  | "interview"
  | "rejected"
  | "offer"
  | "withdrawn";

export type ApplicationInterviewStage =
  | "phone_screen"
  | "technical"
  | "onsite"
  | "final"
  | "other";

export type ApplicationNote = {
  text: string;
  created_at: string;
};

export type ApplicationFollowUp = {
  description: string;
  due_date: string | null;
  created_at: string;
  done: boolean;
};

export type ApplicationTimelineEntry = {
  at: string;
  label: string;
};

export type ApplicationJobSummary = {
  id: number;
  title: string;
  employer_name: string;
  source_url: string;
};

export type Application = {
  id: number;
  job_id: number;
  cv_id: number | null;
  status: ApplicationStatus;
  applied_at: string | null;
  confirmation_number: string | null;
  interview_date: string | null;
  interview_stage: ApplicationInterviewStage | null;
  offer_details: string | null;
  rejection_reason: string | null;
  outcome_date: string | null;
  notes: ApplicationNote[];
  follow_ups: ApplicationFollowUp[];
  created_at: string;
  updated_at: string;
};

export type ApplicationDetail = Application & {
  job: ApplicationJobSummary;
  timeline: ApplicationTimelineEntry[];
};

export type ApplicationUpdateInput = {
  status?: ApplicationStatus;
  confirmation_number?: string | null;
  interview_date?: string | null;
  interview_stage?: ApplicationInterviewStage | null;
  offer_details?: string | null;
  rejection_reason?: string | null;
  outcome_date?: string | null;
};

export type ApplicationNoteInput = {
  text: string;
};

export type ApplicationFollowUpInput = {
  description: string;
  due_date?: string | null;
};
