from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


ApplicationAnswerCategory = Literal[
    "work_authorization",
    "sponsorship",
    "availability",
    "notice_period",
    "relocation",
    "remote_preference",
    "expected_salary",
    "company_interest",
    "cover_letter",
    "other",
]


class ApplicationAnswerBase(BaseModel):
    category: ApplicationAnswerCategory

    question_label: str = Field(
        min_length=2,
        max_length=300,
    )

    answer_text: str = Field(
        min_length=1,
        max_length=8000,
    )

    verified: bool = False

    manually_confirmed: bool = False

    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator(
        "question_label",
        "answer_text",
    )
    @classmethod
    def clean_required_text(
        cls,
        value: str,
    ) -> str:
        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("This field cannot be empty.")

        return cleaned_value

    @field_validator("notes", mode="before")
    @classmethod
    def clean_optional_text(
        cls,
        value: object,
    ) -> object:
        if isinstance(value, str):
            cleaned_value = value.strip()
            return cleaned_value or None

        return value


class ApplicationAnswerCreate(ApplicationAnswerBase):
    pass


class ApplicationAnswerUpdate(ApplicationAnswerBase):
    pass


class ApplicationAnswerResponse(ApplicationAnswerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_profile_id: int
    requires_manual_confirmation: bool
    created_at: datetime
    updated_at: datetime
