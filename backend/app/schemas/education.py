from datetime import date, datetime
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class EducationBase(BaseModel):
    institution: str = Field(
        min_length=2,
        max_length=250,
    )

    degree: str = Field(
        min_length=2,
        max_length=250,
    )

    field_of_study: str | None = Field(
        default=None,
        max_length=250,
    )

    start_date: date

    end_date: date | None = None

    grade: str | None = Field(
        default=None,
        max_length=100,
    )

    location: str | None = Field(
        default=None,
        max_length=200,
    )

    description: str | None = Field(
        default=None,
        max_length=3000,
    )

    is_current: bool = False
    verified: bool = False

    @field_validator(
        "institution",
        "degree",
        "field_of_study",
        "grade",
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

    @model_validator(mode="after")
    def validate_education_dates(self) -> Self:
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


class EducationCreate(EducationBase):
    pass


class EducationUpdate(EducationBase):
    pass


class EducationResponse(EducationBase):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    candidate_profile_id: int
    created_at: datetime
    updated_at: datetime