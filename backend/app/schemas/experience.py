from datetime import date, datetime
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ExperienceBase(BaseModel):
    company: str = Field(
        min_length=2,
        max_length=250,
    )

    job_title: str = Field(
        min_length=2,
        max_length=250,
    )

    employment_type: str | None = Field(
        default=None,
        max_length=100,
    )

    location: str | None = Field(
        default=None,
        max_length=200,
    )

    start_date: date

    end_date: date | None = None

    is_current: bool = False

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    responsibilities: list[str] = Field(
        default_factory=list,
        max_length=30,
    )

    achievements: list[str] = Field(
        default_factory=list,
        max_length=30,
    )

    technologies: list[str] = Field(
        default_factory=list,
        max_length=50,
    )

    verified: bool = False

    @field_validator(
        "company",
        "job_title",
        "employment_type",
        "location",
        "description",
        mode="before",
    )
    @classmethod
    def clean_text(
        cls,
        value: object,
    ) -> object:
        if isinstance(value, str):
            cleaned_value = value.strip()
            return cleaned_value or None

        return value

    @field_validator(
        "responsibilities",
        "achievements",
        "technologies",
    )
    @classmethod
    def clean_lists(
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
            self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError(
                "End date cannot be before start date."
            )

        return self


class ExperienceCreate(ExperienceBase):
    pass


class ExperienceUpdate(ExperienceBase):
    pass


class ExperienceResponse(ExperienceBase):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    candidate_profile_id: int
    created_at: datetime
    updated_at: datetime