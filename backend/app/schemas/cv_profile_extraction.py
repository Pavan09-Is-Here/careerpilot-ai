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


class SuggestedEducationResponse(BaseModel):
    institution: str
    degree: str
    start_date: str
    end_date: str | None = None
    is_current: bool
    field_of_study: str | None = None
    grade: str | None = None
    description: str
    evidence: str


class SuggestedExperienceResponse(BaseModel):
    company: str
    job_title: str
    start_date: str
    end_date: str | None = None
    is_current: bool
    location: str | None = None
    description: str
    responsibilities: list[str]
    evidence: str


class SuggestedProjectResponse(BaseModel):
    name: str
    description: str
    technologies: list[str]
    features: list[str]
    project_url: str | None = None
    github_url: str | None = None
    evidence: str


class SuggestedCertificationResponse(BaseModel):
    name: str
    issuing_organization: str
    issue_date: str
    credential_id: str | None = None
    description: str
    evidence: str


class ProfileSuggestionResponse(BaseModel):
    document_id: int
    extraction_version: str
    verified: bool
    fields: list[SuggestedFieldResponse]
    skills: list[SuggestedSkillResponse]
    education: list[SuggestedEducationResponse]
    experience: list[SuggestedExperienceResponse]
    projects: list[SuggestedProjectResponse]
    certifications: list[SuggestedCertificationResponse]
    manual_review: list[ManualSuggestionResponse]


class ApplyProfileSuggestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    apply_profile: bool = True
    apply_skills: bool = True
    apply_education: bool = True
    apply_experience: bool = True
    apply_projects: bool = True
    apply_certifications: bool = True
    include_sensitive: bool = False
    overwrite: bool = False


class ApplyProfileSuggestionResponse(BaseModel):
    document_id: int
    verified: bool
    applied_fields: list[str]
    skipped_existing_fields: list[str]
    added_skills: list[str]
    added_education: list[str]
    added_experience: list[str]
    added_projects: list[str]
    added_certifications: list[str]
    manual_review: list[dict]
