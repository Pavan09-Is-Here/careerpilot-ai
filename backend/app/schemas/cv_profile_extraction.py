from pydantic import BaseModel, ConfigDict


class SuggestedFieldResponse(BaseModel):
    field: str
    value: str
    evidence: str
    sensitive: bool
    auto_fill: bool
    note: str = ""


class SuggestedSkillResponse(BaseModel):
    name: str
    evidence: str


class ManualSuggestionResponse(BaseModel):
    category: str
    content: str
    reason: str


class ProfileSuggestionResponse(BaseModel):
    document_id: int
    extraction_version: str
    verified: bool
    fields: list[SuggestedFieldResponse]
    skills: list[SuggestedSkillResponse]
    manual_review: list[ManualSuggestionResponse]


class ApplyProfileSuggestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    apply_profile: bool = True
    apply_skills: bool = True
    include_sensitive: bool = False
    overwrite: bool = False


class ApplyProfileSuggestionResponse(BaseModel):
    document_id: int
    verified: bool
    applied_fields: list[str]
    skipped_existing_fields: list[str]
    added_skills: list[str]
    manual_review: list[dict]
