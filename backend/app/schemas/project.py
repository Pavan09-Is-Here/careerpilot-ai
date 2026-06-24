from datetime import date, datetime
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ProjectBase(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=250,
    )

    role: str | None = Field(
        default=None,
        max_length=200,
    )

    project_type: str | None = Field(
        default=None,
        max_length=100,
    )

    description: str = Field(
        min_length=10,
        max_length=5000,
    )

    start_date: date | None = None
    end_date: date | None = None

    is_current: bool = False

    project_url: str | None = Field(
        default=None,
        max_length=500,
    )

    github_url: str | None = Field(
        default=None,
        max_length=500,
    )

    technologies: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    features: list[str] = Field(
        default_factory=list,
        max_length=50,
    )

    achievements: list[str] = Field(
        default_factory=list,
        max_length=50,
    )

    verified: bool = False

    @field_validator(
        "name",
        "description",
        mode="before",
    )
    @classmethod
    def clean_required_text(
        cls,
        value: object,
    ) -> object:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator(
        "role",
        "project_type",
        "project_url",
        "github_url",
        mode="before",
    )
    @classmethod
    def clean_optional_text(
        cls,
        value: object,
    ) -> object:
        if isinstance(value, str):
            cleaned_value = value.strip()
            return cleaned_value or None

        return value

    @field_validator(
        "project_url",
        "github_url",
    )
    @classmethod
    def validate_urls(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not value.startswith(
            ("http://", "https://")
        ):
            raise ValueError(
                "URL must start with http:// or https://"
            )

        return value

    @field_validator(
        "technologies",
        "features",
        "achievements",
    )
    @classmethod
    def clean_string_lists(
        cls,
        values: list[str],
    ) -> list[str]:
        cleaned_values: list[str] = []
        seen_values: set[str] = set()

        for value in values:
            cleaned_value = value.strip()

            if not cleaned_value:
                continue

            comparison_value = cleaned_value.lower()

            if comparison_value in seen_values:
                continue

            seen_values.add(comparison_value)
            cleaned_values.append(cleaned_value)

        return cleaned_values

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.is_current:
            self.end_date = None

        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError(
                "End date cannot be before start date."
            )

        return self


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    candidate_profile_id: int
    created_at: datetime
    updated_at: datetime
