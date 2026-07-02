export type ApplicationRunStatus =
  | "paused_for_gate"
  | "submitted"
  | "cancelled"
  | "failed";

export type ApplicationRunGate = {
  code: string;
  detail: string;
  acknowledged: boolean;
};

export type ApplicationRunFillField = {
  field: string;
  field_type: string;
  source: string;
  action: string;
  preview: string | null;
};

export type ApplicationRunManualField = {
  field: string;
  reason: string;
};

export type ApplicationRun = {
  id: number;
  job_id: number;
  application_package_id: number | null;
  status: ApplicationRunStatus;
  pause_reason: string | null;
  gates: ApplicationRunGate[];
  fill_plan: ApplicationRunFillField[];
  manual_fields: ApplicationRunManualField[];
  confirmation_number: string | null;
  submitted_at: string | null;
  driver: string;
  workflow_version: string;
  created_at: string;
  updated_at: string;
};
