export type NotificationCategory =
  | "application_prepared"
  | "application_submitted"
  | "manual_action_required"
  | "new_matching_jobs";

export type NotificationStatus =
  | "pending"
  | "sent"
  | "failed"
  | "suppressed";

export type Notification = {
  id: number;
  category: string;
  channel: string;
  recipient: string;
  subject: string;
  body: string;
  status: string;
  related_job_id: number | null;
  error: string | null;
  created_at: string;
  sent_at: string | null;
};

export type NotificationPage = {
  items: Notification[];
  total: number;
  limit: number;
  offset: number;
};

export type NotificationDeliverResult = {
  sent: number;
  failed: number;
  skipped: number;
};

export type NotificationFilters = {
  category?: NotificationCategory;
  status?: NotificationStatus;
  limit?: number;
  offset?: number;
};
