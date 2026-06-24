from datetime import date, datetime
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class CertificationBase(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=250,
    )

    issuing_organization: str = Field(
        min_length=2,
        max_length=250,
    )

    credential_id: str | None = Field(
        default=None,
        max_length=250,
    )

    credential_url: str | None = Field(
        default=None,
        max_length=500,
    )

    issue_date: date

    expiry_date: date | None = None

    does_not_expire: bool = False

    description: str | None = Field(
        default=None,
        max_length=3000,
    )

    skills: list[str] = Field(
        default_factory=list,
        max_length=50,
    )

    verified: bool = False

    @field_validator(
        "name",
        "issuing_organization",
    )
    @classmethod
    def clean_required_text(
        cls,
        value: str,
    ) -> str:
        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(
                "This field cannot be empty."
            )

        return cleaned_value

    @field_validator(
        "credential_id",
        "credential_url",
        "description",
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

    @field_validator("credential_url")
    @classmethod
    def validate_credential_url(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not value.startswith(
            ("http://", "https://")
        ):
            raise ValueError(
                "Credential URL must start with "
                "http:// or https://."
            )

        return value

    @field_validator("skills")
    @classmethod
    def clean_skills(
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
        if self.does_not_expire:
            self.expiry_date = None

        if (
            self.expiry_date is not None
            and self.expiry_date < self.issue_date
        ):
            raise ValueError(
                "Expiry date cannot be before "
                "the issue date."
            )

        return self


class CertificationCreate(CertificationBase):
    pass


class CertificationUpdate(CertificationBase):
    pass


class CertificationResponse(CertificationBase):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    candidate_profile_id: int
    created_at: datetime
    updated_at: datetime