export type ProfileSuggestionField = {
  field: string;
  value: string;
  evidence: string;
  sensitive: boolean;
  auto_fill: boolean;
  note: string;
};

export type ProfileSuggestionSkill = {
  name: string;
  evidence: string;
};

export type ProfileSuggestionManual = {
  category: string;
  content: string;
  reason: string;
};

export type ProfileSuggestion = {
  document_id: number;
  extraction_version: string;
  verified: boolean;
  fields: ProfileSuggestionField[];
  skills: ProfileSuggestionSkill[];
  manual_review: ProfileSuggestionManual[];
};

export type ApplyProfileSuggestionInput = {
  applyProfile?: boolean;
  applySkills?: boolean;
  includeSensitive?: boolean;
  overwrite?: boolean;
};

export type ApplyProfileSuggestionResult = {
  document_id: number;
  verified: boolean;
  applied_fields: string[];
  skipped_existing_fields: string[];
  added_skills: string[];
  manual_review: Array<Record<string, unknown>>;
};
