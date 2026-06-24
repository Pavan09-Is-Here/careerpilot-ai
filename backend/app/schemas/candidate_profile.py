from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CandidateProfileBase(BaseModel):
    full_name: str = Field(
        min_length=2,
        max_length=150,
    )

    email: str = Field(
        min_length=5,
        max_length=255,
    )

    phone: str | None = Field(
        default=None,
        max_length=50,
    )

    location: str | None = Field(
        default=None,
        max_length=150,
    )

    professional_title: str | None = Field(
        default=None,
        max_length=200,
    )

    professional_summary: str | None = Field(
        default=None,
        max_length=3000,
    )

    linkedin_url: str | None = Field(
        default=None,
        max_length=500,
    )

    github_url: str | None = Field(
        default=None,
        max_length=500,
    )

    portfolio_url: str | None = Field(
        default=None,
        max_length=500,
    )

    work_authorization: str | None = Field(
        default=None,
        max_length=250,
    )

    requires_sponsorship: bool = False
    willing_to_relocate: bool = False

    preferred_work_modes: list[str] = Field(
        default_factory=list,
        max_length=3,
    )

    target_roles: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    preferred_locations: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    minimum_salary: int | None = Field(
        default=None,
        ge=0,
        le=1_000_000,
    )

    salary_currency: str = Field(
        default="GBP",
        min_length=3,
        max_length=10,
    )

    minimum_match_score: int = Field(
        default=85,
        ge=85,
        le=100,
    )

    auto_apply_enabled: bool = False
    facts_verified: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned_value = value.strip().lower()

        if "@" not in cleaned_value:
            raise ValueError("Enter a valid email address.")

        return cleaned_value

    @field_validator(
        "full_name",
        "phone",
        "location",
        "professional_title",
        "professional_summary",
        "linkedin_url",
        "github_url",
        "portfolio_url",
        "work_authorization",
        mode="before",
    )
    @classmethod
    def clean_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned_value = value.strip()
            return cleaned_value or None

        return value

    @field_validator(
        "preferred_work_modes",
        "target_roles",
        "preferred_locations",
    )
    @classmethod
    def clean_string_lists(cls, values: list[str]) -> list[str]:
        cleaned_values: list[str] = []

        for value in values:
            cleaned_value = value.strip()

            if (
                cleaned_value
                and cleaned_value.lower()
                not in {item.lower() for item in cleaned_values}
            ):
                cleaned_values.append(cleaned_value)

        return cleaned_values

    @field_validator("salary_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()


class CandidateProfileUpsert(CandidateProfileBase):
    pass


class CandidateProfileResponse(CandidateProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime