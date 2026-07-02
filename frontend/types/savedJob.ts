import type { NormalizedJobListItem } from "@/types/job";

export type SavedJobReviewStatus =
  | "saved"
  | "shortlisted"
  | "dismissed"
  | "archived";

export type SavedJob = {
  id: number;
  job_id: number;
  review_status: SavedJobReviewStatus;
  notes: string | null;
  status_changed_at: string;
  created_at: string;
  updated_at: string;
  job: NormalizedJobListItem;
};

export type SavedJobPage = {
  items: SavedJob[];
  total: number;
  page: number;
  page_size: number;
};

export type SavedJobUpdateInput = {
  review_status?: SavedJobReviewStatus;
  notes?: string;
};
